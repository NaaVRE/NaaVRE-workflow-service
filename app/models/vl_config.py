import logging
from typing import Optional

from pydantic import BaseModel

from app.models.wf_engine_config import WfEngineConfig

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class VLConfig(BaseModel):
    name: str
    wf_engine_config: WfEngineConfig
    base_image_tags_url: Optional[str] = None
    module_mapping_url: Optional[str] = None
    cell_github_url: Optional[str] = None
    cell_github_token: Optional[str] = None
    registry_url: str
