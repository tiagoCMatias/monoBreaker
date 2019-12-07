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

    def update_static_relations(self, static_relations):
        for view in static_relations:
            for model in static_relations[view]:
                e = list(map(lambda x: x['name'] == model['name'], [e.to_json() for e in self.entities_list]))
                t = [i for i, x in enumerate(e) if x]
                view_entity = Entity(app_name=view, name=view)
                if t:
                    new_relation = Relation(origin=view_entity, destination=self.entities_list[t[0]], weight=model['usage'])
                    self.graph_network.add_node_list([view_entity])
                    self.graph_network.add_edge_list([new_relation])
                    self.entities_list.append(view_entity)
                    self.relations_list.append(new_relation)

    def read_model_file(self):
        if os.path.isfile(self.file_path):
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

    def show_graph(self, labels=False, savefig=False):
        pos = nx.spring_layout(self.graph_network.main_graph)
        if labels:
            nx.draw_networkx_labels(self.graph_network.main_graph, pos=pos, font_size=10)
            nx.draw_networkx(self.graph_network.main_graph, with_labels=labels)
        else:
            nx.draw_networkx(self.graph_network.main_graph, with_labels=False)
        if savefig:
            plt.savefig("Graph.png", format="PNG")
        plt.show()

    def save_graph_cuts(self):
        for idx, graph_cut in enumerate(self.graph_network.list_of_graph_cuts):
            pos = nx.spring_layout(graph_cut, k=0.25, iterations=50)
            nx.draw_networkx_labels(graph_cut, pos=pos, font_size=10)
            nx.draw_networkx(graph_cut, with_labels=True)
            plt.savefig("graph_cut_{}.png".format(idx), format="PNG")
            plt.show()

    def show_graph_cuts(self):
        for graph in self.graph_network.list_of_graph_cuts:
            self.graph_network.show_graph(graph)

    def create_cuts_gelphi(self):
        for idx, graph in enumerate(self.graph_network.list_of_graph_cuts):
            nx.write_gexf(graph, "output/graph_{}.gexf".format(idx))
            self.graph_network.show_graph(graph)
        nx.write_gexf(self.graph_network.main_graph, "output/graph_main.gexf")

    def create_main_graph_gephi(self):
        nx.write_gexf(self.graph_network.main_graph, "output/graph_main.gexf")


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
    def __init__(self, origin: Entity, destination: Entity, weight=1):
        self.origin = origin
        self.destination = destination
        self.r_type = 'AGGREGATION'
        self.weight = weight

    def to_json(self):
        return {
            "origin": str(self.origin.to_dict()),
            "destination": str(self.destination.to_dict()),
            "type": str(self.r_type),
            "weight": self.weight
        }
