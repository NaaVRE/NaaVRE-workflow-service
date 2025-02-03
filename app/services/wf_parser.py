import logging

from app.models.naavre_wf2 import Naavrewf2

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def is_special_node(node=None) -> bool:
    return node['type'] == 'splitter' or node['type'] == 'merger' or node[
        'type'] == 'visualizer'


class WorkflowParser:
    logger = logging.getLogger(__name__)
    nodes: dict
    links: dict
    splitters: dict
    dependencies: dict
    cells: dict

    def __init__(self, naavrewf2: Naavrewf2):

        self.nodes = naavrewf2.nodes
        self.links = naavrewf2.links
        self.dependencies = {}
        self.cells = {}
        for wf_node_id in self.nodes:
            self.dependencies[self.nodes[wf_node_id]['id']] = []
            if not is_special_node(self.nodes[wf_node_id]):
                self.cells[self.nodes[wf_node_id]['id']] = \
                    self.nodes[wf_node_id]['properties']['cell']

        # self.__parse_links()

    def __parse_links(self):
        for k in self.links:
            link = self.links[k]

            to_node = self.nodes[link['to']['nodeId']]
            from_node = self.nodes[link['from']['nodeId']]

            if not from_node:
                raise Exception('Error while parsing link: ' + link[
                    'from'] + ' from node not found')
            if 'type' not in from_node:
                raise Exception('Error while parsing link: ' + link[
                    'from'] + ' from node has no type')
            if 'id' not in from_node:
                raise Exception('Error while parsing link: ' + link[
                    'from'] + ' from node has no id')

            from_special_node = (is_special_node(from_node))

            if from_special_node:
                task_name = f'{from_node["type"]}-{from_node["id"][:7]}'
            else:
                id = self.__get_id(from_node['id'])
                print(id)
                # cell = Catalog.get_cell_from_id(id)
                # task_name = f'{cell["task_name"]}-{from_node["id"][:7]}'

            self.dependencies[to_node['id']].append({
                'task_name': task_name,
                'port_id': link['from']['portId'],
                'og_port_id': link['to']['portId'],
                'type': from_node['type']
            })

    def __get_id(self, node_id) -> str:
        return self.nodes[node_id]['properties']['id']

    def get_workflow_cells(self) -> dict:
        return self.cells

    def get_dependencies_dag(self) -> dict:
        return self.dependencies
