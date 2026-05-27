from abc import abstractmethod
from collections.abc import Mapping
from typing import Optional

from jinja2 import PackageLoader, Environment, StrictUndefined
from packaging.version import Version

from app.models.naavre_wf2 import Node, InternalWorkflowComponent
from app.models.naavrewf2_payload import Naavrewf2Payload
from app.models.vl_config import VLConfig
from app.services.wf_parser import WorkflowParser

json_args_supported_version = Version('v2')


class WFEngine:
    template_env: Environment
    vl_config: VLConfig
    naavrewf2_payload: Optional[Naavrewf2Payload]
    parser: Optional[WorkflowParser]
    naavrewf2_payload_params: Optional[list]
    secrets: Optional[list]
    user_name: Optional[str]
    user_groups: Optional[list[str]]
    virtual_lab_name: Optional[str]
    nodes: Optional[Mapping[str, Node]]
    cron_schedule: Optional[str]

    def __init__(self, vl_config: VLConfig):
        loader = PackageLoader('app', 'templates')
        self.template_env = Environment(
            loader=loader,
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,
            )
        self.vl_config = vl_config
        self.naavrewf2_payload = None
        self.parser = None
        self.naavrewf2_payload_params = None
        self.secrets = None
        self.user_name = None
        self.user_groups = None
        self.virtual_lab_name = None
        self.nodes = None

    def set_payload(self, naavrewf2_payload: Naavrewf2Payload):
        self.naavrewf2_payload = naavrewf2_payload
        self.parser = WorkflowParser(naavrewf2_payload.naavrewf2)
        exceptions = []
        self.naavrewf2_payload_params = naavrewf2_payload.params
        for param in self.naavrewf2_payload_params:
            if 'value' not in param:
                exceptions.append(f"Parameter {param['value']} is "
                                  f"missing a value")
        if exceptions:
            raise ValueError("Invalid parameters: " + "; ".join(exceptions))
        self.secrets = naavrewf2_payload.secrets
        self.user_name = naavrewf2_payload.user_name
        self.user_groups = naavrewf2_payload.user_groups
        self.virtual_lab_name = naavrewf2_payload.virtual_lab
        self.nodes = self.set_json_args_supported(
            naavrewf2_payload.naavrewf2.nodes)
        self.cron_schedule = naavrewf2_payload.cron_schedule
        self.lint(naavrewf2_payload)

    @abstractmethod
    def submit(self):
        pass

    @abstractmethod
    def get_wf(self, workflow_url: str):
        pass

    @abstractmethod
    def delete_wf(self, workflow_url: str):
        pass

    @abstractmethod
    def get_wfs_for_recurring_wf(self, workflow_url: str):
        pass

    @abstractmethod
    def lint(self, workflow_payload: Naavrewf2Payload):
        pass

    def set_json_args_supported(self, nodes):
        for node_id in nodes:
            node = nodes[node_id]
            cell = InternalWorkflowComponent(
                **node.properties.cell.model_dump())
            if (cell.template_format and Version(
                    cell.template_format) >= json_args_supported_version):
                cell.json_args_supported = True
            else:
                cell.json_args_supported = False
            node.properties.cell = cell
        return nodes
