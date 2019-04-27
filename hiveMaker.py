import optparse
import sys
import traceback

from modules.GraphMaker import GraphMaker
from modules.ModelParser import ModelParser
from modules.StaticAnalysis import StaticAnalysis
from modules.profileUtils import DynamicAnalysis

if __name__ == "__main__":

    db_name = 'Test.db'
    directory_path = 'Samples/3pl_api'

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

            model_analizer = ModelParser(directory_path)
            model_analizer.read_model_file()
            model_analizer.create_graph()
            model_analizer.cut_graph()

            static_analisys = StaticAnalysis()
            static_analisys.analyze_django_project(directory_path)

            list_of_changes = []

            for idx, graph_cut in enumerate(model_analizer.graph.list_of_graph_cuts):
                list_of_files = []
                for node in graph_cut.nodes:
                    node_file = [file for file in static_analisys.project_analysis if
                                 (node in file['module_name'] and len(file['django_models']) > 0)]
                    if node_file:
                        model_module = node_file[0]['module_path'].replace("/", ".").replace(".py", "").split(".")[-2:]
                        model_module = ".".join(model_module)
                        imports = [imports for imports in static_analisys.project_analysis if
                                   len(imports['imports']) > 0]
                        for each_import in imports:
                            for module in each_import['imports']:
                                if model_module in module['module']:
                                    list_of_files.append(model_module + ".py")
                                    m = each_import['module_path'].replace("/", ".").replace(".py", "").split(".")[-2:]
                                    m = ".".join(m)
                                    list_of_files.append(m)
                list_of_changes.append({
                    'graph_cut': graph_cut,
                    'list_of_files': sorted(set(list_of_files)) if list_of_files else None
                })

            # model_analizer.show_graph_cuts()

            urls = static_analisys.parse_url_file()
            static_relations = static_analisys.create_static_relations(django_analysis)
            new_dynamic_analysis = DynamicAnalysis(db_name, directory_path)
            dynamic_analysis = new_dynamic_analysis.calculate_model_usage(urls)

            django_model_names = [names for names in model_analizer.graph.main_graph.nodes]

            django_table_and_model_names = []

            for django_model in django_model_names:
                model_list = [static_django_model['django_models'] for static_django_model in
                              static_analisys.project_analysis if len(static_django_model['django_models']) > 0]
                model_match = [model for model in model_list if django_model.lower() == model[0]['name'].lower()]
                if model_match:
                    django_table_and_model_names.append({
                        'django_model_name': model_match[0][0]['name'],
                        'db_table': model_match[0][0]['db_table']
                    })
                    print(".")

            transform_analysis = dynamic_analysis

            for view in transform_analysis:
                for model in view['db_info']:
                    model_name = [django_name for django_name in django_table_and_model_names if
                                  django_name['db_table'].replace('"', '').lower() == model['model'].replace('"',
                                                                                                             '').lower()]
                    if model_name:
                        model['model'] = model_name[0]['django_model_name']

            model_analizer.graph.update(transform_analysis)

            system_graph = GraphMaker(dynamic_analysis)
            system_graph.make_graph()
            # system_graph.print_graph(system_graph.G)

            multiple_graphs = system_graph.split_graph(parts=2)
            system_graph.update_splitted_graph(multiple_graphs)

            for graph in multiple_graphs:
                system_graph.print_graph(graph)

            # update_relations(static_relations, urls, dynamic_analysis, django_models)

            # [view['module'].split(".")[-1] for view in urls if "SalesOrder-without" in view.get('functionCall', [])]


        except Exception as e:
            print(traceback.format_exc())
            print("error: {}".format(e))

    print("""
        Directory: {}
        Import Data: {}
        Class List: {}
    """.format(directory_path, import_list, file_info))

    print("Existing")
    sys.exit(0)
