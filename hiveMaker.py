import ast
import itertools
import optparse
import os
import sys
from collections import defaultdict
from fnmatch import fnmatch

import matplotlib.pyplot as plt
import networkx as nx
from networkx.algorithms.community import girvan_newman

from modules.parseUrls import parse_url
from modules.profileUtils import DynamicAnalysis


class HoneyMaker(ast.NodeVisitor):

    def __init__(self, file_path):
        self.names = []
        self.imports = []
        self.number_of_imports = {}
        self.module_path = file_path
        self.module_name = os.path.basename(file_path)
        self.code_string = open(file_path).read()
        self.functions = []
        self.classes = []
        self.class_methods = {}
        self.django_models = []
        self.django_views = []
        self.class_names = []

    def to_dict(self):
        return {
            'module_name': self.module_name,
            'module_path': self.module_path,
            'names': self.names,
            'classes': self.classes,
            'class_names': self.class_names,
            'imports': self.imports,
            'import_info': self.number_of_imports,
            'django_models': self.django_models,
            'django_views': self.django_views
        }

    @staticmethod
    def is_django_model(class_):
        if len(class_.bases) > 0:
            if isinstance(class_.bases[0], ast.Attribute):
                if "Model" is class_.bases[0].attr:
                    return True
        return False

    def parse_django_model(self, django_model):
        if hasattr(django_model, 'body'):
            for class_body in django_model.body:
                if isinstance(class_body, ast.ClassDef):
                    if "Meta" in class_body.name:
                        for model_meta_class_body in class_body.body:
                            if isinstance(model_meta_class_body, ast.Assign):
                                if model_meta_class_body.targets[0].id == 'db_table':
                                    self.django_models.append({
                                        'name': django_model.name,
                                        'db_table': model_meta_class_body.value.s
                                    })

    @staticmethod
    def is_django_view(class_):
        if len(class_.bases) > 0:
            if isinstance(class_.bases[0], ast.Name):
                if hasattr(class_.bases[0], 'id'):
                    if "viewset" in class_.bases[0].id.lower():
                        return True
        return False

    def parse_django_view(self, django_view):
        functions = [
            function for function in django_view.body if isinstance(function, ast.FunctionDef)
        ]
        self.django_views.append({
            'name': django_view.name,
            'methods': [function.name for function in functions if hasattr(function, "name")]
        })

    def parse_file(self):
        try:
            node = ast.parse(self.code_string)
            self.functions = [n for n in node.body if isinstance(n, ast.FunctionDef)]
            self.classes = [n for n in node.body if isinstance(n, ast.ClassDef)]
            self.class_names = [class_name.name for class_name in self.classes]

            for class_ in self.classes:
                if self.is_django_model(class_):
                    self.parse_django_model(class_)
                if self.is_django_view(class_):
                    self.parse_django_view(class_)

                methods = [n for n in class_.body if isinstance(n, ast.FunctionDef)]
                self.class_methods = [method.name for method in methods]

            self.generic_visit(node)
            self.calculate_imports()
        except Exception as e:
            print("Bug - {}".format(str(e)))

    def visit_ImportFrom(self, node):
        module = node.module
        for n in node.names:
            self.imports.append({
                'module': module,
                'name': n.name,  # .split('.'),
                'asname': n.asname,
                'is_model': True if any("model" in module for module in module.split(".")) else False
            })

    def visit_Name(self, node):
        if hasattr(node, 'id'):
            self.names.append({
                'class': node.id
            })

    def calculate_imports(self):
        for my_import in self.imports:
            self.number_of_imports[my_import['name']] = 0
            my_import.update({'usage': 0})

        for my_import in self.imports:
            for my_class in self.names:
                if my_class['class'] == my_import['name']:
                    my_import['usage'] += 1
                    self.number_of_imports[my_import['name']] += 1

    def get_classes(self, node):
        self.classes = [n for n in node.body if isinstance(n, ast.ClassDef)]
        for _class in self.classes:
            # print("Class name:", _class.name)
            methods = [n for n in _class.body if isinstance(n, ast.FunctionDef)]
            for method in methods:
                self.class_methods[_class.name] = method


def create_static_relations(module_list):
    relations = defaultdict(list)
    for module in module_list:
        for _import in module.get('imports', []):
            for _module in module_list:
                for class_module in _module.get('classes', []):
                    # print("{} - {}".format(_import['name'] , class_module.name))
                    if _import.get('name', []) == class_module.name:
                        if len(module['django_views']) > 0:
                            relations[module['django_views'][0]['name']].append({'name': _import.get('name', None),
                                                                                 'usage': _import.get('usage', None)})
    return relations


def create_graph(relations):
    generated_graph = nx.Graph()
    for k, v in relations.items():
        for new_edge in v:
            # print("Node:{} - {} - W:{}".format(k, new_edge['name'], new_edge['usage']))
            generated_graph.add_edge(k, new_edge['name'], weight=new_edge['usage'])

    return generated_graph


def update_relations(static_relations, urls, dynamic_analysis, django_models):
    for relation in static_relations:
        for function in [url['name'] for url in urls if relation.lower() in url['module'].split(".")[-1].lower()]:
            dynamic_data = dynamic_analysis.get(function)
            if dynamic_data:
                print(dynamic_data)


def make_graphs(dynamic_analysis):
    G = nx.Graph()

    model_names = set([])

    for view in dynamic_analysis:
        G.add_node(view['view_name'], type='View')
        for model in view['db_info']:
            model_name = model['model'].replace('"', '').replace("'", "")
            if model_name not in model_names:
                model_names.add(model['model'])
                G.add_node(model['model'], type='Model')
            G.add_edge(view['view_name'], model['model'], weight=model['usage'])
    print(".")

    groups = set(nx.get_node_attributes(G,'type').values())

    mapping = dict(zip(sorted(groups), itertools.count()))
    nodes = G.nodes()
    colors = [mapping[G.node[n]['type']] for n in nodes]

    multi_graph = []

    comp = girvan_newman(G)
    k = 4
    for communities in itertools.islice(comp, k):
        community_graph = nx.Graph()
        for names in tuple(sorted(c) for c in communities):
            for name in names:
                community_graph.add_node(name)
        multi_graph.append(community_graph)
        print(".")
    print(".")

    pos = nx.spring_layout(G)
    ec = nx.draw_networkx_edges(G, pos, alpha=0.5)
    nc = nx.draw_networkx_nodes(G, pos, nodelist=nodes, node_color=colors,
                                with_labels=True, node_size=100, cmap=plt.cm.jet)
    plt.colorbar(nc)
    plt.axis('off')
    plt.show()

    for graph in multi_graph:
        pos = nx.spring_layout(graph)
        ec = nx.draw_networkx_edges(graph, pos, alpha=0.5)
        nc = nx.draw_networkx_nodes(graph, pos, nodelist=nodes, node_color=colors,
                                    with_labels=True, node_size=100, cmap=plt.cm.jet)
        plt.colorbar(nc)
        plt.axis('off')
        plt.show()

    print("End...")
    # nx.draw(G, with_labels=True)
    # plt.show()


if __name__ == "__main__":

    db_name = 'Test.db'
    directory_path = 'Samples/core'
    file_pattern = '*.py'

    import_list = []
    file_info = []
    django_analysis = []

    parser = optparse.OptionParser()
    parser.add_option("--pyfile", action="store", dest="pyfile",
                      help="Path to Django Project")
    parser.add_option("--dbname", action="store", dest="dbname",
                      help="Input to sqlite database (Default:{})".format(db_name))
    (options, args) = parser.parse_args()

    if options.dbname:
        db_name = options.dbname

    if options.pyfile:
        try:
            for path, subdirs, files in os.walk(directory_path):
                for name in files:
                    if fnmatch(name, file_pattern):
                        honeyMaker = HoneyMaker(os.path.join(path, name))
                        honeyMaker.parse_file()
                        django_analysis.append(honeyMaker.to_dict())

            django_models = [models['django_models'][0] for models in django_analysis if
                             len(models['django_models']) > 0]
            urls = parse_url(directory_path)
            static_relations = create_static_relations(django_analysis)
            new_dynamic_analysis = DynamicAnalysis(db_name, directory_path)
            dynamic_analysis = new_dynamic_analysis.calculate_model_usage()

            # update_relations(static_relations, urls, dynamic_analysis, django_models)

            make_graphs(dynamic_analysis)
            # [view['module'].split(".")[-1] for view in urls if "SalesOrder-without" in view.get('functionCall', [])]

            G = create_graph(static_relations)

            nx.write_gexf(G, "output/{}.gexf".format(directory_path.split("/")[1]))

        except Exception as e:
            print("error: {}".format(e))

    print("""
        Directory: {}
        Import Data: {}
        Class List: {}
    """.format(directory_path, import_list, file_info))

    print("Existing")
    sys.exit(0)
