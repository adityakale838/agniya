"""
AGNIYA API server (Flask). Launched by start.ps1.

What it does, precisely:
- /api/upload   : stores a CSV, suggests per-column encryption
- /api/encrypt  : encrypts every Paillier column with fresh randomness (packed: many
                  values per ciphertext). 'OPE+Paillier' columns are packed in sorted
                  order and get one OPE tag per row, so a range is a run of slots
- /api/query    : SUM / AVG / COUNT computed by multiplying ciphertexts, then ONE decryption

Two trust models:
- /api/upload, /api/encrypt, /api/query (dashboard demo): this process receives the plaintext
  CSV and generates and holds the private key in memory. It is the data owner.
- /api/v2/columns, /api/v2/aggregate (use agniya.client.AgniyaClient): the client keeps the
  private key and the OPE keys. This process only ever sees the public modulus n, packed
  ciphertexts, values per ciphertext, row counts and sorted OPE tags, and returns ciphertexts.
  It is honest-but-curious: nothing here protects the integrity of results.
  Its columns persist in SQLite at AGNIYA_STORE (default api/agniya_store.sqlite3) and are
  reloaded at start-up. The demo datasets are NOT persisted: they include the private key.
Decimal columns are stored as fixed-point integers with FIXED_POINT_DECIMALS digits.
"""

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
from agniya.core.paillier import MIN_KEY_BITS, PaillierPublicKey, generate_keypair
from agniya.core.batch_packing import decrypt_sorted_groups, group_pages, range_plan
from agniya.hybrid.fast_ope import FastOPE

FIXED_POINT_DECIMALS = 4
PAILLIER_TYPES = {'Paillier-2048', 'OPE+Paillier'}
GROUP_MAX_VALUES = 64  # GROUP BY copies are built for columns with at most this many distinct values

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
        packed.update(ope=ope, ope_max=top, ope_offset=offset, fscale=fscale,
                      ope_tags=ope.encrypt_list([k - offset for k in keys]))
        cache[(by, fc)] = packed
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
    if operation not in ('SUM', 'AVG', 'COUNT'):
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
    response = {}

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
            response.update(filter_applied=True, filter_column=fc, range={'min': range_min, 'max': range_max},
                            records_before_filter=packed['count'], filter_selectivity=(j - i) / packed['count'])
        else:
            sums = db.packer.sum_groups(packed)
            cts = packed['ciphertexts']
        sc = col['scale']
        groups = [{'group': g, 'sum': s / sc, 'count': c, 'avg': s / sc / c if c else 0} for g, (s, c) in sums.items()]
        for x in groups:
            x['result'] = {'SUM': x['sum'], 'AVG': x['avg'], 'COUNT': x['count']}[operation]
        count = sum(c for _, c in sums.values())
        total_scaled = sum(s for s, _ in sums.values())
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
        response.update(filter_applied=True, filter_column=fc, range={'min': range_min, 'max': range_max},
                        records_before_filter=packed['count'],
                        filter_selectivity=count / max(packed['count'], 1),
                        security_note='OPE tags reveal the order of values to whoever holds them; '
                                      'the key holder also sees the slots of the <=2 ciphertexts cut by the range edges')
    else:
        cts = col['packed']['ciphertexts']
        count = col['packed']['count']
        total_scaled = db.sum_column(col['packed']) if operation != 'COUNT' else 0

    total = total_scaled / col['scale'] if col['scale'] != 1 else total_scaled
    result = {'SUM': total, 'AVG': (total / count) if count else 0, 'COUNT': count}[operation]
    elapsed_ms = (time.perf_counter() - start) * 1000

    response.update({
        'success': True, 'operation': operation, 'field': field, 'column': field,
        'result': float(result), 'time_ms': round(elapsed_ms, 2), 'query_time_ms': round(elapsed_ms, 2),
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
    return con


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
    ds = owner_datasets.get(name)
    if ds is not None and ds['pub'].n != n:
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
    ds = owner_datasets.setdefault(name, {'pub': pub, 'columns': {}})
    ds['columns'][column] = {'cts': cts, 'slots': slots, 'count': count, 'tags': tags, 'macs': macs}
    return jsonify({'success': True, 'dataset': name, 'column': column, 'ciphertexts': len(cts),
                    'count': count, 'range_filterable': tags is not None})


@app.route('/api/v2/delete', methods=['POST'])
def v2_delete_dataset():
    """Delete a dataset (all its columns) from memory and the store. The caller must send the
    dataset's modulus n, the same ownership check as uploads (the API has no authentication)."""
    d = request.json or {}
    name = d.get('dataset')
    ds = owner_datasets.get(name)
    if ds is None:
        return jsonify({'error': 'Unknown dataset'}), 404
    try:
        n = int(str(d.get('n')), 16)
    except ValueError:
        return jsonify({'error': 'n must be hex'}), 400
    if n != ds['pub'].n:
        return jsonify({'error': 'n does not match this dataset'}), 403
    with closing(_store()) as con, con:
        con.execute('DELETE FROM columns WHERE dataset = ?', (name,))
    del owner_datasets[name]
    return jsonify({'success': True, 'dataset': name, 'columns_deleted': len(ds['columns'])})


@app.route('/api/v2/aggregate', methods=['POST'])
def v2_aggregate():
    """Encrypted SUM over a column, optionally over rows whose OPE tag is in [lo_tag, hi_tag]. `rows` is
    the row range used; with a range on a column with tag MACs, `witnesses` are the ciphertexts around
    its ends with their rows' OPE tags and MACs, so the client can check where the range was cut."""
    d = request.json or {}
    ds = owner_datasets.get(d.get('dataset'))
    col = ds['columns'].get(d.get('column')) if ds else None
    if col is None:
        return jsonify({'error': 'Unknown dataset or column'}), 404
    start = time.perf_counter()
    i, j = 0, col['count']
    if d.get('lo_tag') is not None or d.get('hi_tag') is not None:
        if col['tags'] is None:
            return jsonify({'error': 'Column was uploaded without OPE tags'}), 400
        try:
            if d.get('lo_tag') is not None:
                i = bisect_left(col['tags'], int(d['lo_tag']))
            if d.get('hi_tag') is not None:
                j = bisect_right(col['tags'], int(d['hi_tag']))
        except (TypeError, ValueError):
            return jsonify({'error': 'Tags must be integers'}), 400
    product, edges = range_plan(ds['pub'], col['cts'], col['slots'], col['count'], i, j) if i < j else (None, [])
    s = col['slots']
    j = max(i, j)
    witnesses = []
    if col.get('macs') and (d.get('lo_tag') is not None or d.get('hi_tag') is not None):
        for c in sorted({r // s for r in (i - 1, i, j - 1, j) if 0 <= r < col['count']}):
            witnesses.append({'index': c, 'tags': [str(t) for t in col['tags'][c * s:(c + 1) * s]],
                              'mac': format(col['macs'][c], '032x')})
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
