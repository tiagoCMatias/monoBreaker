import unittest
from unittest.mock import patch

from modules.ModelParser import ModelParser
from modules.StaticAnalysis import StaticAnalysis
from modules.profileUtils import DynamicAnalysis


class TestMonoBreaker(unittest.TestCase):
    def setUp(self) -> None:
        self.directory_path = '../Samples/catalogue/'

    def testDirectoryParse(self):
        project_info = ModelParser(self.directory_path)
        self.assertEqual(project_info.relations_list, [])
        self.assertEqual(project_info.entities_list, [])

    def testParseURL(self):
        project_info = ModelParser(self.directory_path)
        project_info.read_model_file()
        self.assertNotEqual(project_info.relations_list, [])
        self.assertNotEqual(project_info.entities_list, [])

    def testCreateInitGraph(self):
        project_info = ModelParser(self.directory_path)
        project_info.read_model_file()
        project_info.create_graph()
        main_graph = project_info.graph_network.main_graph
        self.assertEqual(list(main_graph.nodes), ['Category', 'Catalogue'])

    def testCutGraph(self):
        project_info = ModelParser(self.directory_path)
        self.assertEqual(project_info.graph_network.list_of_graph_cuts, [])
        project_info.read_model_file()
        project_info.create_graph()
        project_info.cut_graph()
        self.assertNotEqual(project_info.graph_network.list_of_graph_cuts, [])

    def testShowGraph(self):
        project_info = ModelParser(self.directory_path)
        project_info.read_model_file()
        project_info.create_graph()
        project_info.cut_graph()
        with patch("matplotlib.pyplot.show") as show_patch:
            project_info.show_graph()
            assert show_patch.called

    def testStaticAnalysis(self):
        static_analisys = StaticAnalysis()
        static_analisys.analyze_django_project(self.directory_path)
        urls = static_analisys.parse_url_file()
        self.assertIsInstance(urls, list)
        self.assertIsInstance(urls[0], dict)

    def testDynamicAnalysis(self):
        db_name = 'Test.db'
        static_analisys = StaticAnalysis()
        static_analisys.analyze_django_project(self.directory_path)
        urls = static_analisys.parse_url_file()
        dynamic_analysis = DynamicAnalysis(db_name, self.directory_path).calculate_model_usage(urls)
        self.assertNotEqual(dynamic_analysis, [])


if __name__ == "__main__":
    unittest.main()
