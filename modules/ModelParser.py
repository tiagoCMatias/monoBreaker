import json
import os

import networkx as nx
from matplotlib import pyplot as plt

from modules.GraphNetwork import GraphNetwork


class ModelParser:

    def __init__(self, file_path):
        self.file_path = file_path + '/models.json'
        self.entities_list = []
        self.relations_list = []
        self.graph_network = GraphNetwork()

    def read_model_file(self):
        if os.path.isfile(self.file_path) :
            with open(self.file_path) as data_file:
                data = json.load(data_file)

            self.entities_list = []
            self.relations_list = []
            for graphs in data['graphs']:
                for models in graphs['models']:
                    new_entity = Entity(models['app_name'], models['name'])
                    self.entities_list.append(new_entity)
                    for relation in models['relations']:
                        target_destination = Entity(relation.get('target_app', ''), relation.get('target', ''))
                        new_relation = Relation(new_entity, target_destination)
                        self.relations_list.append(new_relation)
        else:
            raise Exception('Unable to Locate models.json file')

    def create_graph(self):
        self.graph_network = GraphNetwork()
        self.graph_network.add_node_list(self.entities_list)
        self.graph_network.add_edge_list(self.relations_list)
        # self.graph.show_graph()

    def cut_graph(self):
        self.graph_network.cut_graph()

    def show_graph(self, labels=False):
        nx.draw(self.graph_network.main_graph, with_labels=labels)
        plt.show()

    def show_graph_cuts(self):
        for graph in self.graph_network.list_of_graph_cuts:
            self.graph_network.show_graph(graph)


class Entity:
    def __init__(self, app_name, name):
        self.app_name = app_name
        self.name = name

    def to_dict(self):
        return self.name

    def to_json(self):
        return {
            "app_name": str(self.app_name),
            "name": str(self.name)
        }


class Relation:
    def __init__(self, origin: Entity, destination: Entity):
        self.origin = origin
        self.destination = destination
        self.r_type = 'AGGREGATION'
        self.weight = 1

    def to_json(self):
        return {
            "origin": str(self.origin.to_dict()),
            "destination": str(self.destination.to_dict()),
            "type": str(self.r_type),
            "weight": self.weight
        }


