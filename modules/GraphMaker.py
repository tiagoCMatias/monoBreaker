import itertools
import traceback

import networkx as nx
from matplotlib import pyplot as plt
from networkx.algorithms import community
from networkx.algorithms.community import girvan_newman


class GraphMaker:

    def __init__(self, data):
        self.data = data
        self.G = nx.Graph()

    def reset_grah(self):
        self.G = nx.Graph()

    def make_graph(self):
        model_names = set([])
        for view in self.data:
            self.G.add_node(view['main_module'], type='View')
            for model in view['db_info']:
                model_name = model['model'].replace('"', '').replace("'", "")
                if model_name not in model_names:
                    model_names.add(model['model'])
                    self.G.add_node(model['model'], type='Model')
                self.G.add_edge(view['main_module'], model['model'], weight=model['usage'])

    def graph_type(self, type, graph=None):
        if graph is None:
            graph = self.G
        return (n for n, v in graph.nodes(data=True) if v['type'].lower() == type.lower())

    def split_graph(self, graph_to_split = None, parts=1):
        if graph_to_split is None:
            graph_to_split = self.G

        multi_graph = []

        comp = girvan_newman(graph_to_split)

        def community_generator(graph):
            communities_generator = community.girvan_newman(graph)

            top_level_communities = next(communities_generator)
            next_level_communities = next(communities_generator)

            return next_level_communities # , top_level_communities

        next_level_communities = community_generator(graph_to_split)

        for lvl_comunnity in sorted(map(sorted, next_level_communities)):
            community_graph = nx.Graph()
            for node in lvl_comunnity:
                # for node in nodes:
                community_graph.add_node(node)
            for node_in_community in list(community_graph.nodes):
                try:
                    relations = [relation for relation in self.G.edges(node_in_community)]
                    for relation in relations:
                        if community_graph.has_node(relation[0]) and community_graph.has_node(relation[1]):
                            relation_weight = self.G[relation[0]][relation[1]].get('weight', 0)
                            community_graph.add_edge(node_in_community, relation, weigth=relation_weight)
                        else:
                            print("Missing: {}".format(relation[1] if community_graph.has_node(relation[0]) else relation[0]))
                except Exception as e:
                    print(traceback.format_exc())
                    print("error: {}".format(str(e)))
            # for n_comunnity in sorted(map(sorted, next_communities)):
            #    print(n_comunnity)
            multi_graph.append(community_graph)

        k = parts
        for communities in itertools.islice(comp, k):
            community_graph = nx.Graph()
            for names in tuple(sorted(c) for c in communities):
                for name in names:
                    type = 'Model' if name in self.graph_type('Model', graph_to_split) else 'View'
                    community_graph.add_node(name, type=type)
            multi_graph.append(community_graph)
        return multi_graph

    def update_splitted_graph(self, multi_graph: [nx.Graph]):
        for graph in multi_graph:
            missing_in_grap = []
            for node in graph.nodes:
                try:
                    node_info = [relation for relation in self.G.edges(node)]
                    # node_info = list(sum(node_info, ()))
                    for relation in node_info:
                        if graph.has_node(relation[0]) and graph.has_node(relation[1]):
                            relation_weight = self.G[relation[0]][relation[1]].get('weight', 0)
                            graph.add_edge(relation[0], relation[1], weight=relation_weight)
                        else:
                            missing_in_grap.append({
                                'missing': relation[1] if graph.has_node(relation[0]) else relation[0]
                            })
                except Exception as e:
                    print(traceback.format_exc())
                    print("error: {}".format(str(e)))

    def print_graph(self, graph_to_print=None):
        if graph_to_print is None:
            graph_to_print = self.G

        groups = set(nx.get_node_attributes(graph_to_print, 'type').values())

        mapping = dict(zip(sorted(groups), itertools.count()))
        nodes = graph_to_print.nodes()
        colors = []
        if mapping:
            colors = [mapping[graph_to_print.node[n]['type']] for n in nodes]

        pos = nx.spring_layout(graph_to_print, k=0.15, iterations=20)  # nx.spring_layout(G)
        ec = nx.draw_networkx_edges(graph_to_print, pos, alpha=0.5)
        if colors:
            nc = nx.draw_networkx_nodes(graph_to_print, pos, nodelist=nodes, node_color=colors,
                                        with_labels=True, node_size=100, cmap=plt.cm.jet)
            plt.colorbar(nc)

        plt.axis('off')
        nx.draw(graph_to_print, with_labels=True)
        plt.show()

    def save_to_file(self, project_path):
        nx.write_gexf(self.G, "output/{}.gexf".format(project_path.split("/")[1]))