import json
import os
from fastapi.testclient import TestClient

from app.main import app

if os.path.exists('resources'):
    base_path = 'resources'
elif os.path.exists('app/tests/resources/'):
    base_path = 'app/tests/resources/'
client = TestClient(app)


def test_submit():
    workflows_json_path = os.path.join(base_path)
    workflow_files = os.listdir(workflows_json_path)
    for workflow_file in workflow_files:
        workflow_path = os.path.join(workflows_json_path, workflow_file)
        with open(workflow_path) as f:
            print('Testing workflow: ' + workflow_file)
            workflow_dict = json.load(f)
        f.close()

        naavrewf2Payload_json_payload = workflow_dict.copy()
        submit_response = client.post(
            '/submit/',
            headers={'Authorization': 'Bearer ' + os.getenv('AUTH_TOKEN')},
            json=naavrewf2Payload_json_payload,
        )
        assert submit_response.status_code == 200
