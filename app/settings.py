from typing import List

import yaml
from pydantic_settings import BaseSettings

from app.models.vl_config import VLConfig


class WorkflowServiceSettings(BaseSettings):
    root_path: str
    debug: bool
    vl_config: List[VLConfig]


class Settings:
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.wf_service_settings = self.load_config()

    def load_config(self) -> WorkflowServiceSettings:
        """
        Load the configuration from the YAML file and parse it into VLConfig.
        """
        with open(self.config_file, 'r') as file:
            config_data = yaml.safe_load(file)
        return WorkflowServiceSettings(**config_data)
