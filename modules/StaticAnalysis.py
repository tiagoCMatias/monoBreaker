import ast
import os
import re
from collections import defaultdict
from fnmatch import fnmatch

from modules.GraphNetwork import GraphNetwork


class StaticAnalysis:

    def __init__(self, file_pattern='*.py'):
        self.file_pattern = file_pattern
        self.project_analysis = []
        self.project_path = None
        self.urls = []

    def create_static_relations(self, module_list):
        relations = defaultdict(list)
        for module in module_list:
            for _import in module.get('imports', []):
                for _module in module_list:
                    for class_module in _module.get('classes', []):
                        # print("{} - {}".format(_import['name'] , class_module.name))
                        if _import.get('name', []) == class_module.name:
                            if len(module['django_views']) > 0:
                                relations[module['django_views'][0]['name']].append({'name': _import.get('name', None),
                                                                                     'usage': _import.get('usage',
                                                                                                          None)})
        return relations

    def analyze_django_project(self, path_of_project):
        self.project_path = path_of_project
        for path, subdirs, files in os.walk(path_of_project):
            for name in files:
                if fnmatch(name, self.file_pattern):
                    honeyMaker = HoneyMaker(os.path.join(path, name))
                    honeyMaker.parse_file()
                    self.project_analysis.append(honeyMaker.to_dict())

    def list_models(self):
        if self.project_analysis:
            return [models['django_models'][0] for models in self.project_analysis if len(models['django_models']) > 0]

    def parse_url_file(self):
        self.urls = []
        url_file = self.project_path + '/urls.txt'
        if os.path.isfile(url_file):  # True
            with open(url_file) as fp:
                line = fp.readline()
                cnt = 1
                while line:
                    # print("Line {}: {}".format(cnt, line.strip()))
                    endpoint = re.findall("[^\t]+", line.replace("\n", ""))
                    self.urls.append({
                        'name': endpoint[0],
                        'module': endpoint[1],
                        'functionCall': endpoint[2] if len(endpoint) > 2 else ''
                    })
                    line = fp.readline()
                    cnt += 1
        else:
            raise Exception("No url file provided")
        return self.urls

    def create_report(self, graph_model: GraphNetwork, analysis=None):

        if analysis:
            files = []
            for idx, cut in enumerate(graph_model.list_of_graph_cuts):

                missing_modules_in_cut = self._analyse_graph_cut(cut, graph_model.main_graph)
                instructions = []
                for missing_module in missing_modules_in_cut:
                    module_instructions = None
                    views_where_module_occurs = [view['db_info'] for view in analysis if
                                                 any(model['model'] == missing_module for model in view['db_info'])]
                    module = [y for x in views_where_module_occurs for y in x if
                              y['model'].lower() == missing_module.lower()]
                    if module:
                        if any(model_type.lower() == 'select' for model_type in module[0]['model_type']):
                            module_instructions = "Missing: {} - Model - Type: {}\n" \
                                                  "Change files requiring the model\n" \
                                                  "Possible Refactoring: \n" \
                                                  "\t - Api Composition\n" \
                                                  "\t - Synchronous Remote Call\n" \
                                                  "\t - Asynchronous Remove Call\n".format(module[0]['model'], 'Read')
                                    #module_instructions = """Model: {} - has high demand for read operations, to keep functionallity make remote calls to the service containing the model.""".format(
                                # module[0]['model'])
                        if any(model_type.lower() == 'update' for model_type in module[0]['model_type']):
                            module_instructions = "Missing: {} - Model - Type: {}\n" \
                                                  "Change files requiring the model\n" \
                                                  "Possible Refactoring: \n" \
                                                  "\t - Remote Call\n" \
                                                  "\t - Saga\n".format(module[0]['model'], 'Write')
                            # module_instructions = """Model: {} - has high demand for write operations, to keep functionallity duplicate the model and sync write operations between services""".format(
                            #    module[0]['model'])
                    if module_instructions:
                        instructions.append(module_instructions)
                files.append({
                    'graph': idx,
                    'instructions': instructions if instructions is not None else 'Everything is good'
                })

        list_of_changes = []
        list_of_graphs = graph_model.list_of_graph_cuts
        for idx, graph_cut in enumerate(list_of_graphs):
            list_of_files = []
            for node in graph_cut.nodes:
                node_file = [file for file in self.project_analysis if
                             (node in file['module_name'] and len(file['django_models']) > 0)]
                if node_file:
                    model_module = node_file[0]['module_path'].replace("/", ".").replace(".py", "").split(".")[-2:]
                    model_module = ".".join(model_module)
                    imports = [imports for imports in self.project_analysis if
                               len(imports['imports']) > 0]
                    for each_import in imports:
                        for module in each_import['imports']:
                            if model_module in module['module']:
                                list_of_files.append(model_module + ".py")
                                m = each_import['module_path'].replace("/", ".").replace(".py", "").split(".")[-2:]
                                m = ".".join(m)
                                list_of_files.append(m)
            if list_of_files:
                list_of_changes.append({
                    'graph_cut': graph_cut,
                    'graph_number': idx,
                    'list_of_files': sorted(set(list_of_files)),
                    'instructions': files[idx]['instructions'] if analysis else 'No instructions'
                })
        return list_of_changes

    def _analyse_graph_cut(self, graph_cut, original_graph):
        missing_files = []
        for node in graph_cut.nodes:
            relations = [relation for relation in original_graph.edges(node)]
            # relation = list(sum(relation, ()))
            for relation in relations:
                if graph_cut.has_node(relation[0]) and graph_cut.has_node(relation[1]):
                    relation_weight = original_graph[relation[0]][relation[1]].get('weight', 0)
                    graph_cut.add_edge(relation[1], relation[0], weigth=relation_weight)
                else:
                    print("Missing: {}".format(relation[1] if graph_cut.has_node(relation[0]) else relation[0]))
                    missing_files.append(
                        relation[1] if graph_cut.has_node(relation[0]) else relation[0]
                    )
        return missing_files


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
