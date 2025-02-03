from abc import ABC

import yaml

from app.models.vl_config import VLConfig
from app.services.wf_engines.wf_engine import WFEngine


class ArgoEngine(WFEngine, ABC):

    def __init__(self, naavrewf2_payload, vl_config: VLConfig):
        super().__init__(naavrewf2_payload, vl_config)
        self.workflow_template = self.template_env.get_template(
            'argo_workflow.jinja2')

    def submit(self):
        cells = self.parser.get_workflow_cells()
        global_params = []
        for _nid, cell in cells.items():
            global_params.extend(cell['params'])
        if self.secrets:
            k8s_secret_name = self.add_secrets_to_k8s()
        else:
            k8s_secret_name = None

        workflow_name = 'n-a-a-vre-' + self.naavrewf2_payload.user_name
        vlab_slug = self.naavrewf2_payload.virtual_lab
        self.workflow_template.render(
            vlab_slug=vlab_slug,
            deps_dag=self.parser.get_dependencies_dag(),
            cells=cells,
            nodes=self.naavrewf2_payload.naavrewf2.nodes,
            global_params=global_params,
            k8s_secret_name=k8s_secret_name,
            image_repo=self.vl_config['image_repo'],
            workflow_name=workflow_name,
            workflow_service_account=self.vl_config[
                'workflow_service_account'],
            workdir_storage_size=self.vl_config['workdir_storage_size'],
        )
        workflow_doc = yaml.safe_load(self.workflow_template)

        req_body = {
            "vlab": vlab_slug,
            "workflow_payload": {
                "workflow": workflow_doc
            }
        }
        print(req_body)
        self.run_url = "https://example.org/"
        return {"run_url": self.run_url, "naavrewf2": None}
