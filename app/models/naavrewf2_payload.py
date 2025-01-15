import logging
from typing import Literal, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Naavrewf2Payload (BaseModel):
    title: str