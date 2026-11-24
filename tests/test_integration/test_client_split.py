"""Client-held keys: the server stores and aggregates ciphertexts it cannot decrypt."""
import json
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api"))
import server_optimized as srv  # noqa: E402
from agniya.client import AgniyaClient, dataset_token  # noqa: E402
from agniya.core.integrity import IntegrityError  # noqa: E402
from agniya.core.paillier import sum_ciphertexts  # noqa: E402

SENT = []  # every request body the server received


def transport(path, body):
    SENT.append(json.dumps(body))
    r = srv.app.test_client().post(path, json=body)
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code}: {r.get_json()['error']}")
    return r.get_json()


@pytest.fixture(scope="module")
def setup():
    rng = pd.Series(range(300))
    df = pd.DataFrame({
        "amount": (rng * 37.1234 - 900).round(4),
        "age": (rng % 60 + 18).astype(int),
        "score": ((rng * 7919) % 1000 * 0.37 - 50).round(2),
        "region": [None if i % 29 == 0 else f"lbl-{'nsew'[i * i % 7 % 4]}" for i in range(300)],  # skewed
    })
    c = AgniyaClient(transport, dataset="split")
    c.upload("amount", df["amount"], decimals=4)
    c.upload("age", df["age"], range_filter=True)
    c.upload("score", df["score"], decimals=2, range_filter=True)
    c.upload_by("amount", df["amount"], by="age", by_values=df["age"], decimals=4)
    c.upload_by("age", df["age"], by="score", by_values=df["score"], by_decimals=2)
    c.upload_grouped("amount", df["amount"], by="region", by_values=df["region"], decimals=4)
    df["decade"] = df["age"] // 10 * 10
    c.upload_grouped("score", df["score"], by="decade", by_values=df["decade"], decimals=2)  # int labels
    c.upload_grouped("amount", df["amount"], by="region", by_values=df["region"], decimals=4,
                     where="score", where_values=df["score"], where_decimals=2)
    c.upload_grouped("age", df["age"], by="decade", by_values=df["decade"], where="age", where_values=df["age"])
    # 60 groups: more than one plaintext holds, so several pages ("score#age", "score#age@1", ...)
    assert c.upload_grouped("score", df["score"], by="age", by_values=df["age"], decimals=2)["pages"] > 1
    assert c.upload_grouped("amount", df["amount"], by="age", by_values=df["age"], decimals=4,
                            where="score", where_values=df["score"], where_decimals=2)["pages"] > 1
    return c, df


@pytest.mark.parametrize("col", ["amount", "age", "score"])
def test_unfiltered_matches_pandas(setup, col):
    c, df = setup
    r = c.query(col)
    assert r["sum"] == pytest.approx(df[col].sum(), abs=1e-6)
    assert r["count"] == len(df) and r["avg"] == pytest.approx(df[col].mean(), abs=1e-6)


@pytest.mark.parametrize("col,lo,hi", [("age", 30, 40), ("age", None, 20), ("age", 70, None), ("age", 200, 300),
                                       ("age", 18, 18), ("score", -50, 0), ("score", -10.5, 120.25),
                                       ("score", 12.34, 12.34), ("score", 400, 500), ("score", None, None)])
def test_range_matches_pandas(setup, col, lo, hi):
    c, df = setup
    x = df[col]
    sel = x[(x >= (lo if lo is not None else -1e9)) & (x <= (hi if hi is not None else 1e9))]
    r = c.query(col, lo, hi)
    assert r["count"] == len(sel) and r["sum"] == pytest.approx(sel.sum(), abs=1e-6)


@pytest.mark.parametrize("col,by,lo,hi", [("amount", "age", 30, 40), ("amount", "age", None, 20),
                                          ("amount", "age", 200, 300), ("age", "score", -10.5, 120.25),
                                          ("age", "score", 12.34, 12.34), ("age", "score", None, None)])
def test_sum_where_other_column_in_range(setup, col, by, lo, hi):
    c, df = setup
    b = df[by]
    sel = df[col][(b >= (lo if lo is not None else -1e9)) & (b <= (hi if hi is not None else 1e9))]
    r = c.query(col, lo, hi, by=by)
    assert r["count"] == len(sel) and r["sum"] == pytest.approx(sel.sum(), abs=1e-6)


def test_upload_by_skips_missing_rows(setup):
    c, _ = setup
    c.upload_by("x", [1, None, 3, float("nan"), 5], by="y", by_values=[10, 20, None, 40, 50])
    assert c.query("x", 0, 100, by="y") == {"sum": 6, "count": 2, "avg": 3.0}
    with pytest.raises(ValueError, match="upload_by"):
        c.query("amount", 1, 2, by="score")


@pytest.mark.parametrize("col,by", [("amount", "region"), ("score", "decade"), ("score", "age")])
def test_group_by_matches_pandas(setup, col, by):
    c, df = setup
    want = df[[col, by]].dropna().groupby(by)[col].agg(["sum", "count"])
    got = c.query_groups(col, by)
    assert set(got) == set(want.index)
    for label, row in want.iterrows():
        assert got[label]["count"] == row["count"] and got[label]["sum"] == pytest.approx(row["sum"], abs=1e-6)
        assert got[label]["avg"] == pytest.approx(row["sum"] / row["count"], abs=1e-6)


@pytest.mark.parametrize("col,by,where,lo,hi", [("amount", "region", "score", -10.5, 120.25), ("amount", "region", "score", None, 0),
                                               ("amount", "region", "score", 300, None), ("amount", "region", "score", 12.34, 12.34),
                                               ("amount", "region", "score", 900, 1000), ("amount", "region", "score", None, None),
                                               ("age", "decade", "age", 25, 44), ("amount", "age", "score", -10.5, 120.25),
                                               ("amount", "age", "score", None, None), ("amount", "age", "score", 12.34, 12.34)])
def test_group_by_with_range_matches_pandas(setup, col, by, where, lo, hi):
    c, df = setup
    rows = df[list(dict.fromkeys([col, by, where]))].dropna()
    w = rows[where]
    want = rows[(w >= (lo if lo is not None else -1e9)) & (w <= (hi if hi is not None else 1e9))].groupby(by)[col].agg(
        ["sum", "count"])
    got = c.query_groups(col, by, lo, hi, where=where)
    assert set(got) == set(want.index)
    for label, row in want.iterrows():
        assert got[label]["count"] == row["count"] and got[label]["sum"] == pytest.approx(row["sum"], abs=1e-6)


def test_group_by_skips_missing_rows(setup):
    c, df = setup
    c.upload_grouped("x", [1, None, 3, float("nan"), 5, 7], by="g", by_values=["a", "a", None, "b", "b", "a"])
    assert c.query_groups("x", "g") == {"a": {"sum": 8, "count": 2, "avg": 4.0}, "b": {"sum": 5, "count": 1, "avg": 5.0}}
    with pytest.raises(ValueError, match="upload_grouped"):
        c.query_groups("amount", "score")
    with pytest.raises(ValueError, match="where='age'"):
        c.query_groups("amount", "region", 1, 2, where="age")
    with pytest.raises(ValueError, match="No rows"):
        c.upload_grouped("x", [None], by="g", by_values=["a"])


def test_server_never_sees_private_key_or_plaintext(setup):
    c, df = setup
    sent = "".join(SENT)
    assert "lbl-" not in sent  # group labels stay with the client
    for secret in (c.priv.p, c.priv.q, c.priv.lambda_n, c.priv.mu):
        assert str(secret) not in sent and format(secret, "x") not in sent
    stored = srv.owner_datasets["split"]
    assert set(stored) == {"pub", "columns", "token_hash"} and not hasattr(stored["pub"], "p")
    assert dataset_token(c.priv, "split") not in json.dumps(stored["token_hash"])  # only its hash
    assert set(stored["columns"]["amount"]) == {"cts", "slots", "count", "tags", "macs"}


def _stored(body):
    return srv.owner_datasets["split"]["columns"][body["column"]]["cts"]


def _times(r, c, k):  # the answer's product times ciphertext k (an honest server never does this)
    return {**r, "product": format(int(r["product"], 16) * k % c.pub.n_squared, "x")}


def _later_cut(r, body):  # answer as if lo were above the first row in range: drops rows at the low end
    tags = srv.owner_datasets["split"]["columns"][body["column"]]["tags"]
    return transport("/api/v2/aggregate", {**body, "lo_tag": tags[r["rows"][0]] + 1})


def _wit(r, f):
    w = [dict(x, tags=list(x["tags"])) for x in r["witnesses"]]
    f(w)
    return {**r, "witnesses": w}


SUM_ALL = lambda c: c.query("amount")  # noqa: E731
RANGE = lambda c: c.query("score", -40, 300)  # noqa: E731  edge, whole ciphertext, edge
PAGES = lambda c: c.query_groups("score", "age")  # noqa: E731
PAGES_RANGE = lambda c: c.query_groups("amount", "age", 0, 99.5, where="score")  # noqa: E731


@pytest.mark.parametrize("query,change", [
    (SUM_ALL, lambda c, b, r: _times(r, c, _stored(b)[0])),  # one row counted twice
    (SUM_ALL, lambda c, b, r: _times(r, c, int(r["product"], 16))),  # every row doubled
    (SUM_ALL, lambda c, b, r: _times(r, c, 1 + 5 * c.pub.n)),  # + a constant the server encrypted
    (SUM_ALL, lambda c, b, r: {**r, "product": format(sum_ciphertexts(c.pub, _stored(b)[1:]), "x")}),  # rows left out
    (SUM_ALL, lambda c, b, r: {**r, "count": r["count"] - 1}),
    (RANGE, lambda c, b, r: _times(r, c, _stored(b)[0])),
    (RANGE, lambda c, b, r: {**r, "edges": [{**r["edges"][0], "ciphertext": format(_stored(b)[1], "x")}] + r["edges"][1:]}),
    (RANGE, lambda c, b, r: {**r, "edges": [{**r["edges"][0], "first_slot": r["edges"][0]["first_slot"] + 1}] + r["edges"][1:]}),
    (RANGE, lambda c, b, r: _later_cut(r, b)),  # a consistent answer for fewer rows
    (RANGE, lambda c, b, r: {**r, "witnesses": []}),
    (RANGE, lambda c, b, r: {k: v for k, v in r.items() if k != "rows"}),  # a server from before integrity checks
    (RANGE, lambda c, b, r: {**r, "product": "zz"}),  # malformed
    (SUM_ALL, lambda c, b, r: {**r, "edges": None}),
    (RANGE, lambda c, b, r: _wit(r, lambda w: w[0]["tags"].__setitem__(0, str(int(w[0]["tags"][0]) - 1)))),
    (RANGE, lambda c, b, r: _wit(r, lambda w: w[0].__setitem__("index", w[0]["index"] + 1))),
    (PAGES, lambda c, b, r: transport("/api/v2/aggregate", {**b, "column": "score#age@1"})
     if b["column"] == "score#age" else r),  # another page's answer
    (PAGES, lambda c, b, r: _times(r, c, _stored(b)[-1]) if b["column"] == "score#age@1" else r),
    (PAGES_RANGE, lambda c, b, r: _later_cut(r, b) if b["column"] == "amount#age|score@1" else r),
    (PAGES_RANGE, lambda c, b, r: _times(r, c, _stored(b)[0]) if b["column"] == "amount#age|score" else r),
])
def test_wrong_answers_are_caught(setup, query, change):
    c, _ = setup
    honest = query(c)

    def post(path, body):
        r = transport(path, body)
        return change(c, body, r) if path == "/api/v2/aggregate" else r
    c.post = post
    try:
        with pytest.raises(IntegrityError):
            query(c)
    finally:
        c.post = transport
    assert query(c) == honest


def test_store_from_before_tag_macs_is_upgraded(tmp_path, monkeypatch):
    import sqlite3
    from contextlib import closing
    path = str(tmp_path / "old.sqlite3")
    with closing(sqlite3.connect(path)) as con, con:
        con.execute("CREATE TABLE columns (dataset TEXT, name TEXT, n TEXT, slots INTEGER, count INTEGER, "
                    "cts BLOB, tags BLOB, PRIMARY KEY (dataset, name))")
    monkeypatch.setattr(srv, "STORE_PATH", path)
    with closing(srv._store()) as con:
        assert "macs" in [r[1] for r in con.execute("PRAGMA table_info(columns)")]


def test_key_files_without_mac_keys_still_load(setup, tmp_path):
    c, _ = setup
    old = {k: {f: v for f, v in m.items() if f != "mac_key"} for k, m in c.columns.items()}
    c2 = AgniyaClient(transport, "split", _keys=(c.pub, c.priv))
    c2.columns = old  # as loaded from a key file written before integrity tags: answers are not checked
    assert c2.query("score", -10.5, 120.25) == c.query("score", -10.5, 120.25)
    assert c2.query_groups("score", "age") == c.query_groups("score", "age")


def test_range_needs_ope_column(setup):
    c, _ = setup
    with pytest.raises(ValueError):
        c.query("amount", lo=1)
    with pytest.raises(RuntimeError, match="400"):
        transport("/api/v2/aggregate", {"dataset": "split", "column": "amount", "lo_tag": 1,
                                        "token": dataset_token(c.priv, "split")})


@pytest.mark.parametrize("patch,code", [({"n": "ff"}, 400), ({"ciphertexts": ["zz"]}, 400),
                                        ({"count": 10**6}, 400), ({"ope_tags": [5, 1, 2], "count": 3}, 400),
                                        ({"ciphertexts": ["0"]}, 400), ({"tag_macs": ["00" * 16] * 2}, 400),
                                        ({"ope_tags": [1, 2, 3], "count": 3, "tag_macs": ["00" * 16]}, 400),
                                        ({"ope_tags": [1, 2, 3], "count": 3, "tag_macs": ["ff" * 17] * 2}, 400)])
def test_upload_validation(setup, patch, code):
    c, _ = setup
    ok = {"dataset": "v", "column": "x", "n": format(c.pub.n, "x"), "ciphertexts": ["2", "3"], "slots": 2, "count": 3,
          "token": dataset_token(c.priv, "v")}
    assert srv.app.test_client().post("/api/v2/columns", json=ok).status_code == 200
    body = {**ok, "count": 4, **patch}
    assert srv.app.test_client().post("/api/v2/columns", json=body).status_code == code


def test_other_key_for_same_dataset_rejected(setup):
    c, _ = setup
    other = AgniyaClient(transport, dataset="split")
    with pytest.raises(RuntimeError, match="403"):  # another key cannot make the token
        other.upload("y", [1, 2, 3])
    other.priv = c.priv  # the token, but another modulus
    with pytest.raises(RuntimeError, match="409"):
        other.upload("y", [1, 2, 3])


def test_key_file_round_trip(setup, tmp_path):
    c, df = setup
    path = str(tmp_path / "split.agniya-key")
    c.save(path, "correct horse")
    raw = open(path).read()
    for secret in (c.priv.p, c.priv.q):
        assert str(secret) not in raw and format(secret, "x") not in raw
    c2 = AgniyaClient.load(path, "correct horse", transport)
    assert c2.pub.n == c.pub.n and c2.priv.p == c.priv.p and c2.dataset == "split"
    assert c2.query("score", -10.5, 120.25) == c.query("score", -10.5, 120.25)
    assert c2.query("age", -10.5, 120.25, by="score") == c.query("age", -10.5, 120.25, by="score")
    assert c2.query("amount")["sum"] == pytest.approx(df["amount"].sum(), abs=1e-6)
    assert c2.query_groups("amount", "region") == c.query_groups("amount", "region")
    assert c2.query_groups("score", "decade") == c.query_groups("score", "decade")  # int labels survive JSON
    assert c2.query_groups("amount", "region", 0, 99.5, where="score") == c.query_groups("amount", "region", 0, 99.5, where="score")
    assert c2.query_groups("score", "age") == c.query_groups("score", "age")  # pages survive the file
    assert c2.query_groups("amount", "age", 0, 99.5, where="score") == c.query_groups("amount", "age", 0, 99.5, where="score")


def test_key_file_rejects_wrong_password_and_tampering(setup, tmp_path):
    c, _ = setup
    path = str(tmp_path / "k")
    c.save(path, "pw")
    with pytest.raises(ValueError, match="Wrong password"):
        AgniyaClient.load(path, "nope", transport)
    d = json.load(open(path))
    for field, value in [("kdf", {**d["kdf"], "r": 4}), ("nonce", "A" * 16),
                         ("ciphertext", d["ciphertext"][:-8] + "AAAAAAA=")]:
        json.dump({**d, field: value}, open(path, "w"))
        with pytest.raises(ValueError):
            AgniyaClient.load(path, "pw", transport)
    with pytest.raises(ValueError):
        c.save(path, "")


def test_store_survives_restart(setup):
    c, df = setup
    before = {col: c.query(col) for col in ("amount", "age")} | {"range": c.query("score", -10.5, 120.25)}
    srv.owner_datasets.clear()
    srv.load_store()  # what a server restart does
    stored = srv.owner_datasets["split"]["columns"]["score"]
    assert stored["tags"] == sorted(stored["tags"]) and len(stored["tags"]) == len(df)
    after = {col: c.query(col) for col in ("amount", "age")} | {"range": c.query("score", -10.5, 120.25)}
    assert after == before


def test_tags_must_be_64_bit(setup):
    c, _ = setup
    body = {"dataset": "v64", "column": "x", "n": format(c.pub.n, "x"), "ciphertexts": ["2"],
            "slots": 2, "count": 2, "ope_tags": [1, 2 ** 64]}
    assert srv.app.test_client().post("/api/v2/columns", json=body).status_code == 400
    body["ope_tags"] = [-1, 3]
    assert srv.app.test_client().post("/api/v2/columns", json=body).status_code == 400


def test_delete_dataset(setup):
    c, df = setup
    other = AgniyaClient(transport, dataset="to-delete")
    other.upload("x", [1, 2, 3])
    for body, code in [({}, 401), ({"token": dataset_token(c.priv, "to-delete")}, 403)]:
        assert srv.app.test_client().post("/api/v2/delete", json={"dataset": "to-delete", **body}).status_code == code
    assert other.delete()["columns_deleted"] == 1
    assert "to-delete" not in srv.owner_datasets
    srv.load_store()  # gone from disk too
    assert "to-delete" not in srv.owner_datasets and "split" in srv.owner_datasets
    assert srv.app.test_client().post("/api/v2/delete", json={"dataset": "to-delete", "n": "1"}).status_code == 404


def test_store_size_limit(setup, monkeypatch):
    monkeypatch.setattr(srv, "STORE_MAX_BYTES", 1)
    c = AgniyaClient(transport, dataset="too-big")
    with pytest.raises(RuntimeError, match="507"):
        c.upload("x", [1, 2, 3])
    assert "too-big" not in srv.owner_datasets


def test_client_with_non_admissible_key_uses_standard_randomness(setup):
    from agniya.core.number_theory import generate_prime
    from agniya.core.paillier import keypair_from_primes
    keys = keypair_from_primes(generate_prime(1024), generate_prime(1024))  # like a browser-made key
    c = AgniyaClient(transport, dataset="non-admissible", _keys=keys)
    assert c._djn_ok is False
    c.upload("x", [1.5, -2.25, 10], decimals=2)
    assert c.query("x")["sum"] == pytest.approx(9.25)


def test_every_v2_call_needs_the_dataset_token(setup):
    c, _ = setup
    post = srv.app.test_client().post
    wrong = dataset_token(c.priv, "elsewhere")
    for path, body in [("/api/v2/aggregate", {"column": "amount"}), ("/api/v2/quantiles", {"column": "age", "q": [0.5]}),
                       ("/api/v2/columns", {"column": "x", "n": format(c.pub.n, "x"), "ciphertexts": ["2"],
                                            "slots": 1, "count": 1}), ("/api/v2/delete", {})]:
        assert post(path, json={"dataset": "split", **body}).status_code == 401, path
        assert post(path, json={"dataset": "split", **body, "token": wrong}).status_code == 403, path
    assert post("/api/v2/columns", json={"dataset": "new-one", "column": "x", "n": format(c.pub.n, "x"),
                                         "ciphertexts": ["2"], "slots": 1, "count": 1}).status_code == 401
    assert c.query("amount")["count"] == 300  # the owner still gets in


def test_dataset_from_before_tokens_is_claimed_by_the_first_token(setup):
    c, _ = setup
    ds = srv.owner_datasets["split"]
    saved = ds.pop("token_hash")
    try:
        assert c.query("age")["count"] == 300  # claims it
        other = AgniyaClient(transport, dataset="split")
        with pytest.raises(RuntimeError, match="403"):
            other._v2("/api/v2/aggregate", {"column": "age"})
    finally:
        ds["token_hash"] = saved


QS = [0, 0.1, 0.25, 0.5, 0.75, 0.9, 1]


@pytest.mark.parametrize("col,lo,hi", [("age", None, None), ("score", None, None), ("age", 30, 45),
                                       ("score", -10.5, 120.25), ("score", 120, 120.5), ("age", 77, None)])
def test_quantiles_match_pandas(setup, col, lo, hi):
    c, df = setup
    rows = df[col][(df[col] >= (lo if lo is not None else -1e18)) & (df[col] <= (hi if hi is not None else 1e18))]
    got = c.quantiles(col, QS, lo, hi)
    if rows.empty:
        assert got == [None] * len(QS)
    else:
        assert got == pytest.approx([rows.quantile(q) for q in QS], abs=1e-9), (col, lo, hi)


def test_quantiles_of_an_empty_range_and_unsorted_columns(setup):
    c, _ = setup
    assert c.quantiles("score", [0.5], 400, 500) == [None]  # above every value: not sent to the server
    assert c.quantiles("score", [0.5], 100.001, 100.009) == [None]  # inside the range, between values
    with pytest.raises(ValueError):
        c.quantiles("amount", [0.5])  # not range_filter=True: not sorted


def _cell(r, f):
    cells = [dict(x) for x in r["cells"]]
    f(cells)
    return {**r, "cells": cells}


MEDIAN = lambda c: c.quantiles("score", [0.5])  # noqa: E731
MEDIAN_RANGE = lambda c: c.quantiles("score", [0, 0.5, 1], -10.5, 120.25)  # noqa: E731


@pytest.mark.parametrize("query,change", [
    (MEDIAN, lambda c, b, r: _cell(r, lambda x: x[0].__setitem__("ciphertext", format(_stored(b)[0], "x")))),
    (MEDIAN, lambda c, b, r: _cell(r, lambda x: x.pop())),
    (MEDIAN, lambda c, b, r: _cell(r, lambda x: x[0].__setitem__("row", x[0]["row"] + 1))),
    (MEDIAN, lambda c, b, r: {**r, "count": r["count"] - 1}),
    (MEDIAN_RANGE, lambda c, b, r: transport("/api/v2/quantiles", {  # a consistent answer for fewer rows
        **b, "lo_tag": srv.owner_datasets["split"]["columns"]["score"]["tags"][r["rows"][0]] + 1})),
    (MEDIAN_RANGE, lambda c, b, r: {**r, "witnesses": []}),
    (MEDIAN_RANGE, lambda c, b, r: {k: v for k, v in r.items() if k != "rows"}),
    (MEDIAN_RANGE, lambda c, b, r: {**r, "cells": "zz"}),
])
def test_wrong_quantile_answers_are_caught(setup, query, change):
    c, _ = setup
    honest = query(c)

    def post(path, body):
        r = transport(path, body)
        return change(c, body, r) if path == "/api/v2/quantiles" else r
    c.post = post
    try:
        with pytest.raises(IntegrityError):
            query(c)
    finally:
        c.post = transport
    assert query(c) == honest


@pytest.fixture(scope="module")
def spread(setup):
    c, df = setup
    c.upload("v_amount", df["amount"], decimals=4, squares=True)
    c.upload("v_score", df["score"], decimals=2, range_filter=True, squares=True)
    c.upload_by("v_amount", df["amount"], by="age", by_values=df["age"], decimals=4, squares=True)
    c.upload_grouped("v_amount", df["amount"], by="region", by_values=df["region"], decimals=4, squares=True)
    assert c.upload_grouped("v_amount", df["amount"], by="age", by_values=df["age"], decimals=4, where="score",
                            where_values=df["score"], where_decimals=2, squares=True)["pages"] > 1
    return c, df


def _var_std(x):  # pandas, ddof=1; None where it gives NaN (fewer than 2 rows)
    return [None if pd.isna(v) else pytest.approx(v, rel=1e-9, abs=1e-9) for v in (x.var(), x.std())]


@pytest.mark.parametrize("col,lo,hi,by", [("v_amount", None, None, None), ("v_score", None, None, None),
                                          ("v_score", -10.5, 120.25, None), ("v_score", 12.34, 12.34, None),
                                          ("v_score", 400, 500, None), ("v_amount", 30, 40, "age"),
                                          ("v_amount", None, 20, "age")])
def test_variance_and_stddev_match_pandas(spread, col, lo, hi, by):
    c, df = spread
    x, f = df[col[2:]], df[by or col[2:]]
    sel = x[(f >= (lo if lo is not None else -1e9)) & (f <= (hi if hi is not None else 1e9))]
    r = c.query(col, lo, hi, by=by)
    assert r["count"] == len(sel) and [r["var"], r["std"]] == _var_std(sel)
    assert "var" not in c.query("amount")  # columns without squares: as before


@pytest.mark.parametrize("by,lo,hi,where", [("region", None, None, None), ("age", 0, 99.5, "score"),
                                            ("age", None, None, "score")])
def test_group_variance_matches_pandas(spread, by, lo, hi, where):
    c, df = spread
    rows = df[list(dict.fromkeys(["amount", by] + ([where] if where else [])))].dropna()
    if where:
        w = rows[where]
        rows = rows[(w >= (lo if lo is not None else -1e9)) & (w <= (hi if hi is not None else 1e9))]
    want = rows.groupby(by)["amount"]
    got = c.query_groups("v_amount", by, lo, hi, where=where)
    assert set(got) == set(want.groups)
    for label, x in want:
        assert [got[label]["var"], got[label]["std"]] == _var_std(x)


SQ = lambda c: c.query("v_score", -40, 300)  # noqa: E731


@pytest.mark.parametrize("change", [
    lambda c, b, r: transport("/api/v2/aggregate", {**b, "column": "v_score"}) if b["column"] == "v_score^2" else r,
    lambda c, b, r: _times(r, c, _stored(b)[0]) if b["column"] == "v_score^2" else r,
    lambda c, b, r: _later_cut(r, b) if b["column"] == "v_score^2" else r,
])
def test_wrong_square_answers_are_caught(spread, change):
    c, _ = spread
    honest = SQ(c)

    def post(path, body):
        r = transport(path, body)
        return change(c, body, r) if path == "/api/v2/aggregate" else r
    c.post = post
    try:
        with pytest.raises(IntegrityError):
            SQ(c)
    finally:
        c.post = transport
    assert SQ(c) == honest


def test_variance_survives_the_key_file(spread, tmp_path):
    c, _ = spread
    c.save(str(tmp_path / "k"), "pw")
    c2 = AgniyaClient.load(str(tmp_path / "k"), "pw", transport)
    assert c2.query("v_score", -10.5, 120.25) == c.query("v_score", -10.5, 120.25)
    assert c2.query_groups("v_amount", "age", 0, 99.5, where="score") == c.query_groups("v_amount", "age", 0, 99.5, where="score")


@pytest.fixture(scope="module")
def sorted_groups(setup):
    c, df = setup
    c.upload_sorted_groups("amount", df["amount"], by="region", by_values=df["region"], decimals=4)
    c.upload_sorted_groups("score", df["score"], by="age", by_values=df["age"], decimals=2)  # 60 groups, int labels
    return c, df


@pytest.mark.parametrize("col,by", [("amount", "region"), ("score", "age")])
def test_group_quantiles_match_pandas(sorted_groups, col, by):
    c, df = sorted_groups
    got = c.quantiles(col, QS, by=by)
    want = df[[col, by]].dropna().groupby(by)[col]
    assert set(got) == set(want.groups)
    for label, x in want:
        assert got[label] == [pytest.approx(x.quantile(q), abs=1e-9) for q in QS], label


GQ = lambda c: c.quantiles("amount", QS, by="region")  # noqa: E731


@pytest.mark.parametrize("change", [
    lambda r: {**r, "ciphertexts": r["ciphertexts"][::-1]},  # swapped
    lambda r: {**r, "ciphertexts": r["ciphertexts"][:-1]},  # one missing
    lambda r: {**r, "ciphertexts": [r["ciphertexts"][0]] * len(r["ciphertexts"])},  # another index's ciphertext
    lambda r: {**r, "ciphertexts": ["zz"] + r["ciphertexts"][1:]},  # malformed
])
def test_wrong_group_quantile_answers_are_caught(sorted_groups, change):
    c, _ = sorted_groups
    honest = GQ(c)
    c.post = lambda path, body: change(transport(path, body)) if path == "/api/v2/ciphertexts" else transport(path, body)
    try:
        with pytest.raises(IntegrityError):
            GQ(c)
    finally:
        c.post = transport
    assert GQ(c) == honest


def test_group_quantiles_need_their_copy_and_survive_the_key_file(sorted_groups, tmp_path):
    c, _ = sorted_groups
    with pytest.raises(ValueError, match="upload_sorted_groups"):
        c.quantiles("age", [0.5], by="region")
    with pytest.raises(RuntimeError, match="400"):
        c._v2("/api/v2/ciphertexts", {"column": "amount#region^sorted", "index": [10 ** 6]})
    c.save(str(tmp_path / "k"), "pw")
    c2 = AgniyaClient.load(str(tmp_path / "k"), "pw", transport)
    assert c2.quantiles("score", [0.5], by="age") == c.quantiles("score", [0.5], by="age")
