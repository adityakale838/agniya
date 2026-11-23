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

from agniya.core.batch_packing import BatchedAggregator, group_layout
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
    group_cases = [[0, [1], 1], [637_704_270, [325, 364, 325, 324], 1], [637_704_270, [69] * 47, 1],
                   [637_704_271, [1338] * 47, 3], [2**40, [10**6] * 100, 1], [9, [3] * 300, 3]]
    b = run_ts({"layout": {"p": a["p"], "q": a["q"], "cases": cases, "group_cases": group_cases}}, tmp_path)
    agg = BatchedAggregator(pub, priv)
    assert [list(x) for x in b["layout"]] == [list(agg.layout(m, c)) for m, c in cases]
    assert [list(x) for x in b["groupLayout"]] == [list(group_layout(pub, m, s, d)) for m, s, d in group_cases]


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
            "grouped": [{"column": "charges", "values": df["charges"].tolist(), "by": "age", "by_values": df["age"].tolist(),
                         "decimals": 4}],
            "queries": queries, "tamper": [["double", "query", "charges", None, None], ["double", "query", "age", 30, 45],
                                           ["no-witnesses", "query", "charges", 5000, 20000.5],
                                           ["double", "groups", "charges", "age"]]}}, tmp_path)
    finally:
        httpd.shutdown()
    scale = {"charges": 10**4, "age": 1, "bmi": 10**4}
    for (col, lo, hi), ans in zip(queries, a["answers"]):
        x = df[col]
        sel = x[(x >= (lo if lo is not None else -1e18)) & (x <= (hi if hi is not None else 1e18))]
        exact = sum(int(round(float(v) * scale[col])) for v in sel) / scale[col]  # what Python stores
        assert ans["count"] == len(sel), (col, lo, hi)
        assert ans["sum"] == pytest.approx(exact, abs=1e-9), (col, lo, hi)
        assert ans["verified"] is True
    assert len(a["tampered"]) == 4 and all(m.startswith("Integrity check failed") for m in a["tampered"]), a["tampered"]
    stored = json.dumps({k: str(v) for k, v in srv.owner_datasets["browser-e2e"]["columns"]["charges"].items()})
    assert a["p"] not in stored and format(int(a["p"]), "x") not in stored


def test_fixed_point_rounding_matches_python(tmp_path):
    """Exact .5 cases are common (5-decimal data at scale 10^4): both sides must round half to even."""
    df = pd.read_csv(os.path.join(ROOT, "data", "insurance_real.csv"))
    values = df["charges"].tolist() + [0.00005, 0.00015, -2.5, -3.5, 2.5, 1e-9, 123456.78905]
    for scale in (1, 10**4):
        a = run_ts({"fixed": {"values": values, "scale": scale}}, tmp_path)
        assert [int(v) for v in a["fixed"]] == [int(round(float(v) * scale)) for v in values]


@pytest.mark.parametrize("password,salt,n,r,p,dklen", [
    ("password", b"NaCl", 1024, 8, 16, 64),               # RFC 7914 test vector
    ("pleaseletmein", b"SodiumChloride", 16384, 8, 1, 64),  # RFC 7914 test vector
    ("correct horse \u00e9", b"0123456789abcdef", 2**17, 8, 1, 32),  # the key-file parameters, non-ASCII password
])
def test_scrypt_matches_hashlib(tmp_path, password, salt, n, r, p, dklen):
    import hashlib
    a = run_ts({"scrypt": {"password": password, "salt_hex": salt.hex(), "n": n, "r": r, "p": p, "dklen": dklen}}, tmp_path)
    want = hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, maxmem=256 * 1024 * 1024, dklen=dklen)
    assert a["scrypt"] == want.hex()


@pytest.fixture(scope="module")
def live_server():
    from werkzeug.serving import make_server
    httpd = make_server("127.0.0.1", 0, srv.app)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def _exact(df, col, lo, hi, scale):
    x = df[col]
    sel = x[(x >= (lo if lo is not None else -1e18)) & (x <= (hi if hi is not None else 1e18))]
    return len(sel), sum(int(round(float(v) * scale)) for v in sel) / scale


def _groups(df, col, by, where=None, lo=None, hi=None):
    """{label: (count, exact fixed-point sum)} as both clients store charges (4 decimals), optionally
    only rows with lo <= where <= hi."""
    if where:
        df = df.dropna(subset=[where])
        df = df[(df[where] >= lo) & (df[where] <= hi)]
    return {g: (len(x), sum(int(round(v * 10**4)) for v in x) / 10**4) for g, x in df.dropna(subset=[by]).groupby(by)[col]}


def _check(got_groups, want):
    got = {g["group"]: (g["count"], g["sum"]) for g in got_groups}
    assert got.keys() == want.keys()
    for label, (count, total) in want.items():
        assert got[label][0] == count and got[label][1] == pytest.approx(total, abs=1e-9)
    return got


def test_key_file_browser_to_python(tmp_path, live_server):
    from agniya.client import AgniyaClient
    df = pd.read_csv(os.path.join(ROOT, "data", "insurance_real.csv"))
    ages = df["age"].tolist()
    ages[0] = None  # rows missing either value are skipped by uploadBy, as by upload_by
    regions = df["region"].tolist()
    regions[1] = None  # and by uploadGrouped, as by upload_grouped
    a = run_ts({"client": {"url": live_server, "dataset": "kf-b2p", "save_password": "pw \u00e9", "columns": [
        {"name": "charges", "values": df["charges"].tolist(), "decimals": 4, "range": True},
        {"name": "age", "values": df["age"].tolist(), "decimals": 0, "range": False}],
        "by": [{"column": "charges", "values": df["charges"].tolist(), "by": "age", "by_values": ages,
                "decimals": 4, "by_decimals": 0}],
        "grouped": [{"column": "charges", "values": df["charges"].tolist(), "by": "region", "by_values": regions,
                     "decimals": 4},
                    {"column": "charges", "values": df["charges"].tolist(), "by": "region", "by_values": regions,
                     "decimals": 4, "where": "age", "where_values": ages, "where_decimals": 0},
                    # 47 ages: several plaintexts ("charges#age", "charges#age@1", ...)
                    {"column": "charges", "values": df["charges"].tolist(), "by": "age", "by_values": ages, "decimals": 4},
                    {"column": "charges", "values": df["charges"].tolist(), "by": "age", "by_values": ages,
                     "decimals": 4, "where": "bmi", "where_values": df["bmi"].tolist(), "where_decimals": 4}],
        "group_queries": [["charges", "region"], ["charges", "region", 30, 45, "age"], ["charges", "age"],
                          ["charges", "age", 25.5, 30.07, "bmi"]],
        "queries": [["charges", 30, 45, "age"], ["charges", None, None, "age"]]}}, tmp_path)
    rest = df.iloc[1:]
    for (lo, hi), ans in zip([(30, 45), (-1e18, 1e18)], a["answers"]):
        sel = rest["charges"][(rest["age"] >= lo) & (rest["age"] <= hi)]
        assert ans["count"] == len(sel)
        assert ans["sum"] == pytest.approx(sum(int(round(v * 10**4)) for v in sel) / 10**4, abs=1e-9)
    want = _groups(df.drop(index=1), "charges", "region")
    got = {g["group"]: (g["count"], g["sum"]) for g in a["groups"][0]["groups"]}
    assert got.keys() == want.keys()
    for label, (count, total) in want.items():
        assert got[label][0] == count and got[label][1] == pytest.approx(total, abs=1e-9)
    want_f = _groups(df.drop(index=[0, 1]), "charges", "region", "age", 30, 45)  # rows 0, 1 miss age / region
    got_f = {g["group"]: (g["count"], g["sum"]) for g in a["groups"][1]["groups"]}
    assert got_f.keys() == want_f.keys()
    for label, (count, total) in want_f.items():
        assert got_f[label][0] == count and got_f[label][1] == pytest.approx(total, abs=1e-9)
    assert a["groups"][2]["pages"] > 1 and a["groups"][3]["pages"] > 1
    got_a = _check(a["groups"][2]["groups"], _groups(df.drop(index=0), "charges", "age"))
    got_af = _check(a["groups"][3]["groups"], _groups(df.drop(index=0), "charges", "age", "bmi", 25.5, 30.07))
    path = tmp_path / "browser.agniya-key"
    path.write_text(a["keyfile"])
    with pytest.raises(ValueError, match="Wrong password"):
        AgniyaClient.load(str(path), "nope", live_server)
    c = AgniyaClient.load(str(path), "pw \u00e9", live_server)
    assert c.dataset == "kf-b2p" and c.priv.p == int(a["p"])
    for col, lo, hi, scale in [("charges", 5000, 20000.5, 10**4), ("charges", None, None, 10**4), ("age", None, None, 1)]:
        r = c.query(col, lo, hi)
        count, total = _exact(df, col, lo, hi, scale)
        assert r["count"] == count and r["sum"] == pytest.approx(total, abs=1e-9)
    r = c.query("charges", 30, 45, by="age")  # the browser's "charges|age" copy, read by Python
    assert (r["count"], r["sum"]) == (a["answers"][0]["count"], pytest.approx(a["answers"][0]["sum"], abs=1e-9))
    py = c.query_groups("charges", "region")  # the browser's "charges#region" copy, read by Python
    assert {k: (v["count"], pytest.approx(v["sum"], abs=1e-9)) for k, v in py.items()} == got
    py = c.query_groups("charges", "region", 30, 45, where="age")  # "charges#region|age", read by Python
    assert {k: (v["count"], pytest.approx(v["sum"], abs=1e-9)) for k, v in py.items()} == got_f
    for args, want in [(("charges", "age"), got_a), (("charges", "age", 25.5, 30.07, "bmi"), got_af)]:
        py = c.query_groups(*args[:2], *args[2:4], where=args[4] if len(args) > 2 else None)  # the browser's pages
        assert {k: (v["count"], pytest.approx(v["sum"], abs=1e-9)) for k, v in py.items()} == want


def test_key_file_python_to_browser(tmp_path, live_server):
    from agniya.client import AgniyaClient
    df = pd.read_csv(os.path.join(ROOT, "data", "insurance_real.csv"))
    c = AgniyaClient(live_server, dataset="kf-p2b")
    c.upload("charges", df["charges"], decimals=4, range_filter=True)
    c.upload("bmi", df["bmi"], decimals=4)
    c.upload_grouped("charges", df["charges"], by="children", by_values=df["children"], decimals=4)  # int labels
    c.upload_grouped("charges", df["charges"], by="children", by_values=df["children"], decimals=4,
                     where="bmi", where_values=df["bmi"], where_decimals=4)
    assert c.upload_grouped("charges", df["charges"], by="age", by_values=df["age"], decimals=4)["pages"] > 1
    assert c.upload_grouped("charges", df["charges"], by="age", by_values=df["age"], decimals=4,
                            where="bmi", where_values=df["bmi"], where_decimals=4)["pages"] > 1
    path = tmp_path / "python.agniya-key"
    c.save(str(path), "pw")
    queries = [["charges", 5000, 20000.5], ["charges", None, 1200], ["bmi", None, None]]
    a = run_ts({"load": {"keyfile": path.read_text(), "password": "pw", "url": live_server, "queries": queries,
                         "group_queries": [["charges", "children"], ["charges", "children", 25.5, 30.07, "bmi"],
                                           ["charges", "age"], ["charges", "age", 25.5, 30.07, "bmi"]]}},
                tmp_path)
    assert "error" not in a, a.get("error")
    assert a["dataset"] == "kf-p2b"
    assert {x["name"]: x["count"] for x in a["columns"] if "#" not in x["name"]} == {"charges": 1338, "bmi": 1338}
    want = _groups(df, "charges", "children")
    got = {g["group"]: (g["count"], g["sum"]) for g in a["groups"][0]["groups"]}
    assert got.keys() == want.keys()  # Python's int labels come back as numbers
    for label, (count, total) in want.items():
        assert got[label][0] == count and got[label][1] == pytest.approx(total, abs=1e-9)
    want_f = _groups(df, "charges", "children", "bmi", 25.5, 30.07)
    got_f = {g["group"]: (g["count"], g["sum"]) for g in a["groups"][1]["groups"]}
    assert got_f.keys() == want_f.keys()
    for label, (count, total) in want_f.items():
        assert got_f[label][0] == count and got_f[label][1] == pytest.approx(total, abs=1e-9)
    _check(a["groups"][2]["groups"], _groups(df, "charges", "age"))  # Python's pages, read by the browser
    _check(a["groups"][3]["groups"], _groups(df, "charges", "age", "bmi", 25.5, 30.07))
    for (col, lo, hi), ans in zip(queries, a["answers"]):
        count, total = _exact(df, col, lo, hi, 10**4)
        assert ans["count"] == count and ans["sum"] == pytest.approx(total, abs=1e-9)
    bad = run_ts({"load": {"keyfile": path.read_text(), "password": "wrong", "url": live_server, "queries": []}}, tmp_path)
    assert bad["error"] == "Wrong password or modified key file"
    d = json.loads(path.read_text())
    d["kdf"]["r"] = 4  # header is authenticated
    tampered = run_ts({"load": {"keyfile": json.dumps(d), "password": "pw", "url": live_server, "queries": []}}, tmp_path)
    assert tampered["error"] == "Wrong password or modified key file"
