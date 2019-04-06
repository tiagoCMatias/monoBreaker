import ast
import optparse
import os
import re
import sys
from collections import defaultdict
from fnmatch import fnmatch

import networkx as nx


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

    def to_dict(self):
        return {
            'module_name': self.module_name,
            'module_path': self.module_path,
            'names': self.names,
            'classes': self.classes,
            'imports': self.imports,
            'import_info': self.number_of_imports
        }

    def parse_file(self):
        node = ast.parse(self.code_string)
        self.functions = [n for n in node.body if isinstance(n, ast.FunctionDef)]
        self.classes = [n for n in node.body if isinstance(n, ast.ClassDef)]

        for class_ in self.classes:
            # print("Class name:", class_.name)
            methods = [n for n in class_.body if isinstance(n, ast.FunctionDef)]
            self.class_methods = [method.name for method in methods]

        self.generic_visit(node)
        self.calculate_imports()

    def visit_ImportFrom(self, node):
        module = node.module
        for n in node.names:
            self.imports.append({
                'module': module,
                'name': n.name,  # .split('.'),
                'asname': n.asname
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


if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option("--pyfile", action="store", dest="pyfile",
                      help="Take input from a Python source file")
    (options, args) = parser.parse_args()

    import_list = []
    file_info = []
    directory_info = []

    directory_path = 'Samples/aggregation_service_api'
    urls = []

    if options.pyfile:
        # file = options.pyfile
        try:
            pattern = '*.py'
            for path, subdirs, files in os.walk(directory_path):
                for name in files:
                    if fnmatch(name, pattern):
                        honeyMaker = HoneyMaker(os.path.join(path, name))
                        honeyMaker.parse_file()
                        directory_info.append(honeyMaker.to_dict())
            url_file = directory_path + '/url.txt'
            with open(url_file) as fp:
                line = fp.readline()
                cnt = 1
                while line:
                    print("Line {}: {}".format(cnt, line.strip()))
                    endpoint = re.findall("[^\t]+", line.replace("\n", ""))
                    urls.append({
                        'name': endpoint[0],
                        'module': endpoint[1],
                        'functionCall': endpoint[2]
                    })
                    line = fp.readline()
                    cnt += 1

        except Exception as e:
            print("error: {}".format(e))

    G = nx.Graph()
    data = defaultdict(list)

    for module in directory_info:
        for _import in module.get('imports', []):
            for _module in directory_info:
                for class_module in _module.get('classes', []):
                    # print("{} - {}".format(_import['name'] , class_module.name))
                    if _import.get('name', []) == class_module.name:
                        data[module['module_name']].append({'name': _import.get('name', None),
                                                            'usage': _import.get('usage', None)})

    for k, v in data.items():
        for new_edge in v:
            # print("Node:{} - {} - W:{}".format(k, new_edge['name'], new_edge['usage']))
            G.add_edge(k, new_edge['name'], weight=new_edge['usage'])

    nx.write_gexf(G, "output/{}.gexf".format(directory_path.split("/")[1]))

    print("""
        File: {}
        Import Data: {}
        Class List: {}
    """.format(options.pyfile, import_list, file_info))

print("Existing")
sys.exit(1)
