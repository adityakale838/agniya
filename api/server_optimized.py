"""
AGNIYA API server (Flask). Launched by start.ps1.

What it does, precisely:
- /api/upload   : stores a CSV, suggests per-column encryption
- /api/encrypt  : encrypts every Paillier column with fresh randomness (packed: many
                  values per ciphertext). 'OPE+Paillier' columns are packed in sorted
                  order and get one OPE tag per row, so a range is a run of slots
- /api/query    : SUM / AVG / COUNT computed by multiplying ciphertexts, then ONE decryption;
                  MIN / MAX / MEDIAN on OPE+Paillier columns (sorted: one ciphertext each);
                  VARIANCE / STDDEV from SUM(x) and SUM((x - c)^2) of a squared copy made on first use

Two trust models:
- /api/upload, /api/encrypt, /api/query (dashboard demo): this process receives the plaintext
  CSV and generates and holds the private key in memory. It is the data owner.
- /api/v2/columns, /aggregate, /quantiles, /ranges, /ciphertexts, /delete (use agniya.client.AgniyaClient): the client
  keeps the private key and the OPE keys. This process only ever sees the public modulus n, packed
  ciphertexts, values per ciphertext, row counts and sorted OPE tags, and returns ciphertexts.
  The client checks every answer (agniya/core/integrity.py). Every call needs the dataset's
  token (derived from the private key by the client); only its SHA-256 is stored here.
  Its columns persist in SQLite at AGNIYA_STORE (default api/agniya_store.sqlite3) and are
  reloaded at start-up. The demo datasets are NOT persisted: they include the private key.
Decimal columns are stored as fixed-point integers with FIXED_POINT_DECIMALS digits.
"""

import hashlib
import hmac
import os
import sys
import time
import secrets
import sqlite3
from contextlib import closing
from bisect import bisect_left, bisect_right

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pyope.ope import ValueRange

from agniya.core.ultimate_system import UltimateOptimizedDatabase
from agniya.core.paillier import MIN_KEY_BITS, PaillierPublicKey, decrypt_crt, generate_keypair
from agniya.core.batch_packing import (decrypt_sorted_groups, group_pages, quantile_rows, range_plan, sample_variance,
                                       slot_value, squares)
from agniya.hybrid.fast_ope import FastOPE

FIXED_POINT_DECIMALS = 4
PAILLIER_TYPES = {'Paillier-2048', 'OPE+Paillier'}
GROUP_MAX_VALUES = 64  # GROUP BY copies are built for columns with at most this many distinct values
ORDER_STATS = {'MIN': 0.0, 'MEDIAN': 0.5, 'MAX': 1.0}  # quantiles of a sorted (OPE+Paillier) column
SPREAD = ('VARIANCE', 'STDDEV')  # sample (ddof=1), as pandas and SQL

app = Flask(__name__)
CORS(app, origins=os.environ.get('AGNIYA_CORS_ORIGINS', 'http://localhost:3000').split(','))

# Server-side demo mode: one key for every dataset, made once at startup (safe primes, ~1-6 s)
# so /api/encrypt does not pay key generation. This server holds the private key either way.
SERVER_KEYS = generate_keypair(2048)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

# filename -> {'db', 'columns': {name: column-state}, 'record_count'}
encrypted_datasets = {}


def _to_fixed_point(series: pd.Series):
    """Non-null values as ints, plus the scale used (1 for integer columns)."""
    values = series.dropna()
    scale = 1 if pd.api.types.is_integer_dtype(series) else 10 ** FIXED_POINT_DECIMALS
    return [int(round(float(v) * scale)) for v in values], scale


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'AGNIYA API: Paillier-2048 aggregation over encrypted columns',
        'version': '5.0.0',
        'features': {
            'paillier_2048': True,
            'randomized_encryption': True,
            'batch_packing': True,
            'offline_randomness_pool': True,
            'ope_range_filter': True,
            'gpu_acceleration': False,
        },
    })


@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files or request.files['file'].filename == '':
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'Invalid file type. Only CSV allowed'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        return jsonify({'error': f'Failed to parse CSV: {e}'}), 400

    schema = []
    for col in df.columns:
        numeric = pd.api.types.is_numeric_dtype(df[col])
        if col.lower() in ('id', 'user_id', 'customer_id'):
            suggested = 'Plaintext'
        else:
            suggested = 'Paillier-2048' if numeric else 'AES-256'
        schema.append({'name': col, 'type': 'int' if pd.api.types.is_integer_dtype(df[col])
                       else 'float' if numeric else 'str', 'encryption': suggested})

    return jsonify({
        'success': True, 'filename': filename, 'records': len(df), 'fields': len(df.columns),
        'schema': schema, 'size_kb': round(os.path.getsize(filepath) / 1024, 2),
        'sample_data': df.head(3).fillna('').to_dict('records'),
    })


@app.route('/api/encrypt', methods=['POST'])
def encrypt_dataset():
    data = request.json or {}
    filename, schema = data.get('filename'), data.get('schema')
    if not filename or not schema:
        return jsonify({'error': 'Missing filename or schema'}), 400
    filepath = os.path.join(UPLOAD_FOLDER, secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404

    df = pd.read_csv(filepath)
    sample_size = data.get('sample_size')
    if sample_size and sample_size < len(df):
        df = df.sample(n=sample_size, random_state=42).reset_index(drop=True)

    fields = [f for f in schema if f.get('encryption') in PAILLIER_TYPES and f.get('name') in df.columns]
    if not fields:
        return jsonify({'error': 'No Paillier fields selected.'}), 400
    bad = [f['name'] for f in fields if not pd.api.types.is_numeric_dtype(df[f['name']])]
    if bad:
        return jsonify({'error': f'Paillier fields must be numeric: {bad}'}), 400

    start = time.perf_counter()
    db = UltimateOptimizedDatabase(keys=SERVER_KEYS)
    columns, total_cts, tag_of = {}, 0, {}
    for f in fields:
        name = f['name']
        values, scale = _to_fixed_point(df[name])
        ope_col = f['encryption'] == 'OPE+Paillier' and bool(values)
        if ope_col:
            values.sort()  # sorted packing: a value range is a contiguous run of slots
        column = db.encrypt_column(values)
        state = {'packed': column, 'scale': scale, 'nulls': int(df[name].isna().sum())}
        total_cts += len(column['ciphertexts'])

        if ope_col:
            offset, top = values[0], max(values[-1] - values[0], 1)
            ope = FastOPE(secrets.token_bytes(32), in_range=ValueRange(0, top),
                          out_range=ValueRange(0, 2 ** 64 - 1))
            tags = ope.encrypt_list([v - offset for v in values])  # sorted, like values
            state.update(offset=offset, ope=ope, ope_max=top, ope_tags=tags, by={})
            tag_of[name] = dict(zip(values, tags))
        columns[name] = state

    # SUM(a) WHERE b in range: for each OPE column b, a copy of every other column a packed in b's
    # order, over the rows where both are present, with b's tags for those rows.
    # ponytail: one extra packed copy per (OPE column, other column) pair; fine for a few columns.
    for b, tag in tag_of.items():
        bs = columns[b]
        for a, cs in columns.items():
            rows = df[[a, b]].dropna()
            if a == b or rows.empty:
                continue
            pairs = sorted((int(round(float(y) * bs['scale'])), int(round(float(x) * cs['scale'])))
                           for x, y in zip(rows[a], rows[b]))
            packed = db.encrypt_column([x for _, x in pairs])
            bs['by'][a] = {'packed': packed, 'tags': [tag[y] for y, _ in pairs]}
            total_cts += len(packed['ciphertexts'])

    # SUM(a) GROUP BY g: for every column g (encrypted or not) with few distinct values, a copy of each
    # encrypted column a packed by group, so one decryption per page of groups gives every sum and count.
    group_cols = [g for g in df.columns if 2 <= df[g].nunique() <= GROUP_MAX_VALUES]
    for a, cs in columns.items():
        cs['groups'] = {}
        for g in group_cols:
            rows = df[[a, g]].dropna()  # rows missing a or g drop out (pandas groupby default)
            if a == g or rows.empty:
                continue
            try:
                packed = db.packer.encrypt_groups([int(round(float(x) * cs['scale'])) for x in rows[a]], list(rows[g]))
            except ValueError:  # values too large for one plaintext: no copy, query says so
                continue
            cs['groups'][g] = packed
            total_cts += len(packed['ciphertexts'])

    db.pool.close()  # release worker processes; queries need no new randomness
    elapsed = time.perf_counter() - start
    encrypted_datasets[filename] = {'db': db, 'columns': columns, 'record_count': len(df), 'df': df}
    return jsonify({
        'success': True,
        'records_encrypted': len(df),
        'total_records': len(df),
        'time_seconds': round(elapsed, 3),
        'throughput': round(len(df) / elapsed, 1) if elapsed else None,
        'ciphertexts': total_cts,
        'fields': {n: {'values': c['packed']['count'], 'null_rows': c['nulls'], 'scale': c['scale'],
                       'packed_ciphertexts': len(c['packed']['ciphertexts']),
                       'values_per_ciphertext': c['packed']['slots'],
                       'range_filterable': 'ope' in c, 'group_by': sorted(c['groups'])} for n, c in columns.items()},
        'key_bits': db.public_key.n.bit_length(),
    })


def _tag_range(tags, ope, top, scale, offset, lo, hi):
    """Rows i..j-1 of a column with sorted OPE `tags` whose value is in [lo, hi] (either may be None or '')."""
    shift = lambda v: int(round(float(v) * scale)) - offset  # noqa: E731
    lo_s = shift(lo) if lo not in (None, '') else 0
    hi_s = shift(hi) if hi not in (None, '') else top
    if lo_s > top or hi_s < 0 or lo_s > hi_s:
        return 0, 0
    return bisect_left(tags, ope.encrypt(max(lo_s, 0))), bisect_right(tags, ope.encrypt(min(hi_s, top)))


def _filtered_groups(ds, field, by, fc):
    """Copy of `field` for GROUP BY `by` WHERE fc in range, packed in fc order with fc's OPE tags.
    Built on first use and kept: one per (field, by, fc) up front would be fields x groups x filters copies."""
    col = ds['columns'][field]
    cache = col.setdefault('filtered_groups', {})
    if (by, fc) not in cache:
        df = ds['df']
        if fc not in df.columns or not pd.api.types.is_numeric_dtype(df[fc]):
            raise ValueError(f'Range filters need a numeric column, not {fc}')
        rows = df[list(dict.fromkeys([field, by, fc]))].dropna()
        if rows.empty:
            raise ValueError(f'No rows have {field}, {by} and {fc}')
        fscale = 1 if pd.api.types.is_integer_dtype(df[fc]) else 10 ** FIXED_POINT_DECIMALS
        trip = sorted(((int(round(float(w) * fscale)), int(round(float(a) * col['scale'])), g)
                       for a, g, w in zip(rows[field], rows[by], rows[fc])), key=lambda r: r[:2])
        db = ds['db']
        packed = db.packer.encrypt_sorted_groups([a for _, a, _ in trip], [g for _, _, g in trip])
        db.pool.close()
        keys = [w for w, _, _ in trip]
        offset, top = keys[0], max(keys[-1] - keys[0], 1)
        ope = FastOPE(secrets.token_bytes(32), in_range=ValueRange(0, top), out_range=ValueRange(0, 2 ** 64 - 1))
        packed.update(ope=ope, ope_max=top, ope_offset=offset, fscale=fscale, rows=trip,
                      ope_tags=ope.encrypt_list([k - offset for k in keys]))
        cache[(by, fc)] = packed
    return cache[(by, fc)]


def _squares(ds, field, how):
    """(copy of `field` holding (x - c)^2, c) packed like the copy `how` names, for VARIANCE and STDDEV:
    ('all',) the column itself, ('by', fc) its copy in fc order, ('group', g) and ('fgroup', g, fc) its
    GROUP BY copies. Built on first use and kept, like _filtered_groups."""
    col, df, db = ds['columns'][field], ds['df'], ds['db']
    cache = col.setdefault('squares', {})
    if how not in cache:
        fx = lambda xs: [int(round(float(x) * col['scale'])) for x in xs]  # noqa: E731
        labels = None
        if how[0] == 'all':
            xs = fx(df[field].dropna())
            if 'ope' in col:
                xs.sort()
        elif how[0] == 'by':
            rows, fs = df[[field, how[1]]].dropna(), ds['columns'][how[1]]['scale']
            xs = [x for _, x in sorted((int(round(float(y) * fs)), int(round(float(x) * col['scale'])))
                                       for x, y in zip(rows[field], rows[how[1]]))]  # as encrypt_dataset's pairs
        elif how[0] == 'group':
            rows = df[[field, how[1]]].dropna()
            xs, labels = fx(rows[field]), list(rows[how[1]])
        else:
            trip = _filtered_groups(ds, field, how[1], how[2])['rows']
            xs, labels = [a for _, a, _ in trip], [g for _, _, g in trip]
        sq, c = squares(xs)
        packed = (db.encrypt_column(sq) if labels is None else db.packer.encrypt_groups(sq, labels) if how[0] == 'group'
                  else db.packer.encrypt_sorted_groups(sq, labels))
        db.pool.close()
        cache[how] = (packed, c)
    return cache[how]


def _sorted_groups(ds, field, by, fc=None):
    """(copy of `field` sorted within each group of `by`, {label: (first row, end row)}, {label: sorted fc keys})
    for MIN / MAX / MEDIAN GROUP BY by; with fc, sorted by (fc, field) within each group, so the rows with fc in a
    range are one run per group (keys: fc in fixed point). Built on first use and kept."""
    col, df = ds['columns'][field], ds['df']
    cache = col.setdefault('sorted_groups', {})
    if (by, fc) not in cache:
        if fc and (fc not in df.columns or not pd.api.types.is_numeric_dtype(df[fc])):
            raise ValueError(f'Range filters need a numeric column, not {fc}')
        fscale = 1 if not fc or pd.api.types.is_integer_dtype(df[fc]) else 10 ** FIXED_POINT_DECIMALS
        xs, spans, keys = [], {}, {}
        for g, x in df[list(dict.fromkeys([field, by] + ([fc] if fc else [])))].dropna().groupby(by):
            pairs = sorted((int(round(float(w) * fscale)) if fc else 0, int(round(float(v) * col['scale'])))
                           for v, w in zip(x[field], x[fc] if fc else x[field]))
            label = g.item() if hasattr(g, 'item') else g
            spans[label], keys[label] = (len(xs), len(xs) + len(pairs)), [w for w, _ in pairs]
            xs += [v for _, v in pairs]
        packed = ds['db'].encrypt_column(xs)
        ds['db'].pool.close()
        cache[(by, fc)] = (packed, spans, keys, fscale)
    return cache[(by, fc)]


@app.route('/api/query', methods=['POST'])
def execute_query():
    data = request.json or {}
    operation = (data.get('type') or data.get('operation') or '').upper()
    field = data.get('column') or data.get('field')
    filename = data.get('filename')
    range_min = data.get('range_min', data.get('rangeMin'))
    range_max = data.get('range_max', data.get('rangeMax'))
    fc = data.get('filter_column') or data.get('filterColumn') or field  # WHERE fc in [min, max]

    if not operation or not field or not filename:
        return jsonify({'error': 'Missing parameters'}), 400
    if operation not in ('SUM', 'AVG', 'COUNT') + SPREAD and operation not in ORDER_STATS:
        return jsonify({'error': f'Unsupported operation: {operation}'}), 400
    ds = encrypted_datasets.get(filename)
    if ds is None:
        return jsonify({'error': 'Dataset not encrypted yet. Call /api/encrypt first.'}), 404
    col = ds['columns'].get(field)
    if col is None:
        return jsonify({'error': f'Field {field} is not Paillier-encrypted'}), 400

    db = ds['db']
    start = time.perf_counter()
    filtered = range_min not in (None, '') or range_max not in (None, '')
    group_by = data.get('group_by') or data.get('groupBy')
    spread = operation in SPREAD
    response = {}

    def finish(n, s1, s2, c):  # VARIANCE / STDDEV from SUM(x) and SUM((x - c)^2), fixed point
        v = sample_variance(n, s1, s2, c, col['scale'])
        return v if v is None or operation == 'VARIANCE' else v ** 0.5

    if operation in ORDER_STATS and group_by:
        if group_by not in col['groups']:
            return jsonify({'error': f'{operation} GROUP BY needs a column with 2-{GROUP_MAX_VALUES} distinct values'}), 400
        try:
            packed, spans, keys, fscale = _sorted_groups(ds, field, group_by, fc if filtered else None)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        if filtered:  # each group's run of rows with fc in range
            lo = int(round(float(range_min) * fscale)) if range_min not in (None, '') else None
            hi = int(round(float(range_max) * fscale)) if range_max not in (None, '') else None
            spans = {g: (i + (bisect_left(keys[g], lo) if lo is not None else 0),
                         i + (bisect_right(keys[g], hi) if hi is not None else j - i)) for g, (i, j) in spans.items()}
            spans = {g: (i, j) for g, (i, j) in spans.items() if i < j}
        in_order = not filtered or fc == field  # rows in range sorted by value: only the quantile rows are read
        s, cs, q = packed['slots'], packed['ciphertexts'], ORDER_STATS[operation]
        rows = {r for i, j in spans.values() for r in (quantile_rows(i, j, q)[:2] if in_order else range(i, j))}
        cts = list(dict.fromkeys(cs[r // s] for r in sorted(rows)))
        plain = {c: decrypt_crt(db.pub, db.priv, c) for c in cts}
        value = {r: slot_value(plain[cs[r // s]], r % s, packed['slot_bits']) + packed['offset'] for r in rows}
        groups = []
        for g, (i, j) in spans.items():
            vs = value if in_order else dict(enumerate(sorted(value[r] for r in range(i, j)), i))
            a, b, f = quantile_rows(i, j, q)
            groups.append({'group': g, 'count': j - i, 'result': (vs[a] + (vs[b] - vs[a]) * f) / col['scale']})
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return jsonify({
            'success': True, 'operation': operation, 'field': field, 'column': field, 'group_by': group_by,
            'groups': groups, 'result': None, 'pages': 1, 'time_ms': elapsed_ms, 'query_time_ms': elapsed_ms,
            'records_processed': sum(g['count'] for g in groups), 'ciphertexts_aggregated': len(cts),
            'encrypted_computation': True,
            **({'filter_applied': True, 'filter_column': fc, 'range': {'min': range_min, 'max': range_max},
                'records_before_filter': packed['count'],
                'filter_selectivity': sum(g['count'] for g in groups) / max(packed['count'], 1)} if filtered else {}),
            'security_note': f'A copy of {field} sorted within each group: the answer for each group is one row (two for an '
                             'interpolated median), so only the ciphertexts holding them were decrypted. Whoever serves '
                             'them learns which ciphertexts were read, so roughly where each group starts and ends.',
            'encryption_proof': {
                'ciphertext_bit_lengths': [c.bit_length() for c in cts[:3]],
                'modulus_n_bit_length': db.public_key.n.bit_length(),
                'verification': f'{len(cts)} of {len(cs)} packed ciphertexts picked by sorted position and decrypted',
                'computation_type': 'Order statistic per group on a copy sorted within groups',
            },
        })

    if operation in ORDER_STATS:
        if group_by or 'ope' not in col or fc != field:
            return jsonify({'error': f'{operation} needs an OPE+Paillier field (sorted), filtered by itself, '
                                     'without GROUP BY'}), 400
        packed, s = col['packed'], col['packed']['slots']
        i, j = (_tag_range(col['ope_tags'], col['ope'], col['ope_max'], col['scale'], col['offset'], range_min, range_max)
                if filtered else (0, packed['count']))
        result, cts = None, []
        if i < j:
            a, b, frac = quantile_rows(i, j, ORDER_STATS[operation])
            cts = list(dict.fromkeys(packed['ciphertexts'][r // s] for r in (a, b)))
            plain = {c: decrypt_crt(db.pub, db.priv, c) for c in cts}
            va, vb = (slot_value(plain[packed['ciphertexts'][r // s]], r % s, packed['slot_bits']) + packed['offset']
                      for r in (a, b))
            result = (va + (vb - va) * frac) / col['scale']
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return jsonify({
            'success': True, 'operation': operation, 'field': field, 'column': field, 'result': result,
            'time_ms': elapsed_ms, 'query_time_ms': elapsed_ms, 'records_processed': j - i,
            'ciphertexts_aggregated': len(cts), 'encrypted_computation': True,
            **({'filter_applied': True, 'filter_column': fc, 'range': {'min': range_min, 'max': range_max},
                'records_before_filter': packed['count'], 'filter_selectivity': (j - i) / max(packed['count'], 1)}
               if filtered else {}),
            'security_note': 'The column is packed in sorted order, so this is one row (two for an interpolated '
                             'median): its ciphertext was decrypted on its own, which shows the key holder the '
                             'other values in that ciphertext. OPE tags reveal the order of values.',
            'encryption_proof': {
                'ciphertext_bit_lengths': [c.bit_length() for c in cts],
                'modulus_n_bit_length': db.public_key.n.bit_length(),
                'verification': f'{len(cts)} packed ciphertext(s) picked by sorted position and decrypted; no other '
                                'ciphertext was decrypted',
                'computation_type': 'Order statistic on a sorted packed column',
            },
        })

    if group_by:
        packed = col['groups'].get(group_by)
        if packed is None:
            return jsonify({'error': f'No GROUP BY copy of {field} by {group_by} (needs 2-{GROUP_MAX_VALUES} '
                                     'distinct values and rows with both)'}), 400
        if filtered:
            try:
                packed = _filtered_groups(ds, field, group_by, fc)
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            i, j = _tag_range(packed['ope_tags'], packed['ope'], packed['ope_max'], packed['fscale'],
                              packed['ope_offset'], range_min, range_max)
            lanes, pages = packed['lanes'], group_pages(packed)
            plans = [range_plan(db.pub, p, lanes, packed['count'], i, j) if i < j else (None, []) for p in pages]
            sums = decrypt_sorted_groups(db.pub, db.priv, plans, packed)
            cts = [c for p in pages for c in p[i // lanes:(j - 1) // lanes + 1]] if i < j else []
            if spread:
                sq, shift = _squares(ds, field, ('fgroup', group_by, fc))
                sums2 = decrypt_sorted_groups(db.pub, db.priv, [
                    range_plan(db.pub, p, sq['lanes'], sq['count'], i, j) if i < j else (None, []) for p in group_pages(sq)], sq)
            response.update(filter_applied=True, filter_column=fc, range={'min': range_min, 'max': range_max},
                            records_before_filter=packed['count'], filter_selectivity=(j - i) / packed['count'])
        else:
            sums = db.packer.sum_groups(packed)
            cts = packed['ciphertexts']
            if spread:
                sq, shift = _squares(ds, field, ('group', group_by))
                sums2 = db.packer.sum_groups(sq)
        sc = col['scale']
        groups = [{'group': g, 'sum': s / sc, 'count': c, 'avg': s / sc / c if c else 0} for g, (s, c) in sums.items()]
        for x in groups:
            x['result'] = (finish(x['count'], sums[x['group']][0], sums2[x['group']][0], shift) if spread
                           else {'SUM': x['sum'], 'AVG': x['avg'], 'COUNT': x['count']}[operation])
        count = sum(c for _, c in sums.values())
        total_scaled = sum(s for s, _ in sums.values())
        total2 = sum(s for s, _ in sums2.values()) if spread else 0
        pages = packed.get('pages', 1)
        per_page = f' per page of groups ({pages} pages)' if pages > 1 else ''
        response.update(group_by=group_by, groups=groups, pages=pages, security_note=(
            f'The ciphertexts inside the range are multiplied and decrypted once{per_page}, the <=2 cut by its edges '
            f'on their own. OPE tags of {fc} reveal its order; the ciphertexts alone reveal no labels or group sizes.'
            if filtered else
            f'One product of the ciphertexts and one decryption{per_page}: every group sum and count comes out of its '
            'own slots. The ciphertexts alone reveal no labels or group sizes.'))
    elif filtered:
        fcol = ds['columns'].get(fc)
        if fcol is None or 'ope' not in fcol:
            return jsonify({'error': f'Range filters need {fc} encrypted as OPE+Paillier'}), 400
        if fc == field:
            packed, tags = col['packed'], fcol['ope_tags']
        elif field in fcol['by']:
            packed, tags = fcol['by'][field]['packed'], fcol['by'][field]['tags']
        else:
            return jsonify({'error': f'No rows have both {field} and {fc}'}), 400
        i, j = _tag_range(tags, fcol['ope'], fcol['ope_max'], fcol['scale'], fcol['offset'], range_min, range_max)
        count, s = j - i, packed['slots']
        cts = packed['ciphertexts'][i // s:(j - 1) // s + 1] if count else []
        total_scaled = db.packer.sum_range(packed, i, j) if operation != 'COUNT' else 0
        if spread:
            sq, shift = _squares(ds, field, ('all',) if fc == field else ('by', fc))
            total2 = db.packer.sum_range(sq, i, j)
        response.update(filter_applied=True, filter_column=fc, range={'min': range_min, 'max': range_max},
                        records_before_filter=packed['count'],
                        filter_selectivity=count / max(packed['count'], 1),
                        security_note='OPE tags reveal the order of values to whoever holds them; '
                                      'the key holder also sees the slots of the <=2 ciphertexts cut by the range edges')
    else:
        cts = col['packed']['ciphertexts']
        count = col['packed']['count']
        total_scaled = db.sum_column(col['packed']) if operation != 'COUNT' else 0
        if spread:
            sq, shift = _squares(ds, field, ('all',))
            total2 = db.sum_column(sq)

    total = total_scaled / col['scale'] if col['scale'] != 1 else total_scaled
    result = (finish(count, total_scaled, total2, shift) if spread else {'SUM': total, 'AVG': (total / count) if count else 0, 'COUNT': count}[operation])
    elapsed_ms = (time.perf_counter() - start) * 1000

    response.update({
        'success': True, 'operation': operation, 'field': field, 'column': field,
        'result': None if result is None else float(result), 'time_ms': round(elapsed_ms, 2), 'query_time_ms': round(elapsed_ms, 2),
        'records_processed': count, 'ciphertexts_aggregated': len(cts) if operation != 'COUNT' or group_by else 0,
        'encrypted_computation': operation != 'COUNT' or bool(group_by),
        'encryption_proof': {
            'ciphertext_bit_lengths': [c.bit_length() for c in cts[:3]],
            'modulus_n_bit_length': db.public_key.n.bit_length(),
            'verification': f'{len(cts)} packed ciphertexts: whole ones multiplied mod n^2 and decrypted once'
                            + ('; range-edge ones decrypted separately' if filtered else ''),
            'computation_type': 'Paillier homomorphic addition',
        },
    })
    return jsonify(response)


@app.route('/api/databases', methods=['GET'])
def list_databases():
    return jsonify({'databases': [
        {'filename': name, 'records': ds['record_count'], 'paillier_fields': list(ds['columns'])}
        for name, ds in encrypted_datasets.items()]})


# ---- client-held keys: public key + ciphertexts in, ciphertexts out ------------------------
# dataset -> {'pub': PaillierPublicKey, 'columns': {name: {'cts', 'slots', 'count', 'tags'}}}
owner_datasets = {}
STORE_PATH = os.environ.get('AGNIYA_STORE', os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                         'agniya_store.sqlite3'))
TAG_BYTES = 8  # OPE tags live in [0, 2^64)
MAC_BYTES = 16  # client MACs of each ciphertext's OPE tags (truncated HMAC-SHA256)
STORE_MAX_BYTES = int(float(os.environ.get('AGNIYA_STORE_MAX_MB', '1024')) * 2**20)  # ciphertexts + tags


def _store():
    con = sqlite3.connect(STORE_PATH)
    con.execute('CREATE TABLE IF NOT EXISTS columns (dataset TEXT, name TEXT, n TEXT, slots INTEGER, '
                'count INTEGER, cts BLOB, tags BLOB, macs BLOB, PRIMARY KEY (dataset, name))')
    if 'macs' not in [r[1] for r in con.execute('PRAGMA table_info(columns)')]:  # stores from before tag MACs
        con.execute('ALTER TABLE columns ADD COLUMN macs BLOB')
    con.execute('CREATE TABLE IF NOT EXISTS owners (dataset TEXT PRIMARY KEY, token_hash TEXT)')
    return con


def _token_hash(d):
    t = d.get('token')
    return hashlib.sha256(t.encode()).hexdigest() if isinstance(t, str) and len(t) >= 32 else None


def _deny(name, d):
    """None when request body d carries dataset name's token, else an error response. A dataset
    stored before tokens existed is claimed by the first token sent for it."""
    h, ds = _token_hash(d), owner_datasets[name]
    if h is None:
        return jsonify({'error': 'This dataset needs its token (sent by AgniyaClient and the dashboard)'}), 401
    if ds.get('token_hash') is None:
        with closing(_store()) as con, con:
            con.execute('INSERT OR REPLACE INTO owners VALUES (?, ?)', (name, h))
        ds['token_hash'] = h
    elif not hmac.compare_digest(h, ds['token_hash']):
        return jsonify({'error': 'Wrong token for this dataset'}), 403
    return None


def _pack(xs, width):
    return b''.join(x.to_bytes(width, 'big') for x in xs)


def _unpack(blob, width):
    return [int.from_bytes(blob[i:i + width], 'big') for i in range(0, len(blob), width)]


def _public_key(n):
    return PaillierPublicKey(n, n + 1, n * n, n.bit_length())


def load_store():
    """Rebuild owner_datasets from the SQLite store (runs at import, i.e. at server start)."""
    owner_datasets.clear()
    with closing(_store()) as con:
        for dataset, name, n, slots, count, cts, tags, macs in con.execute(
                'SELECT dataset, name, n, slots, count, cts, tags, macs FROM columns'):
            pub = _public_key(int(n, 16))
            ds = owner_datasets.setdefault(dataset, {'pub': pub, 'columns': {}})
            ds['columns'][name] = {'cts': _unpack(cts, (pub.n_squared.bit_length() + 7) // 8), 'slots': slots,
                                   'count': count, 'tags': _unpack(tags, TAG_BYTES) if tags is not None else None,
                                   'macs': _unpack(macs, MAC_BYTES) if macs is not None else None}
        for dataset, h in con.execute('SELECT dataset, token_hash FROM owners'):
            if dataset in owner_datasets:
                owner_datasets[dataset]['token_hash'] = h


def _hex_ints(xs, bound, what):
    out = [int(x, 16) for x in xs]
    if any(not 0 < v < bound for v in out):
        raise ValueError(f'{what} out of range')
    return out


@app.route('/api/v2/columns', methods=['POST'])
def v2_store_column():
    d = request.json or {}
    try:
        name, column = str(d['dataset']), str(d['column'])
        n = int(d['n'], 16)
        if n.bit_length() < MIN_KEY_BITS or n % 2 == 0:
            raise ValueError(f'n must be an odd modulus of at least {MIN_KEY_BITS} bits')
        cts = _hex_ints(d['ciphertexts'], n * n, 'ciphertext')
        slots, count = int(d['slots']), int(d['count'])
        if slots < 1 or not slots * (len(cts) - 1) < count <= slots * len(cts):
            raise ValueError('count does not match ciphertexts and slots')
        tags = d.get('ope_tags')
        if tags is not None:
            tags = [int(t) for t in tags]
            if len(tags) != count or any(a > b for a, b in zip(tags, tags[1:]))                     or (tags and not 0 <= tags[0] <= tags[-1] < 2 ** (8 * TAG_BYTES)):
                raise ValueError('ope_tags must be sorted 64-bit values, one per value')
        macs = d.get('tag_macs')  # the client's MAC of each ciphertext's OPE tags, returned with range answers
        if macs is not None:
            macs = [int(x, 16) for x in macs]
            if tags is None or len(macs) != len(cts) or any(not 0 <= x < 2 ** (8 * MAC_BYTES) for x in macs):
                raise ValueError('tag_macs must be one 16-byte hex MAC per ciphertext, with ope_tags')
    except (KeyError, TypeError, ValueError) as e:
        return jsonify({'error': f'Bad column upload: {e}'}), 400
    ds, h = owner_datasets.get(name), _token_hash(d)
    if ds is None and h is None:
        return jsonify({'error': 'A new dataset needs a token (sent by AgniyaClient and the dashboard)'}), 401
    if ds is not None:
        denied = _deny(name, d)
        if denied:
            return denied
        if ds['pub'].n != n:
            return jsonify({'error': f'Dataset {name} uses a different public key'}), 409
    pub = ds['pub'] if ds else _public_key(n)
    cts_blob = _pack(cts, (pub.n_squared.bit_length() + 7) // 8)
    tags_blob = _pack(tags, TAG_BYTES) if tags is not None else None
    macs_blob = _pack(macs, MAC_BYTES) if macs is not None else None
    with closing(_store()) as con, con:  # committed to disk before we answer
        used = con.execute('SELECT COALESCE(SUM(LENGTH(cts) + COALESCE(LENGTH(tags), 0) + COALESCE(LENGTH(macs), 0)), 0) '
                           'FROM columns WHERE NOT (dataset = ? AND name = ?)', (name, column)).fetchone()[0]
        if used + len(cts_blob) + len(tags_blob or b'') + len(macs_blob or b'') > STORE_MAX_BYTES:
            return jsonify({'error': f'Store limit of {STORE_MAX_BYTES // 2**20} MB reached '
                                     '(AGNIYA_STORE_MAX_MB); delete a dataset first'}), 507
        con.execute('INSERT OR REPLACE INTO columns (dataset, name, n, slots, count, cts, tags, macs) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (name, column, format(n, 'x'), slots, count, cts_blob, tags_blob, macs_blob))
        if ds is None:
            con.execute('INSERT OR REPLACE INTO owners VALUES (?, ?)', (name, h))
    ds = owner_datasets.setdefault(name, {'pub': pub, 'columns': {}, 'token_hash': h})
    ds['columns'][column] = {'cts': cts, 'slots': slots, 'count': count, 'tags': tags, 'macs': macs}
    return jsonify({'success': True, 'dataset': name, 'column': column, 'ciphertexts': len(cts),
                    'count': count, 'range_filterable': tags is not None})


@app.route('/api/v2/delete', methods=['POST'])
def v2_delete_dataset():
    """Delete a dataset (all its columns) from memory and the store; needs the dataset's token."""
    d = request.json or {}
    name = d.get('dataset')
    ds = owner_datasets.get(name)
    if ds is None:
        return jsonify({'error': 'Unknown dataset'}), 404
    denied = _deny(name, d)
    if denied:
        return denied
    with closing(_store()) as con, con:
        con.execute('DELETE FROM columns WHERE dataset = ?', (name,))
        con.execute('DELETE FROM owners WHERE dataset = ?', (name,))
    del owner_datasets[name]
    return jsonify({'success': True, 'dataset': name, 'columns_deleted': len(ds['columns'])})


def _v2_column(d):
    """(dataset, column, error response) for body d, checking the dataset's token."""
    ds = owner_datasets.get(d.get('dataset'))
    col = ds['columns'].get(d.get('column')) if ds else None
    if col is None:
        return None, None, (jsonify({'error': 'Unknown dataset or column'}), 404)
    return ds, col, _deny(d['dataset'], d)


def _v2_rows(col, d):
    """(i, j, witnesses, error response): rows i..j-1 have OPE tags in [lo_tag, hi_tag] (all rows without
    them); witnesses are the ciphertexts around both ends with their tags and the client's MACs."""
    i, j = 0, col['count']
    ranged = d.get('lo_tag') is not None or d.get('hi_tag') is not None
    if ranged:
        if col['tags'] is None:
            return 0, 0, [], (jsonify({'error': 'Column was uploaded without OPE tags'}), 400)
        try:
            if d.get('lo_tag') is not None:
                i = bisect_left(col['tags'], int(d['lo_tag']))
            if d.get('hi_tag') is not None:
                j = max(i, bisect_right(col['tags'], int(d['hi_tag'])))
        except (TypeError, ValueError):
            return 0, 0, [], (jsonify({'error': 'Tags must be integers'}), 400)
    s, witnesses = col['slots'], []
    if ranged and col.get('macs'):
        for c in sorted({r // s for r in (i - 1, i, j - 1, j) if 0 <= r < col['count']}):
            witnesses.append({'index': c, 'tags': [str(t) for t in col['tags'][c * s:(c + 1) * s]],
                              'mac': format(col['macs'][c], '032x')})
    return i, j, witnesses, None


@app.route('/api/v2/quantiles', methods=['POST'])
def v2_quantiles():
    """MIN / MAX / MEDIAN / any quantile of a sorted (OPE-tagged) column, optionally over rows with tags in
    [lo_tag, hi_tag]: for each q in `q` the stored ciphertexts of rows a and b of quantile_rows (pandas'
    linear interpolation). The client decrypts them, checks their integrity tags and reads one slot each."""
    d = request.json or {}
    _, col, err = _v2_column(d)
    if err:
        return err
    if col['tags'] is None:
        return jsonify({'error': 'Quantiles need a column uploaded with range_filter=True (sorted)'}), 400
    try:
        qs = [float(q) for q in d['q']]
        if not 0 < len(qs) <= 101 or any(not 0 <= q <= 1 for q in qs):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        return jsonify({'error': 'q must be 1-101 numbers in [0, 1]'}), 400
    start = time.perf_counter()
    i, j, witnesses, err = _v2_rows(col, d)
    if err:
        return err
    rows = sorted({r for q in qs for r in quantile_rows(i, j, q)[:2]}) if i < j else []
    s = col['slots']
    return jsonify({'count': j - i, 'rows': [i, j], 'witnesses': witnesses,
                    'cells': [{'row': r, 'ciphertext': format(col['cts'][r // s], 'x')} for r in rows],
                    'time_ms': round((time.perf_counter() - start) * 1000, 2)})


@app.route('/api/v2/ciphertexts', methods=['POST'])
def v2_ciphertexts():
    """Stored ciphertexts of a column by index (`index`: up to 4096 of them), e.g. the ones holding each group's
    quantile rows in a copy sorted within groups. The client checks each one's integrity tag."""
    d = request.json or {}
    _, col, err = _v2_column(d)
    if err:
        return err
    try:
        ks = [int(k) for k in d['index']]
        if not 0 < len(ks) <= 4096 or any(not 0 <= k < len(col['cts']) for k in ks):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        return jsonify({'error': f"index must be 1-4096 ciphertext indices below {len(col['cts'])}"}), 400
    return jsonify({'ciphertexts': [format(col['cts'][k], 'x') for k in ks]})


@app.route('/api/v2/ranges', methods=['POST'])
def v2_ranges():
    """Row ranges for several (lo_tag, hi_tag) pairs on one OPE-tagged column (`ranges`: up to 1024), each with
    the witnesses that let the client check the cut, e.g. one range per group of a copy sorted within groups."""
    d = request.json or {}
    _, col, err = _v2_column(d)
    if err:
        return err
    rs = d.get('ranges')
    if not isinstance(rs, list) or not 0 < len(rs) <= 1024 or not all(isinstance(r, dict) for r in rs):
        return jsonify({'error': 'ranges must be 1-1024 objects with lo_tag / hi_tag'}), 400
    out = []
    for r in rs:
        i, j, witnesses, err = _v2_rows(col, r)
        if err:
            return err
        out.append({'rows': [i, j], 'witnesses': witnesses})
    return jsonify({'ranges': out})


@app.route('/api/v2/aggregate', methods=['POST'])
def v2_aggregate():
    """Encrypted SUM over a column, optionally over rows whose OPE tag is in [lo_tag, hi_tag]. `rows` is
    the row range used; with a range on a column with tag MACs, `witnesses` are the ciphertexts around
    its ends with their rows' OPE tags and MACs, so the client can check where the range was cut."""
    d = request.json or {}
    ds, col, err = _v2_column(d)
    if err:
        return err
    start = time.perf_counter()
    i, j, witnesses, err = _v2_rows(col, d)
    if err:
        return err
    product, edges = range_plan(ds['pub'], col['cts'], col['slots'], col['count'], i, j) if i < j else (None, [])
    s = col['slots']
    return jsonify({
        'count': j - i, 'rows': [i, j], 'witnesses': witnesses,
        'product': format(product, 'x') if product is not None else None,
        'edges': [{'ciphertext': format(c, 'x'), 'first_slot': lo, 'end_slot': hi} for c, lo, hi in edges],
        'ciphertexts_used': (j - 1) // s - i // s + 1 if i < j else 0,
        'time_ms': round((time.perf_counter() - start) * 1000, 2),
    })


load_store()

if __name__ == '__main__':
    host = os.environ.get('AGNIYA_HOST', '127.0.0.1')
    debug = os.environ.get('AGNIYA_DEBUG') == '1'  # never expose the Werkzeug debugger on a network
    print(f"AGNIYA API on http://{host}:5000 (debug={debug})")
    app.run(debug=debug, host=host, port=5000)
