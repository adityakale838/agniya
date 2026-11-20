"""
Benchmark of the current AGNIYA code. Every README/UI number must come from here.

Run:  envb\\Scripts\\python.exe -X utf8 tools\\bench.py [--rows 20000] [--skip-server] [--skip-seal]
Writes tools/bench_results.json. (tools/verify_claims.py is the audit of the old main branch.)
"""
import argparse, io, json, os, platform, random, statistics, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import gmpy2
from agniya.core import paillier as P
from agniya.core.precomputation import RandomnessPool
from agniya.core.batch_packing import BatchedAggregator

R = {}


def med(fn, n):
    ts = []
    for _ in range(n):
        t = time.perf_counter(); fn(); ts.append(time.perf_counter() - t)
    return statistics.median(ts)


def section(name, d):
    R[name] = d
    print(f"{name}: {json.dumps(d)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=20_000)
    ap.add_argument("--skip-server", action="store_true")
    ap.add_argument("--skip-seal", action="store_true")
    a = ap.parse_args()
    random.seed(1)
    section("env", {"python": sys.version.split()[0], "platform": platform.platform(),
                    "cpu": platform.processor(), "cpus": os.cpu_count(), "gmpy2": gmpy2.version()})

    t = time.perf_counter(); pub, priv = P.generate_keypair(2048)
    section("keygen_2048", {"seconds": round(time.perf_counter() - t, 3), "n_bits": pub.n.bit_length()})

    m = 123_456
    c = P.encrypt(pub, m)
    section("single_value_ms", {
        "encrypt": round(med(lambda: P.encrypt(pub, m), 20) * 1e3, 3),
        "decrypt": round(med(lambda: P.decrypt(pub, priv, c), 20) * 1e3, 3),
        "decrypt_crt": round(med(lambda: P.decrypt_crt(pub, priv, c), 20) * 1e3, 3),
    })

    pool = RandomnessPool(pub)
    k = 512
    t = time.perf_counter(); pool.refill(k); off = time.perf_counter() - t
    t = time.perf_counter(); cts = [pool.encrypt(v) for v in range(k)]; on = time.perf_counter() - t
    section("randomness_pool", {"offline_ms_per_rn_all_cores": round(off / k * 1e3, 3),
                                "online_us_per_encryption": round(on / k * 1e6, 2),
                                "all_ciphertexts_distinct": len(set(cts)) == k})

    cts2048 = [P.encrypt(pub, i) for i in range(64)] * 32
    t = med(lambda: P.sum_ciphertexts(pub, cts2048), 5)
    section("homomorphic_add", {"ciphertexts": len(cts2048), "ms": round(t * 1e3, 2),
                                "adds_per_sec": round(len(cts2048) / t)})

    agg = BatchedAggregator(pub, priv, encrypt_batch=RandomnessPool(pub).encrypt_batch)
    values = [random.randint(3_000_000, 15_000_000) for _ in range(a.rows)]  # cents
    t = time.perf_counter(); col = agg.encrypt_column(values); t_enc = time.perf_counter() - t
    t = time.perf_counter(); total = agg.sum_column(col); t_sum = time.perf_counter() - t
    section("packed_column", {"rows": a.rows, "values_per_ciphertext": col["slots"],
                              "ciphertexts": len(col["ciphertexts"]), "exact": total == sum(values),
                              "encrypt_s": round(t_enc, 3), "encrypt_rows_per_sec": round(a.rows / t_enc),
                              "sum_ms": round(t_sum * 1e3, 2), "sum_rows_per_sec": round(a.rows / t_sum)})

    if not a.skip_server:
        sys.path.insert(0, os.path.join(ROOT, "api"))
        import pandas as pd
        import server_optimized as srv
        cl = srv.app.test_client()
        csv = os.path.join(ROOT, "data", "insurance_real.csv")
        df = pd.read_csv(csv)
        with open(csv, "rb") as f:
            cl.post("/api/upload", data={"file": (io.BytesIO(f.read()), "insurance_real.csv")},
                    content_type="multipart/form-data")
        schema = [{"name": "charges", "encryption": "Paillier-2048"}]
        t = time.perf_counter()
        enc = cl.post("/api/encrypt", json={"filename": "insurance_real.csv", "schema": schema}).get_json()
        t_enc = time.perf_counter() - t
        q = cl.post("/api/query", json={"filename": "insurance_real.csv", "type": "SUM", "column": "charges"}).get_json()
        exact = float(df["charges"].sum())
        section("server_insurance_charges", {"rows": len(df), "encrypt_s": round(t_enc, 3),
                                             "ciphertexts": enc.get("ciphertexts"), "query_ms": q["time_ms"],
                                             "sum": q["result"], "pandas_sum": round(exact, 4),
                                             "abs_error": round(abs(q["result"] - exact), 6)})

    if not a.skip_seal:
        try:
            import tenseal as ts
            ctx = ts.context(ts.SCHEME_TYPE.BFV, poly_modulus_degree=8192, plain_modulus=1032193)
            vals = [random.randint(1, 200) for _ in range(4096)]
            t = med(lambda: ts.bfv_vector(ctx, vals), 5)
            section("seal_bfv_reference", {"values_per_ciphertext": 4096, "encrypt_ms": round(t * 1e3, 2),
                                           "us_per_value": round(t / 4096 * 1e6, 3)})
        except ImportError:
            pass

    with open(os.path.join(ROOT, "tools", "bench_results.json"), "w") as f:
        json.dump(R, f, indent=2)


if __name__ == "__main__":
    main()
