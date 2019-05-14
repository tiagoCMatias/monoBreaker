import copy
import itertools

import networkx as nx
from matplotlib import pyplot as plt
from networkx.algorithms import community


class GraphNetwork:
    def __init__(self):
        self.main_graph = nx.Graph()
        self.list_of_graph_cuts = []
        self.missing_files = []


    def update(self, transform_analysis):
        update_graph = self.main_graph

        highest_node_usage = 1
        # biggest_weight = sorted(update_graph.degree, key=lambda x: x[1], reverse=True)[0][1]
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
                    update_graph.add_edge(info['model'], view['modules'][0], weight=node_weight)

        self.main_graph = update_graph
        # return update_graph

    def add_node_list(self, node_list):
        for node in node_list:
            self.main_graph.add_node(node.name)

    def add_edge_list(self, relation_list):
        for relation in relation_list:
            self.main_graph.add_edge(relation.origin.name, relation.destination.name, weight=relation.weight)

    def show_graph(self, graph=None, labels=True):
        if graph is None:
            graph = copy.deepcopy(self.main_graph)
        nx.spring_layout(graph,k=0.15,iterations=20)
        nx.draw(graph, with_labels=labels)
        plt.show()

    def cut_graph(self, graph_to_cut: nx.Graph = None):
        if graph_to_cut is None:
            graph_to_cut = copy.deepcopy(self.main_graph)
        communities_generator = community.girvan_newman(graph_to_cut)

        top_level_communities = next(communities_generator)
        next_level_communities = next(communities_generator)

        list_of_missing_files = []

        self.list_of_graph_cuts = []
        for lvl_comunnity in sorted(map(sorted, next_level_communities)):
            new_cut = nx.Graph()
            for node in lvl_comunnity:
                new_cut.add_node(node)
            self.list_of_graph_cuts.append(new_cut)

        for cut in self.list_of_graph_cuts:
            missing_files = []
            for node in cut.nodes:
                relations = [relation for relation in graph_to_cut.edges(node)]
                # relation = list(sum(relation, ()))
                for relation in relations:
                    if cut.has_node(relation[0]) and cut.has_node(relation[1]):
                        relation_weight = graph_to_cut[relation[0]][relation[1]].get('weight', 0)
                        cut.add_edge(relation[1], relation[0], weigth=relation_weight)
                    else:
                        # print("Missing: {}".format(relation[1] if cut.has_node(relation[0]) else relation[0]))
                        missing_files.append({
                            'file': relation[1] if cut.has_node(relation[0]) else relation[0]
                        })
            list_of_missing_files.append(missing_files)
        self.missing_files = list_of_missing_files
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