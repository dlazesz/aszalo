#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import sys
import itertools
from pathlib import Path
from copy import deepcopy
from argparse import ArgumentParser, FileType

from yamale import make_schema, make_data, validate, YamaleError
from sqlalchemy import create_engine, MetaData, Table, Column, ForeignKey, String, Integer, Float, text

col_types_to_sql_types = {'str': (str, String), 'int': (int, Integer), 'float': (float, Float), 'none': (None, None)}


def check_config_and_header(header, config):

    # Check the header
    header_new = {col_name.lower() for col_name in header if len(col_name) > 0}
    len_header_new = len(header_new)
    if len(header) != len_header_new:
        raise ValueError(f'Empty or matching (case insensitively) column names found'
                         f' in input file header: ({header}) !')

    if len_header_new != len(config['columns']):
        raise ValueError(f'The number of column in input file\'s header ({len(header)})'
                         f' does not matches the number of columns defined in the config ({len(config["columns"])}) !')

    # Create lookup table for header-config column order synchronization
    header_to_no = {col_name: no for no, col_name in enumerate(header)}
    # Init list for random access
    new_columns = [None]*len_header_new

    # Init helpers
    has_main_table_col = False
    col_names, sep_sql_col_names, main_sql_col_names = set(), set(), []
    main_sql_table_names, sep_sql_table_names, sep_col_types = set(), set(), set()
    main_sql_table_name = None

    # Overlay config
    default = config['default']
    for column in config['columns']:
        nc = deepcopy(default)
        nc.update(column)

        if not nc.get('column_name', False):
            raise ValueError(f'column_name must be set for column {nc} !')

        if not nc.get('separate', False):
            has_main_table_col = True  # Separate false or not set -> main table column
        else:  # Separate column, should have no table_name set
            if nc.get('table_name', False):
                raise ValueError(f'table_name must be omitted as it will be overwritten'
                                 f' for separate column {nc["column_name"]} with {nc["column_name"].upper()} !')
            nc['table_name'] = nc['column_name'].upper()

        if len(nc.keys()) != 6:
            raise ValueError(f'There are missing or extra attributes'
                             f' for column {nc["column_name"]}: {", ".join(nc.keys())} !')

        # Convert properties from dict keys for easier handling
        column_name = nc['column_name']
        column_no = header_to_no[column_name]
        sql_table_name, sql_col_name = nc['table_name'], nc['sql_column_name']
        column_type, py_column_type, sql_column_type = nc['column_type'], None, None
        index, separate = nc['index'], nc['separate']

        # Duplicated column name: SQL is case insensitive and does not allow empty column names!
        conv_col_name = column_name.lower()
        if conv_col_name in col_names or len(conv_col_name) == 0:
            raise ValueError(f'column_name ({column_name}) is case insensitive, non-empty and must be uniq'
                             f' for every column !')
        col_names.add(conv_col_name)

        # Config must correspond to the header
        if conv_col_name not in header_new:
            raise ValueError(f'column_name in config file ({column_name}) does not match any column definitions'
                             f' in the header ({header}) !')

        if column_type not in col_types_to_sql_types.keys():
            raise ValueError(f'Invalid column_type for column {column_name}: {column_type} !')
        # These are passed to the row insertion step!
        py_column_type, sql_column_type = col_types_to_sql_types[column_type]

        # id column must be omitted if exists
        if sql_col_name.lower() == 'id' and py_column_type is not None:
            raise ValueError(f'sql_column_name can not be id for column {column_name} only with type none !')

        if separate:
            sep_sql_col_names.add(sql_col_name)
            sep_sql_table_names.add(sql_table_name)
            sep_col_types.add(column_type)
        else:
            main_sql_col_names.append(sql_col_name)
            main_sql_table_names.add(sql_table_name)
            main_sql_table_name = sql_table_name

        # Add checked columns to the list possibly in random order (with the help of the look-up table)
        new_columns[column_no] = \
            (column_name, sql_table_name, sql_col_name, py_column_type, sql_column_type, index, separate)

    if not has_main_table_col:
        raise ValueError(f'All coulmns ({", ".join(col_names)}) can not be in separate tables'
                         f' because main table would be empty!')

    # We allow no separate columns, but it there are any they must have the same sql_column_name
    if len(sep_sql_col_names) > 1:
        raise ValueError(f'sql_column_name must be the same for every separate column'
                         f' ({", ".join(sep_sql_col_names)}) !')

    # We allow no separate columns, but it there are any they must have the same column_type
    if len(sep_col_types) > 1:
        raise ValueError(f'column_type must be the same for every separate column  ({", ".join(sep_col_types)}) !')

    # Main table column names must be unique
    if len(set(main_sql_col_names)) != len(main_sql_col_names):
        raise ValueError(f'sql_column_name must be uniq for every non-separate column'
                         f' ({", ".join(main_sql_col_names)}) !')

    if len(main_sql_table_names) != 1:
        raise ValueError(f'The main table\'s name ({", ".join(main_sql_table_names)}) must be the same'
                         f' (case sensitive) for all non-separate column names !')

    # Table names must be unique
    if main_sql_table_name in sep_sql_table_names:
        raise ValueError(f'The main table\'s name ({main_sql_table_name}) must differ from'
                         f' the separate column names ({", ".join(sep_sql_table_names)}) !')

    return main_sql_table_name, new_columns


def create_tables(engine, main_table_name, cols):
    metadata = MetaData()

    main_table = Table(main_table_name, metadata,
                       Column('id', Integer, primary_key=True),
                       *(Column(sql_col_name, sql_column_type, index=index)
                         for (_, _, sql_col_name, _, sql_column_type, index, separate) in cols if not separate)
                       )

    other_tables = {sql_table_name: Table(sql_table_name, metadata,
                                          Column('id', Integer, ForeignKey(f'{main_table_name}.id'), index=True),
                                          Column(sql_col_name, sql_column_type, index=index))
                    for (_, sql_table_name, sql_col_name, _, sql_column_type, index, separate) in cols if separate}

    metadata.create_all(engine)

    return main_table, other_tables


def gen_table_dict(lines, column_defs):
    no_of_cols = len(column_defs)
    for i, line in enumerate(lines, start=2):
        columns = line.rstrip('\n').split('\t')
        if len(columns) != no_of_cols:
            raise ValueError(f'The number of columns ({len(columns)}) in the current row ({i}) does not equal'
                             f' the required number of cols ({no_of_cols})!')

        cur_row_main = {}
        cur_row_other = {}
        for (column_name, sql_table_name, sql_col_name, py_column_type, _, _, separate), value \
                in zip(column_defs, columns):
            # Omit none type columns and NULL-valued columns (if they are separated), and convert the rest
            if py_column_type is not None and (not separate or value != 'NULL'):
                try:
                    col_val = py_column_type(value)
                except ValueError as e:
                    e.message = f'The type ({py_column_type.__name__}) for column ({column_name})' \
                                f' has invalid value ({value}) !'
                    raise
                if separate:
                    cur_row_other[(sql_table_name, sql_col_name)] = col_val
                else:
                    cur_row_main[sql_col_name] = col_val

        yield cur_row_main, cur_row_other


def chunked_iterator(iterable, n):
    # Original source:
    # https://stackoverflow.com/questions/8991506/iterate-an-iterator-by-chunks-of-n-in-python/29524877#29524877
    it = iter(iterable)
    try:
        while True:
            yield itertools.chain((next(it),), itertools.islice(it, n-1))
    except StopIteration:
        return


def tsv2sql(in_file, out_db, config, chunksize=100000):
    # Checked config
    main_table_name, column_defs = check_config_and_header(next(in_file).rstrip('\n').split('\t'), config)

    # Create database and empty Table
    engine = create_engine(f'sqlite:///{out_db}')
    main_table, other_tables = create_tables(engine, main_table_name, column_defs)

    # Fill Table
    with engine.connect() as conn:
        for i, batch in enumerate(chunked_iterator(gen_table_dict(in_file, column_defs), chunksize), start=1):
            with conn.begin():
                for main_table_vals, o_tables_vals in batch:
                    row = conn.execute(main_table.insert(), main_table_vals)  # Instert row
                    for (o_tab_name, o_col_name), val in o_tables_vals.items():  # Insert other features to their table
                        conn.execute(other_tables[o_tab_name].insert(),
                                     {'id': row.inserted_primary_key[0], o_col_name: val})

            print(i*chunksize, flush=True)
        print('VACUUM-ing...', flush=True)
        conn.execute(text('VACUUM;'))


def load_and_validate(schema_fname, fname, strict=True):
    # Load schema and data
    config_schema = make_schema(schema_fname)
    data = make_data(fname)

    # Validate
    try:
        validate(config_schema, data, strict)
    except YamaleError as e:
        for result in e.results:
            print('Error validating data {0} with {1}:'.format(result.data, result.schema), file=sys.stderr)
            for error in result.errors:
                print('', error, sep='\t', file=sys.stderr)
        exit(1)
    return data[0][0]


def parse_args():
    parser = ArgumentParser(description='Convert TSV files to SQLite format')
    parser.add_argument('-i', '--input', dest='input_file', type=FileType(encoding='UTF-8'),
                        help='Input file (cool_data.tsv or STDIN)', metavar='COOL_DATA.TSV', default=sys.stdin)
    parser.add_argument('-o', '--output', dest='output_file', required=True,
                        help='Output SQLite db filename (cool_data.sqlite3)', metavar='COOL_DATA.SQLITE3')
    parser.add_argument('-c', '--config', dest='config', required=True, type=Path,
                        help='The config file defines the database schema', metavar='SCHEMA_DEF.YAML')
    options = vars(parser.parse_args())

    return options


def main():
    opts = parse_args()
    config_schema = Path(__file__).parent / 'tsv2sql_config_schema.yaml'
    config = load_and_validate(config_schema, opts['config'])
    tsv2sql(opts['input_file'], opts['output_file'], config)
    opts['input_file'].close()  # Because argparse opened it in FileType()


if __name__ == '__main__':
    main()
