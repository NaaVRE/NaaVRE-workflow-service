from pathlib import Path
import json
import logging
import os

from fastapi.testclient import TestClient

from app.main import app

if os.path.exists('resources'):
    base_path = 'resources'
elif os.path.exists('app/tests/resources/'):
    base_path = 'app/tests/resources/'
client = TestClient(app)
logger = logging.getLogger(__name__)
tests_resources_dir = Path(__file__).parent / "resources"

user_auth_token = os.getenv('AUTH_TOKEN')


def test_convert():
    workflow_dirs = os.path.join(base_path)
    workflow_test_files = [f.path for f in os.scandir(workflow_dirs) if
                           f.is_dir()]
    for workflow_test_folder in workflow_test_files:
        print('Testing workflow: ' + workflow_test_folder)
        workflow_payload_path = os.path.join(workflow_test_folder,
                                             'wf_payload.json')
        with open(workflow_payload_path) as f:
            workflow_dict = json.load(f)
        workflow_file_path = os.path.join(workflow_test_folder, 'wf.naavrewf')
        with open(workflow_file_path) as f:
            workflow_file = json.load(f)
        nodes = workflow_file['chart']['nodes']
        links = workflow_file['chart']['links']

        workflow_dict['naavrewf2']['nodes'] = nodes
        workflow_dict['naavrewf2']['links'] = links

        convert_response = client.post(
            '/convert/',
            headers={'Authorization': 'Bearer ' + user_auth_token},
            json=workflow_dict,
        )

        responses_dict = {'convert': {'code': 200, 'message': 'OK'}}
        responses_path = os.path.join(workflow_test_folder, 'responses.json')
        if os.path.exists(responses_path):
            with open(responses_path) as f:
                responses_dict = json.load(f)

        if convert_response.status_code != \
                responses_dict['convert']['code']:
            print(convert_response.text)

        assert convert_response.status_code == \
               responses_dict['convert']['code']
        if convert_response.status_code != 200 and \
                responses_dict['convert']['code'] != 200:
            continue
