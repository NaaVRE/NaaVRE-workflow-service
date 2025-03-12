from collections.abc import Mapping, Sequence
from typing import Optional
import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class BaseImage(BaseModel):
    build: str
    runtime: str

class Dependency(BaseModel):
    name: str
    module: Optional[str]
    asname: Optional[str]

class BaseVariable(BaseModel):
    name: str
    type: str | None

class Input(BaseVariable):
    pass

class Output(BaseVariable):
    pass

class Conf(BaseModel):
    name: str
    assignation: str

class Param(BaseVariable):
    default_value: Optional[str]

class Secret(BaseVariable):
    pass

class Cell(BaseModel):
    url: str
    title: str
    description: Optional[str]
    created: Optional[str]
    modified: Optional[str]
    owner: Optional[str]
    virtual_lab: Optional[str]
    container_image: str
    base_container_image: Optional[BaseImage]
    dependencies: Sequence[Dependency]
    inputs: Sequence[Input]
    outputs: Sequence[Output]
    confs: Sequence[Conf]
    params: Sequence[Param]
    secrets: Sequence[Secret]
    kernel: Optional[str]
    source_url: Optional[str]

class SpecialCell(Cell):
    type: str

class PortProperties(BaseModel):
    color: str
    parentNodeType: str

class Port(BaseModel):
    id: str
    type: str
    properties: PortProperties

class NodeProperties(BaseModel):
    cell: Cell

class Node(BaseModel):
    id: str
    type: str
    properties: NodeProperties
    ports: Mapping[str, Port]

class LinkOriginDestination(BaseModel):
    nodeId: str
    portId: str

class Link(BaseModel):
    id: str
    from_: LinkOriginDestination = Field(..., alias='from')
    to: LinkOriginDestination

class Naavrewf2(BaseModel):
    nodes: Mapping[str, Node]
    links: Mapping[str, Link]
