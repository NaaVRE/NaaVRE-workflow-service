import json
import logging
import os
from datetime import datetime
from pathlib import Path
from time import sleep

from croniter import croniter
from fastapi.testclient import TestClient

from app.main import app
from app.models.naavrewf2_payload import Naavrewf2Payload

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


def get_num_of_max_parallel_tasks(workflow_dict):
    splitters = []
    for param in workflow_dict['params']:
        if 'param_max_branches' in param['name']:
            entry = {'node_id': param['node_id'], 'value': param['value']}
            splitters.append(entry)

    splitter_targets = []
    for link_id in workflow_dict['naavrewf2']['links']:
        link = workflow_dict['naavrewf2']['links'][link_id]
        for splitter in splitters:
            if ('from' in link and
                    link['from']['nodeId'] == splitter['node_id']):
                splitter['parallel_task_id'] = link['to']['nodeId']
                splitter_targets.append(splitter)

    parallel_tasks = {}
    for branch in splitter_targets:
        parallel_task_name = \
            workflow_dict['naavrewf2']['nodes'][branch['parallel_task_id']][
                'properties']['cell']['title']
        parallel_tasks[parallel_task_name] = branch['value']
    return parallel_tasks


def check_max_branch_count(wf_status_response_json=None, parallel_tasks=None):
    wf_nodes = {}
    if 'nodes' not in wf_status_response_json['status']:
        return
    for node_name in wf_status_response_json['status']['nodes']:
        node = wf_status_response_json['status']['nodes'][node_name]
        name = node['templateName']
        node_type = node['type']
        if node_type == 'TaskGroup':
            wf_nodes[name] = int(
                wf_status_response_json['status']['nodes'][node_name][
                    'progress'].split('/')[1]) - 2
    for task_name in parallel_tasks:
        for wf_nodes_name in wf_nodes:
            if task_name in wf_nodes_name:
                expected_count = parallel_tasks[task_name]
                count = wf_nodes[wf_nodes_name]
                assert count == expected_count, (f"Expected {expected_count} "
                                                 f"branches for task "
                                                 f"{task_name}, but got "
                                                 f"{count}")


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
    parallel_tasks = get_num_of_max_parallel_tasks(workflow_dict=workflow_dict)
    check_max_branch_count(wf_status_response_json=wf_status_response_json,
                           parallel_tasks=parallel_tasks)


def test_submit():
    workflow_dirs = os.path.join(base_path)
    workflow_test_files = [f.path for f in os.scandir(workflow_dirs) if
                           f.is_dir()]
    # Submit all in one loop and monitor them in a separate loop
    wf_submit_responses = []
    for workflow_test_folder in workflow_test_files:
        if 'py_conf_param_secret' not in workflow_test_folder:
            continue
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

        # Test model
        try:
            Naavrewf2Payload(**workflow_dict)
        except TypeError as ex:
            assert False, f"Error creating Naavrewf2Payload: {ex}"

        submit_response = client.post(
            '/submit/',
            headers={'Authorization': 'Bearer ' + user_auth_token},
            json=workflow_dict,
        )
        responses_dict = {'submit': {'code': 200, 'message': 'OK'}}
        responses_path = os.path.join(workflow_test_folder, 'responses.json')
        if os.path.exists(responses_path):
            with open(responses_path) as f:
                responses_dict = json.load(f)

        if submit_response.status_code != \
                responses_dict['submit']['code']:
            print(submit_response.text)

        assert submit_response.status_code == \
               responses_dict['submit']['code']
        if submit_response.status_code != 200 and \
                responses_dict['submit']['code'] != 200:
            continue
        # Check run_url that the workflow was submitted successfully
        submit_response_json = submit_response.json()
        wf_submit_responses.append(submit_response_json)

    # Monitor wf execution
    for submit_response_json in wf_submit_responses:
        run_url = submit_response_json['run_url']
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
