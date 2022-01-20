#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import re
import sys
import itertools
from zipfile import ZipFile
from codecs import iterdecode
from collections import Counter
from argparse import ArgumentParser, ArgumentTypeError

from sqlalchemy import Column, Integer, String, MetaData, Table, create_engine, ForeignKey


non_word = re.compile(r'^[^\w]+$')
log = open('re.log', 'w', encoding='UTf-8')


def parse_mazsola(inp_file):
    with ZipFile(inp_file) as mazsola_zip:
        with mazsola_zip.open('mazsola_adatbazis.txt') as mazsola_txt:
            for line in iterdecode(mazsola_txt, 'latin2'):
                line = line.strip()
                if len(line) > 0:
                    ind = line.index('stem@@')  # Start index of argument frame description
                    sent = line[:ind]
                    args = {}
                    for arg in line[ind:].split():
                        case, stem = arg.split('@@')
                        if case not in args:
                            args[case] = stem
                        else:
                            print('ERROR: unexpected characters in line:', line, file=sys.stderr, flush=True)
                    yield sent, args


def filter_mazsola_entry(sent, args, sents):
    if sent in sents:
        print('ERROR: Omitting duplicate sent:', sent, args, file=sys.stderr, flush=True)
        return True
    sents.add(sent)
    if args['STEM'] == 'NULL' or args['STEM'].endswith('null'):
        print('ERROR: Omitting frame with null verb stem:', sent, args, file=sys.stderr, flush=True)
        return True
    if '' in args:
        print('ERROR: Omitting empty argument case:', sent, args, file=sys.stderr, flush=True)
        return True
    words = sent.split()
    non_words = [word for word in words if non_word.match(word)]
    if len(non_words) > 10:  # This is a very lax filter with very few false positive (see debug log)
        print(sent, file=log)
        return True
    return False


def normalize_argframe(args):
    ret = {}
    for case, arg_stem in args.items():
        case = case.strip('.').replace('}', '').replace('--', '-').upper()  # Due to bad tokenisation?
        if case not in ret:
            ret[case] = arg_stem
        else:
            print('ERROR: Omitting duplicate case after normalisation:', args, file=sys.stderr, flush=True)

    return ret


def filter_rare_args(entries, case_count, threshold=5):
    rare_arg_types = {case for case, freq in case_count.items() if freq < threshold}
    new_entries = []
    for sent, args in entries:
        if len(args.keys() & rare_arg_types) == 0:
            new_entries.append((sent, args))
        else:
            print('ERROR: Omitting entry with rare argument case:', args.keys() & rare_arg_types, sent,
                  file=sys.stderr, flush=True)

    return new_entries


def filter_mazsola(mazsola, threshold=5):
    case_count = Counter()
    entries = []
    sents = set()
    for sentence, argframe in mazsola:
        argframe = normalize_argframe(argframe)
        if not filter_mazsola_entry(sentence, argframe, sents):
            for case in argframe.keys():
                case_count[case] += 1
            entries.append((sentence, argframe))
    return filter_rare_args(entries, case_count, threshold)


def create_tables(engine, metadata, arg_cases):
    mazsola_table = Table('mazsola', metadata,
                          Column('id', Integer, primary_key=True),
                          Column('sent', String),
                          Column('verbstem', String, index=True))

    other_tables = {case: Table(case, metadata,
                                Column('id', Integer, ForeignKey('mazsola.id'), index=True),
                                Column('argstem', String, index=True))
                    for case in arg_cases if case != 'STEM'}
    metadata.create_all(engine)
    return mazsola_table, other_tables


def gen_mazsola_dict(arg_tables, mazsola):
    for sent, args in mazsola:
        new_args = {}
        for case, val in args.items():  # Because SQL is case insensitive and does not allow empty table names
            case = case.upper()
            if len(case) == 0:
                print('ERROR: Omitting empty argument case from frame:', sent, args, file=sys.stderr, flush=True)
            elif case in new_args:
                print('ERROR: Omitting double argument after uppercasing:', sent, args, file=sys.stderr, flush=True)
            else:
                new_args[case] = val

        yield {'sent': sent, 'verbstem': new_args['STEM']}, {arg_tables[case]: val for case, val in new_args.items()
                                                             if case != 'STEM'}


def chunked_iterator(iterable, n):
    # Original source:
    # https://stackoverflow.com/questions/8991506/iterate-an-iterator-by-chunks-of-n-in-python/29524877#29524877
    it = iter(iterable)
    try:
        while True:
            yield itertools.chain((next(it),), itertools.islice(it, n-1))
    except StopIteration:
        return


def mazsola2sql(in_file, out_db, filter_entries=True, rare_arg_threshold=5, chunksize=100000):
    orig_mazsola = parse_mazsola(in_file)
    if filter_entries:
        mazsola_final = filter_mazsola(orig_mazsola, rare_arg_threshold)
    else:
        mazsola_final = list(orig_mazsola)

    # SQL is case insensitive and does not allow empty table names!
    frequent_args = sorted({case.upper() for _, args in mazsola_final for case in args.keys() if len(case) > 0})

    engine = create_engine(f'sqlite:///{out_db}')
    metadata = MetaData()
    mazsola_table, other_tables = create_tables(engine, metadata, frequent_args)
    with engine.connect() as conn:
        for i, batch in enumerate(chunked_iterator(gen_mazsola_dict(other_tables, mazsola_final), chunksize), start=1):
            with conn.begin():
                for main_table_vals, arg_tables in batch:
                    row = conn.execute(mazsola_table.insert(), main_table_vals)  # Instert sentence
                    for other_table_name, val in arg_tables.items():  # Insert args to their table
                        conn.execute(other_table_name.insert(), {'id': row.inserted_primary_key[0], 'argstem': val})
            print(i*chunksize, flush=True)
        print('VACUUM-ing...', flush=True)
        conn.execute('VACUUM;')


def check_positive(value):
    # Original source:
    # https://stackoverflow.com/questions/14117415/in-python-using-argparse-allow-only-positive-integers/14117511#14117511
    try:
        ivalue = int(value)
    except ValueError:
        ivalue = -1
    if ivalue <= 0:
        raise ArgumentTypeError(f'{value} is an invalid positive int value')
    return ivalue


def parse_args():
    parser = ArgumentParser(description='Convert Mazsola to SQLite format with or without filtering')
    parser.add_argument('-i', '--input', dest='input_file', required=True,
                        help='Input file (mazsola_adatbazis.txt.zip)', metavar='FILES')
    parser.add_argument('-o', '--output', dest='output_file', required=True,
                        help='Output SQLite filename (mazsola.sqlite3)', metavar='FILE')
    parser.add_argument('-f', '--filter', dest='filter', action='store_true',
                        help='Filter Mazsola or not (default: true)')
    parser.add_argument('-t', '--threshold', dest='threshold', type=check_positive, metavar='NUM', default=5,
                        help='If any argument in entry occurs less then threshold the entry will be discarded')
    options = vars(parser.parse_args())

    if not options['filter'] and options['threshold'] is not None:
        raise ArgumentTypeError('Threshold can not be specified if filter is not set!')

    return options


if __name__ == '__main__':
    opts = parse_args()
    mazsola2sql(opts['input_file'], opts['output_file'], opts['filter'], opts['threshold'])
