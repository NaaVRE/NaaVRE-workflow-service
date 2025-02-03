import base64
import json
import os
from abc import abstractmethod

import requests
from jinja2 import PackageLoader, Environment

from app.models.naavrewf2_payload import Naavrewf2Payload
from app.models.vl_config import VLConfig
from app.services.wf_parser import WorkflowParser


class WFEngine:

    def __init__(self, naavrewf2_payload: Naavrewf2Payload,
                 vl_config: VLConfig):
        self.naavrewf2_payload = Naavrewf2Payload
        self.parser = WorkflowParser(naavrewf2_payload.naavrewf2)
        loader = PackageLoader('app', 'templates')
        self.template_env = Environment(loader=loader, trim_blocks=True,
                                        lstrip_blocks=True)
        self.vl_config = vl_config
        self.secrets = naavrewf2_payload.secrets
        self.user_name = naavrewf2_payload.user_name
        self.virtual_lab_name = naavrewf2_payload.virtual_lab

    @abstractmethod
    def submit(self):
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
