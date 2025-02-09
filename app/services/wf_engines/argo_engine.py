import os
from abc import ABC

import requests
import yaml

from app.models.naavrewf2_payload import Naavrewf2Payload
from app.models.vl_config import VLConfig
from app.services.wf_engines.wf_engine import WFEngine


class ArgoEngine(WFEngine, ABC):

    def __init__(self, naavrewf2_payload: Naavrewf2Payload,
                 vl_config: VLConfig):
        super().__init__(naavrewf2_payload, vl_config)
        self.naavrewf2 = naavrewf2_payload.naavrewf2
        self.workflow_template = self.template_env.get_template(
            'argo_workflow.jinja2')
        # Add '/' at the end of the endpoint if not present
        if vl_config.wf_engine_config.api_endpoint[-1] != '/':
            vl_config.wf_engine_config.api_endpoint += '/'
        self.api_endpoint = (vl_config.wf_engine_config.api_endpoint +
                             "api/v1/workflows/" +
                             vl_config.wf_engine_config.namespace)
        self.token = (vl_config.wf_engine_config.access_token.replace
                      ('"', '')).replace('Bearer ', '')

    def submit(self):
        cells = self.parser.get_workflow_cells()
        parameters = []
        for _nid, cell in cells.items():
            parameters.extend(cell['params'])
        if self.secrets:
            k8s_secret_name = self.add_secrets_to_k8s()
        else:
            k8s_secret_name = None
        workflow_name = 'n-a-a-vre-' + self.user_name
        vlab_slug = self.virtual_lab_name

        service_account = self.vl_config.wf_engine_config.service_account
        workdir_storage_size = (self.vl_config.
                                wf_engine_config.workdir_storage_size)
        workflow_yaml = self.workflow_template.render(
            vlab_slug=vlab_slug,
            deps_dag=self.parser.get_dependencies_dag(),
            nodes=self.nodes,
            global_params=parameters,
            k8s_secret_name=k8s_secret_name,
            image_registry=self.vl_config.registry_url,
            workflow_name=workflow_name,
            workflow_service_account=service_account,
            workdir_storage_size=workdir_storage_size
        )
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        # Convert YAML to JSON
        workflow_dict = yaml.safe_load(workflow_yaml)
        response = requests.post(self.api_endpoint,
                                 json={"workflow": workflow_dict},
                                 headers=headers,
                                 verify=os.getenv('VERIFY_SSL', 'true').
                                 lower() == 'true')

        if response.status_code != 200:
            raise Exception('Error submitting workflow: ' + response.text)
        workflow_name = response.json()["metadata"]["name"]

        print(response.text)
        print(response.json())
        # Get the

        run_url = (self.vl_config.wf_engine_config.api_endpoint +
                   f"workflows/"
                   f"{self.vl_config.wf_engine_config.namespace}/"
                   f"{workflow_name}")
        return {'run_url': run_url, 'naavrewf2': self.naavrewf2}
