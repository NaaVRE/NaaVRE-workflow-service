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
    workflows_json_path = os.path.join(base_path, 'naavrewf2_payload')
    workflow_files = os.listdir(workflows_json_path)
    for workflow_file in workflow_files:
        workflow_path = os.path.join(workflows_json_path, workflow_file)
        with open(workflow_path) as f:
            print('Testing workflow: ' + workflow_file)
            workflow_dict = json.load(f)
        f.close()

        convert_response = client.post(
            '/convert/',
            headers={'Authorization': 'Bearer ' + user_auth_token},
            json=workflow_dict,
        )

        # Print the response for debugging
        print(convert_response.json())
        assert convert_response.status_code == 200
        assert convert_response.json() is not None
