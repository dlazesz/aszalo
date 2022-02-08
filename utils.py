#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import os

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy, inspect
from sqlalchemy import Table, MetaData

from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

from read_config import read_config, aditional_init_from_database

# TODO wire it out as parameter
settings = read_config(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml'))

app = Flask('aszalo')
app.secret_key = 'any random string'
app.config['SQLALCHEMY_DATABASE_URI'] = settings['database_uri']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.config['JSON_AS_ASCII'] = False
db = SQLAlchemy(app)

# All tables imported automatically, but we need to create a mapping from names to objects to use them easily
table_objs = {table_name: Table(table_name, MetaData(), autoload_with=db.engine)
              for table_name in inspect(db.engine).get_table_names()}
table_column_objs = {(table_name, col_obj.key): col_obj for table_name, table_obj in table_objs.items()
                     for col_obj in table_obj.columns}

# Settings are updated from the database
aditional_init_from_database(settings, table_objs, table_column_objs, db.session)


# Other ultility functions
# https://flask.palletsprojects.com/en/1.1.x/patterns/apierrors/
class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self, message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict(),)
    response.status_code = error.status_code
    return response


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


auth = HTTPBasicAuth()
"""
OR
request.environ.get('REMOTE_USER')
request.environ.pop('HTTP_X_PROXY_REMOTE_USER', None)
"""

users = {
    "john": generate_password_hash("hello"),
    "susan": generate_password_hash("bye")
}


@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username
