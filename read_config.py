#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import os
import sys
from copy import deepcopy
from locale import setlocale, LC_ALL
from re import compile as re_compile, error as re_error

from sqlalchemy import column
from yamale import make_schema, make_data, validate, YamaleError
from yamale.validators import DefaultValidators, Validator


class Set(Validator):
    """ Custom set validator """
    tag = 'set'

    def _is_valid(self, value):
        return isinstance(value, dict) and set(value.values()) == {None}


validators = DefaultValidators.copy()  # This is a dictionary
validators[Set.tag] = Set
config_schema = make_schema(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config_schema.yaml'),
                            validators=validators)


def valid_re_or_none(re_str):
    try:
        regex = re_compile(re_str)
    except re_error:
        return None
    return regex


def load_and_validate(schema, fname, strict=True):
    data = make_data(fname)
    try:
        validate(schema, data, strict)
    except YamaleError as e:
        for result in e.results:
            print('Error validating data {0} with {1}:'.format(result.data, result.schema), file=sys.stderr)
            for error in result.errors:
                print('', error, sep='\t', file=sys.stderr)
        exit(1)
    return data[0][0]


def read_config(conf_file):
    """
    import yamale

    site_schema = yamale.make_schema(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'site_schema.yaml'))
    crawl_schema = yamale.make_schema(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'crawl_schema.yaml'))
    config = load_and_validate(crawl_schema, current_task_config_filename)

    with open(conf_file, 'rb') as fh:
        config = yaml_load(fh, Loader=yaml_SafeLoader)

    """

    config = load_and_validate(config_schema, conf_file)
    setlocale(LC_ALL, config['ui-strings']['locale'])
    # Escape string for HTML
    config['ui-strings']['footer'] = config['ui-strings']['footer'].replace(r':\ ', ': ')

    if 'exluded_tables' not in config:
        config['exluded_tables'] = set()

    if 'exluded_columns' not in config:
        config['exluded_columns'] = set()

    # Overlay config
    default = config['default']
    new_fields = []
    for field in config['fields']:
        nf = deepcopy(default)
        nf.update(field)

        if len(nf.keys()) != 11:
            raise ValueError(f'Some attributes are missing for field {nf}')

        # Check for valid regexes
        if nf['regex'] and len(nf['value']) > 0 and valid_re_or_none(nf['value']) is None:
            raise ValueError('value attribute for {0} is not valid regex!'.format(nf['api_name']))

        # Check for valid regexes
        if nf['fn_regex'] and nf['fn_value'] is not None and len(nf['fn_value']) > 0 and \
                valid_re_or_none(nf['value']) is None:
            raise ValueError('fn_value attribute for {0} is not valid regex!'.format(nf['api_name']))

        # To be able to distinguish simple fields from complex ones
        simple_input = nf['table_name'] is not None
        nf['simple_input'] = simple_input
        if simple_input:
            nf['table_name'] = {nf['table_name']}

        # Bool to HTML notation
        nf['not'] = 'checked' if nf['not'] else ''
        nf['regex'] = 'checked' if nf['regex'] else ''
        nf['fn_not'] = 'checked' if nf['fn_not'] else ''
        nf['fn_regex'] = 'checked' if nf['fn_regex'] else ''
        nf['sort_key'] = 'checked' if nf['sort_key'] else ''
        new_fields.append(nf)

    # Unique API name
    if len({field['api_name'] for field in new_fields}) < len(new_fields):
        raise ValueError('api_name attribute must be unique!')

    # Exactly one sort key
    sort_keys = [field['api_name'] for field in new_fields if len(field['sort_key']) > 0]
    if len(sort_keys) != 1:
        raise ValueError('Configuration need exactly one sort_key!')
    config['default_sort_key'] = sort_keys[0]

    config['fields'] = new_fields
    config['database_uri'] = 'sqlite:///{0}'.format(config['database_name'])

    return config


def aditional_init_from_database(settings, table_objs, session):
    """Updates settings dictionary from database information"""
    selectable_tables = table_objs.keys() - settings['exluded_tables']
    selectable_tables_list = sorted(selectable_tables)
    basic_cols = {(next(iter(field['table_name'])), field['col_name']) for field in settings['fields']
                  if field['table_name'] is not None and field['col_name'] not in settings['exluded_columns']}
    # Init static variable from database also check for invalid table names
    try:
        all_elems_per_col = {(table_name, col_name):
                             sorted(x._asdict()[col_name] for x in
                                    session.query(table_objs[table_name]).select_from(table_objs[table_name]).
                                    with_entities(column(col_name)).distinct().all())
                             for table_name, col_name in basic_cols}
    except KeyError as e:
        e.args = (f'Table \'{e.args[0]}\' not found in database!',)
        raise
    # Some additional initialisations based on the SQL database
    for inp_field in settings['fields']:
        if not inp_field['simple_input']:
            inp_field['all_featelems'] = list(inp_field['featelems_aliases'].keys()) + selectable_tables_list
            invalid_alias_value = set(inp_field['featelems_aliases'].values()) - selectable_tables
            if len(invalid_alias_value) > 0:
                raise ValueError(f'Some values in featelems_aliases ({invalid_alias_value}) points to invalid table'
                                 f' names!')
        else:
            inp_field['all_featelems'] = selectable_tables_list
            table_name = next(iter(inp_field['table_name']))
            inp_field['all_elems'] = all_elems_per_col.get((table_name, inp_field['col_name']), [])
