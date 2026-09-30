import logging
import os
from typing import Optional

import cachetools
import requests
from pydantic import BaseModel, field_validator
import re
from app.models.naavre_wf2 import Naavrewf2

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
MIME_RE = re.compile(
    r"^[a-zA-Z0-9][a-zA-Z0-9!#$&^_.+-]*/[a-zA-Z0-9][a-zA-Z0-9!#$&^_.+-]*$"
)


@cachetools.func.ttl_cache(ttl=6 * 3600)
def get_valid_viz_kinds():
    url = os.getenv("FDO_VALID_VIZ_KINDS_URL")
    try:
        return requests.get(url).json()
    except Exception as e:
        raise ValueError('Failed to load valid viz kinds from ' +
                         url) from e


def is_valid_mime_type(value: str) -> bool:
    return bool(MIME_RE.fullmatch(value))


class Naavrewf2Payload(BaseModel):
    virtual_lab: str
    params: Optional[list[dict[str, str]]] | None = None
    secrets: Optional[list[dict[str, str]]] | None = None
    naavrewf2: Naavrewf2
    user_name: Optional[str] | None = None
    user_groups: Optional[list[str]] | None = None
    cron_schedule: Optional[str] | None = None

    @field_validator('params')
    @classmethod
    def validate_params(cls, params):
        if params is not None:
            for param in params:
                if 'name' not in param or 'value' not in param:
                    raise ValueError(f"Invalid parameter: {param}")
                if param['name'] == 'fdo_writer_run_id':
                    # VValue mus be a valid UUID
                    uuid_regex = re.compile(r'^[0-9a-fA-F]{8}-'
                                            r'[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-'
                                            r'[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
                    if not uuid_regex.match(param['value']):
                        raise ValueError(f"Invalid UUID for fdo_writer_run_id"
                                         f": {param['value']}")
                if param['name'] == 'fdo_writer_viz_kind':
                    # Value must be a valid viz kind
                    fdo_valid_viz_kinds = get_valid_viz_kinds()
                    if param['value'] not in fdo_valid_viz_kinds:
                        raise ValueError(f"Invalid viz kind for "
                                         f"fdo_writer_viz_kind: "
                                         f"{param['value']}")
                if param['name'] == 'fdo_writer_data_format':
                    if not is_valid_mime_type(param['value']):
                        raise ValueError(f"Invalid data format for "
                                         f"fdo_writer_data_format: "
                                         f"{param['value']}")
        return params

    @field_validator('cron_schedule')
    @classmethod
    def validate_cron_schedule(cls, cron_str):
        if cron_str is not None:
            from croniter import croniter
            if not croniter.is_valid(cron_str):
                raise ValueError(f"Invalid cron schedule: {cron_str}")
        return cron_str

    def set_user_name(self, user_name: str):
        self.user_name = user_name
        return self

    def set_user_groups(self, user_groups: list[str]):
        self.user_groups = user_groups
        return self
