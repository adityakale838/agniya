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
    c.upload_grouped("charges", charges, by="region", by_values=regions, decimals=4)
    c.query_groups("charges", "region")     # {'northeast': {'sum', 'count', 'avg'}, ...}
    c.upload_grouped("charges", charges, by=["region", "smoker"], by_values=[regions, smokers], decimals=4)
    c.query_groups("charges", ["region", "smoker"])  # {('northeast', 'no'): {...}, ...}: GROUP BY both
    c.upload_grouped("charges", charges, by="region", by_values=regions, decimals=4,
                     where="age", where_values=ages)
    c.query_groups("charges", "region", lo=30, hi=45, where="age")  # ... WHERE 30 <= age <= 45 GROUP BY region
    c.quantiles("charges", [0, 0.5, 1])     # MIN, MEDIAN, MAX (range_filter=True columns; lo=, hi= too)
    c.upload_sorted_groups("charges", charges, by="region", by_values=regions, decimals=4)
    c.quantiles("charges", [0.5], by="region")  # {'northeast': [median], ...}
    c.upload_sorted_groups("charges", charges, by="region", by_values=regions, decimals=4, where="age", where_values=ages)
    c.quantiles("charges", [0.5], lo=30, hi=45, by="region", where="age")  # ... WHERE 30 <= age <= 45
    c.upload("charges", charges, decimals=4, range_filter=True, squares=True)
    c.query("charges", lo=5000)              # ... plus 'var' and 'std' (VARIANCE / STDDEV, as pandas)

    c.save("claims.agniya-key", password)    # scrypt + AES-256-GCM; losing it loses the data
    c = AgniyaClient.load("claims.agniya-key", password, "http://127.0.0.1:5000")

The server is not trusted to see data, nor to compute correctly: every answer is checked here
against integrity tags in the ciphertexts (agniya/core/integrity.py) and IntegrityError is raised
when it is not the honest result over the uploaded data. Columns from key files made before
integrity tags are not checked. Every call carries the dataset's token (dataset_token), so only
this key's holder can upload to, query or delete the dataset.
"""

import base64
import hashlib
import json
import math
import os
import secrets
import urllib.error
import urllib.request
from itertools import accumulate
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Union

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pyope.ope import ValueRange

from agniya.core.batch_packing import (BatchedAggregator, decrypt_groups, decrypt_range, decrypt_sorted_groups,
                                       group_pages, quantile_rows, sample_variance, slot_value)
from agniya.core.batch_packing import squares as _squares
from agniya.core.integrity import ColumnMac, IntegrityError, range_cuts
from agniya.core.paillier import decrypt_crt, generate_keypair, is_djn_admissible, keypair_from_primes
from agniya.core.precomputation import RandomnessPool
from agniya.hybrid.fast_ope import FastOPE

Transport = Callable[[str, dict], dict]  # (path, json body) -> json response; raises on errors
KEY_FILE_FORMAT = 'agniya-client-key/1'
SCRYPT = {'n': 2 ** 17, 'r': 8, 'p': 1}  # 128 MiB, ~0.3-0.5 s per save/load: slows password guessing


def _file_key(password: str, salt: bytes, kdf: dict) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=kdf['n'], r=kdf['r'], p=kdf['p'],
                          maxmem=256 * 1024 * 1024, dklen=32)


def dataset_token(priv, dataset: str) -> str:
    """Access token for `dataset` on /api/v2. Only the private key's holder can compute it, so key files
    need nothing new; the server stores its SHA-256. The browser client computes the same token."""
    return hashlib.sha256(f'agniya/v2 dataset token\0{min(priv.p, priv.q)}\0{dataset}'.encode()).hexdigest()


def _by(by: Union[str, Sequence[str]], by_values=None):
    """(name, labels) for GROUP BY `by`: a column name with by_values one label per row, or a list of names
    with by_values one column each, GROUP BY all of them: the labels are tuples (None where a part is missing)
    and the copies are named after "a,b"."""
    if isinstance(by, str):
        return by, by_values
    by = list(by)
    if by_values is None:
        return ','.join(by), None
    cols = [list(v) for v in by_values]
    if len(cols) != len(by) or len(by) < 2:
        raise ValueError('GROUP BY several columns: by and by_values need one entry per column, at least 2')
    ok = lambda x: x is not None and x == x  # noqa: E731  x == x is False for NaN
    return ','.join(by), [tuple(x.item() if hasattr(x, 'item') else x for x in t) if all(map(ok, t)) else None
                          for t in zip(*cols, strict=True)]


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
            c = {k: m[k] for k in ('scale', 'fscale', 'slot_bits', 'slots', 'offset', 'count', 'lanes', 'labels', 'pages',
                                   'mac_key', 'shift', 'sizes', 'wspan', 'woff') if k in m}
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
            if 'labels' in m:
                m['labels'] = [tuple(x) if isinstance(x, list) else x for x in m['labels']]  # GROUP BY several columns
            c.columns[name] = m
        return c

    def upload(self, column: str, values: Iterable[float], decimals: int = 0,
               range_filter: bool = False, squares: bool = False) -> dict:
        """Encrypt a numeric column here and store only ciphertexts (and OPE tags) on the server.
        squares=True also stores "column^2": (x - c)^2 per row (c, about the mean, stays here) with the
        same OPE tags, so query() also returns VARIANCE and STDDEV. It costs a second upload of the column,
        and its ciphertext count shows the server roughly how wide the spread is (the squares' bit length)."""
        scale = 10 ** decimals
        ints = [int(round(v * scale)) for v in values]  # fixed point; NaN raises
        if range_filter:
            ints.sort()  # sorted packing: a value range is a contiguous run of slots
        return self._upload(column, ints, scale, ints if range_filter else None, scale, squares)

    def upload_by(self, column: str, values: Iterable[float], by: str, by_values: Iterable[float],
                  decimals: int = 0, by_decimals: int = 0, squares: bool = False) -> dict:
        """Store `column` packed in the order of `by` (one row each, same order), so that
        query(column, lo, hi, by=by) sums `column` over rows with lo <= by <= hi. Rows where either
        value is missing (None/NaN) are left out. The server gets OPE tags of `by` under a fresh key."""
        s, fs = 10 ** decimals, 10 ** by_decimals
        rows = sorted((int(round(b * fs)), int(round(a * s))) for a, b in zip(values, by_values, strict=True)
                      if a is not None and b is not None and a == a and b == b)  # x == x is False for NaN
        return self._upload(f'{column}|{by}', [a for _, a in rows], s, [b for b, _ in rows], fs, squares)

    def upload_grouped(self, column: str, values: Iterable[float], by: Union[str, Sequence[str]], by_values: Iterable,
                       decimals: int = 0, where: Optional[str] = None, where_values: Optional[Iterable[float]] = None,
                       where_decimals: int = 0, squares: bool = False) -> dict:
        """Store `column` packed by the labels in `by_values` (one per row, same order), so that
        query_groups(column, by) returns every group's sum and count from one decryption. Rows where
        either is missing are left out. The labels stay here; the server sees the number of slots
        per ciphertext and the number of ciphertexts (about the biggest group's size / lanes).
        Groups that do not share one plaintext are split into pages, each stored as its own server
        column ("column#by", "column#by@1", ...) and decrypted on its own.

        With where= (and where_values, one per row), the copy is packed in the order of that column
        and gets its OPE tags, so query_groups(..., lo, hi, where=where) groups only the rows with
        lo <= where <= hi. Such a copy needs about len(rows) / lanes ciphertexts, and the server
        also learns what a range filter shows: the row count and the order of the where values."""
        s = 10 ** decimals
        by, by_values = _by(by, by_values)
        ok = lambda x: x is not None and x == x  # noqa: E731  x == x is False for NaN
        if where is None:
            rows = [(int(round(a * s)), b) for a, b in zip(values, by_values, strict=True) if ok(a) and ok(b)]
            if not rows:
                raise ValueError(f'No rows have both {column} and {by}')
        else:
            fs = 10 ** where_decimals
            rows = sorted(((int(round(w * fs)), int(round(a * s)), b)
                           for a, b, w in zip(values, by_values, where_values, strict=True) if ok(a) and ok(b) and ok(w)),
                          key=lambda r: r[:2])
            if not rows:
                raise ValueError(f'No rows have {column}, {by} and {where}')
        if where is None:
            vals, labels, name, tags, base = [a for a, _ in rows], [b for _, b in rows], f'{column}#{by}', None, {}
        else:
            vals, labels, name = [a for _, a, _ in rows], [b for _, _, b in rows], f'{column}#{by}|{where}'
            tags, base = self._ope_tags([w for w, _, _ in rows])
            base['fscale'] = fs
        jobs = [(name, vals, s, {})]
        if squares:
            sq_ints, c = _squares(vals)
            jobs.append((f'{name}^2', sq_ints, s * s, {'shift': c}))
        pool = RandomnessPool(self.pub, method=None if self._djn_ok else 'standard')
        out = None
        for col, vs, sc, extra in jobs:
            mac = ColumnMac(self.pub.n)
            agg = BatchedAggregator(self.pub, self.priv, encrypt_batch=pool.encrypt_batch, mac=mac)
            if where is None:
                packed = agg.encrypt_groups(vs, labels)
                body = {'slots': packed['slots'], 'count': packed['slots'] * (len(packed['ciphertexts']) // packed['pages'])}
            else:
                packed = agg.encrypt_sorted_groups(vs, labels)
                body = {'slots': packed['lanes'], 'count': len(rows), 'ope_tags': tags}  # cut like a sorted column
            for p, cts in enumerate(group_pages(packed)):
                r = self._v2('/api/v2/columns', {'dataset': self.dataset, 'column': col + (f'@{p}' if p else ''),
                                                  'n': format(self.pub.n, 'x'), 'ciphertexts': [format(c, 'x') for c in cts],
                                                  **body, **({'tag_macs': mac.tag_macs(p, tags, packed['lanes'])} if tags else {})})
            self.columns[col] = {**base, **extra, 'scale': sc, 'count': body['count'],  # count: per server column
                                 'mac_key': base64.b64encode(mac.key).decode(),
                                 **{k: packed[k] for k in ('slot_bits', 'slots', 'lanes', 'labels', 'offset', 'pages')}}
            out = out or {**r, 'column': name, 'ciphertexts': len(packed['ciphertexts']), 'pages': packed['pages']}
        pool.close()
        return out

    def upload_sorted_groups(self, column: str, values: Iterable[float], by: Union[str, Sequence[str]], by_values: Iterable,
                             decimals: int = 0, where: Optional[str] = None, where_values: Optional[Iterable[float]] = None,
                             where_decimals: int = 0) -> dict:
        """Store `column` sorted within each group of `by` (labels in by_values, one per row) as "column#by^sorted",
        so quantiles(column, qs, by=by) gives every group's MIN / MEDIAN / MAX / any quantile. Rows where either is
        missing are left out. The labels and group sizes stay here, but reading a quantile shows the server which
        ciphertexts hold it, so roughly where each group starts and ends (to within a ciphertext of rows).

        With where= (where_values one per row; not needed when where is column itself), the copy
        "column#by^sorted|where" is sorted by where within each group and gets OPE tags of (group, where), so
        quantiles(..., lo, hi, by=by, where=where) uses only rows with lo <= where <= hi. The tags show the server
        the order of the where values within each group and, by their jumps, where groups start. When where is
        another column, a query reads every row in range (one decryption per ciphertext of them)."""
        by, by_values = _by(by, by_values)
        if where == column and where_values is None:
            where_values, where_decimals = values, decimals
        s, fs, groups = 10 ** decimals, 10 ** where_decimals, {}
        ok = lambda x: x is not None and x == x  # noqa: E731  x == x is False for NaN
        values = list(values)
        ws = where_values if where else [0] * len(values)
        for a, b, w in zip(values, by_values, ws, strict=True):
            if ok(a) and ok(b) and ok(w):
                groups.setdefault(b.item() if hasattr(b, 'item') else b, []).append((int(round(w * fs)), int(round(a * s))))
        if not groups:
            raise ValueError(f'No rows have {column}, {by}' + (f' and {where}' if where else ''))
        labels = sorted(groups)
        rows = [(gi, w, a) for gi, g in enumerate(labels) for w, a in sorted(groups[g])]
        name = f'{column}#{by}^sorted' + (f'|{where}' if where else '')
        meta = {'labels': labels, 'sizes': [len(groups[g]) for g in labels]}
        keys = None
        if where:
            woff = min(w for _, w, _ in rows)
            meta.update(woff=woff, wspan=max(w for _, w, _ in rows) - woff + 1)
            keys = [gi * meta['wspan'] + w - woff for gi, w, _ in rows]  # sorted: (group, where)
        r = self._upload(name, [a for _, _, a in rows], s, keys, fs)
        self.columns[name].update(meta)
        return r

    def query_groups(self, column: str, by: Union[str, Sequence[str]], lo: Optional[float] = None, hi: Optional[float] = None,
                     where: Optional[str] = None) -> dict:
        """{label: {'sum', 'count', 'avg'}} for SUM / COUNT / AVG(column) GROUP BY by (needs upload_grouped).
        With where=, only rows with lo <= where <= hi (needs upload_grouped(..., where=where)); groups
        with no such rows are left out, as in SQL. Copies uploaded with squares=True also give each
        group's 'var' and 'std' (None for a group of one row). by= a list of columns: GROUP BY all of them,
        with tuple labels (needs upload_grouped with the same list)."""
        by = _by(by)[0]
        name = f'{column}#{by}' + (f'|{where}' if where else '')
        if name not in self.columns:
            raise ValueError(f'Call upload_grouped({column!r}, ..., by={by!r}' + (f', where={where!r}' if where else '')
                             + ') first')
        m = self.columns[name]
        rng = None
        if where:
            rng = self._range_tags(m, lo, hi)
            if rng is None:
                return {}
        sums = self._group_sums(name, rng)
        sq = self._group_sums(f'{name}^2', rng) if f'{name}^2' in self.columns else None
        out = {}
        for label, (total, count) in sums.items():
            g = {'sum': total / m['scale'] if m['scale'] != 1 else total, 'count': count}
            g['avg'] = g['sum'] / count if count else 0
            if sq is not None:
                g.update(self._spread(name, m, count, total, sq.get(label, (0, 0))))
            out[label] = g
        return out

    def _group_sums(self, name: str, rng: Optional[dict]) -> Dict:
        """{label: (sum, count)} in fixed point from server column(s) `name` (one per page), checked."""
        m = self.columns[name]
        rs = [self._v2('/api/v2/aggregate', {**(rng or {}), 'column': name + (f'@{p}' if p else '')})
              for p in range(m.get('pages', 1))]
        plain = {}
        for p, r in enumerate(rs):
            plain.update(self._answer(m, name, r, p, rng))
        if not rng:
            return decrypt_groups(self.pub, self.priv, [int(r['product'], 16) for r in rs], m, dec=plain.__getitem__)
        if len({tuple(r.get('rows', ())) for r in rs}) > 1:
            raise IntegrityError(f'The pages of {name} were cut at different rows')
        return decrypt_sorted_groups(self.pub, self.priv, [
            (int(r['product'], 16) if r['product'] else None,
             [(int(e['ciphertext'], 16), max(0, e['first_slot']), min(e['end_slot'], m['lanes'])) for e in r['edges']])
            for r in rs], m, dec=plain.__getitem__)

    def _spread(self, name: str, m: dict, count: int, total: int, sq: tuple) -> dict:
        """{'var', 'std'} from the fixed-point sum of `name` and (sum, count) of its "name^2" copy."""
        if sq[1] != count:
            raise IntegrityError(f'{name} and {name}^2 were summed over different rows')
        try:
            var = sample_variance(count, total, sq[0], self.columns[f'{name}^2']['shift'], m['scale'])
        except ValueError:
            raise IntegrityError(f"The server's answer for {name}^2 does not match {name}") from None
        return {'var': var, 'std': None if var is None else math.sqrt(var)}

    def _ope_tags(self, keys: list):
        """OPE tags for sorted `keys` under a fresh key, and the column metadata to make more."""
        off, top = keys[0], max(keys[-1] - keys[0], 1)
        ope = FastOPE(secrets.token_bytes(32), in_range=ValueRange(0, top), out_range=ValueRange(0, 2 ** 64 - 1))
        return ope.encrypt_list([k - off for k in keys]), {'ope': ope, 'ope_offset': off, 'ope_top': top}

    def _range_tags(self, m: dict, lo: Optional[float], hi: Optional[float]) -> Optional[dict]:
        """{'lo_tag', 'hi_tag'} for lo <= value <= hi on a column with OPE tags; None if the range is empty."""
        fs = m.get('fscale', m['scale'])  # key files from before upload_by have no fscale
        lo_s = int(round(lo * fs)) - m['ope_offset'] if lo is not None else 0
        hi_s = int(round(hi * fs)) - m['ope_offset'] if hi is not None else m['ope_top']
        if lo_s > m['ope_top'] or hi_s < 0 or lo_s > hi_s:
            return None  # empty range: nothing to ask the server
        return {'lo_tag': m['ope'].encrypt(max(lo_s, 0)), 'hi_tag': m['ope'].encrypt(min(hi_s, m['ope_top']))}

    def _upload(self, name: str, ints: list, scale: int, keys: Optional[list], fscale: int, sq: bool = False) -> dict:
        """Pack and encrypt `ints`; `keys` (sorted, one per value) become the OPE tags. With sq, also
        "name^2" holding (x - c)^2 in the same row order, with the same tags (so one range cuts both)."""
        tags, ope_meta = self._ope_tags(keys) if keys else (None, {})
        jobs = [(name, ints, scale, {})]
        if sq and ints:
            sq_ints, c = _squares(ints)
            jobs.append((f'{name}^2', sq_ints, scale * scale, {'shift': c}))
        # DJN randomness only on admissible moduli (our keys); e.g. browser-made keys get textbook r^n
        pool = RandomnessPool(self.pub, method=None if self._djn_ok else 'standard')
        out = None
        for col, vals, sc, extra in jobs:
            mac = ColumnMac(self.pub.n)
            packed = BatchedAggregator(self.pub, self.priv, encrypt_batch=pool.encrypt_batch, mac=mac).encrypt_column(vals)
            body = {'dataset': self.dataset, 'column': col, 'n': format(self.pub.n, 'x'),
                    'ciphertexts': [format(c, 'x') for c in packed['ciphertexts']],
                    'slots': packed['slots'], 'count': packed['count']}
            if tags:
                body.update(ope_tags=tags, tag_macs=mac.tag_macs(0, tags, packed['slots']))
            r = self._v2('/api/v2/columns', body)
            out = out or r
            self.columns[col] = {'scale': sc, 'fscale': fscale, 'mac_key': base64.b64encode(mac.key).decode(), **ope_meta,
                                 **extra, **{k: packed[k] for k in ('slot_bits', 'slots', 'offset', 'count')}}
        pool.close()  # ponytail: new pool per column; keep one open if many big columns are uploaded
        return out

    def _answer(self, m: dict, name: str, r: dict, page: int, rng: Optional[dict]) -> Dict[int, int]:
        """{ciphertext: plaintext} for one /api/v2/aggregate answer (page `page` of column `name`), after
        checking it is the product and edges of the stored ciphertexts for the rows the range selects."""
        if rng and 'mac_key' in m and 'rows' not in r:
            raise IntegrityError(f'The server sent no rows to check {name} against: it predates integrity checks '
                                 '(update the server before the clients)')
        try:  # a malformed answer is a failed check too
            product = int(r['product'], 16) if r['product'] else None
            edges = [int(e['ciphertext'], 16) for e in r['edges']]
            plain = {c: decrypt_crt(self.pub, self.priv, c) for c in ([product] if product is not None else []) + edges}
            if 'mac_key' not in m:
                return plain  # uploaded before integrity tags: not checked
            mac = ColumnMac(self.pub.n, base64.b64decode(m['mac_key']))
            s = m['lanes'] if 'lanes' in m and 'ope' in m else m['slots']  # values per ciphertext on the server
            i, j = (int(r['rows'][0]), int(r['rows'][1])) if rng else (0, m['count'])
            full, cuts = range_cuts(s, m['count'], i, j)
            ok = (r['count'] == j - i and (product is None) == (not full) and len(cuts) == len(edges)
                  and all((e['first_slot'], e['end_slot']) == (lo, hi) for e, (_, lo, hi) in zip(r['edges'], cuts))
                  and (not full or mac.check(plain[product], page, full[0], len(full)))
                  and all(mac.check(plain[ct], page, c, 1) for ct, (c, _, _) in zip(edges, cuts))
                  and (not rng or mac.check_cut(page, s, m['count'], i, j, r['witnesses'], rng['lo_tag'], rng['hi_tag'])))
        except (KeyError, TypeError, ValueError, IndexError):
            ok = False
        if not ok:
            raise IntegrityError(f"The server's answer for {name} does not match the uploaded data")
        return plain

    def _v2(self, path: str, body: dict) -> dict:
        """POST to /api/v2 with this dataset's name and token."""
        return self.post(path, {**body, 'dataset': self.dataset, 'token': dataset_token(self.priv, self.dataset)})

    def delete(self) -> dict:
        """Delete this dataset from the server (all columns). The key stays usable for new uploads."""
        r = self._v2('/api/v2/delete', {})
        self.columns.clear()
        return r

    def quantiles(self, column: str, qs: Sequence[float], lo: Optional[float] = None,
                  hi: Optional[float] = None, by: Union[str, Sequence[str], None] = None, where: Optional[str] = None):
        """Quantiles of a column uploaded with range_filter=True, as pandas computes them (linear
        interpolation): q = 0 is MIN, 0.5 MEDIAN, 1 MAX. Optionally only rows with lo <= value <= hi;
        None for each q when no row is. The column is packed sorted, so each quantile reads one or two
        rows: their ciphertexts are decrypted here (which shows this client the other values in them).
        With by= (needs upload_sorted_groups): {label: [one value per q]} for every group; with where= too,
        only rows with lo <= where <= hi, leaving out groups with none (as SQL)."""
        qs = [float(q) for q in qs]
        if by:
            return self._group_quantiles(column, _by(by)[0], qs, lo, hi, where)
        m = self.columns.get(column)
        if m is None or 'ope' not in m or '|' in column or '#' in column:
            raise ValueError(f'{column} was not uploaded with range_filter=True')
        rng = None
        if lo is not None or hi is not None:
            rng = self._range_tags(m, lo, hi)
            if rng is None:
                return [None] * len(qs)
        r = self._v2('/api/v2/quantiles', {'column': column, 'q': qs, **(rng or {})})
        if rng and 'mac_key' in m and 'rows' not in r:
            raise IntegrityError(f'The server sent no rows to check {column} against: update the server')
        try:  # the cells must be exactly the rows these quantiles need, from the stored ciphertexts
            i, j = (int(r['rows'][0]), int(r['rows'][1])) if rng else (0, m['count'])
            want = sorted({x for q in qs for x in quantile_rows(i, j, q)[:2]}) if i < j else []
            cells = {int(c['row']): int(c['ciphertext'], 16) for c in r['cells']}
            value = (self._cell_values(m, want, [cells[x] for x in want])
                     if r['count'] == j - i and sorted(cells) == want and 0 <= i <= j <= m['count'] else None)
            if value is not None and rng and 'mac_key' in m and not ColumnMac(
                    self.pub.n, base64.b64decode(m['mac_key'])).check_cut(
                    0, m['slots'], m['count'], i, j, r['witnesses'], rng['lo_tag'], rng['hi_tag']):
                value = None
        except (KeyError, TypeError, ValueError, IndexError):
            value = None
        if value is None:
            raise IntegrityError(f"The server's answer for {column} does not match the uploaded data")
        if i == j:
            return [None] * len(qs)
        return [self._interpolate(value, i, j, q) / m['scale'] for q in qs]

    def _group_quantiles(self, column: str, by: str, qs: List[float], lo: Optional[float], hi: Optional[float],
                         where: Optional[str]) -> dict:
        name = f'{column}#{by}^sorted' + (f'|{where}' if where else '')
        m = self.columns.get(name)
        if m is None:
            raise ValueError(f'Call upload_sorted_groups({column!r}, ..., by={by!r}' + (f', where={where!r}' if where else '')
                             + ') first')
        if not where and (lo is not None or hi is not None):
            raise ValueError('A range needs where= (the column it applies to)')
        starts = list(accumulate([0] + m['sizes']))
        spans = dict(zip(m['labels'], zip(starts, starts[1:])))
        if where:
            spans = self._group_ranges(m, name, spans, lo, hi)
        in_order = not where or where == column  # rows in range are sorted by value: read only the quantile rows
        want = sorted({x for i, j in spans.values() for x in
                       ({y for q in qs for y in quantile_rows(i, j, q)[:2]} if in_order else range(i, j))})
        value = self._fetch_rows(m, name, want)
        out = {}
        for label, (i, j) in spans.items():
            vs = value if in_order else dict(enumerate(sorted(value[x] for x in range(i, j)), i))
            out[label] = [self._interpolate(vs, i, j, q) / m['scale'] for q in qs]
        return out

    def _group_ranges(self, m: dict, name: str, spans: dict, lo: Optional[float], hi: Optional[float]) -> dict:
        """{label: (i, j)}: each group's rows with lo <= where <= hi, from the server and checked; empty groups left out."""
        fs = m.get('fscale', m['scale'])  # browser key files omit it when equal
        a0 = int(round(lo * fs)) - m['woff'] if lo is not None else 0
        b0 = int(round(hi * fs)) - m['woff'] if hi is not None else m['wspan'] - 1
        a0, b0 = max(a0, 0), min(b0, m['wspan'] - 1)
        tags = {}
        for gi, label in enumerate(m['labels']):  # OPE keys are group * wspan + where - woff, shifted by ope_offset
            a = max(gi * m['wspan'] + a0 - m['ope_offset'], 0)
            b = min(gi * m['wspan'] + b0 - m['ope_offset'], m['ope_top'])
            if a0 <= b0 and a <= b:
                tags[label] = {'lo_tag': m['ope'].encrypt(a), 'hi_tag': m['ope'].encrypt(b)}
        if not tags:
            return {}
        r = self._v2('/api/v2/ranges', {'column': name, 'ranges': list(tags.values())})
        mac = ColumnMac(self.pub.n, base64.b64decode(m['mac_key'])) if 'mac_key' in m else None
        out = {}
        try:
            ok = len(r['ranges']) == len(tags)
            for (label, t), x in zip(tags.items(), r['ranges']):
                i, j = int(x['rows'][0]), int(x['rows'][1])
                ok = ok and spans[label][0] <= i <= j <= spans[label][1] and (
                    mac is None or mac.check_cut(0, m['slots'], m['count'], i, j, x['witnesses'], t['lo_tag'], t['hi_tag']))
                if i < j:
                    out[label] = (i, j)
        except (KeyError, TypeError, ValueError, IndexError):
            ok = False
        if not ok:
            raise IntegrityError(f"The server's ranges for {name} do not match the uploaded data")
        return out

    def _fetch_rows(self, m: dict, name: str, rows: List[int]) -> Dict[int, int]:
        """{row: fixed-point value} for `rows` of server column `name`, from its stored ciphertexts, checked."""
        index = sorted({x // m['slots'] for x in rows})
        try:
            got = []
            for k in range(0, len(index), 4096):
                got += self._v2('/api/v2/ciphertexts', {'column': name, 'index': index[k:k + 4096]})['ciphertexts']
            cts = dict(zip(index, (int(c, 16) for c in got), strict=True))
            value = self._cell_values(m, rows, [cts[x // m['slots']] for x in rows])
        except (KeyError, TypeError, ValueError, IndexError):
            value = None
        if value is None:
            raise IntegrityError(f"The server's answer for {name} does not match the uploaded data")
        return value

    def _cell_values(self, m: dict, rows: List[int], cts: List[int]) -> Optional[Dict[int, int]]:
        """{row: fixed-point value} from cts[k], the stored ciphertext holding rows[k]; None when one of them is not
        the ciphertext the integrity tags say is at that index."""
        s = m['slots']
        plain = {ct: decrypt_crt(self.pub, self.priv, ct) for ct in set(cts)}
        if 'mac_key' in m:
            mac = ColumnMac(self.pub.n, base64.b64decode(m['mac_key']))
            if not all(mac.check(plain[ct], 0, x // s, 1) for x, ct in zip(rows, cts)):
                return None
        return {x: slot_value(plain[ct], x % s, m['slot_bits']) + m['offset'] for x, ct in zip(rows, cts)}

    @staticmethod
    def _interpolate(value: Dict[int, int], i: int, j: int, q: float) -> float:
        a, b, frac = quantile_rows(i, j, q)
        return value[a] + (value[b] - value[a]) * frac

    def query(self, column: str, lo: Optional[float] = None, hi: Optional[float] = None,
              by: Optional[str] = None) -> dict:
        """SUM / COUNT / AVG over the column, optionally only rows with lo <= value <= hi, where
        value is the column itself or, with by=, the column `by` (needs upload_by first). Columns
        uploaded with squares=True also give 'var' and 'std' (VARIANCE / STDDEV with ddof=1, as pandas;
        None for fewer than 2 rows)."""
        name = f'{column}|{by}' if by and by != column else column
        if name not in self.columns:
            raise ValueError(f'Call upload_by({column!r}, ..., by={by!r}) first' if name != column
                             else f'Unknown column {column!r}')
        m = self.columns[name]
        sq = self.columns.get(f'{name}^2')
        tags = None
        if lo is not None or hi is not None:
            if 'ope' not in m:
                raise ValueError(f'{column} was uploaded without range_filter=True')
            tags = self._range_tags(m, lo, hi)
            if tags is None:
                return {'sum': 0, 'count': 0, 'avg': 0, **({'var': None, 'std': None} if sq else {})}
        total, count = self._sum(name, tags)
        s = total / m['scale'] if m['scale'] != 1 else total
        out = {'sum': s, 'count': count, 'avg': s / count if count else 0}
        if sq:
            out.update(self._spread(name, m, count, total, self._sum(f'{name}^2', tags)))
        return out

    def _sum(self, name: str, tags: Optional[dict]) -> tuple:
        """(fixed-point sum, count) of server column `name` over the rows `tags` selects (all without), checked."""
        m = self.columns[name]
        r = self._v2('/api/v2/aggregate', {'column': name, **(tags or {})})
        plain = self._answer(m, name, r, 0, tags)
        slots = m['slots']
        product = int(r['product'], 16) if r['product'] else None
        edges = [(int(e['ciphertext'], 16), max(0, e['first_slot']), min(e['end_slot'], slots)) for e in r['edges']]
        total = decrypt_range(self.pub, self.priv, product, edges, m['slot_bits'], slots, dec=plain.__getitem__)
        return total + m['offset'] * r['count'], r['count']
