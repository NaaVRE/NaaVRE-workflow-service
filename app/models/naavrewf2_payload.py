import logging
from typing import Optional

from pydantic import BaseModel, Field, StrictBool, StrictFloat, StrictInt, StrictStr

from app.models.naavre_wf2 import Naavrewf2

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class PayloadParam(BaseModel):
    node_id: str
    name: str
    value: StrictBool | StrictInt | StrictFloat | StrictStr | None = Field(
        description="Scalar/null payload value; not validated per parameter name."
    )


class Naavrewf2Payload(BaseModel):
    virtual_lab: str
    params: Optional[list[PayloadParam]] | None = None
    secrets: Optional[list] = None
    naavrewf2: Naavrewf2
    user_name: Optional[str] | None = None
    user_groups: Optional[list[str]] | None = None
    cron_schedule: Optional[str] | None = None

    def set_user_name(self, user_name: str):
        self.user_name = user_name
        return self

    def set_user_groups(self, user_groups: list[str]):
        self.user_groups = user_groups
        return self
