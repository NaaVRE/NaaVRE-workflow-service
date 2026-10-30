from app.services.wf_engines.argo_engine import _collect_node_items


def test_collect_node_items_preserves_distinct_input_bindings():
    items = [
        {
            'name': 'shared_output',
            'to_task': 'consumer',
            'from_task': 'producer',
            'input_parameter_name': 'first_input',
        },
        {
            'name': 'shared_output',
            'to_task': 'consumer',
            'from_task': 'producer',
            'input_parameter_name': 'second_input',
        },
    ]

    collected = _collect_node_items(items, 'consumer')

    assert len(collected) == 1
    assert collected[0]['input_parameter_names'] == [
        'first_input',
        'second_input',
    ]
