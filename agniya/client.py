"""
Data-owner client for the /api/v2 endpoints of api/server_optimized.py.

The Paillier private key, the OPE keys and every plaintext stay in this object. The server
receives: the public modulus n, packed ciphertexts, values per ciphertext, the row count and,
for range-filterable columns, one OPE tag per row in sorted order. Queries come back as
ciphertexts and are decrypted here.

    c = AgniyaClient("http://127.0.0.1:5000", dataset="claims")
    c.upload("charges", charges, decimals=4, range_filter=True)
    c.query("charges")                       # {'sum', 'count', 'avg'}
    c.query("charges", lo=5000, hi=20000)    # rows with 5000 <= charges <= 20000
    c.upload_by("charges", charges, by="age", by_values=ages, decimals=4)
    c.query("charges", lo=30, hi=45, by="age")  # SUM(charges) WHERE 30 <= age <= 45

    c.save("claims.agniya-key", password)    # scrypt + AES-256-GCM; losing it loses the data
    c = AgniyaClient.load("claims.agniya-key", password, "http://127.0.0.1:5000")

The server is trusted to compute correctly (honest-but-curious), not to see data.
"""

import base64
import hashlib
import json
import os
import secrets
import urllib.error
import urllib.request
from typing import Callable, Dict, Iterable, Optional, Union

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pyope.ope import ValueRange

from agniya.core.batch_packing import BatchedAggregator, decrypt_range
from agniya.core.paillier import generate_keypair, is_djn_admissible, keypair_from_primes
from agniya.core.precomputation import RandomnessPool
from agniya.hybrid.fast_ope import FastOPE

Transport = Callable[[str, dict], dict]  # (path, json body) -> json response; raises on errors
KEY_FILE_FORMAT = 'agniya-client-key/1'
SCRYPT = {'n': 2 ** 17, 'r': 8, 'p': 1}  # 128 MiB, ~0.3-0.5 s per save/load: slows password guessing


def _file_key(password: str, salt: bytes, kdf: dict) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=kdf['n'], r=kdf['r'], p=kdf['p'],
                          maxmem=256 * 1024 * 1024, dklen=32)


def http_transport(base_url: str) -> Transport:
    def post(path: str, body: dict) -> dict:
        req = urllib.request.Request(base_url.rstrip('/') + path, data=json.dumps(body).encode(),
                                     headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"{e.code}: {json.load(e).get('error')}") from None
    return post


class AgniyaClient:
    def __init__(self, server: Union[str, Transport], dataset: str, key_size: int = 2048, _keys=None):
        self.post = http_transport(server) if isinstance(server, str) else server
        self.dataset = dataset
        self.pub, self.priv = _keys or generate_keypair(key_size)
        self.columns: Dict[str, dict] = {}  # client-only: scale, offsets, slot bits, OPE key
        self._djn_ok = is_djn_admissible(self.priv)

    def save(self, path: str, password: str):
        """Write every secret this client holds (Paillier primes, OPE keys, column layouts) to
        `path`, encrypted with AES-256-GCM under a scrypt key derived from `password`."""
        if not password:
            raise ValueError('A password is required')
        cols = {}
        for name, m in self.columns.items():
            c = {k: m[k] for k in ('scale', 'fscale', 'slot_bits', 'slots', 'offset', 'count') if k in m}
            if 'ope' in m:
                c.update(ope_key=base64.b64encode(m['ope'].key).decode(), ope_offset=m['ope_offset'], ope_top=m['ope_top'])
            cols[name] = c
        secret = json.dumps({'dataset': self.dataset, 'p': format(self.priv.p, 'x'),
                             'q': format(self.priv.q, 'x'), 'columns': cols}).encode()
        salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
        header = {'format': KEY_FILE_FORMAT, 'kdf': {'name': 'scrypt', **SCRYPT, 'salt': base64.b64encode(salt).decode()}}
        aad = json.dumps(header, sort_keys=True).encode()  # header is authenticated too
        ct = AESGCM(_file_key(password, salt, SCRYPT)).encrypt(nonce, secret, aad)
        tmp = f'{path}.tmp'
        with open(tmp, 'w') as f:
            json.dump({**header, 'nonce': base64.b64encode(nonce).decode(),
                       'ciphertext': base64.b64encode(ct).decode()}, f)
        os.replace(tmp, path)  # never leave a half-written key file behind

    @classmethod
    def load(cls, path: str, password: str, server: Union[str, Transport]) -> 'AgniyaClient':
        """Restore a client written by save(); raises ValueError on a wrong password or a modified file."""
        with open(path) as f:
            d = json.load(f)
        if d.get('format') != KEY_FILE_FORMAT or d.get('kdf', {}).get('name') != 'scrypt':
            raise ValueError('Not an AGNIYA client key file')
        kdf = d['kdf']
        aad = json.dumps({'format': d['format'], 'kdf': kdf}, sort_keys=True).encode()
        try:
            secret = json.loads(AESGCM(_file_key(password, base64.b64decode(kdf['salt']), kdf)).decrypt(
                base64.b64decode(d['nonce']), base64.b64decode(d['ciphertext']), aad))
        except InvalidTag:
            raise ValueError('Wrong password or modified key file') from None
        c = cls(server, secret['dataset'], _keys=keypair_from_primes(int(secret['p'], 16), int(secret['q'], 16)))
        for name, m in secret['columns'].items():
            if 'ope_key' in m:
                m['ope'] = FastOPE(base64.b64decode(m.pop('ope_key')), in_range=ValueRange(0, m['ope_top']),
                                   out_range=ValueRange(0, 2 ** 64 - 1))
            c.columns[name] = m
        return c

    def upload(self, column: str, values: Iterable[float], decimals: int = 0,
               range_filter: bool = False) -> dict:
        """Encrypt a numeric column here and store only ciphertexts (and OPE tags) on the server."""
        scale = 10 ** decimals
        ints = [int(round(v * scale)) for v in values]  # fixed point; NaN raises
        if range_filter:
            ints.sort()  # sorted packing: a value range is a contiguous run of slots
        return self._upload(column, ints, scale, ints if range_filter else None, scale)

    def upload_by(self, column: str, values: Iterable[float], by: str, by_values: Iterable[float],
                  decimals: int = 0, by_decimals: int = 0) -> dict:
        """Store `column` packed in the order of `by` (one row each, same order), so that
        query(column, lo, hi, by=by) sums `column` over rows with lo <= by <= hi. Rows where either
        value is missing (None/NaN) are left out. The server gets OPE tags of `by` under a fresh key."""
        s, fs = 10 ** decimals, 10 ** by_decimals
        rows = sorted((int(round(b * fs)), int(round(a * s))) for a, b in zip(values, by_values, strict=True)
                      if a is not None and b is not None and a == a and b == b)  # x == x is False for NaN
        return self._upload(f'{column}|{by}', [a for _, a in rows], s, [b for b, _ in rows], fs)

    def _upload(self, name: str, ints: list, scale: int, keys: Optional[list], fscale: int) -> dict:
        """Pack and encrypt `ints`; `keys` (sorted, one per value) become the OPE tags."""
        meta = {'scale': scale, 'fscale': fscale}
        body = {'dataset': self.dataset, 'column': name, 'n': format(self.pub.n, 'x')}
        if keys:
            off, top = keys[0], max(keys[-1] - keys[0], 1)
            ope = FastOPE(secrets.token_bytes(32), in_range=ValueRange(0, top),
                          out_range=ValueRange(0, 2 ** 64 - 1))
            body['ope_tags'] = ope.encrypt_list([k - off for k in keys])
            meta.update(ope=ope, ope_offset=off, ope_top=top)
        # DJN randomness only on admissible moduli (our keys); e.g. browser-made keys get textbook r^n
        pool = RandomnessPool(self.pub, method=None if self._djn_ok else 'standard')
        packed = BatchedAggregator(self.pub, self.priv, encrypt_batch=pool.encrypt_batch).encrypt_column(ints)
        pool.close()  # ponytail: new pool per column; keep one open if many big columns are uploaded
        meta.update(slot_bits=packed['slot_bits'], slots=packed['slots'], offset=packed['offset'], count=packed['count'])
        body.update(ciphertexts=[format(c, 'x') for c in packed['ciphertexts']],
                    slots=packed['slots'], count=packed['count'])
        r = self.post('/api/v2/columns', body)
        self.columns[name] = meta
        return r

    def delete(self) -> dict:
        """Delete this dataset from the server (all columns). The key stays usable for new uploads."""
        r = self.post('/api/v2/delete', {'dataset': self.dataset, 'n': format(self.pub.n, 'x')})
        self.columns.clear()
        return r

    def query(self, column: str, lo: Optional[float] = None, hi: Optional[float] = None,
              by: Optional[str] = None) -> dict:
        """SUM / COUNT / AVG over the column, optionally only rows with lo <= value <= hi, where
        value is the column itself or, with by=, the column `by` (needs upload_by first)."""
        name = f'{column}|{by}' if by and by != column else column
        if name not in self.columns:
            raise ValueError(f'Call upload_by({column!r}, ..., by={by!r}) first' if name != column
                             else f'Unknown column {column!r}')
        m = self.columns[name]
        body = {'dataset': self.dataset, 'column': name}
        if lo is not None or hi is not None:
            if 'ope' not in m:
                raise ValueError(f'{column} was uploaded without range_filter=True')
            fs = m.get('fscale', m['scale'])  # key files from before upload_by have no fscale
            lo_s = int(round(lo * fs)) - m['ope_offset'] if lo is not None else 0
            hi_s = int(round(hi * fs)) - m['ope_offset'] if hi is not None else m['ope_top']
            if lo_s > m['ope_top'] or hi_s < 0 or lo_s > hi_s:
                return {'sum': 0, 'count': 0, 'avg': 0}  # empty range: nothing to ask the server
            body.update(lo_tag=m['ope'].encrypt(max(lo_s, 0)), hi_tag=m['ope'].encrypt(min(hi_s, m['ope_top'])))
        r = self.post('/api/v2/aggregate', body)
        slots = m['slots']
        product = int(r['product'], 16) if r['product'] else None
        edges = [(int(e['ciphertext'], 16), max(0, e['first_slot']), min(e['end_slot'], slots)) for e in r['edges']]
        total = decrypt_range(self.pub, self.priv, product, edges, m['slot_bits'], slots) + m['offset'] * r['count']
        total = total / m['scale'] if m['scale'] != 1 else total
        return {'sum': total, 'count': r['count'], 'avg': total / r['count'] if r['count'] else 0}
