from collections.abc import Mapping, Sequence
from typing import Optional, Literal
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
    template_format: Optional[str] = None
    extra_properties: Optional[Mapping[str, str]] = None


class SpecialCell(Cell):
    """A SpecialCell is a lightweight/variant of Cell and therefore inherits
    all Cell fields. Keep this class so typing that expects SpecialCell
    continues to work, but inherit from Cell instead of BaseModel.
    """
    type: Literal['splitter', 'merger']


class InternalWorkflowComponent(Cell):
    """ An InternalWorkflowComponent is a Cell that represents an internal
    workflow. It has the same fields as a Cell, but it also has an additional
    field called 'json_args_supported' which indicates whether the internal
    workflow supports JSON arguments. This field is set to True if the template
    format version of the cell is greater than or equal to the version
    specified in 'json_args_supported_version', and False otherwise.
    """
    json_args_supported: bool = False


class PortProperties(BaseModel):
    color: str
    parentNodeType: str


class Port(BaseModel):
    id: str
    type: str
    properties: PortProperties


class NodeProperties(BaseModel):
    cell: Cell | SpecialCell = Field(union_mode='left_to_right')


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
