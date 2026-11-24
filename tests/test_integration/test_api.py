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
                                      ("score", "region"), ("age", "visits"), ("amount", "age")])
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
        assert (r["pages"] > 1) == (by == "age")  # 60 groups: several plaintexts


def test_group_by_rejects(client):
    c, _ = client
    assert "No GROUP BY copy" in q(c, type="SUM", column="amount", group_by="name")["error"]  # 200 distinct
    assert "numeric" in q(c, type="SUM", column="amount", group_by="region", filter_column="name", rangeMin=1)["error"]


@pytest.mark.parametrize("field,by,fc,lo,hi", [("amount", "region", "age", 30, 40), ("amount", "region", "amount", -100, 2000),
                                               ("visits", "region", "score", -10.5, 120.25), ("age", "visits", "age", None, 25),
                                               ("score", "region", "age", 18, 18), ("amount", "region", "age", 200, 300),
                                               ("amount", "age", "score", -10.5, 120.25), ("score", "age", "age", 30, 49)])
def test_group_by_with_range(client, field, by, fc, lo, hi):
    c, df = client
    rows = df[list(dict.fromkeys([field, by, fc]))].dropna()
    w = rows[fc]
    want = rows[(w >= (lo if lo is not None else -1e9)) & (w <= (hi if hi is not None else 1e9))].groupby(by)[field].agg(
        ["sum", "mean", "count"])
    for op, agg in [("SUM", "sum"), ("AVG", "mean"), ("COUNT", "count")]:
        r = q(c, type=op, column=field, group_by=by, filter_column=fc, rangeMin=lo, rangeMax=hi)
        got = {g["group"]: g["result"] for g in r["groups"]}
        assert set(got) == set(want.index), r  # groups with no rows in range are left out, as in SQL
        for label, row in want.iterrows():
            assert got[label] == pytest.approx(row[agg], abs=1e-6), (op, label)
        assert r["records_processed"] == want["count"].sum() and r["filter_applied"]


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


@pytest.mark.parametrize("col,lo,hi", [("age", None, None), ("score", None, None), ("age", 30, 40),
                                       ("score", -10.5, 120.25), ("score", 12.34, 12.34), ("score", 400, 500)])
def test_min_max_median_match_pandas(client, col, lo, hi):
    c, df = client
    x = df[col]
    sel = x[(x >= (lo if lo is not None else -1e9)) & (x <= (hi if hi is not None else 1e9))]
    for op, want in [("MIN", sel.min()), ("MAX", sel.max()), ("MEDIAN", sel.median())]:
        r = q(c, type=op, column=col, rangeMin=lo, rangeMax=hi)
        assert r["records_processed"] == len(sel), r
        assert (r["result"] is None) if sel.empty else r["result"] == pytest.approx(want, abs=1e-9), (op, r)
        assert len(r["encryption_proof"]["ciphertext_bit_lengths"]) <= 2


def test_min_max_median_need_a_sorted_column(client):
    c, _ = client
    assert "OPE+Paillier" in q(c, type="MIN", column="amount")["error"]  # packed unsorted
    assert "OPE+Paillier" in q(c, type="MEDIAN", column="amount", filter_column="age", rangeMin=30)["error"]


def _close(got, want):  # pandas gives NaN for fewer than 2 rows; we give None
    return got is None if pd.isna(want) else got == pytest.approx(want, rel=1e-9, abs=1e-9)


@pytest.mark.parametrize("field,by,fc,lo,hi", [("amount", None, None, None, None), ("visits", None, None, None, None),
                                               ("score", None, "score", -10.5, 120.25), ("age", None, "age", 18, 18),
                                               ("amount", None, "age", 30, 40), ("score", None, "age", 200, 300),
                                               ("amount", "region", None, None, None), ("score", "age", None, None, None),
                                               ("amount", "region", "age", 30, 40), ("amount", "age", "score", -10.5, 120.25)])
def test_variance_and_stddev_match_pandas(client, field, by, fc, lo, hi):
    c, df = client
    rows = df[list(dict.fromkeys([field] + [x for x in (by, fc) if x]))].dropna()
    if fc:
        w = rows[fc]
        rows = rows[(w >= (lo if lo is not None else -1e9)) & (w <= (hi if hi is not None else 1e9))]
    for op, agg in [("VARIANCE", "var"), ("STDDEV", "std")]:
        r = q(c, type=op, column=field, group_by=by, filter_column=fc, rangeMin=lo, rangeMax=hi)
        assert _close(r["result"], getattr(rows[field], agg)()), (op, r)
        assert r["records_processed"] == len(rows)
        if by:
            want = getattr(rows.groupby(by)[field], agg)()
            got = {g["group"]: g["result"] for g in r["groups"]}
            assert set(got) == set(want.index) and all(_close(got[k], v) for k, v in want.items()), (op, r)


@pytest.mark.parametrize("field,by", [("amount", "region"), ("score", "age"), ("visits", "region")])
def test_min_max_median_by_group_match_pandas(client, field, by):
    c, df = client
    want = df[[field, by]].dropna().groupby(by)[field]
    for op, agg in [("MIN", "min"), ("MAX", "max"), ("MEDIAN", "median")]:
        r = q(c, type=op, column=field, group_by=by)
        got = {g["group"]: g["result"] for g in r["groups"]}
        assert got.keys() == set(want.groups), r
        for label, v in getattr(want, agg)().items():
            assert got[label] == pytest.approx(v, abs=1e-9), (op, label)
        assert r["records_processed"] == want.size().sum()


@pytest.mark.parametrize("field,by,fc,lo,hi", [("amount", "region", "age", 30, 40), ("amount", "region", "amount", -100, 2000),
                                               ("visits", "region", "score", -10.5, 120.25), ("score", "age", "score", 0, None),
                                               ("amount", "region", "age", 200, 300)])
def test_min_max_median_by_group_with_a_range_match_pandas(client, field, by, fc, lo, hi):
    c, df = client
    rows = df[list(dict.fromkeys([field, by, fc]))].dropna()
    w = rows[fc]
    want = rows[(w >= (lo if lo is not None else -1e9)) & (w <= (hi if hi is not None else 1e9))].groupby(by)[field]
    for op, agg in [("MIN", "min"), ("MAX", "max"), ("MEDIAN", "median")]:
        r = q(c, type=op, column=field, group_by=by, filter_column=fc, rangeMin=lo, rangeMax=hi)
        got = {g["group"]: g["result"] for g in r["groups"]}
        assert got.keys() == set(want.groups), r  # groups with no rows in range are left out
        for label, v in getattr(want, agg)().items():
            assert got[label] == pytest.approx(v, abs=1e-9), (op, label)
    assert "numeric" in q(c, type="MEDIAN", column="amount", group_by="region", filter_column="name", rangeMin=1)["error"]


@pytest.mark.parametrize("op,agg,fc,lo,hi", [("SUM", "sum", None, None, None), ("AVG", "mean", None, None, None),
                                             ("STDDEV", "std", None, None, None), ("MEDIAN", "median", None, None, None),
                                             ("SUM", "sum", "age", 30, 50), ("MEDIAN", "median", "age", 30, 50),
                                             ("VARIANCE", "var", "score", -10.5, 120.25)])
def test_group_by_two_columns(client, op, agg, fc, lo, hi):
    c, df = client
    rows = df[list(dict.fromkeys(["amount", "region", "visits"] + ([fc] if fc else [])))].dropna()
    if fc:
        rows = rows[(rows[fc] >= lo) & (rows[fc] <= hi)]
    want = getattr(rows.groupby(["region", "visits"])["amount"], agg)()
    r = q(c, type=op, column="amount", group_by="region,visits", filter_column=fc, rangeMin=lo, rangeMax=hi)
    got = {g["group"]: g["result"] for g in r["groups"]}
    assert got.keys() == {f"{a}, {b}" for a, b in want.index}, r  # labels "region, visits" ("n, 3.0": visits has NaNs)
    for (a, b), v in want.items():
        assert (got[f"{a}, {b}"] is None) if pd.isna(v) else got[f"{a}, {b}"] == pytest.approx(v, rel=1e-9, abs=1e-9)


def test_group_by_two_columns_rejects(client):
    c, _ = client
    assert "Unknown" in q(c, type="SUM", column="amount", group_by="region,nope")["error"]
    assert "groups" in q(c, type="SUM", column="amount", group_by="region,name")["error"]  # 200+ groups
