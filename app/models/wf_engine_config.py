import logging

from pydantic import BaseModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class WorkflowEngineConfig(BaseModel):
    name: str
    api_endpoint: str
    access_token: str
