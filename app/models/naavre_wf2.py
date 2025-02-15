import logging

from pydantic import BaseModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Naavrewf2(BaseModel):
    nodes: dict
    links: dict
