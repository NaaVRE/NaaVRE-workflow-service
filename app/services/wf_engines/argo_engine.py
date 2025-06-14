import os
from abc import ABC

from slugify import slugify
import jinja2
import requests
import yaml

from app.models.vl_config import VLConfig
from app.services.wf_engines.wf_engine import WFEngine


def is_cron(workflow_dict):
    if workflow_dict['kind'] == 'CronWorkflow':
        return True
    return False


def include_file(env):
    def _include(name, **kwargs):
        template = env.get_template(name)
        return template.render(**kwargs)
    return _include


class ArgoEngine(WFEngine, ABC):
    workflow_template: jinja2.Template
    api_endpoint: str
    token: str

    def __init__(self, vl_config: VLConfig):
        super().__init__(vl_config)
        self.template_env.globals['include'] = include_file(self.template_env)
        self.workflow_template = self.template_env.get_template(
            'argo_workflow_top.j2')
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

    def submit(self):
        workflow_dict = self.naavrewf2_2_argo_workflow()
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
        return {'run_url': run_url, 'naavrewf2':
                self.naavrewf2_payload.naavrewf2}

    def naavrewf2_2_argo_workflow(self):
        if self.secrets:
            k8s_secret_name = self.add_secrets_to_k8s()
        else:
            k8s_secret_name = None
        workflow_name = 'n-a-a-vre-' + slugify(self.user_name)
        service_account = self.vl_config.wf_engine_config.service_account
        workdir_storage_size = (self.vl_config.
                                wf_engine_config.workdir_storage_size)

        workflow_yaml = self.workflow_template.render(
            vlab_slug=self.virtual_lab_name,
            deps_dag=self.parser.get_dependencies_dag(),
            nodes=self.nodes,
            global_params=self.params,
            k8s_secret_name=k8s_secret_name,
            workflow_name=workflow_name,
            workflow_service_account=service_account,
            workdir_storage_size=workdir_storage_size,
            cron_schedule=self.cron_schedule
        )
        workflow_dict = yaml.safe_load(workflow_yaml)
        return workflow_dict

    def get_wf(self, workflow_url: str):
        # Get the workflow status from the Argo API
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
            raise Exception('Error getting workflow status: ' + response.text)
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
