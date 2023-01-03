#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import re
import sys
from zipfile import ZipFile
from codecs import iterdecode
from collections import Counter
from argparse import ArgumentParser, ArgumentTypeError, FileType


log = open('re.log', 'w', encoding='UTf-8')
non_word = re.compile(r'^\W+$')


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


def gen_mazsola_tsv_rows(mazsola, header_keys):
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

        new_args['frame'] = ' '.join(sorted(case for case in new_args.keys() if case != 'STEM'))
        new_args['sent'] = sent

        yield [new_args.get(elem, 'NULL') for elem in header_keys]  # NULL is the value of missing fields


def mazsola2tsv(in_file, out_file, filter_entries=True, rare_arg_threshold=5):
    orig_mazsola = parse_mazsola(in_file)
    if filter_entries:
        mazsola_final = filter_mazsola(orig_mazsola, rare_arg_threshold)
    else:
        mazsola_final = list(orig_mazsola)

    # SQL is case insensitive and does not allow empty table names!
    args_header = sorted({case.upper() for _, args in mazsola_final for case in args.keys()
                          if len(case) > 0 and case != 'STEM'})
    args_header.append('STEM')
    args_header.append('frame')
    args_header.append('sent')

    print('INFO: Writing output!', file=sys.stderr, flush=True)
    print(*args_header, sep='\t', file=out_file)
    for line in gen_mazsola_tsv_rows(mazsola_final, args_header):
        print(*line, sep='\t', file=out_file)


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
                        help='Input file (mazsola_adatbazis.txt.zip)', metavar='FILE')
    parser.add_argument('-o', '--output', dest='output_file', required=True, type=FileType('w', encoding='UTF-8'),
                        help='Output TSV filename (mazsola.TSV)', metavar='FILE', default=sys.stdout)
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
    mazsola2tsv(opts['input_file'], opts['output_file'], opts['filter'], opts['threshold'])
    opts['output_file'].close()  # Because argparse opened it in FileType()
