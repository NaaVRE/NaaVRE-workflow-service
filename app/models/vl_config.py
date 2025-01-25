

import logging


from pydantic import BaseModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class VLConfig(BaseModel):
    name: str
    wf_engine: str
    other_config: str
