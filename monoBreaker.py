import optparse
import sys
import traceback

from modules.ModelParser import ModelParser
from modules.StaticAnalysis import StaticAnalysis
from modules.profileUtils import DynamicAnalysis


def main():
    db_name = 'Test.db'
    directory_path = 'Samples/3pl_api'

    parser = optparse.OptionParser()
    parser.add_option("--pyfile", action="store", dest="pyfile",
                      help="Path to Django Project")
    parser.add_option("--nooption", action="store", dest="nooption",
                      help="Disable user input")
    parser.add_option("--dbname", action="store", dest="dbname",
                      help="Input to sqlite database (Default:{})".format(db_name))
    (options, args) = parser.parse_args()

    if options.dbname:
        db_name = options.dbname

    if options.pyfile:
        try:

            print("Starting Static Analysis")
            model_analizer = ModelParser(directory_path)
            model_analizer.read_model_file()
            model_analizer.create_graph()
            model_analizer.cut_graph()

            static_analisys = StaticAnalysis()
            static_analisys.analyze_django_project(directory_path)

            # list_of_changes = static_analisys.create_report(model_analizer.graph_network)

            urls = static_analisys.parse_url_file()
            # static_relations = static_analisys.create_static_relations(django_analysis)

            # sorted(model_analizer.graph_network.main_graph.degree, key=lambda x: x[1], reverse=False)

            show_graph = input("show initial graph (y/n):")

            if "y" in show_graph.lower():
                print("Close the plot to continue")
                model_analizer.show_graph()

            print("Starting Dynamic Analysis")

            new_dynamic_analysis = DynamicAnalysis(db_name, directory_path)
            dynamic_analysis = new_dynamic_analysis.calculate_model_usage(urls)

            django_model_names = [names for names in model_analizer.graph_network.main_graph.nodes]

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

            transform_analysis = dynamic_analysis

            for view in transform_analysis:
                for model in view['db_info']:
                    model_name = [django_name for django_name in django_table_and_model_names if
                                  django_name['db_table'].replace('"', '').lower() == model['model'].replace('"',
                                                                                                             '').lower()]
                    if model_name:
                        model['model'] = model_name[0]['django_model_name']

            model_analizer.graph_network.update(transform_analysis)

            model_analizer.cut_graph()

            while True:
                final_options = input("Options:\n"
                                      "1: Show Updated Graph\n"
                                      "2: Show graph cuts\n"
                                      "3: Create Report\n"
                                      "4: Delete Single Nodes\n"
                                      "Other input will terminate the program\n")
                if final_options.isdigit():
                    final_options = int(final_options)
                    if final_options == 1:
                        print("Close the plot to continue")
                        model_analizer.show_graph()
                    if final_options == 2:
                        print("Close the plot to continue")
                        model_analizer.show_graph_cuts()
                    if final_options == 3:
                        final_changes = static_analisys.create_report(model_analizer.graph_network, transform_analysis)

                        files_analyzed = len(static_analisys.project_analysis)
                        django_views = [names for names in static_analisys.project_analysis if
                                        len(names['django_views']) > 0]
                        django_models = [names for names in static_analisys.project_analysis if
                                         len(names['django_models']) > 0]
                        print("Total Files: {}\n"
                              "Django_Views: {}\n"
                              "Django_Models: {}\n"
                              "".format(files_analyzed, len(django_views), len(django_models)))
                        for changes in final_changes:
                            print("GraphNumber: {}\n"
                                  "list_of_files: {}\n\n"
                                  "instructions: {}\n"
                                  "".format(changes['graph_number'], [file for file in changes['list_of_files']],
                                            [change for change in changes['instructions']]))
                    if final_options == 4:
                        model_analizer.graph_network.remove_isolated_nodes()
                        model_analizer.cut_graph()

                    if final_options == 0:
                        break

        except Exception as e:
            print(traceback.format_exc())
            print("error: {}".format(e))

    print("Existing")
    sys.exit(0)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupt received! Exiting cleanly...")