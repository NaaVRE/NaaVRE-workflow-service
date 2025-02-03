import logging

from pydantic import BaseModel

from app.models.wf_engine_config import WorkflowEngineConfig

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class VLConfig(BaseModel):
    name: str
    wf_engine: WorkflowEngineConfig
    other_config: str
    image_registry: str
