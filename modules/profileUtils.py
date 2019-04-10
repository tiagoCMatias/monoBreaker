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


class DynamicAnalysis:
    def __init__(self, db_name, directory_path):
        self.engine = db.create_engine('sqlite:///' + db_name)
        self._create_database(directory_path)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def retrieve_all_request(self):
        return self.session.query(Request).filter(Request.view_name.isnot(None)).all()

    def retrieve_unique_requests(self):
        return self.session.query(Request).filter(Request.view_name.isnot(None)).all()

    def _create_database(self, directory_path):
        conn = self.engine.connect()

        read_requests = pd.read_csv(directory_path + request_csv_file)
        read_requests.to_sql(request_table_name, conn, if_exists='append',
                             index=False)  # Insert the values from the csv file into the table 'REQUEST'

        read_sql_queries = pd.read_csv(directory_path + sql_queries_csv_file)
        read_sql_queries.to_sql(sql_queries_table_name, conn, if_exists='replace',
                                index=False)  # Replace the values from the csv file into the table 'SQL_REQUESTS'

    def retrieve_queries(self):
        requests = self.session.query(Request).distinct(Request.path).filter(Request.view_name.isnot(None)).all()

        for request in requests:
            sql_query = self.session.query(SqlQuery).filter(SqlQuery.id.in_(request.id)).all()
            print(sql_query)
