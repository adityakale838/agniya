"""Independent check: Microsoft SEAL (BFV, through TenSEAL) computes the same SUM, COUNT, AVG, GROUP BY and
range totals as AGNIYA's Paillier client, exactly, on the same fixed-point data.

BFV here uses a 41-bit prime plaintext modulus t = 1 (mod 2 * 8192), so batching works and every total in
these datasets stays below t / 2. The GROUP BY and WHERE masks are plaintext vectors on SEAL's side: this is
a check of the arithmetic, not a privacy design. Skipped where tenseal isn't installed (as in CI).
"""
import json
import os
import sys

import pandas as pd
import pytest

ts = pytest.importorskip("tenseal")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api"))
import server_optimized as srv  # noqa: E402
from agniya.client import AgniyaClient  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
T = 1099511922689  # smallest prime above 2^40 with T = 1 (mod 16384)


def transport(path, body):
    r = srv.app.test_client().post(path, json=json.loads(json.dumps(body)))
    assert r.status_code < 400, r.get_json()
    return r.get_json()


@pytest.fixture(scope="module")
def seal():
    ctx = ts.context(ts.SCHEME_TYPE.BFV, poly_modulus_degree=8192, plain_modulus=T)
    ctx.generate_galois_keys()

    def total(xs, mask=None):  # encrypted vector, optional plaintext mask, encrypted sum, decrypt
        enc = ts.bfv_vector(ctx, list(xs))
        return (enc * list(mask) if mask is not None else enc).sum().decrypt()[0]
    return total


def fixed(series, decimals):
    return [int(round(v * 10 ** decimals)) for v in series]


def test_insurance_sum_avg_group_by_and_range_match_seal(seal):
    df = pd.read_csv(os.path.join(ROOT, "data", "insurance_real.csv"))
    x = fixed(df["charges"], 4)
    c = AgniyaClient(transport, dataset="seal-crosscheck-insurance")
    c.upload("charges", df["charges"], decimals=4)
    c.upload_by("charges", df["charges"], by="age", by_values=df["age"], decimals=4)
    c.upload_grouped("charges", df["charges"], by="region", by_values=df["region"], decimals=4)
    ones = [1] * len(x)

    r = c.query("charges")
    assert round(r["sum"] * 10**4) == seal(x) and r["count"] == seal(ones)
    assert r["avg"] == pytest.approx(seal(x) / 10**4 / seal(ones), rel=1e-12)

    for label, g in c.query_groups("charges", "region").items():
        mask = [int(v == label) for v in df["region"]]
        assert round(g["sum"] * 10**4) == seal(x, mask) and g["count"] == seal(ones, mask), label

    r = c.query("charges", 30, 45, by="age")
    mask = [int(30 <= a <= 45) for a in df["age"]]
    assert round(r["sum"] * 10**4) == seal(x, mask) and r["count"] == seal(ones, mask)
    c.delete()


def test_bank_exposure_and_default_rate_match_seal(seal):
    df = pd.read_csv(os.path.join(ROOT, "data", "bank_customers.csv"))
    loans, defaults = fixed(df["loan_amount"], 2), list(df["default_flag"])
    c = AgniyaClient(transport, dataset="seal-crosscheck-bank")
    c.upload_grouped("loan_amount", df["loan_amount"], by="risk_band", by_values=df["risk_band"], decimals=2)
    c.upload_grouped("default_flag", df["default_flag"], by="segment", by_values=df["segment"])
    for label, g in c.query_groups("loan_amount", "risk_band").items():
        mask = [int(v == label) for v in df["risk_band"]]
        assert round(g["sum"] * 100) == seal(loans, mask), label
    for label, g in c.query_groups("default_flag", "segment").items():
        mask = [int(v == label) for v in df["segment"]]
        assert g["sum"] == seal(defaults, mask) and g["count"] == seal([1] * len(df), mask), label
    c.delete()
