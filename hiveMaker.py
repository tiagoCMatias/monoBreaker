import ast
import optparse
import os
import re
import sys
from collections import defaultdict
from fnmatch import fnmatch

import networkx as nx

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
                        relations[module['module_path']].append({'name': _import.get('name', None),
                                                                        'usage': _import.get('usage', None)})
    return relations


def create_graph(relations):
    generated_graph = nx.Graph()
    for k, v in relations.items():
        for new_edge in v:
            # print("Node:{} - {} - W:{}".format(k, new_edge['name'], new_edge['usage']))
            generated_graph.add_edge(k, new_edge['name'], weight=new_edge['usage'])

    return generated_graph


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

            new_dynamic_analysis = DynamicAnalysis(db_name, directory_path)
            dynamic_analysis = new_dynamic_analysis.analise_queries()
            urls = parse_url(directory_path)
            static_relations = create_static_relations(django_analysis)

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
