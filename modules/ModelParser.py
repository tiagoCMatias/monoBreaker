import json
import os
import itertools
import traceback

import networkx as nx
from matplotlib import pyplot as plt
from networkx.algorithms import community


class ModelParser:

    def __init__(self, file_path):
        self.file_path = file_path + '/models.json'
        self.entities_list = []
        self.relations_list = []
        self.graph = GraphBuilder()

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
            print(".")
        else:
            raise Exception('Unable to Locate models.json file')

    def create_graph(self):
        self.graph = GraphBuilder()
        self.graph.add_nodes(self.entities_list)
        self.graph.add_edges(self.relations_list)
        # self.graph.show_graph()

    def cut_graph(self):
        self.graph.cut_graph()

    def show_graph_cuts(self):
        for graph in self.graph.list_of_graph_cuts:
            self.graph.show_graph(graph)


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


class GraphBuilder:
    def __init__(self):
        self.main_graph = nx.Graph()
        self.list_of_graph_cuts = []


    def update(self, transform_analysis):
        update_graph = self.main_graph

        highest_node_usage = 1

        added_weight = 4

        for view in transform_analysis:
            view_max_usage = max([info['usage'] for info in view['db_info']], default=0)
            highest_node_usage = view_max_usage if highest_node_usage < view_max_usage else highest_node_usage

        for view in transform_analysis:
            update_graph.add_node(view['modules'][0], type='View')
            for info in view['db_info']:
                if update_graph.has_node(info['model']):
                    node_weight = update_graph[info['model']].get(info['model'], {}).get('weight', 1)
                    node_weight = node_weight / highest_node_usage
                    node_weight = round((node_weight * added_weight) + 1)
                    print(".")
                    update_graph.add_edge(info['model'], view['modules'][0], weight=node_weight)

        biggest_weight = sorted(update_graph.degree, key=lambda x: x[1], reverse=True)[0][1]



        print(".")

    def add_nodes(self, node_list):
        for node in node_list:
            self.main_graph.add_node(node.name)

    def add_edges(self, relation_list):
        for relation in relation_list:
            self.main_graph.add_edge(relation.origin.name, relation.destination.name, weight=relation.weight)

    def show_graph(self, graph=None, labels=True):
        if graph is None:
            graph = self.main_graph
        nx.spring_layout(graph,k=0.15,iterations=20)
        nx.draw(graph, with_labels=labels)
        plt.show()

    def cut_graph(self, graph=None):
        if graph is None:
            graph = self.main_graph
        communities_generator = community.girvan_newman(graph)

        top_level_communities = next(communities_generator)
        next_level_communities = next(communities_generator)

        self.list_of_graph_cuts = []
        for lvl_comunnity in sorted(map(sorted, next_level_communities)):
            print(".")
            new_cut = nx.Graph()
            for node in lvl_comunnity:
                new_cut.add_node(node)
            self.list_of_graph_cuts.append(new_cut)

        for cut in self.list_of_graph_cuts:
            for node in cut.nodes:
                relations = [relation for relation in graph.edges(node)]
                # relation = list(sum(relation, ()))
                for relation in relations:
                    if cut.has_node(relation[0]) and cut.has_node(relation[1]):
                        relation_weight = graph[relation[0]][relation[1]].get('weight', 0)
                        cut.add_edge(relation[1], relation[0], weigth=relation_weight)
                    else:
                        print("Missing: {}".format(relation[1] if cut.has_node(relation[0]) else relation[0]))
        return self.list_of_graph_cuts

    def print_graph(self, graph_to_print=None):
        if graph_to_print is None:
            graph_to_print = self.main_graph

        groups = set(nx.get_node_attributes(graph_to_print, 'type').values())

        mapping = dict(zip(sorted(groups), itertools.count()))
        nodes = graph_to_print.nodes()
        colors = []
        if mapping:
            colors = [mapping[graph_to_print.node[n]['type']] for n in nodes]

        pos = nx.spring_layout(graph_to_print) # nx.spring_layout(graph_to_print, k=0.15, iterations=20)  # nx.spring_layout(G)
        ec = nx.draw_networkx_edges(graph_to_print, pos, alpha=0.5)
        if colors:
            nc = nx.draw_networkx_nodes(graph_to_print, pos, nodelist=nodes, node_color=colors,
                                        with_labels=True, node_size=100, cmap=plt.cm.jet)
            plt.colorbar(nc)

        plt.axis('off')
        nx.draw(graph_to_print, with_labels=True)
        plt.show()