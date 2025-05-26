import base64
import json
import os
from abc import abstractmethod
from typing import Optional
from collections.abc import Mapping

import requests
from jinja2 import PackageLoader, Environment, StrictUndefined

from app.models.naavrewf2_payload import Naavrewf2Payload
from app.models.naavre_wf2 import Node
from app.models.vl_config import VLConfig
from app.services.wf_parser import WorkflowParser


class WFEngine:
    template_env: Environment
    vl_config: VLConfig
    naavrewf2_payload: Optional[Naavrewf2Payload]
    parser: Optional[WorkflowParser]
    secrets: Optional[dict]
    user_name: Optional[str]
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
        self.secrets = None
        self.user_name = None
        self.virtual_lab_name = None
        self.nodes = None

    def set_payload(self, naavrewf2_payload: Naavrewf2Payload):
        self.naavrewf2_payload = naavrewf2_payload
        self.parser = WorkflowParser(naavrewf2_payload.naavrewf2)
        self.secrets = naavrewf2_payload.secrets
        self.user_name = naavrewf2_payload.user_name
        self.virtual_lab_name = naavrewf2_payload.virtual_lab
        self.nodes = naavrewf2_payload.naavrewf2.nodes
        self.cron_schedule = naavrewf2_payload.cron_schedule

    @abstractmethod
    def submit(self, user_jwt: Optional[str] = None):
        pass

    @abstractmethod
    def get_wf(self, workflow_url: str, user_jwt: Optional[str] = None):
        pass

    @abstractmethod
    def delete_wf(self, workflow_url: str):
        pass

    def add_secrets_to_k8s(self):
        secrets_creator_api_endpoint = os.getenv(
            'SECRETS_CREATOR_API_ENDPOINT')
        # Make sure that the secrets_creator_api_endpoint has a '/' at the end
        if not secrets_creator_api_endpoint.endswith('/'):
            secrets_creator_api_endpoint += '/'
        secrets_creator_api_endpoint_access_token = os.getenv(
            'SECRETS_CREATOR_API_TOKEN')
        body = {}
        # Assumes secures are a dictionary of
        # secret_name: {value: secret_value}
        for secret_name, secret_value_k_v in self.secrets.items():
            body[secret_name] = base64.b64encode(
                secret_value_k_v['value'].encode()).decode()

        resp = requests.post(
            f"{secrets_creator_api_endpoint}",
            verify=os.getenv('VERIFY_SSL', 'true').lower() == 'true',
            headers={
                'accept': 'application/json',
                'X-Auth': secrets_creator_api_endpoint_access_token,
                'Content-Type': 'application/json'
            },
            data=json.dumps(body),
        )
        resp.raise_for_status()
        secret_name = resp.json()['secretName']
        return secret_name
