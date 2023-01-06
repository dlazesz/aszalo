#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import sys
from math import log
from functools import lru_cache
from argparse import ArgumentParser

import uvicorn
from fastapi import Request, Response

from model import query
from utils import app, InvalidUsage, str2bool, settings  # , get_current_username
from view import parse_view, render_result, parse_filter, render_filter


@app.get('/filter')
async def filter_field(request: Request):
    return main_filter(request.query_params)


def main_filter(input_args):  #, username: str = Depends(get_current_username)):
    ret_val, status_code = parse_filter(input_args)
    result_json = render_filter(ret_val)
    result = Response(result_json, status_code, media_type='application/json')
    return result


@app.get('/')  # So one can create permalink for searches!
async def index(request: Request):  #, username: str = Depends(get_current_username)):
    return main_query(request.query_params, str(request.base_url), str(request.url))


def main_query(input_args, base_url='', full_url=''):
    exc_tb, state, query_details, other_params = parse_view(input_args)
    messages = []
    if len(exc_tb) > 0:
        # Raise the first exception (REST API JSON, CLI) or flash all (WebUI)
        if other_params['format'] != 'HTML':
            tb, message, status_code = exc_tb[0]
            raise InvalidUsage(message, status_code=status_code).with_traceback(tb)
        else:
            for _, message, _ in exc_tb:
                messages.append(message)
    count, out, res = execute_query(query_details, limit=other_params['limit'],
                                    offset=other_params.get('page', 0)*other_params['limit'])
    result = render_result(state, count, out, res, messages, base_url, full_url, other_params['format'])
    if other_params['format'] == 'HTML' and len(base_url) > 0:
        result = Response(content=result, media_type='text/html')
    elif other_params['format'] == 'JSON' and len(base_url) > 0:
        result = Response(content=result, media_type='application/json')
    elif other_params['format'] == 'TSV' and len(base_url) > 0:
        result = Response(content=result, media_type='text/tab-separated-values',
                          headers={'Content-Disposition': 'attachment; filename=result.tsv'})
    return result


def lin_scale(freq, min_freq, max_freq, min_size=80, max_size=240):  # The font-size should be between 7 and 40
    if max_freq - min_freq == 0:
        return 100
    return ((freq - min_freq) / (max_freq - min_freq)) * (max_size - min_size) + min_size


@lru_cache(10)
def execute_query(query_details, limit=1000, offset=0):
    count, out, examples = 0, [], {}
    if len(query_details) > 0:
        count, min_freq, max_freq, out_prev, out_disp, out_next, examples = query(query_details, limit, offset)

        # Postprocess
        if count > 0:
            out = []
            i = 0
            for part, is_displayed in ((out_prev, False), (out_disp, True), (out_next, False)):
                for key, freq in part:
                    # These values are used in the HTML template
                    page_no = i//limit
                    out.append((key, freq, page_no, is_displayed, lin_scale(log(freq), log(min_freq), log(max_freq))))
                    i += freq

    return count, out, examples


def parse_args():
    arg_parser = ArgumentParser(prog='Aszaló')
    state = settings['fields']
    for field_state in state:
        col_api_name = field_state['api_name']
        arg_parser.add_argument(f'--{col_api_name}', type=str, default=field_state['value'])
        arg_parser.add_argument(f'--{col_api_name}NOT', type=str2bool, nargs='?', const=True,
                                default=field_state['not'], metavar='True/False')
        arg_parser.add_argument(f'--{col_api_name}REGEX', type=str2bool, nargs='?', const=True,
                                default=field_state['regex'], metavar='True/False')
        if not field_state['simple_input']:
            arg_parser.add_argument(f'--{col_api_name}FEATNAME', type=str, default=field_state['fn_value'])
            arg_parser.add_argument(f'--{col_api_name}FEATNAME_NOT', type=str2bool, nargs='?', const=True,
                                    default=field_state['fn_not'], metavar='True/False')
            arg_parser.add_argument(f'--{col_api_name}FEATNAME_REGEX', type=str2bool, nargs='?', const=True,
                                    default=field_state['fn_regex'], metavar='True/False')

    arg_parser.add_argument('--sort', type=str, default=settings['default_sort_key'])
    arg_parser.add_argument('--page', type=int, default=0)
    arg_parser.add_argument('--format', choices={'JSON', 'TSV', 'HTML'}, default='TSV')
    arg_parser.add_argument('--limit', type=int, default=1000)
    cli_args = vars(arg_parser.parse_args())
    for arg_name, arg in cli_args.items():
        if arg_name.endswith(('NOT', 'REGEX')):
            if arg:
                cli_args[arg_name] = 'checked'
            else:
                cli_args[arg_name] = ''

    return cli_args


if __name__ == '__main__':
    if len(sys.argv) > 1:
        args = parse_args()
        print(main_query(args))
    else:
        uvicorn.run('main:app')
