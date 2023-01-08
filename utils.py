#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from pathlib import Path
from secrets import compare_digest
from json import dumps as json_dumps
from contextlib import contextmanager

from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import Request, Response, HTTPException, Depends, FastAPI
from jinja2 import FileSystemLoader, Environment


from sqlalchemy.orm import sessionmaker
from sqlalchemy import Table, MetaData, inspect, create_engine

from read_config import read_config, aditional_init_from_database

# TODO wire it out as parameter
JINJA_TEMPLATES_DIR = 'templates'
CONFIG_FILE_PATH = Path(__file__).parent / 'config.yaml'

settings = read_config(CONFIG_FILE_PATH)

app = FastAPI(title='aszalo')

engine = create_engine(settings['database_uri'], connect_args={'check_same_thread': False}, echo=False)
SessionLocal = sessionmaker(autoflush=False, bind=engine)

@contextmanager
def get_db():
    """Dependency vs. contextmanager
       INFO: https://fastapi.tiangolo.com/tutorial/sql-databases/#create-a-dependency
       INFO: https://docs.python.org/3/library/contextlib.html#contextlib.contextmanager
    """
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


# All tables imported automatically, but we need to create a mapping from names to objects to use them easily
table_objs = {table_name: Table(table_name, MetaData(), autoload_with=engine)
              for table_name in inspect(engine).get_table_names()}
table_column_objs = {(table_name, col_obj.key): col_obj for table_name, table_obj in table_objs.items()
                 for col_obj in table_obj.columns}

# Settings are updated from the database
with get_db() as db:
    aditional_init_from_database(settings, table_objs, table_column_objs, db)


def jinja2_env_factory(templates_directory):
    """ Create a render_template() with pure JINJA2 to be as modular as possible
        INFO: https://jinja.palletsprojects.com/en/3.1.x/api/
    """
    env = Environment(loader=FileSystemLoader(templates_directory), autoescape=True)
    def render_template_fun(template_name, **variables_dict):
        template = env.get_template(template_name)
        return template.render(**variables_dict)

    return render_template_fun

render_template = jinja2_env_factory(JINJA_TEMPLATES_DIR)


class InvalidUsage(Exception):
    """INFO: https://fastapi.tiangolo.com/tutorial/handling-errors/#install-custom-exception-handlers"""
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        super().__init__(self, message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


@app.exception_handler(InvalidUsage)
async def exception_handler(_: Request, exc: InvalidUsage):
    """INFO: https://fastapi.tiangolo.com/tutorial/handling-errors/#install-custom-exception-handlers"""
    result_json = json_dumps(exc.to_dict(), ensure_ascii=False, indent=4)
    return Response(result_json, exc.status_code, media_type='application/json')


def str2bool(v, missing=False):
    """
    Original code from:
     https://stackoverflow.com/questions/15008758/parsing-boolean-values-with-argparse/43357954#43357954
    """
    if v.lower() in {'yes', 'true', 't', 'y', '1'}:
        return True
    elif v.lower() in {'no', 'false', 'f', 'n', '0'}:
        return False
    else:
        return missing


users = {
    "john": "hello",
    "susan": "bye"
}


security = HTTPBasic()
"""
OR
request.environ.get('REMOTE_USER')
request.environ.pop('HTTP_X_PROXY_REMOTE_USER', None)
"""

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    """INFO: https://fastapi.tiangolo.com/advanced/security/http-basic-auth/"""
    if credentials.username in users and \
        compare_digest(users.get(credentials.username), credentials.password):
        return credentials.username

    raise HTTPException(
        status_code=401,
        detail='Incorrect email or password',
        headers={'WWW-Authenticate': 'Basic'},
    )
