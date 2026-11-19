import json
import os
from pathlib import Path

from app.main import set_fdo_valid_viz_kinds_url
from app.settings.service_settings import (
    DEFAULT_FDO_VALID_VIZ_KINDS_URL,
    Settings,
)


CONFIGURATION_PATH = Path(__file__).parents[2] / "configuration.json"


def test_fdo_valid_viz_kinds_url_loaded_from_configuration(monkeypatch):
    with CONFIGURATION_PATH.open(encoding="utf-8") as configuration_file:
        configuration = json.load(configuration_file)

    monkeypatch.delenv("FDO_VALID_VIZ_KINDS_URL", raising=False)
    configured_url = configuration["fdo_valid_viz_kinds_url"]
    settings = Settings(config=configuration)

    set_fdo_valid_viz_kinds_url(
        settings.service_settings.fdo_valid_viz_kinds_url
    )

    assert os.environ["FDO_VALID_VIZ_KINDS_URL"] == configured_url


def test_fdo_valid_viz_kinds_url_defaults_when_missing(monkeypatch):
    with CONFIGURATION_PATH.open(encoding="utf-8") as configuration_file:
        configuration = json.load(configuration_file)
    configuration.pop("fdo_valid_viz_kinds_url", None)
    monkeypatch.delenv("FDO_VALID_VIZ_KINDS_URL", raising=False)
    settings = Settings(config=configuration)

    set_fdo_valid_viz_kinds_url(
        settings.service_settings.fdo_valid_viz_kinds_url
    )

    assert os.environ["FDO_VALID_VIZ_KINDS_URL"] == (
        DEFAULT_FDO_VALID_VIZ_KINDS_URL
    )
