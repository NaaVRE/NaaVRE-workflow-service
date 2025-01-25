import logging
from typing import Optional

from pydantic import BaseModel

from app.models.naavre_wf2 import Naavrewf2

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Naavrewf2Payload(BaseModel):
    virtual_lab: str
    params: Optional[dict] | None = None
    secrets: Optional[dict] | None = None
    naavrewf2: Naavrewf2
    user_name: Optional[str] | None = None

    def set_user_name(self, user_name: str):
        self.user_name = user_name
        return self
