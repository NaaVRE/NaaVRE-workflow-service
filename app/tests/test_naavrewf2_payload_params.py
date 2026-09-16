import pytest
from pydantic import ValidationError

from app.models.naavrewf2_payload import Naavrewf2Payload


def _base_payload():
    return {
        "virtual_lab": "openlab",
        "naavrewf2": {
            "nodes": {},
            "links": {}
        }
    }


def test_params_accepts_list_of_node_id_name_value_entries():
    payload = _base_payload()
    payload["params"] = [
        {
            "node_id": "f7418da0-788c-4fc7-a18c-45c6766a09f0",
            "name": "param_city",
            "value": "Amsterdam"
        },
        {
            "node_id": "f7418da0-788c-4fc7-a18c-45c6766a09f0",
            "name": "param_forecast_hours",
            "value": 48
        },
        {
            "node_id": "f7418da0-788c-4fc7-a18c-45c6766a09f0",
            "name": "param_include_wind",
            "value": True
        },
        {
            "node_id": "f7418da0-788c-4fc7-a18c-45c6766a09f0",
            "name": "param_optional_note",
            "value": None
        }
    ]

    model = Naavrewf2Payload(**payload)

    assert model.params is not None
    assert model.params[0].node_id == "f7418da0-788c-4fc7-a18c-45c6766a09f0"
    assert model.params[0].name == "param_city"
    assert model.params[0].value == "Amsterdam"
    assert model.params[1].value == 48
    assert model.params[2].value is True
    assert model.params[3].value is None


@pytest.mark.parametrize("missing_field", ["node_id", "name", "value"])
def test_params_rejects_entries_missing_required_fields(missing_field):
    payload = _base_payload()
    param = {
        "node_id": "f7418da0-788c-4fc7-a18c-45c6766a09f0",
        "name": "param_city",
        "value": "Amsterdam"
    }
    param.pop(missing_field)
    payload["params"] = [param]

    with pytest.raises(ValidationError) as exc_info:
        Naavrewf2Payload(**payload)

    assert f"params.0.{missing_field}" in str(exc_info.value)


def test_params_remains_optional():
    payload = _base_payload()
    model = Naavrewf2Payload(**payload)

    assert model.params is None
