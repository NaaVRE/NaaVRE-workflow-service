import base64
import json
import os
from abc import ABC
from collections import defaultdict
from functools import lru_cache

# from profiling_decorator import profile
import jinja2
import requests
import yaml
from slugify import slugify

from app.models.naavrewf2_payload import Naavrewf2Payload
from app.models.vl_config import VLConfig
from app.services.wf_engines.wf_engine import WFEngine

MAX_TASK_TITLE_LEN = 62


def build_task_title(node, node_id: str) -> str:
    is_special_node = (
            node.type == "splitter"
            or node.type == "merger"
            or node.type == "fdo-writer"
    )
    title = (
        f"{node.type}-{node.id[:7]}"
        if is_special_node
        else f"{node.properties.cell.title}-{node.id[:7]}"
    )
    return title


def is_cron(workflow_dict):
    if workflow_dict['kind'] == 'CronWorkflow':
        return True
    return False


def include_file(env):
    def _include(name, **kwargs):
        template = env.get_template(name)
        return template.render(**kwargs)
    return _include


def _base_input_name(port_name: str) -> str:
    return '_'.join(port_name.split('_')[:-1])


def _build_io_type_index(node) -> dict:
    ports = (list(node.properties.cell.inputs) +
             list(node.properties.cell.outputs))
    return {port.name: port.type for port in ports}


def _build_param_type_index(node) -> dict:
    return {port.name: port.type for port in node.properties.cell.params}


def _collect_node_items(items: list, title: str) -> list:
    node_items = []
    seen_names = set()
    for item in items:
        if ((item['to_task'] == title or item['from_task'] == title)
                and item['name'] not in seen_names):
            seen_names.add(item['name'])
            node_items.append(item)
    return node_items


def set_node_io(dependencies_dag: dict, nodes: dict,
                payload_params: list) -> dict:
    payload_params = payload_params or []
    payload_params_by_node = defaultdict(list)
    for payload_param in payload_params:
        payload_params_by_node[payload_param['node_id']].append(payload_param)

    all_parameters = []
    all_artifacts = []
    for node_id in nodes:
        node = nodes[node_id]
        title = build_task_title(node=node, node_id=node_id)
        node.properties.cell.task_title = title

        io_types = _build_io_type_index(node)
        param_types = _build_param_type_index(node)

        for dependency in dependencies_dag.get(node_id, []):
            name = dependency['from_port']
            from_task = dependency['task_name']
            from_port = dependency['from_port']
            input_name = dependency['to_port']
            input_name_base = _base_input_name(input_name)
            parameter_type = io_types.get(input_name_base)

            if dependency['type'] == 'splitter':
                with_param = (
                    f'"{{{{tasks.{from_task}.outputs.parameters.'
                    f'{from_port}}}}}"'
                )
                parameter = {'name': name,
                             'value': '"{{item}}"',
                             'withParam': with_param,
                             'to_task': title,
                             'from_task': from_task,
                             'input_parameter_name': input_name_base,
                             'input_parameter_value':
                                 f'{{{{inputs.parameters.{name}}}}}',
                             'type': parameter_type}
                all_parameters.append(parameter)
            elif node.type == 'merger':
                value = (f'"{{{{tasks.{from_task}.outputs.parameters.'
                         f'{name}}}}}"')
                parameter = {'name': name,
                             'value': value,
                             'to_task': title,
                             'from_task': from_task,
                             'input_parameter_name': input_name_base,
                             'type': parameter_type,
                             'input_parameter_value':
                                 f'{{{{inputs.parameters.{name}}}}}'}
                all_parameters.append(parameter)
            else:
                take_from = (
                    f'"{{{{tasks.{from_task}.outputs.artifacts.'
                    f'{from_port}}}}}"'
                )
                artifact = {'name': name,
                            'from': take_from,
                            'to_task': title,
                            'from_task': from_task,
                            'input_parameter_name': input_name_base,
                            'type': parameter_type}
                all_artifacts.append(artifact)

        for payload_param in payload_params_by_node.get(node_id, []):
            name = payload_param['name']
            short_id = payload_param['node_id'][:7]
            wf_param_name = f'{name}_{short_id}'
            value = f'"{{{{workflow.parameters.{wf_param_name}}}}}"'
            parameter = {'name': wf_param_name,
                         'value': value,
                         'to_task': title,
                         'from_task': wf_param_name,
                         'input_parameter_name': wf_param_name,
                         'type': param_types.get(name),
                         'input_parameter_value': value}
            all_parameters.append(parameter)

    for node_id in nodes:
        node = nodes[node_id]
        title = node.properties.cell.task_title
        node.properties.parameters = _collect_node_items(all_parameters, title)
        node.properties.artifacts = _collect_node_items(all_artifacts, title)
        nodes[node_id] = node
    return nodes


class ArgoEngine(WFEngine, ABC):
    workflow_template: jinja2.Template
    api_endpoint: str
    token: str

    def __init__(self, vl_config: VLConfig):
        super().__init__(vl_config)
        self.template_env.globals['include'] = include_file(self.template_env)
        # self.workflow_template = self.template_env.get_template(
        #     'argo_workflow_top.j2')
        self.workflow_template = self.template_env.get_template(
            'argo_workflow_artifacts_top.j2')
        # Add '/' at the end of the endpoint if not present
        if vl_config.wf_engine_config.api_endpoint[-1] != '/':
            vl_config.wf_engine_config.api_endpoint += '/'
        self.api_endpoint = (vl_config.wf_engine_config.api_endpoint +
                             "api/v1/workflows/" +
                             vl_config.wf_engine_config.namespace)
        self.api_cron_endpoint = (vl_config.wf_engine_config.api_endpoint +
                                  "api/v1/cron-workflows/" +
                                  vl_config.wf_engine_config.namespace)
        self.token = (vl_config.wf_engine_config.access_token.replace
                      ('"', '')).replace('Bearer ', '')
        self.extraVolumeMounts = vl_config.wf_engine_config.extraVolumeMounts
        self.secrets_creator_api_endpoint = (vl_config.wf_engine_config.
                                             secrets_creator_api_endpoint)
        if not self.secrets_creator_api_endpoint:
            raise Exception("secrets_creator_api_endpoint is not set in the "
                            "configuration")
        # Make sure that the secrets_creator_api_endpoint has a '/' at the end
        if not self.secrets_creator_api_endpoint.endswith('/'):
            self.secrets_creator_api_endpoint += '/'
        self.secrets_creator_api_token = (vl_config.wf_engine_config.
                                          secrets_creator_api_token)
        if not self.secrets_creator_api_token:
            raise Exception("secrets_creator_api_token is not set in the "
                            "configuration")

    @property
    def user_extra_volume_mounts(self):
        """ Returns extraVolumeMounts for the current user

        Filters extraVolumeMounts:
            - if the volumeMount has no allowedGroups, include it
            - else:
                - if the user is not a member of any groups of allowedGroups,
                  drop the volumeMount
                - else, include the volumeMount, dropping the allowedGroup
                  entry to return a k8s-compatible object.
        """
        if self.extraVolumeMounts:
            return [
                {k: v for k, v in volume_mount.items() if k != 'allowedGroups'}
                for volume_mount in self.extraVolumeMounts
                if (
                        ('allowedGroups' not in volume_mount)
                        or (
                                set(self.user_groups)
                                & set(volume_mount['allowedGroups'])
                        )
                )
                ]
        else:
            return None

    def submit(self):
        workflow_dict = self.naavrewf2_2_argo_workflow(create_secrets=True)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        if is_cron(workflow_dict):
            api_endpoint = self.api_cron_endpoint
            workflow_type = 'cronWorkflow'
            run_url_resource = 'cron-workflows'
        else:
            api_endpoint = self.api_endpoint
            workflow_type = 'workflow'
            run_url_resource = 'workflows'
        response = requests.post(api_endpoint,
                                 json={workflow_type: workflow_dict},
                                 headers=headers,
                                 verify=os.getenv('VERIFY_SSL', 'true').
                                 lower() == 'true')

        if response.status_code != 200:
            raise Exception('Error submitting workflow: ' + response.text)
        workflow_name = response.json()["metadata"]["name"]

        run_url = (self.vl_config.wf_engine_config.api_endpoint +
                   run_url_resource + "/" +
                   f"{self.vl_config.wf_engine_config.namespace}/"
                   f"{workflow_name}")
        return {'run_url': run_url,
                'naavrewf2': self.naavrewf2_payload.naavrewf2}

    @lru_cache
    def naavrewf2_2_argo_workflow(self, create_secrets: bool = True):
        if self.secrets and create_secrets:
            k8s_secret_name = self.add_secrets_to_k8s()
        else:
            k8s_secret_name = None

        workflow_name = 'n-a-a-vre-' + slugify(self.user_name)
        service_account = self.vl_config.wf_engine_config.service_account
        workdir_storage_size = (self.vl_config.
                                wf_engine_config.workdir_storage_size)
        default_max_branches = (
                    self.vl_config.wf_engine_config.default_max_branches
                    or 100)
        nodes = set_node_io(self.parser.get_dependencies_dag(),
                            self.nodes,
                            self.naavrewf2_payload_params)
        dependencies_dag = self.parser.get_dependencies_dag()
        workflow_yaml = self.workflow_template.render(
            vlab_slug=self.virtual_lab_name,
            dependencies_dag=dependencies_dag,
            nodes=nodes,
            naavrewf2_payload_params=self.naavrewf2_payload_params or [],
            k8s_secret_name=k8s_secret_name,
            workflow_name=workflow_name,
            workflow_service_account=service_account,
            workdir_storage_size=workdir_storage_size,
            cron_schedule=self.cron_schedule,
            extraVolumeMounts=self.user_extra_volume_mounts or [],
            default_max_branches=int(default_max_branches),
            shared_dir_mount='/tmp/data'
        )

        workflow_dict = yaml.safe_load(
            workflow_yaml.replace('{unescaped_username}', self.user_name))

        if os.getenv('DEBUG') == 'true':
            print("Generated Argo Workflow YAML:")
            # Save to /tmp/ for inspection
            with open(f"/tmp/{workflow_name}_workflow.yaml", "w") as f:
                f.write(workflow_yaml)
            print(yaml.dump(workflow_dict, sort_keys=False))
        return workflow_dict

    def get_pod_logs(self, workflow_url: str):
        # Get all pod names for the workflow and return their logs
        wf_nodes = self.get_wf(workflow_url=workflow_url)['status']['nodes']
        workflow_name = workflow_url.split('/')[-1]
        pod_names = []
        for node_name in wf_nodes:
            node = wf_nodes[node_name]
            if node['type'] == 'Pod':
                template_scope = node['templateScope'].replace('local/', '')
                pod_name = template_scope + '-' + node['templateName'] + node[
                    'id'].replace(template_scope, '')
                pod_names.append(pod_name)
                print(f"Getting logs for pod: {pod_name}")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        pod_log_urls = []
        for pod_name in pod_names:
            pod_log_url = f"{self.api_endpoint}/{workflow_name}/{pod_name}/log"
            pod_log_urls.append(pod_log_url)
        logs = []
        for pod_log_url in pod_log_urls:
            response = requests.get(pod_log_url, headers=headers,
                                    verify=os.getenv('VERIFY_SSL', 'true').
                                    lower() == 'true')
            if response.status_code != 200:
                raise Exception('Error getting pod logs: ' + response.text)
            logs.append(response.text)
        return logs

    def get_wf(self, workflow_url: str):
        # Get the workflow from the Argo API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        workflow_status_url = self.get_workflow_status_url(
            workflow_url=workflow_url)
        response = requests.get(workflow_status_url, headers=headers,
                                verify=os.getenv('VERIFY_SSL', 'true').
                                lower() == 'true')
        if response.status_code != 200:
            raise Exception('Error getting workflow: ' + response.text)
        return response.json()

    def delete(self, workflow_url: str):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        workflow_status_url = self.get_workflow_status_url(
            workflow_url=workflow_url)
        response = requests.delete(workflow_status_url, headers=headers,
                                   verify=os.getenv('VERIFY_SSL', 'true').
                                   lower() == 'true')
        if response.status_code != 200:
            raise Exception('Error getting workflow status: ' + response.text)
        return response.json()

    def get_workflow_status_url(self, workflow_url: str):
        """
        Extracts the workflow status URL from the provided workflow URL.
        """
        if 'cron-workflows' in workflow_url:
            api_endpoint = self.api_cron_endpoint
        else:
            api_endpoint = self.api_endpoint
        workflow_name = workflow_url.split('/')[-1]
        # If the endpoint does not have a '/' at the end, add it
        if not api_endpoint.endswith('/'):
            api_endpoint += '/'
        return api_endpoint + workflow_name

    def get_wfs_for_recurring_wf(self, workflow_url: str):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        label_selector = ("label=workflows.argoproj.io%2Fcron-workflow%3D" +
                          workflow_url.split('/')[-1])
        api_endpoint = self.api_endpoint + "?" + label_selector
        workflows_response = requests.get(api_endpoint, headers=headers,
                                          verify=os.getenv('VERIFY_SSL',
                                                           'true').lower() ==
                                          'true')
        if workflows_response.status_code != 200:
            raise Exception('Error getting workflows for recurring workflow: '
                            + workflows_response.text)
        return workflows_response.json().get('items', [])

    def add_secrets_to_k8s(self):
        body = {}
        # Assumes secures are a list of
        # [{name:secret_name,value: secret_value}]
        for secret in self.secrets:
            secret_name = secret['name']
            secret_value = secret['value']
            body[secret_name] = base64.b64encode(
                secret_value.encode()).decode()

        resp = requests.post(
            f"{self.secrets_creator_api_endpoint}",
            verify=os.getenv('VERIFY_SSL', 'true').lower() == 'true',
            headers={
                'accept': 'application/json',
                'X-Auth': self.secrets_creator_api_token,
                'Content-Type': 'application/json'
            },
            data=json.dumps(body),
        )
        resp.raise_for_status()
        secret_name = resp.json()['secretName']
        return secret_name

    def lint(self, workflow_payload: Naavrewf2Payload):
        # For now, we will just check that the workflow can be rendered
        try:
            self.naavrewf2_2_argo_workflow(create_secrets=False)
        except jinja2.exceptions.TemplateError as e:
            wf_nodes = workflow_payload.naavrewf2.nodes
            wf_links = workflow_payload.naavrewf2.links
            # Find the nodes that are not connected to any link
            connected_nodes = []
            for node_id in wf_nodes:
                for link_id in wf_links:
                    link = wf_links[link_id]
                    from_node_id = link.from_.nodeId
                    to_node_id = link.to.nodeId
                    if node_id == from_node_id or node_id == to_node_id:
                        connected_nodes.append(node_id)
                        break

            # Find the nodes that are not connected to any link
            unconnected_nodes = [node_id for node_id in wf_nodes
                                 if node_id not in connected_nodes]
            # Get the names of the unconnected nodes
            unconnected_node_names = [wf_nodes[node_id].properties.cell.title
                                      for node_id in unconnected_nodes]
            raise Exception(f"Error rendering workflow template: {str(e)}. "
                            f""f"Unconnected nodes: {unconnected_node_names}")
