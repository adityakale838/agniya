"""webapp/lib/agniya-browser.ts must agree with the Python implementation it mirrors.

Runs the TypeScript under Node (type stripping, Node >= 22.18) via webapp/scripts/crypto-check.mjs.
"""
import json
import os
import random
import secrets
import shutil
import subprocess
import sys
import threading

import pandas as pd
import pytest
from pyope.ope import OPE, ValueRange

from agniya.core.batch_packing import BatchedAggregator
from agniya.core.paillier import keypair_from_primes, decrypt_crt, encrypt

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "api"))
import server_optimized as srv  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def run_ts(job, tmp_path):
    path = tmp_path / "job.json"
    path.write_text(json.dumps(job))
    r = subprocess.run(["node", "--no-warnings", os.path.join(ROOT, "webapp", "scripts", "crypto-check.mjs"), str(path)],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_paillier_both_directions(tmp_path):
    msgs = [0, 1, 42, 2**1000 + 7]
    a = run_ts({"paillier": {"encrypt": [str(m) for m in msgs]}}, tmp_path)
    pub, priv = keypair_from_primes(int(a["p"]), int(a["q"]))
    assert pub.n.bit_length() == 2048
    cts = [int(c) for c in a["ciphertexts"]]
    assert [decrypt_crt(pub, priv, c) for c in cts] == msgs and len(set(cts)) == len(cts)
    py_cts = [encrypt(pub, m) for m in msgs]
    b = run_ts({"paillier": {"p": a["p"], "q": a["q"], "encrypt": [], "decrypt": [str(c) for c in py_cts]}}, tmp_path)
    assert [int(m) for m in b["decrypted"]] == msgs


def test_layout_matches_python(tmp_path):
    a = run_ts({"paillier": {"encrypt": []}}, tmp_path)
    pub, priv = keypair_from_primes(int(a["p"]), int(a["q"]))
    cases = [[0, 0], [1, 1], [46, 1338], [633_000_000, 1338], [2**32 - 1, 3000], [15_000_000, 10**6]]
    b = run_ts({"layout": {"p": a["p"], "q": a["q"], "cases": cases}}, tmp_path)
    agg = BatchedAggregator(pub, priv)
    assert [list(x) for x in b["layout"]] == [list(agg.layout(m, c)) for m, c in cases]


@pytest.mark.parametrize("top", [1, 46, 10**5, 633_000_000, 2**40])
def test_ope_tags_match_pyope(tmp_path, top):
    rng = random.Random(top)
    key = secrets.token_bytes(32)
    values = sorted({rng.randint(0, top) for _ in range(150)} | {0, top})
    a = run_ts({"ope": {"key_hex": key.hex(), "top": str(top), "values": [str(v) for v in values]}}, tmp_path)
    ope = OPE(key, in_range=ValueRange(0, top), out_range=ValueRange(0, 2**64 - 1))
    assert [int(t) for t in a["tags"]] == [ope.encrypt(v) for v in values]


def test_browser_client_end_to_end(tmp_path):
    from werkzeug.serving import make_server
    httpd = make_server("127.0.0.1", 0, srv.app)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        df = pd.read_csv(os.path.join(ROOT, "data", "insurance_real.csv"))
        queries = [["charges", None, None], ["charges", 5000, 20000.5], ["age", 30, 45], ["age", 100, 200],
                   ["bmi", None, None]]
        a = run_ts({"client": {"url": f"http://127.0.0.1:{httpd.server_port}", "dataset": "browser-e2e", "columns": [
            {"name": "charges", "values": df["charges"].tolist(), "decimals": 4, "range": True},
            {"name": "age", "values": df["age"].tolist(), "decimals": 0, "range": True},
            {"name": "bmi", "values": df["bmi"].tolist(), "decimals": 4, "range": False}],
            "queries": queries}}, tmp_path)
    finally:
        httpd.shutdown()
    for (col, lo, hi), ans in zip(queries, a["answers"]):
        x = df[col]
        sel = x[(x >= (lo if lo is not None else -1e18)) & (x <= (hi if hi is not None else 1e18))]
        assert ans["count"] == len(sel), (col, lo, hi)
        assert ans["sum"] == pytest.approx(sel.sum(), abs=len(sel) * 0.5e-4), (col, lo, hi)
    stored = json.dumps({k: str(v) for k, v in srv.owner_datasets["browser-e2e"]["columns"]["charges"].items()})
    assert a["p"] not in stored and format(int(a["p"]), "x") not in stored
