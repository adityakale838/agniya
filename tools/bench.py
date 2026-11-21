"""
AGNIYA benchmark: the ONLY source of performance numbers for README, slides and papers.

    envb\\Scripts\\python.exe -X utf8 tools\\bench.py                 # full run, updates README table
    envb\\Scripts\\python.exe -X utf8 tools\\bench.py --quick         # fewer repetitions, no README update
    ... --out tools/bench_baseline.json --no-readme                    # keep a named snapshot

Rules baked in:
- every timed operation is checked for an exact result; a wrong result aborts the run
- timings: warm-up, then repetitions; report median and p10-p90
- offline (precomputable) and online costs are reported separately
- output records git commit, dirty flag, hardware, library versions
"""
import argparse, io, json, os, platform, random, statistics, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import gmpy2
from agniya.core import paillier as P
from agniya.core.precomputation import RandomnessPool
from agniya.core.batch_packing import BatchedAggregator

R = {}


def stats(fn, reps, warmup=2):
    """Per-call seconds: median, p10, p90."""
    for _ in range(warmup):
        fn()
    ts = []
    for _ in range(reps):
        t = time.perf_counter(); fn(); ts.append(time.perf_counter() - t)
    ts.sort()
    q = lambda f: ts[min(len(ts) - 1, int(f * len(ts)))]
    return {"median": statistics.median(ts), "p10": q(0.1), "p90": q(0.9), "reps": reps}


def ms(s):
    return {k: (round(v * 1e3, 4) if k != "reps" else v) for k, v in s.items()}


def us(s):
    return {k: (round(v * 1e6, 2) if k != "reps" else v) for k, v in s.items()}


def section(name, d):
    R[name] = d
    print(f"{name}: {json.dumps(d)}", flush=True)


def git(*args):
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    except Exception:
        return None


def cpu_name():
    try:
        if sys.platform == "win32":
            import winreg
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            return winreg.QueryValueEx(k, "ProcessorNameString")[0].strip()
        with open("/proc/cpuinfo") as f:
            return next(l.split(":", 1)[1].strip() for l in f if l.startswith("model name"))
    except Exception:
        return platform.processor()


def ram_gb():
    try:
        import psutil
        return round(psutil.virtual_memory().total / 2**30)
    except ImportError:
        return None


def methods():
    try:
        RandomnessPool(P.generate_keypair(2048)[0], method="djn")
        return ["standard", "djn"]
    except TypeError:
        return ["standard"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "tools", "bench_results.json"))
    ap.add_argument("--no-readme", action="store_true")
    ap.add_argument("--sizes", default="1000,10000,100000")
    a = ap.parse_args()
    reps = 7 if a.quick else 25
    sizes = [int(s) for s in a.sizes.split(",")]
    random.seed(1)

    section("meta", {
        "git_commit": git("rev-parse", "--short", "HEAD"), "git_dirty": bool(git("status", "--porcelain")),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "python": sys.version.split()[0],
        "platform": platform.platform(), "cpu": cpu_name(), "ram_gb": ram_gb(), "logical_cpus": os.cpu_count(),
        "gmpy2": gmpy2.version(), "key_bits": 2048, "reps": reps,
    })

    keygen = stats(lambda: P.generate_keypair(2048), max(3, reps // 3), warmup=1)
    pub, priv = P.generate_keypair(2048)
    section("keygen_ms", ms(keygen))

    m = 123_456
    c = P.encrypt(pub, m)
    assert P.decrypt_crt(pub, priv, c) == m == P.decrypt(pub, priv, c)
    section("decrypt_crt_ms", ms(stats(lambda: P.decrypt_crt(pub, priv, c), reps)))

    # r^n generation: the dominant cost of encryption. Offline (precomputable) vs online.
    for method in methods():
        pool = RandomnessPool(pub, method=method, workers=1)
        off = stats(lambda: pool.refill(1), reps)
        pool.refill(reps + 10)
        cts = []
        on = stats(lambda: cts.append(pool.encrypt(m)), reps)
        assert len(set(cts)) == len(cts) and all(P.decrypt_crt(pub, priv, x) == m for x in cts[:5])
        section(f"rn_{method}", {"offline_ms_per_rn_1core": ms(off), "online_us_per_encryption": us(on)})

    cts2048 = [P.encrypt(pub, i) for i in range(64)] * 32
    add = stats(lambda: P.sum_ciphertexts(pub, cts2048), max(5, reps // 3))
    assert P.decrypt_crt(pub, priv, P.sum_ciphertexts(pub, cts2048)) == sum(range(64)) * 32
    section("homomorphic_add", {"ciphertexts": 2048, "ms": ms(add),
                                "adds_per_sec": round(2048 / add["median"])})

    # Packed columns, end to end per size: encrypt (all cores) and SUM.
    for method in methods():
        for n_rows in sizes:
            vals = [random.randint(3_000_000, 15_000_000) for _ in range(n_rows)]  # salaries in cents
            pool = RandomnessPool(pub, method=method)
            agg = BatchedAggregator(pub, priv, encrypt_batch=pool.encrypt_batch)
            t = time.perf_counter(); col = agg.encrypt_column(vals); t_enc = time.perf_counter() - t
            pool.close()
            assert agg.sum_column(col) == sum(vals)
            s = stats(lambda: agg.sum_column(col), max(5, reps // 3))
            section(f"column_{method}_{n_rows}", {
                "rows": n_rows, "values_per_ciphertext": col["slots"], "ciphertexts": len(col["ciphertexts"]),
                "encrypt_s_all_cores": round(t_enc, 3), "encrypt_us_per_value": round(t_enc / n_rows * 1e6, 2),
                "sum_ms": ms(s), "sum_values_per_sec": round(n_rows / s["median"]),
                "storage_bytes_per_value": round(len(col["ciphertexts"]) * 512 / n_rows, 2)})

    # API round trip on a real dataset.
    sys.path.insert(0, os.path.join(ROOT, "api"))
    import pandas as pd
    import server_optimized as srv
    cl = srv.app.test_client()
    csv = os.path.join(ROOT, "data", "insurance_real.csv")
    df = pd.read_csv(csv)
    with open(csv, "rb") as f:
        cl.post("/api/upload", data={"file": (io.BytesIO(f.read()), "insurance_real.csv")},
                content_type="multipart/form-data")
    # OPE columns: "age" has 47 distinct values, "charges" 1,337 (fixed point, 4 decimals).
    for schema_name, schema, rng_col, lo, hi in [
            ("packed", [{"name": "charges", "encryption": "Paillier-2048"}], None, None, None),
            ("packed+ope_age", [{"name": "charges", "encryption": "Paillier-2048"},
                                {"name": "age", "encryption": "OPE+Paillier"}], "age", 30, 45),
            ("ope_charges", [{"name": "charges", "encryption": "OPE+Paillier"}], "charges", 5000, 20000.5)]:
        t = time.perf_counter()
        enc = cl.post("/api/encrypt", json={"filename": "insurance_real.csv", "schema": schema}).get_json()
        t_enc = time.perf_counter() - t
        body = {"filename": "insurance_real.csv", "type": "SUM", "column": "charges"}
        res = cl.post("/api/query", json=body).get_json()["result"]
        assert abs(res - df["charges"].sum()) < len(df) * 0.5e-4, res
        qs = stats(lambda: cl.post("/api/query", json=body), max(5, reps // 3))
        out = {"rows": len(df), "encrypt_s": round(t_enc, 3), "ciphertexts": enc["ciphertexts"], "sum_query_ms": ms(qs)}
        if rng_col:
            rbody = {**body, "column": rng_col, "rangeMin": lo, "rangeMax": hi}
            sel = df[rng_col][(df[rng_col] >= lo) & (df[rng_col] <= hi)]
            r = cl.post("/api/query", json=rbody).get_json()
            assert r["records_processed"] == len(sel) and abs(r["result"] - sel.sum()) < len(sel) * 0.5e-4, r
            out.update(range_query={"column": rng_col, "min": lo, "max": hi, "rows_selected": len(sel),
                                    "ms": ms(stats(lambda: cl.post("/api/query", json=rbody), max(5, reps // 3)))})
        section(f"api_insurance_{schema_name}", out)

    # Baselines in the same harness.
    vals = [random.randint(1, 10**6) for _ in range(100_000)]
    section("baseline_plain_python_sum_100k_ms", ms(stats(lambda: sum(vals), reps)))
    try:
        from phe import paillier as phe
        ppub, _ = phe.generate_paillier_keypair(n_length=2048)
        section("baseline_phe_encrypt_one_value_ms", ms(stats(lambda: ppub.encrypt(m), max(5, reps // 3))))
    except ImportError:
        pass
    try:
        import tenseal as ts
        ctx = ts.context(ts.SCHEME_TYPE.BFV, poly_modulus_degree=8192, plain_modulus=1032193)
        v = [random.randint(1, 200) for _ in range(4096)]
        assert ts.bfv_vector(ctx, v).decrypt() == v
        s = stats(lambda: ts.bfv_vector(ctx, v), max(5, reps // 3))
        section("baseline_seal_bfv_4096_values", {"encrypt_ms": ms(s), "us_per_value": round(s["median"] / 4096 * 1e6, 3)})
    except ImportError:
        pass

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(R, f, indent=2)
    print(f"wrote {a.out}")
    if not (a.quick or a.no_readme):
        update_readme()


def update_readme(results_path=None):
    """Replace the table between BENCH markers in README.md with numbers from the JSON."""
    r = R or json.load(open(results_path or os.path.join(ROOT, "tools", "bench_results.json")))
    meta = r["meta"]
    best = "djn" if "rn_djn" in r else "standard"
    big = max((k for k in r if k.startswith(f"column_{best}_")), key=lambda k: r[k]["rows"])
    col = r[big]
    rn = r[f"rn_{best}"]
    std = r["rn_standard"]
    rows = [
        ("Key generation (2048-bit)", f"{r['keygen_ms']['median']:.0f} ms"),
        ("Decrypt (CRT)", f"{r['decrypt_crt_ms']['median']:.2f} ms"),
        ("rⁿ generation, standard (1 core)", f"{std['offline_ms_per_rn_1core']['median']:.2f} ms"),
    ]
    if best == "djn":
        rows.append(("rⁿ generation, DJN fixed-base (1 core)", f"{rn['offline_ms_per_rn_1core']['median']:.3f} ms"))
    rows += [
        ("Encrypt with a precomputed rⁿ (online)", f"{rn['online_us_per_encryption']['median']:.1f} µs"),
        ("Homomorphic additions", f"{r['homomorphic_add']['adds_per_sec']:,} ciphertexts/s"),
        (f"Packed column, {col['rows']:,} values: encrypt (all cores)",
         f"{col['encrypt_s_all_cores']:.2f} s = {col['encrypt_us_per_value']:.1f} µs/value "
         f"({col['values_per_ciphertext']} values/ciphertext)"),
        (f"Packed column, {col['rows']:,} values: SUM",
         f"{col['sum_ms']['median']:.1f} ms = {col['sum_values_per_sec']:,} values/s (exact)"),
        ("Storage, packed", f"{col['storage_bytes_per_value']} bytes/value"),
    ]
    api = r.get("api_insurance_packed")
    if api:
        rows.append((f"API, insurance_real.csv ({api['rows']:,} rows): encrypt / SUM query",
                     f"{api['encrypt_s']:.2f} s / {api['sum_query_ms']['median']:.1f} ms"))
    ope = r.get("api_insurance_ope_charges")
    if ope:
        rows.append((f"API, insurance_real.csv charges as OPE+Paillier: encrypt / range SUM",
                     f"{ope['encrypt_s']:.2f} s / {ope['range_query']['ms']['median']:.1f} ms"))
    if "baseline_seal_bfv_4096_values" in r:
        rows.append(("Reference: SEAL BFV (TenSEAL), 4,096 values", f"{r['baseline_seal_bfv_4096_values']['us_per_value']} µs/value"))
    if "baseline_phe_encrypt_one_value_ms" in r:
        rows.append(("Reference: python-paillier (phe), one value", f"{r['baseline_phe_encrypt_one_value_ms']['median']:.1f} ms"))
    table = "\n".join(["| Operation | Median |", "|---|---|"] + [f"| {k} | {v} |" for k, v in rows])
    note = (f"_Generated by `tools/bench.py` at commit `{meta['git_commit']}`"
            f"{' (dirty tree)' if meta['git_dirty'] else ''}, {meta['timestamp']}: {meta['cpu']}, "
            f"{meta['logical_cpus']} logical CPUs, {meta.get('ram_gb')} GB RAM, {meta['platform']}, "
            f"Python {meta['python']}, gmpy2 {meta['gmpy2']}. "
            f"p10/p90 and all other sizes in `tools/bench_results.json`._")
    path = os.path.join(ROOT, "README.md")
    text = open(path, encoding="utf-8").read()
    start, end = "<!-- BENCH:START -->", "<!-- BENCH:END -->"
    if start in text and end in text:
        text = text[:text.index(start) + len(start)] + "\n" + table + "\n\n" + note + "\n" + text[text.index(end):]
        open(path, "w", encoding="utf-8").write(text)
        print("README table updated")


if __name__ == "__main__":
    main()
