from collections.abc import Mapping
import logging

from app.models.naavre_wf2 import Naavrewf2, Node, Link, Cell, SpecialCell

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

MAX_TASK_TITLE_LEN = 62


def is_special_node(node: Node) -> bool:
    return node.type in ['splitter', 'merger']


def build_task_title(node: Node) -> str:
    node_id = node.id[:7]
    suffix = f'-{node_id}'
    base_title = node.type if is_special_node(node) else (
        node.properties.cell.title)
    max_base_len = MAX_TASK_TITLE_LEN - len(suffix)
    return f'{base_title[:max_base_len]}{suffix}'


class WorkflowParser:
    logger = logging.getLogger(__name__)
    nodes: Mapping[str, Node]
    links: Mapping[str, Link]
    splitters: dict
    dependencies: dict
    cells: dict[str, Cell | SpecialCell]

    def __init__(self, naavrewf2: Naavrewf2):

        self.nodes = naavrewf2.nodes
        self.links = naavrewf2.links
        self.dependencies = {}
        self.cells = {}
        for node_id, node in self.nodes.items():
            self.dependencies[node.id] = []
            if not is_special_node(node):
                self.cells[node.id] = node.properties.cell

        self.__parse_links()

    def __parse_links(self):
        for k in self.links:
            link = self.links[k]

            to_node = self.nodes[link.to.nodeId]
            from_node = self.nodes[link.from_.nodeId]

            to_node_id = to_node.id[:7]
            from_node_id = from_node.id[:7]

            task_name = build_task_title(from_node)

            self.dependencies[to_node.id].append({
                'task_name': task_name,
                'from_port': f'{link.from_.portId}_{from_node_id}',
                'to_port': f'{link.to.portId}_{to_node_id}',
                'type': from_node.type
            })

    def get_workflow_cells(self) -> Mapping[str, Cell | SpecialCell]:
        return self.cells

    def get_dependencies_dag(self) -> dict:
        return self.dependencies
