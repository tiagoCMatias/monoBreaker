import itertools
import re

import pandas as pd
import sqlalchemy as db
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

request_table_name = 'REQUEST'
request_csv_file = '/silk_request.csv'
sql_queries_table_name = 'SQL_QUERIES'
sql_queries_csv_file = '/silk_sqlquery.csv'


class Request(Base):
    __tablename__ = request_table_name

    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String)
    query_params = db.Column(db.String)
    raw_body = db.Column(db.String)
    body = db.Column(db.String)
    method = db.Column(db.String)
    start_time = db.Column(db.String)
    view_name = db.Column(db.String)
    end_time = db.Column(db.String)
    time_taken = db.Column(db.Float)
    encoded_headers = db.Column(db.String)
    meta_time = db.Column(db.Float)
    meta_num_queries = db.Column(db.Float)
    meta_time_spent_queries = db.Column(db.String)
    pyprofile = db.Column(db.Float)
    num_sql_queries = db.Column(db.Integer)
    prof_file = db.Column(db.Float)


class SqlQuery(Base):
    __tablename__ = sql_queries_table_name

    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String)
    start_time = db.Column(db.String)
    end_time = db.Column(db.String)
    time_taken = db.Column(db.String)
    traceback = db.Column(db.String)
    request_id = db.Column(db.String)


def parse_tables_in_query(sql_str):
    # remove the /* */ comments
    q = re.sub(r"/\*[^*]*\*+(?:[^*/][^*]*\*+)*/", "", sql_str)

    # remove whole line -- and # comments
    lines = [line for line in q.splitlines() if not re.match("^\s*(--|#)", line)]

    # remove trailing -- and # comments
    q = " ".join([re.split("--|#", line)[0] for line in lines])

    # split on blanks, parens and semicolons
    tokens = re.split(r"[\s)(;]+", q)

    # scan the tokens. if we see a FROM or JOIN, we set the get_next
    # flag, and grab the next one (unless it's SELECT).

    result = set()
    get_next = False
    for tok in tokens:
        if get_next:
            if tok.lower() not in ["", "select"]:
                result.add(tok)
            get_next = False
        get_next = tok.lower() in ["from", "join"]

    return {
        'tables': result,
        'query_type': sql_str.split(" ")[0]
    }


def parse_query_type(sql_str: str) -> str:
    return sql_str.split(" ")[0]


class DynamicAnalysis:
    def __init__(self, db_name, directory_path):
        self.engine = db.create_engine('sqlite:///' + db_name)
        self._create_database(directory_path)
        session = sessionmaker(bind=self.engine)
        self.session = session()
        self.query_analysis = []
        self.dynamic_data = []

    def extract_data(self, django_table_and_model_names):
        dynamic_data = self.dynamic_data
        for view in dynamic_data:
            for model in view['db_info']:
                model_name = [django_name for django_name in django_table_and_model_names if
                              django_name['db_table'].replace('"', '').lower() == model['model'].replace('"',
                                                                                                         '').lower()]
                if model_name:
                    model['model'] = model_name[0]['django_model_name']

    def _create_database(self, directory_path):
        conn = self.engine.connect()

        import os
        if os.path.isfile(directory_path + request_csv_file) and os.path.isfile(directory_path + sql_queries_csv_file):
            try:
                read_requests = pd.read_csv(directory_path + request_csv_file)
                read_requests.to_sql(request_table_name, conn, if_exists='replace',
                                     index=True)  # Insert the values from the csv file into the table 'REQUEST'

                read_sql_queries = pd.read_csv(directory_path + sql_queries_csv_file)
                read_sql_queries.to_sql(sql_queries_table_name, conn, if_exists='replace',
                                        index=True)  # Replace the values from the csv file into the table 'SQL_REQUESTS'
            except Exception:
                raise Exception('Cannot import files...')
        else:
            raise Exception("Missing CSVs for dynamic analysis")

    def analise_queries(self):
        requests = self.session.query(Request).distinct(Request.path).filter(Request.view_name.isnot(None)).all()
        self.query_analysis = []
        for request in requests:
            tables = []
            sql_query = self.session.query(SqlQuery).filter(SqlQuery.request_id.in_([request.id])).all()
            # print(sql_query)
            for query in sql_query:
                try:
                    tables.append(parse_tables_in_query(query.query))
                    # print(tables)
                except Exception as e:
                    print("error parsing sql: {}".format(str(e)))
            self.query_analysis.append({
                'path': request.path,
                'view_name': request.view_name,
                'tables': [item for sublist in tables for item in sublist['tables']],
                'type': [query_type['query_type'] for query_type in tables]
            })
        return self.query_analysis

    def calculate_model_usage(self, urls = None):
        self.analise_queries()
        self.dynamic_data = []
        view_names = set([view['view_name'] for view in self.query_analysis])

        for view_name in view_names:
            view_tables = [model['tables'] for model in self.query_analysis if view_name in model['view_name']]
            view_tables = [item for sublist in view_tables for item in sublist]
            db_info = []
            for db_table in [ele for ind, ele in enumerate(view_tables, 1) if ele not in view_tables[ind:]]:
                # print("{} {}".format(db_table, view_tables.count(db_table)))
                model_type = set(list(itertools.chain(*[teste['type'] for teste in self.query_analysis if
                                       any(db_table in table for table in teste['tables'])])))
                db_info.append({
                    'model': db_table,
                    'usage': view_tables.count(db_table),
                    'model_type': model_type
                })
            module_name = list(set([view['module'] for view in urls if view['functionCall'] == view_name]))
            if len(module_name) == 0:
                module_name = list(set([view['module'] for view in urls if view['module'] == view_name]))
            self.dynamic_data.append({
                'view_name': view_name,
                'modules': module_name,
                'main_module': module_name[0],
                'db_info': db_info
            })

        return self.dynamic_data
