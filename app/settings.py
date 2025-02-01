import json
from typing import List

from pydantic_settings import BaseSettings

from app.models.vl_config import VLConfig


class ServiceSettings(BaseSettings):
    vl_configurations: List[VLConfig]


class Settings:
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.service_settings = self.load_config()

    def load_config(self) -> ServiceSettings:
        """
        Load the configuration from the json file and parse it into VLConfig.
        """
        with open(self.config_file, 'r') as file:
            config_data = json.load(file)
        return ServiceSettings(**config_data)

    def get_vl_config(self, virtual_lab) -> VLConfig:
        for setting in self.service_settings.vl_config:
            if setting.name == virtual_lab:
                return setting
