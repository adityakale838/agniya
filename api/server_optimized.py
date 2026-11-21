"""
AGNIYA API server (Flask). Launched by start.ps1.

What it does, precisely:
- /api/upload   : stores a CSV, suggests per-column encryption
- /api/encrypt  : encrypts every Paillier column with fresh randomness (packed: many
                  values per ciphertext). 'OPE+Paillier' columns are packed in sorted
                  order and get one OPE tag per row, so a range is a run of slots
- /api/query    : SUM / AVG / COUNT computed by multiplying ciphertexts, then ONE decryption

Trust model (demo): this process generates and holds the private key in memory only.
It is the data owner, not an untrusted server. Keys are never written to disk.
Decimal columns are stored as fixed-point integers with FIXED_POINT_DECIMALS digits.
"""

import os
import sys
import time
import secrets
from bisect import bisect_left, bisect_right

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pyope.ope import ValueRange

from agniya.core.ultimate_system import UltimateOptimizedDatabase
from agniya.hybrid.fast_ope import FastOPE

FIXED_POINT_DECIMALS = 4
PAILLIER_TYPES = {'Paillier-2048', 'OPE+Paillier'}

app = Flask(__name__)
CORS(app, origins=os.environ.get('AGNIYA_CORS_ORIGINS', 'http://localhost:3000').split(','))

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
    db = UltimateOptimizedDatabase(key_size=2048)
    columns, total_cts = {}, 0
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
            state.update(offset=offset, ope=ope, ope_max=top,
                         ope_tags=ope.encrypt_list([v - offset for v in values]))  # sorted, like values
        columns[name] = state

    db.pool.close()  # release worker processes; queries need no new randomness
    elapsed = time.perf_counter() - start
    encrypted_datasets[filename] ={'db': db, 'columns': columns, 'record_count': len(df)}
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
                       'range_filterable': 'ope' in c} for n, c in columns.items()},
        'key_bits': db.public_key.n.bit_length(),
    })


@app.route('/api/query', methods=['POST'])
def execute_query():
    data = request.json or {}
    operation = (data.get('type') or data.get('operation') or '').upper()
    field = data.get('column') or data.get('field')
    filename = data.get('filename')
    range_min = data.get('range_min', data.get('rangeMin'))
    range_max = data.get('range_max', data.get('rangeMax'))

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
    response = {}

    if filtered:
        if 'ope' not in col:
            return jsonify({'error': f'Range filters need the column encrypted as OPE+Paillier'}), 400
        scale, offset, ope, top = col['scale'], col['offset'], col['ope'], col['ope_max']
        shift = lambda v: int(round(float(v) * scale)) - offset
        lo_s = shift(range_min) if range_min not in (None, '') else 0
        hi_s = shift(range_max) if range_max not in (None, '') else top
        if lo_s > top or hi_s < 0 or lo_s > hi_s:
            idx = None
        else:
            tags = col['ope_tags']
            idx = (bisect_left(tags, ope.encrypt(max(lo_s, 0))), bisect_right(tags, ope.encrypt(min(hi_s, top))))
        i, j = idx or (0, 0)
        count, s = j - i, col['packed']['slots']
        cts = col['packed']['ciphertexts'][i // s:(j - 1) // s + 1] if count else []
        total_scaled = db.packer.sum_range(col['packed'], i, j) if operation != 'COUNT' else 0
        response.update(filter_applied=True, range={'min': range_min, 'max': range_max},
                        records_before_filter=col['packed']['count'],
                        filter_selectivity=count / max(col['packed']['count'], 1),
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
        'records_processed': count, 'ciphertexts_aggregated': len(cts) if operation != 'COUNT' else 0,
        'encrypted_computation': operation != 'COUNT',
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


if __name__ == '__main__':
    host = os.environ.get('AGNIYA_HOST', '127.0.0.1')
    debug = os.environ.get('AGNIYA_DEBUG') == '1'  # never expose the Werkzeug debugger on a network
    print(f"AGNIYA API on http://{host}:5000 (debug={debug})")
    app.run(debug=debug, host=host, port=5000)
