"""Client-held keys: the server stores and aggregates ciphertexts it cannot decrypt."""
import json
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api"))
import server_optimized as srv  # noqa: E402
from agniya.client import AgniyaClient  # noqa: E402

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
    })
    c = AgniyaClient(transport, dataset="split")
    c.upload("amount", df["amount"], decimals=4)
    c.upload("age", df["age"], range_filter=True)
    c.upload("score", df["score"], decimals=2, range_filter=True)
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


def test_server_never_sees_private_key_or_plaintext(setup):
    c, df = setup
    sent = "".join(SENT)
    for secret in (c.priv.p, c.priv.q, c.priv.lambda_n, c.priv.mu):
        assert str(secret) not in sent and format(secret, "x") not in sent
    stored = srv.owner_datasets["split"]
    assert set(stored) == {"pub", "columns"} and not hasattr(stored["pub"], "p")
    assert set(stored["columns"]["amount"]) == {"cts", "slots", "count", "tags"}


def test_range_needs_ope_column(setup):
    c, _ = setup
    with pytest.raises(ValueError):
        c.query("amount", lo=1)
    with pytest.raises(RuntimeError, match="400"):
        transport("/api/v2/aggregate", {"dataset": "split", "column": "amount", "lo_tag": 1})


@pytest.mark.parametrize("patch,code", [({"n": "ff"}, 400), ({"ciphertexts": ["zz"]}, 400),
                                        ({"count": 10**6}, 400), ({"ope_tags": [5, 1, 2], "count": 3}, 400),
                                        ({"ciphertexts": ["0"]}, 400)])
def test_upload_validation(setup, patch, code):
    c, _ = setup
    ok = {"dataset": "v", "column": "x", "n": format(c.pub.n, "x"), "ciphertexts": ["2", "3"], "slots": 2, "count": 3}
    assert srv.app.test_client().post("/api/v2/columns", json=ok).status_code == 200
    body = {"dataset": "v", "column": "x", "n": format(c.pub.n, "x"), "ciphertexts": ["2", "3"],
            "slots": 2, "count": 4, **patch}
    assert srv.app.test_client().post("/api/v2/columns", json=body).status_code == code


def test_other_key_for_same_dataset_rejected(setup):
    c, _ = setup
    other = AgniyaClient(transport, dataset="split")
    with pytest.raises(RuntimeError, match="409"):
        other.upload("y", [1, 2, 3])
