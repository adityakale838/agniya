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

Keys live in memory only (like the server's in-memory store); losing the client loses access.
The server is trusted to compute correctly (honest-but-curious), not to see data.
"""

import json
import secrets
import urllib.error
import urllib.request
from typing import Callable, Dict, Iterable, Optional, Union

from pyope.ope import ValueRange

from agniya.core.batch_packing import BatchedAggregator, decrypt_range
from agniya.core.paillier import generate_keypair
from agniya.core.precomputation import RandomnessPool
from agniya.hybrid.fast_ope import FastOPE

Transport = Callable[[str, dict], dict]  # (path, json body) -> json response; raises on errors


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
    def __init__(self, server: Union[str, Transport], dataset: str, key_size: int = 2048):
        self.post = http_transport(server) if isinstance(server, str) else server
        self.dataset = dataset
        self.pub, self.priv = generate_keypair(key_size)
        self.columns: Dict[str, dict] = {}  # client-only: scale, offsets, slot bits, OPE key

    def upload(self, column: str, values: Iterable[float], decimals: int = 0,
               range_filter: bool = False) -> dict:
        """Encrypt a numeric column here and store only ciphertexts (and OPE tags) on the server."""
        scale = 10 ** decimals
        ints = [int(round(v * scale)) for v in values]  # fixed point; NaN raises
        meta = {'scale': scale}
        body = {'dataset': self.dataset, 'column': column, 'n': format(self.pub.n, 'x')}
        if range_filter and ints:
            ints.sort()  # sorted packing: a value range is a contiguous run of slots
            off, top = ints[0], max(ints[-1] - ints[0], 1)
            ope = FastOPE(secrets.token_bytes(32), in_range=ValueRange(0, top),
                          out_range=ValueRange(0, 2 ** 64 - 1))
            body['ope_tags'] = ope.encrypt_list([v - off for v in ints])
            meta.update(ope=ope, ope_offset=off, ope_top=top)
        pool = RandomnessPool(self.pub)
        packed = BatchedAggregator(self.pub, self.priv, encrypt_batch=pool.encrypt_batch).encrypt_column(ints)
        pool.close()  # ponytail: new pool per column; keep one open if many big columns are uploaded
        meta.update(slot_bits=packed['slot_bits'], slots=packed['slots'], offset=packed['offset'])
        body.update(ciphertexts=[format(c, 'x') for c in packed['ciphertexts']],
                    slots=packed['slots'], count=packed['count'])
        r = self.post('/api/v2/columns', body)
        self.columns[column] = meta
        return r

    def query(self, column: str, lo: Optional[float] = None, hi: Optional[float] = None) -> dict:
        """SUM / COUNT / AVG over the column, optionally only rows with lo <= value <= hi."""
        m = self.columns[column]
        body = {'dataset': self.dataset, 'column': column}
        if lo is not None or hi is not None:
            if 'ope' not in m:
                raise ValueError(f'{column} was uploaded without range_filter=True')
            lo_s = int(round(lo * m['scale'])) - m['ope_offset'] if lo is not None else 0
            hi_s = int(round(hi * m['scale'])) - m['ope_offset'] if hi is not None else m['ope_top']
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
