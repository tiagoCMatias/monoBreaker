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

    return result


from itertools import groupby


def canonicalize_dict(x):
    "Return a (key, value) list sorted by the hash of the key"
    return sorted(x.items(), key=lambda x: hash(x[0]))


def unique_and_count(lst):
    "Return a list of unique dicts with a 'count' key added"
    grouper = groupby(sorted(map(canonicalize_dict, lst)))
    return [dict(k + [("count", len(list(g)))]) for k, g in grouper]


class DynamicAnalysis:
    def __init__(self, db_name, directory_path):
        self.engine = db.create_engine('sqlite:///' + db_name)
        self._create_database(directory_path)
        session = sessionmaker(bind=self.engine)
        self.session = session()
        self.query_analysis = []

    def _create_database(self, directory_path):
        conn = self.engine.connect()

        import os
        if os.path.isfile(directory_path + request_csv_file) and os.path.isfile(directory_path + sql_queries_csv_file):
            read_requests = pd.read_csv(directory_path + request_csv_file)
            read_requests.to_sql(request_table_name, conn, if_exists='append',
                                 index=False)  # Insert the values from the csv file into the table 'REQUEST'

            read_sql_queries = pd.read_csv(directory_path + sql_queries_csv_file)
            read_sql_queries.to_sql(sql_queries_table_name, conn, if_exists='replace',
                                    index=False)  # Replace the values from the csv file into the table 'SQL_REQUESTS'
        else:
            raise Exception("Missing CSVs for dynamic analysis")

    def analise_queries(self):
        requests = self.session.query(Request).distinct(Request.path).filter(Request.view_name.isnot(None)).all()
        self.query_analysis = []
        for request in requests:
            tables = []
            sql_query = self.session.query(SqlQuery).filter(SqlQuery.id.in_(request.id)).all()
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
                'tables': [item for sublist in tables for item in sublist]
            })
        return self.query_analysis

    def calculate_model_usage(self):
        self.analise_queries()
        view_info = {}
        view_names = set([view['view_name'] for view in self.query_analysis])

        for view_name in view_names:
            view_tables = [model['tables'] for model in self.query_analysis if view_name in model['view_name']]
            view_tables = [item for sublist in view_tables for item in sublist]
            db_info = []
            for db_table in [ele for ind, ele in enumerate(view_tables, 1) if ele not in view_tables[ind:]]:
                print("{} {}".format(db_table, view_tables.count(db_table)))
                db_info.append({
                    'model': db_table,
                    'usage': view_tables.count(db_table)
                })
            view_info[view_name.split(".")[-1]] = db_info

        return view_info
