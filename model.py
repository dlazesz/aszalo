#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

# SQL oriented util functions needed for the actual query

from locale import strxfrm
from functools import reduce
from collections import defaultdict
from itertools import chain, islice

from sqlalchemy import not_, or_, and_

from utils import db, table_column_objs, table_objs, settings


def add_condgroup_to_query(b_query, cond_group):
    if cond_group[2] is None:
        return b_query
    else:
        return b_query.filter(condgroup_to_sql(*cond_group))


def condgroup_to_sql(table_names, col_name, form_val, is_not, is_regex):
    """Normally OR elems of cond groups (e.g. "check for value in each table"), but if NOT is present use CNF
        to localise NOTs (e.g. value not in table1 and value not in table2, etc.)
    """
    op = or_
    if is_not and form_val:
        op = and_
    # Add "OR table.col == value" or "AND table.col != value" yield empty list (form_val can not be NULL)
    sql_group = [cond_to_sql(table_name, col_name, form_val, is_not, is_regex) for table_name in table_names]
    conditions = reduce(op, sql_group).self_group()

    return conditions


def cond_to_sql(table_name, col_name, form_val, is_not, is_regex):
    # IS NULL is automatically handled by SQLAlchemy
    cond_part = table_column_objs[(table_name, col_name)] == form_val
    if is_regex:
        cond_part = table_column_objs[(table_name, col_name)].op('regexp')(form_val)
    if is_not:
        cond_part = not_(cond_part)
    return cond_part


def suffix_key(val, skey):
    return f'{val}@{skey}'


def simple_key(val, _):
    return val


def identity(x):
    return x


def join_union_of_groups(sort_keys, union_conds, is_outer=False):
    for table_names, col_name, form_val, is_not, is_regex in union_conds:
        q = []
        for tn in table_names:  # Create subqueries and apply filters if there are any
            sq = db.session.query(table_column_objs[(tn, 'id')].label('key_id'))
            sq = add_condgroup_to_query(sq, ({tn}, col_name, form_val, is_not, is_regex))
            q.append(sq)
        # Union the subqueries and join them to the main queries
        sq = q[0]
        sq = sq.union(*q[1:])
        for sk in sort_keys.keys():
            sort_keys[sk] = sort_keys[sk].join(sq, isouter=is_outer)
            if is_outer:
                key_col = tuple(sq.subquery().c)[0]  # TODO This is not ok LEFT OUTER JOIN B.key is not NULL (=EXCEPT)
                sort_keys[sk] = sort_keys[sk].join(sq, isouter=is_outer).filter(key_col != None)


def execute_prepared_query(sort_keys, limit, offset):
    if len(sort_keys) > 1:
        transform_key = suffix_key
    else:
        transform_key = simple_key

    # Get keys with corresponding IDs
    keys = defaultdict(set)
    for sk in sort_keys.keys():
        for key_id, key_value in sort_keys[sk].all():
            keys[transform_key(key_value, sk)].add(key_id)

    # Return the results
    all_count, min_freq, max_freq, out_prev, out_disp, out_next, examples = 0, 0, 0, [], [], [], {}
    if len(keys) > 0:
        # Stabilized sort
        # Hack
        if isinstance(next(iter(keys.keys())), str):
            locale_dep_sort_key = strxfrm
        else:
            locale_dep_sort_key = identity
        key_to_id = sorted(keys.items(), key=lambda x: (-len(x[1]), locale_dep_sort_key(x[0])))
        max_offset = limit + offset
        for key, ids in key_to_id:  # Get examples only for the displayed values, enables pagination
            len_ids = len(ids)
            if all_count < offset:
                out_prev.append((key, len_ids))
            elif offset <= all_count < max_offset:
                out_disp.append((key, len_ids))
                examples[key] = [ex for ex in get_exmples_for_ids(ids)]
            else:
                out_next.append((key, len_ids))
            all_count += len_ids
        min_freq = len(key_to_id[-1][1])
        max_freq = len(key_to_id[0][1])
    return all_count, min_freq, max_freq, out_prev, out_disp, out_next, examples


def grouper(iterable, n):
    """ Original source:
     https://stackoverflow.com/questions/8991506/iterate-an-iterator-by-chunks-of-n-in-python/29524877#29524877
    """
    iterable = iter(iterable)
    try:
        while True:
            yield chain((next(iterable),), islice(iterable, n-1))
    except StopIteration:
        return


def get_exmples_for_ids(ids):
    disp_table_name = table_objs[settings['displayed_column_table_name']]
    id_col = table_column_objs[(settings['displayed_column_table_name'], 'id')]
    disp_col_name = table_column_objs[(settings['displayed_column_table_name'], settings['displayed_column_name'])]
    for ids_group in grouper(ids, 10000):  # Query by 10 000 entries
        base_query = db.session.query(disp_table_name).with_entities(id_col, disp_col_name)
        final_query = base_query.filter(id_col.in_(ids_group))
        for ex_id, ex in final_query.all():
            yield ex_id, ex.replace('<q>', '"')


def query(query_details, limit=1000, offset=0):
    # Separate params
    conds, sort_key = query_details
    not_tables = []
    union_conds = []
    # Start from the sort key restricted to the conditions
    sort_keys = {skey: db.session.query(table_column_objs[(skey, 'id')].label('key_id'),
                                        table_column_objs[(skey, sort_key[1])].label('key_value')).
                 select_from(table_objs[skey]) for skey in sort_key[0]}
    if sort_key[2] is not None:
        _, col_name, form_val, is_not, is_regex, not_tabs = sort_key[2]  # Sort key conds if there are any
        for sk in sort_keys.keys():
            sort_keys[sk] = add_condgroup_to_query(sort_keys[sk], ({sk}, col_name, form_val, is_not, is_regex))
        if len(not_tabs) > 0:
            not_tables.append((not_tabs, col_name, None, False, False))

    # Filter keys further separately if there are multiple keys
    for table_names, col_name, form_val, is_not, is_regex, not_tabs in conds:
        if len(not_tabs) > 0:
            not_tables.append((not_tabs, col_name, None, False, False))
        if len(table_names) > 1:  # Union later
            union_conds.append((table_names, col_name, form_val, is_not, is_regex))
        elif len(table_names) == 1:
            tn = next(iter(table_names))
            for sk in sort_keys.keys():
                if sk != tn:  # JOIN tables if needed always LEFT join to the key table!
                    table_obj = table_objs[tn]
                    join_on = table_column_objs[(sk, 'id')] == table_column_objs[(tn, 'id')]
                    sort_keys[sk] = sort_keys[sk].join(table_obj, join_on)
            for sk in sort_keys.keys():  # Restrict joined tables
                sort_keys[sk] = add_condgroup_to_query(sort_keys[sk],
                                                       (table_names, col_name, form_val, is_not, is_regex))

    # Add union groups
    join_union_of_groups(sort_keys, union_conds)

    # Remove negated groups
    join_union_of_groups(sort_keys, not_tables, is_outer=True)

    return execute_prepared_query(sort_keys, limit, offset)
