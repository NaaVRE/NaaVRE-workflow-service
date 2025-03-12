from collections.abc import Mapping
import logging

from app.models.naavre_wf2 import Naavrewf2, Node, Link, Cell

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def is_special_node(node: Node) -> bool:
    return node.type in ['splitter', 'merger', 'visualizer']


class WorkflowParser:
    logger = logging.getLogger(__name__)
    nodes: Mapping[str, Node]
    links: Mapping[str, Link]
    splitters: dict
    dependencies: dict
    cells: dict[str, Cell]

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

            to_node_id= to_node.id[:7]
            from_node_id = from_node.id[:7]

            if is_special_node(from_node):
                task_name = f'{from_node.type}-{from_node_id}'
            else:
                task_name = (f'{from_node.properties.cell.title}-'
                             f'{from_node_id}')

            self.dependencies[to_node.id].append({
                'task_name': task_name,
                'port_id': f'{link.from_.portId}_{from_node_id}',
                'og_port_id': f'{link.to.portId}_{to_node_id}',
                'type': from_node.type
            })

    def get_workflow_cells(self) -> Mapping[str, Cell]:
        return self.cells

    def get_dependencies_dag(self) -> dict:
        return self.dependencies
