#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from re import escape as re_escape
from json import dumps as json_dumps
from copy import deepcopy
from itertools import chain
from collections import defaultdict
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

from utils import settings, InvalidUsage, render_template
from read_config import valid_re_or_none

POSSIBLE_FORMATS = {'HTML', 'JSON', 'TSV'}


def parse_view(request_args):
    state = deepcopy(settings['fields'])
    exc_tb, query_params, other_params = [], (), {'limit': 1000, 'format': 'HTML'}
    if len(request_args) > 0:  # If there was an actual request
        form_sort_key = request_args.get('sort', settings['default_sort_key'])
        used_fields, not_fields = defaultdict(list), defaultdict(list)
        conds, sort_key = [], None
        for field_state in state:
            # 1. Update the state of the current field from request from common checkboxes and inputs
            #    Note: Unchecked checkboxes are left out from the request args according to the HTTP GET standard,
            #          while empty input fields are always contained in the requests args.
            #          Omitted checkboxes will be treated as unchecked only if the corresponding input fields
            #          are contained (with any value) in the request args, else checkboxes will get the default value.
            col_api_name = field_state['api_name']
            # 1a. Value
            field_state['value'] = request_args.get(col_api_name, field_state['value'])
            value_in_request_args = col_api_name in request_args
            field_state['not'] = checked_or_empty(request_args.get(f'{col_api_name}NOT'), value_in_request_args,
                                                  field_state['not'])
            field_state['regex'] = checked_or_empty(request_args.get(f'{col_api_name}REGEX'), value_in_request_args,
                                                    field_state['regex'])

            # Regex disabled, still used as parameter
            if len(field_state['regex_disabled']) > 0 and len(field_state['regex']) > 0:
                raise InvalidUsage(settings['ui-strings']['regex-disabled'].
                                   format(field_state['friendly_name'], field_state['api_name']),
                                   status_code=400)

            # 1b. Featname value
            field_state['fn_value'] = request_args.get(f'{col_api_name}FEATNAME', field_state['fn_value'])
            fn_value_in_request_args = f'{col_api_name}FEATNAME' in request_args
            field_state['fn_not'] = checked_or_empty(request_args.get(f'{col_api_name}FEATNAME_NOT'),
                                                     fn_value_in_request_args,
                                                     field_state['fn_not'])
            field_state['fn_regex'] = checked_or_empty(request_args.get(f'{col_api_name}FEATNAME_REGEX'),
                                                       fn_value_in_request_args,
                                                       field_state['fn_regex'])

            # 2. Check formats
            try:
                if field_state['simple_input']:
                    # a) We can specify a feature value (from suggested list)
                    simple_field(field_state, conds, used_fields, not_fields, form_sort_key == col_api_name)
                else:
                    # b) We can specify a feature value (no suggestions) and a feature name (from suggested list)
                    complex_field(field_state, conds, used_fields, not_fields, form_sort_key == col_api_name)
            except InvalidUsage as e:
                exc_tb.append((e.__traceback__, e.message, e.status_code))

            # 4. Check sort key
            if form_sort_key == col_api_name:
                field_state['sort_key'] = 'checked'  # Keep selection even if it fails later
                if field_state['table_name'] is not None:
                    # Get the conditions for the sort key if there are any
                    sk_conds = None
                    if len(conds) > 0 and field_state['table_name'] == conds[-1][0]:
                        sk_conds = conds.pop()
                    # Sort tables in sort_key to get stable order
                    sort_key = (tuple(sorted(field_state['table_name'])), field_state['col_name'], sk_conds)

        # Some extra checking
        query_params = check_state(tuple(conds), sort_key, used_fields, not_fields, request_args, other_params, exc_tb)

    if len(exc_tb) > 0:  # Do nothing on any error, wait for the user to correct the input params!
        query_params = ()

    return exc_tb, state, query_params, other_params


def check_state(conds, sort_key, used_fields, not_fields, request_args, other_params, exc_tb):
    query_params = ()
    # Sort key ok?
    try:
        if sort_key is None:  # Bad omen: no sort key at the end -> The query will not be executed
            query_params = ()
            raise InvalidUsage(settings['ui-strings']['sort_key_invalid'],
                               status_code=400)
        query_params = (conds, sort_key)
    except InvalidUsage as e:
        exc_tb.append((e.__traceback__, e.message, e.status_code))

    # Double field usage (used_fields and not_fields)
    try:
        used_tables = set()
        if sort_key is not None and sort_key[2] is not None:
            used_tables.update(sort_key[2][0])
        for (table_name, _), v in used_fields.items():
            used_tables.add(table_name)
            if len(v) > 1:
                query_params = ()
                raise InvalidUsage(settings['ui-strings']['featname_in_multiple_fields'].
                                   format(table_name, ' and '.join(f'\'{friendly_name}\' ({api_name})'
                                                                   for friendly_name, api_name in v)),
                                   status_code=400)

        not_used_tables = set()
        for (table_name, _), v in not_fields.items():
            not_used_tables.add(table_name)
            if len(v) > 1:
                query_params = ()
                raise InvalidUsage(settings['ui-strings']['featname_in_multiple_fields'].
                                   format(table_name, ' and '.join(f'\'{friendly_name}\' ({api_name})'
                                                                   for friendly_name, api_name in v)),
                                   status_code=400)

        # Check for intersection in used_fiels and not_fields
        common_tablenames_to_fields = defaultdict(list)
        for table_col_name, v in chain(used_fields.items(), not_fields.items()):
            common_tablenames_to_fields[table_col_name].append(v[0])
            if len(common_tablenames_to_fields[table_col_name]) > 1:
                query_params = ()
                raise InvalidUsage(settings['ui-strings']['same_feature_with_pos_and_neg_signs'].
                                   format(table_col_name, ' and '.join(f'\'{friendly_name}\' ({api_name})'
                                                                       for friendly_name, api_name in
                                                                       common_tablenames_to_fields[table_col_name])),
                                   status_code=400)

        # Check maximal number of used tables
        if len(common_tablenames_to_fields) > 60:
            query_params = ()
            raise InvalidUsage(settings['ui-strings']['too_mutch_features_specified'].
                               format(len(used_tables)),
                               status_code=400)
    except InvalidUsage as e:
        exc_tb.append((e.__traceback__, e.message, e.status_code))

    # format parameter
    try:
        format_value = request_args.get('format', 'HTML')  # Argument not supplied -> HTML
        if format_value not in POSSIBLE_FORMATS:
            query_params = ()
            raise InvalidUsage(settings['ui-strings']['invalid_format'].format(format_value, POSSIBLE_FORMATS),
                               status_code=400)
        other_params['format'] = format_value
    except InvalidUsage as e:
        exc_tb.append((e.__traceback__, e.message, e.status_code))

    # limit parameter
    try:
        other_params['limit'] = int(request_args.get('limit', 1000))  # Argument not supplied -> 1000
    except ValueError as e:
        query_params = ()
        exc_tb.append((e.__traceback__, 'Value ({0}) is invalid for \'limit\' expected 0 or greater integer !'.
                       format(request_args['limit']), 400))

    # page parameter
    try:
        other_params['page'] = int(request_args.get('page', 0))  # Argument not supplied -> 0
    except ValueError as e:
        exc_tb.append((e.__traceback__, 'Value ({0}) is invalid for \'page\' expected 0 or greater integer !'.
                      format(request_args['page']), 400))

    return query_params


def simple_field(field_state, conds, used_fields, not_fields, is_sort_key):
    _ = not_fields, is_sort_key  # Silence IDE
    if len(field_state['value']) == 0:
        return  # Empty, ignore field

    # There is value, not a regex, there are all_elems, and still value not in all_elems
    if len(field_state['regex']) == 0 and len(field_state['all_elems']) > 0 and \
            field_state['value'] not in field_state['all_elems']:
        raise InvalidUsage(settings['ui-strings']['invalid_value'].
                           format(field_state['value'], field_state['friendly_name'], field_state['api_name']),
                           status_code=400)

    # Regex compiles or not? (ignore empty regex!)
    if len(field_state['regex']) > 0 and valid_re_or_none(field_state['value']) is None:
        raise InvalidUsage(settings['ui-strings']['invalid_regex'].
                           format(field_state['value'], field_state['friendly_name'], field_state['api_name']),
                           status_code=400)

    # Maintain if a field is used (to check multiple usages later)
    table_name = next(iter(field_state['table_name']))  # Keep the table in the set for the HTML form while accessing it
    used_fields[(table_name, field_state['col_name'])].\
        append((field_state['friendly_name'], field_state['api_name']))

    # Add condition to query parameters (table name is a set, even if it a single table!)
    conds.append((frozenset(field_state['table_name']), field_state['col_name'], field_state['value'],
                 len(field_state['not']) > 0, len(field_state['regex']) > 0, frozenset()))


def complex_field(field_state, conds, used_fields, not_fields, is_sort_key):
    if len(field_state['value']) == 0 and len(field_state['fn_value']) == 0:
        return  # Empty, ignore field

    # There is feature value, but feature name is empty
    if len(field_state['value']) > 0 and len(field_state['fn_value']) == 0:
        raise InvalidUsage(settings['ui-strings']['non_empty_value_for_empty_featname'].
                           format(field_state['value'], field_state['friendly_name'], field_state['api_name']),
                           status_code=400)

    # Check value
    if len(field_state['value']) > 0:
        # Regex compiles or not? (ignore empty regex!)
        if len(field_state['regex']) > 0 and valid_re_or_none(field_state['value']) is None:
            raise InvalidUsage(settings['ui-strings']['invalid_regex'].
                               format(field_state['value'], field_state['friendly_name'], field_state['api_name']),
                               status_code=400)
        value = field_state['value']
        value_is_not = len(field_state['not']) > 0
        value_is_regex = len(field_state['regex']) > 0
    else:
        value = None
        value_is_not = True  # unspecified value for feature name -> anything goes: value is NOT NULL
        value_is_regex = False

    # Parse feature table regex, and add matching tables or just add the single literal table when regex is not checked
    if len(field_state['fn_regex']) > 0:
        fn_value = _grep_value_in_seq(field_state['fn_value'], field_state['all_featelems'])
        if fn_value is not None:
            fn_value = set(fn_value)
        else:  # Invalid regex, ignore field
            raise InvalidUsage(settings['ui-strings']['featname_invalid_regex'].
                               format(field_state['fn_value'], field_state['friendly_name'], field_state['api_name']),
                               status_code=400)

    # Literal or alias tablename for one table (must be one of selectable_tables and aliases)
    elif field_state['fn_value'] in field_state['all_featelems']:
        fn_value = {field_state['fn_value']}
    else:
        raise InvalidUsage(settings['ui-strings']['featname_invalid_value'].
                           format(field_state['fn_value'], field_state['friendly_name'], field_state['api_name']),
                           status_code=400)

    # Look up aliases (the target values of the aliases are validated at init time)
    field_tables = {field_state['featelems_aliases'].get(fn_value_elem, fn_value_elem) for fn_value_elem in fn_value}
    not_tables = set()

    # Negate tables if needed
    if field_state['fn_not']:
        not_tables = field_tables
        field_tables = set()
        # We need field_tables only if value is set! (else only check IS NULL on not_tables)
        if value is not None or is_sort_key:
            field_tables = {fn_value_elem for fn_value_elem in field_state['all_featelems']
                            if fn_value_elem not in not_tables and
                            fn_value_elem not in field_state['featelems_aliases']}

    # Add if not None or invalid Feature name (table name)
    # If too many tables selected (Any or both of field_tables' and not_tables' length are above 60) -> ignore field
    # Facts:
    #  - len(not_tables) == 0 if field_state['fn_not'] == False
    #  - len(field_tables) == 0 if field_state['fn_not'] == True and len(field_state['value']) == 0
    #  - Else both variable counts!
    if len(field_tables) + len(not_tables) > 60:
        raise InvalidUsage(settings['ui-strings']['featname_value_too_broad_regex'].
                           format(field_state['fn_value'], field_state['friendly_name'], field_state['api_name']),
                           status_code=400)
    elif len(field_tables) > 0 or len(not_tables) > 0:
        field_state['table_name'] = frozenset(field_tables)
        # Maintain if a field is (not) used (to check multiple usages later)
        for fn_value in field_tables:
            used_fields[(fn_value, field_state['col_name'])].\
                append((field_state['friendly_name'], field_state['api_name']))
        for fn_value in not_tables:
            not_fields[(fn_value, field_state['col_name'])]. \
                append((field_state['friendly_name'], field_state['api_name']))
    else:
        raise InvalidUsage(settings['ui-strings']['featname_regex_invalid_value'].
                           format(field_state['fn_value'], field_state['friendly_name'], field_state['api_name']),
                           status_code=400)

    # The valid value + fn_value pairs will be OR-ed together while different cond groups will be AND-ed!
    # If fn_value is NOT-ed, fn_value tables will be checked for IS NULL (with AND) and
    #  value will be checked in the complement tables (with OR)
    conds.append((frozenset(field_tables), field_state['col_name'], value, value_is_not, value_is_regex,
                  frozenset(not_tables)))


def _grep_value_in_seq(value, all_elems, like=False):
    # Prefix search (like == True) or full-text search (like == False)
    if like:  # Like SQL LIKE STRING%
        value = re_escape(value)
        value = f'^{value}'
    value_regex = valid_re_or_none(value)
    if value_regex is not None:
        # Add matching tablenames
        value_regex = [value for value in all_elems if value_regex.search(value) is not None]

    return value_regex


def render_result(state, count, out, res, messages, base_url, full_url, out_format='HTML', debug=False):
    # Recipe from:
    # https://stackoverflow.com/questions/7734569/how-do-i-remove-a-query-string-from-url-using-python/7734686#7734686
    full_url_parts = urlparse(full_url)
    query = parse_qs(full_url_parts.query, keep_blank_values=True)
    query.pop('page', None)  # First argument need to be str opposing bytes expected by PyCharm type hints!
    full_url_parts = full_url_parts._replace(query=urlencode(query, True), fragment='')
    full_url_wo_page = urlunparse(full_url_parts)

    if out_format == 'HTML':
        out_content = render_template('layout.html', title=settings['title'], action=base_url, formelems=state,
                                      freq=out, result=res, count=count, ui_strings=settings['ui-strings'],
                                      full_url_wo_page=full_url_wo_page, full_url=full_url, messages=messages)
    elif out_format == 'JSON':
        out = {'freq': out, 'result': res, 'count': count}
        out_content = json_dumps(out, ensure_ascii=False, indent=4)
    else:  # TSV
        out_content = '\n'.join(f'{key}\t{entry_id}\t{entry_value}' for key, val in res.items()
                                for entry_id, entry_value in val)

    # DEBUG
    if debug:
        with open('out.html', 'w', encoding='UTF-8') as fh:
            fh.write(out_content)

    return out_content


def checked_or_empty(val, input_field_present, default):
    """Unchecked checkboxes do not appear by default in GET request"""
    # If checkbox does present and is checked -> checked
    # If checkbox does present and is empty -> unchecked
    # If checkbox does not present and the corresponding input field also does not present -> default value
    # If checkbox does not present and the corresponding input field does present -> unchecked
    if (val is not None and len(val) > 0) or \
            (val is None and not input_field_present and len(default) > 0):
        return 'checked'
    return ''


def parse_filter(request_args):
    # Get current field
    api_name = request_args.get('api_name')
    for field in settings['fields']:
        if field['api_name'] == api_name:
            curr_field = field
            break
    else:
        return {'error': f'No field named {api_name} !'}, 400

    # Setup field vals
    if curr_field['simple_input']:
        value_name = 'value'
        regex_val_name = f'{api_name}REGEX'
        all_elems = curr_field['all_elems']
    else:
        value_name = f'{api_name}FEATNAME'
        regex_val_name = f'{api_name}FEATNAME_REGEX'
        all_elems = curr_field['all_featelems']

    # Get arguments
    value = request_args.get(value_name, '')
    regex_val = request_args.get(regex_val_name, default='false').lower() == 'true'
    max_len = request_args.get('limit', default=40)

    # Sanitize max_len
    try:
        max_len_int = int(max_len)
    except ValueError:
        max_len_int = -1

    if max_len_int <= 1:
        return {'error': f'Value ({max_len}) is invalid integer for limit !'}, 400

    # Retrive values
    if len(value) == 0:
        ret = all_elems
        # return {'error': f'{value_name} ({value}) is empty for field {api_name} !'}, 400
    else:
        ret = _grep_value_in_seq(value, all_elems, not regex_val)

    if ret is None:
        return {'error': f'Value ({value}) is invalid regular expression for field {value_name} !'}, 400

    return {'values': ret[:max_len_int], 'more_elems_length': max(0, len(ret)-max_len_int)}, 200


def render_filter(res):
    if 'values' in res and 'more_elems_length' in res:
        n = res['more_elems_length']
        n_more_elems = settings['ui-strings']['n_more_elems'].format(n)
        if len(res['values']) > 0 and res['values'][-1] != n_more_elems and n > 0:
            res['values'].append(n_more_elems)
    ret = json_dumps(res, ensure_ascii=False, indent=4)
    return ret
