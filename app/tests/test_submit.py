import json
import logging
import os
from datetime import datetime
from pathlib import Path
from time import sleep

from croniter import croniter
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


def check_recurring_workflow(workflow_dict=None, run_url=None):
    schedule = workflow_dict['cron_schedule']
    base_time = datetime.now()
    cron = croniter(schedule, base_time)
    next_execution_time = cron.get_next(datetime)
    # If next_execution_time is more than 5 minutes in the future, skip waiting
    # and checking the workflow status
    if (next_execution_time - datetime.now()).total_seconds() < 300:
        while datetime.now() < next_execution_time:
            # Sleep until the scheduled execution time
            sleep_time = next_execution_time - datetime.now()
            if sleep_time.total_seconds() > 0:
                sleep(
                    sleep_time.total_seconds() + 5)
        # Check the workflow status after the scheduled execution time
        wf_status_response = client.get(
            '/status_recurring_wf/' + workflow_dict['virtual_lab'],
            params={'workflow_url': run_url},
            headers={'Authorization': 'Bearer ' + user_auth_token}
        )
        assert wf_status_response.status_code == 200
        wf_status_response_json = wf_status_response.json()
        assert 'active' in wf_status_response_json['status']
        for workflow_url in wf_status_response_json['workflows_urls']:
            wf_status_response = client.get(
                '/status/' + workflow_dict['virtual_lab'],
                params={'workflow_url': workflow_url},
                headers={'Authorization': 'Bearer ' + user_auth_token}
            )
            assert wf_status_response.status_code == 200
            wf_status_response_json = wf_status_response.json()
            assert wf_status_response_json['status']['phase'] != 'Failed'
            assert wf_status_response_json['status']['phase'] != 'Error'
            wait_for_wf(wf_status_response_json=wf_status_response_json,
                        workflow_dict=workflow_dict,
                        run_url=workflow_url)


def wait_for_wf(wf_status_response_json=None, workflow_dict=None,
                run_url=None):
    print(wf_status_response_json['status']['phase'])
    while 'Running' in wf_status_response_json['status']['phase'] or \
            'Pending' in wf_status_response_json['status']['phase']:
        sleep(5)
        wf_status_response = client.get(
            '/status/' + workflow_dict['virtual_lab'],
            params={'workflow_url': run_url},
            headers={'Authorization': 'Bearer ' + user_auth_token}
        )
        assert wf_status_response.status_code == 200
        wf_status_response_json = wf_status_response.json()
    assert wf_status_response_json['status']['phase'] != 'Failed'
    assert wf_status_response_json['status']['phase'] != 'Error'


def test_submit():
    workflows_json_path = os.path.join(base_path, 'naavrewf2_payload')
    workflow_files = os.listdir(workflows_json_path)
    for workflow_file in workflow_files:
        workflow_path = os.path.join(workflows_json_path, workflow_file)
        with open(workflow_path) as f:
            print('Testing workflow: ' + workflow_file)
            workflow_dict = json.load(f)
        f.close()

        submit_response = client.post(
            '/submit/',
            headers={'Authorization': 'Bearer ' + user_auth_token},
            json=workflow_dict,
        )

        # Print the response for debugging
        print(submit_response.json())
        assert submit_response.status_code == 200
        # Check run_url that the workflow was submitted successfully
        run_url = submit_response.json()['run_url']
        assert run_url is not None

        wf_status_response = client.get(
            '/status/' + workflow_dict['virtual_lab'],
            params={'workflow_url': run_url},
            headers={'Authorization': 'Bearer ' + user_auth_token}
        )

        assert wf_status_response.status_code == 200
        wf_status_response_json = wf_status_response.json()
        if 'phase' in wf_status_response_json['status']:
            assert wf_status_response_json['status']['phase'] != 'Failed'
            assert wf_status_response_json['status']['phase'] != 'Error'
            wait_for_wf(wf_status_response_json=wf_status_response_json,
                        workflow_dict=workflow_dict,
                        run_url=run_url)
        if ('cron_schedule' in workflow_dict and
                workflow_dict['cron_schedule'] is not None):
            check_recurring_workflow(workflow_dict=workflow_dict,
                                     run_url=run_url)
        wf_delete_response = client.delete(
            '/delete/' + workflow_dict['virtual_lab'],
            params={'workflow_url': run_url},
            headers={'Authorization': 'Bearer ' + user_auth_token}
        )
        assert wf_delete_response.status_code == 200
        delete_wf_response_json = wf_delete_response.json()
        print(delete_wf_response_json)
        assert delete_wf_response_json['status'] == 'deleted'
