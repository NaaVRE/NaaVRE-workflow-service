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

        submit_response = client.post(
            '/submit/',
            headers={'Authorization': 'Bearer ' + os.getenv('AUTH_TOKEN')},
            json=workflow_dict,
        )
        # Print the response for debugging
        print(submit_response.json())
        assert submit_response.status_code == 200
        # Check run_url that the workflow was submitted successfully
        run_url = submit_response.json()['run_url']
        assert run_url is not None

        get_wf_response = client.get(
            '/status/'+workflow_dict['virtual_lab'],
            params={'workflow_url': submit_response.json()['run_url']},
            headers={'Authorization': 'Bearer ' + os.getenv('AUTH_TOKEN')}
        )

        assert get_wf_response.status_code == 200
        get_wf_response_json = get_wf_response.json()
        if 'phase' in get_wf_response_json['status']:
            assert get_wf_response_json['status']['phase'] != 'Failed'
        print(get_wf_response_json)

        # Delete the workflow after testing
        delete_wf_response = client.delete(
            '/delete/'+workflow_dict['virtual_lab'],
            params={'workflow_url': submit_response.json()['run_url']},
            headers={'Authorization': 'Bearer ' + os.getenv('AUTH_TOKEN')}
        )
        assert delete_wf_response.status_code == 200
        delete_wf_response_json = delete_wf_response.json()
        print(delete_wf_response_json)
