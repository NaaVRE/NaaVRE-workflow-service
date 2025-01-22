import base64
import json
from abc import abstractmethod

import requests
from jinja2 import PackageLoader, Environment

from app.models.naavrewf2_payload import Naavrewf2Payload
from app.services.wf_parser import WorkflowParser


class WFEngine:

    def __init__(self, naavrewf2_payload: Naavrewf2Payload, vl_config: dict):
        self.naavrewf2_payload = Naavrewf2Payload
        self.parser = WorkflowParser(naavrewf2_payload.naavrewf2)
        loader = PackageLoader('app', 'templates')
        self.template_env = Environment(loader=loader, trim_blocks=True,
                                        lstrip_blocks=True)
        self.vl_config = vl_config

    @abstractmethod
    def submit(self):
        pass

    def add_secrets_to_k8s(self, secrets):
        self.check_environment_variables()
        api_endpoint = self.vl_config['API_ENDPOINT']
        access_token = self.vl_config['NAAVRE_API_TOKEN']
        body = {
            k: base64.b64encode(v.encode()).decode()
            for k, v in secrets.items()
        }
        resp = requests.post(
            f"{api_endpoint}/api/workflows/create_secret/",
            verify=self.vl_config['VERIFY_SSL'],
            headers={
                'Authorization': f"Token {access_token}",
                'Content-Type': 'application/json'
            },
            data=json.dumps(body),
        )
        resp.raise_for_status()
        secret_name = resp.json()['secretName']
        return secret_name
