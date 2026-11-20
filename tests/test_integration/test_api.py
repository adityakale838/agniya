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
    })
    c = srv.app.test_client()
    buf = io.BytesIO(df.to_csv(index=False).encode())
    assert c.post("/api/upload", data={"file": (buf, "t.csv")}, content_type="multipart/form-data").status_code == 200
    schema = [{"name": "amount", "encryption": "Paillier-2048"},
              {"name": "age", "encryption": "OPE+Paillier"},
              {"name": "visits", "encryption": "Paillier-2048"},
              {"name": "name", "encryption": "AES-256"}]
    r = c.post("/api/encrypt", json={"filename": "t.csv", "schema": schema})
    assert r.status_code == 200, r.get_json()
    return c, df


def q(c, **kw):
    return c.post("/api/query", json={"filename": "t.csv", **kw}).get_json()


@pytest.mark.parametrize("col", ["amount", "age", "visits"])
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


def test_ciphertexts_are_real(client):
    c, _ = client
    proof = q(c, type="SUM", column="amount")["encryption_proof"]
    assert proof["modulus_n_bit_length"] == 2048
    assert all(b > 4000 for b in proof["ciphertext_bit_lengths"])
