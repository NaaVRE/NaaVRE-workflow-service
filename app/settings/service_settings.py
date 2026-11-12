from typing import List

from pydantic_settings import BaseSettings

from app.models.vl_config import VLConfig


DEFAULT_FDO_VALID_VIZ_KINDS_URL = (
    "https://raw.githubusercontent.com/NaaVRE/NaaVRE-conf/refs/heads/main/"
    "fdo_valid_viz_kinds.json"
)


class ServiceSettings(BaseSettings):
    vl_configurations: List[VLConfig]
    fdo_valid_viz_kinds_url: str = DEFAULT_FDO_VALID_VIZ_KINDS_URL


class Settings:
    def __init__(self, config: dict = None):
        self.config = config
        self.service_settings = ServiceSettings(**config)

    def get_vl_config(self, virtual_lab) -> VLConfig:
        for setting in self.service_settings.vl_configurations:
            if setting.name == virtual_lab:
                return setting
