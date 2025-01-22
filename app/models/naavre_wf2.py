import logging
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Naavrewf2(BaseModel):
    offset: Optional[dict] | None = None
    scale: Optional[dict] | None = None
    nodes: dict
    links: dict
    selected: Optional[dict] | None = None
    hovered: Optional[dict] | None = None
