import logging
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class WfEngineConfig(BaseModel):
    name: str
    api_endpoint: str
    access_token: str
    service_account: Optional[str] | None = None
    namespace: str
    workdir_storage_size: str = '1Gi'
