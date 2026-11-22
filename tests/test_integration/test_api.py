"""API round-trip: upload -> encrypt -> query must match pandas exactly."""
import io
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api"))
import server_optimized as srv  # noqa: E402


@pytest.fixture(scope="module")
def client():
    rng = pd.Series(range(200))
    df = pd.DataFrame({
        "amount": (rng * 37.1234 - 900).round(4),          # floats incl. negatives
        "age": (rng % 60 + 18).astype(int),                 # OPE-filterable ints
        "visits": [None if i % 17 == 0 else i % 9 for i in range(200)],  # NaNs
        "name": [f"p{i}" for i in range(200)],
        "score": ((rng * 7919) % 1000 * 0.37 - 50).round(2),  # OPE floats incl. negatives, unsorted
        "region": [None if i % 23 == 0 else "nsew"[i * i % 7 % 4] for i in range(200)],  # GROUP BY key, skewed
    })
    c = srv.app.test_client()
    buf = io.BytesIO(df.to_csv(index=False).encode())
    assert c.post("/api/upload", data={"file": (buf, "t.csv")}, content_type="multipart/form-data").status_code == 200
    schema = [{"name": "amount", "encryption": "Paillier-2048"},
              {"name": "age", "encryption": "OPE+Paillier"},
              {"name": "visits", "encryption": "Paillier-2048"},
              {"name": "name", "encryption": "AES-256"},
              {"name": "score", "encryption": "OPE+Paillier"}]
    r = c.post("/api/encrypt", json={"filename": "t.csv", "schema": schema})
    assert r.status_code == 200, r.get_json()
    return c, df


def q(c, **kw):
    return c.post("/api/query", json={"filename": "t.csv", **kw}).get_json()


@pytest.mark.parametrize("col", ["amount", "age", "visits", "score"])
def test_sum_avg_count_match_pandas(client, col):
    c, df = client
    assert q(c, type="SUM", column=col)["result"] == pytest.approx(df[col].sum(), abs=1e-6)
    assert q(c, type="AVG", column=col)["result"] == pytest.approx(df[col].mean(), abs=1e-6)
    assert q(c, type="COUNT", column=col)["result"] == df[col].count()


@pytest.mark.parametrize("lo,hi", [(30, 40), (None, 20), (70, None), (200, 300), (0, 5), (18, 18)])
def test_ope_range_filter(client, lo, hi):
    c, df = client
    sel = df["age"][(df["age"] >= (lo if lo is not None else -10**9)) & (df["age"] <= (hi if hi is not None else 10**9))]
    r = q(c, type="SUM", column="age", rangeMin=lo, rangeMax=hi)
    assert r["result"] == sel.sum() and r["records_processed"] == len(sel)


def test_range_filter_requires_ope(client):
    c, _ = client
    assert "error" in q(c, type="SUM", column="amount", rangeMin=1)
    assert "error" in q(c, type="SUM", column="age", filter_column="amount", rangeMin=1)


@pytest.mark.parametrize("field,by,lo,hi", [("amount", "age", 30, 40), ("visits", "age", None, 25),
                                            ("amount", "score", -10.5, 120.25), ("age", "score", 0, None),
                                            ("score", "age", 18, 18), ("amount", "age", 200, 300)])
def test_sum_where_other_column_in_range(client, field, by, lo, hi):
    c, df = client
    rows = df[[field, by]].dropna()  # SQL: NULLs in either column drop out
    b = rows[by]
    sel = rows[field][(b >= (lo if lo is not None else -1e9)) & (b <= (hi if hi is not None else 1e9))]
    for op, want in [("SUM", sel.sum()), ("AVG", sel.mean() if len(sel) else 0), ("COUNT", len(sel))]:
        r = q(c, type=op, column=field, filter_column=by, rangeMin=lo, rangeMax=hi)
        assert r["result"] == pytest.approx(want, abs=1e-6) and r["records_processed"] == len(sel), r


@pytest.mark.parametrize("field,by", [("amount", "region"), ("visits", "region"), ("amount", "visits"),
                                      ("score", "region"), ("age", "visits")])
def test_group_by(client, field, by):
    c, df = client
    want = df[[field, by]].dropna().groupby(by)[field].agg(["sum", "mean", "count"])
    for op, agg in [("SUM", "sum"), ("AVG", "mean"), ("COUNT", "count")]:
        r = q(c, type=op, column=field, group_by=by)
        got = {g["group"]: g["result"] for g in r["groups"]}
        assert set(got) == set(want.index), r
        for label, row in want.iterrows():
            assert got[label] == pytest.approx(row[agg], abs=1e-6), (op, label)
        assert r["records_processed"] == want["count"].sum()


def test_group_by_rejects(client):
    c, _ = client
    assert "No GROUP BY copy" in q(c, type="SUM", column="amount", group_by="name")["error"]  # 200 distinct
    assert "not supported" in q(c, type="SUM", column="amount", group_by="region", rangeMin=1)["error"]


def test_ciphertexts_are_real(client):
    c, _ = client
    proof = q(c, type="SUM", column="amount")["encryption_proof"]
    assert proof["modulus_n_bit_length"] == 2048
    assert all(b > 4000 for b in proof["ciphertext_bit_lengths"])


@pytest.mark.parametrize("lo,hi", [(-50, 0), (-10.5, 120.25), (None, -49.9), (300, None), (12.34, 12.34), (400, 500)])
def test_ope_range_filter_floats(client, lo, hi):
    c, df = client
    x = df["score"]
    sel = x[(x >= (lo if lo is not None else -1e9)) & (x <= (hi if hi is not None else 1e9))]
    for op, want in [("SUM", sel.sum()), ("COUNT", len(sel))]:
        r = q(c, type=op, column="score", rangeMin=lo, rangeMax=hi)
        assert r["result"] == pytest.approx(want, abs=1e-6) and r["records_processed"] == len(sel)
