"""
Reproducible checks of AGNIYA's README claims against the actual code.

NOTE: this audits `main` @ 340c4cd (before the phase0 cleanup). Run it from a checkout of
that commit; on the cleaned branch the deleted modules report as errors. For the current
code use tools/bench.py.

Run:  envb\\Scripts\\python.exe tools\\verify_claims.py [--key-bits 2048] [--quick]
Writes results to tools/verify_claims_results.json and prints a summary.
Every check is self-contained; a failing check is reported, not fatal.
"""
import argparse, json, os, platform, random, secrets, statistics, sys, time, traceback
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import gmpy2
from agniya.core import paillier as P

R = {}  # results


def timeit(fn, n):
    """Median per-call seconds over n calls."""
    ts = []
    for _ in range(n):
        t = time.perf_counter(); fn(); ts.append(time.perf_counter() - t)
    return statistics.median(ts)


def check(name):
    def deco(fn):
        def run(*a):
            t = time.perf_counter()
            try:
                R[name] = fn(*a)
            except Exception as e:
                R[name] = {"error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc(limit=3)}
            R[name] = R[name] if isinstance(R[name], dict) else {"value": R[name]}
            R[name]["_check_seconds"] = round(time.perf_counter() - t, 2)
            print(f"\n== {name}\n{json.dumps({k: v for k, v in R[name].items() if k != 'trace'}, indent=2, default=str)}")
        return run
    return deco


# ---------------------------------------------------------------- crypto core
@check("keygen")
def c_keygen(bits):
    t = time.perf_counter(); pub, priv = P.generate_keypair(bits); dt = time.perf_counter() - t
    return {"key_bits": bits, "n_bits_actual": pub.n.bit_length(), "seconds": round(dt, 2), "_keys": (pub, priv)}


@check("encrypt_latency")
def c_encrypt(pub, priv, n):
    m = 123456
    n2, nn = pub.n_squared, pub.n
    g_n2 = gmpy2.mpz(n2)

    def builtin_pow():  # textbook, no gmpy2
        r = secrets.randbelow(nn - 1) + 1
        return pow(pub.g, m, n2) * pow(r, nn, n2) % n2

    def g_shortcut_gmpy2():  # g = n+1  =>  g^m = 1 + m*n (mod n^2)
        r = secrets.randbelow(nn - 1) + 1
        return (1 + m * nn) * int(gmpy2.powmod(r, nn, g_n2)) % n2

    p2, q2 = priv.p_squared, priv.q_squared
    q2inv = int(gmpy2.invert(q2, p2))

    def crt_r_n():  # owner-side encryption: r^n via CRT mod p^2, q^2 (needs private key)
        r = secrets.randbelow(nn - 1) + 1
        a = int(gmpy2.powmod(r, nn % (p2 - p2 // priv.p), p2))  # phi(p^2) = p(p-1)
        b = int(gmpy2.powmod(r, nn % (q2 - q2 // priv.q), q2))
        rn = b + q2 * ((a - b) * q2inv % p2)
        return (1 + m * nn) * rn % n2

    # correctness of the two optimised variants
    for f in (g_shortcut_gmpy2, crt_r_n):
        assert P.decrypt_crt(pub, priv, f()) == m, f.__name__
    res = {
        "agniya_encrypt_ms": timeit(lambda: P.encrypt(pub, m), n) * 1e3,
        "textbook_builtin_pow_ms": timeit(builtin_pow, max(3, n // 3)) * 1e3,
        "g_shortcut+gmpy2_ms": timeit(g_shortcut_gmpy2, n) * 1e3,
        "crt_owner_side_ms": timeit(crt_r_n, n) * 1e3,
        "readme_claim_baseline_ms": 285, "readme_claim_optimized_ms": 0.24,
    }
    try:
        from phe import paillier as phe
        ppub, _ = phe.generate_paillier_keypair(n_length=pub.bit_length)
        res["python-paillier(phe)_encrypt_ms"] = timeit(lambda: ppub.raw_encrypt(m), n) * 1e3
    except ImportError:
        pass
    return {k: round(v, 3) if isinstance(v, float) else v for k, v in res.items()}


@check("decrypt_latency")
def c_decrypt(pub, priv, n):
    c = P.encrypt(pub, 987654)
    return {
        "decrypt_ms": round(timeit(lambda: P.decrypt(pub, priv, c), n) * 1e3, 3),
        "decrypt_crt_ms": round(timeit(lambda: P.decrypt_crt(pub, priv, c), n) * 1e3, 3),
        "readme_claim": "100ms -> 25ms",
    }


@check("homomorphic_add_throughput")
def c_add(pub, priv):
    cts = [P.encrypt(pub, i) for i in range(200)]
    n2 = pub.n_squared
    t = time.perf_counter()
    for _ in range(50):
        acc = 1
        for c in cts:
            acc = acc * c % n2
    dt = time.perf_counter() - t
    assert P.decrypt_crt(pub, priv, acc) == sum(range(200))
    return {"adds_per_sec": round(200 * 50 / dt), "readme_claim": 33772}


@check("sliding_window_vs_builtin_pow")
def c_sliding(pub):
    from agniya.core.optimized_modexp import SlidingWindowExponentiator, GMPY2_AVAILABLE
    sw = SlidingWindowExponentiator(4)
    b, e, mod = secrets.randbelow(pub.n_squared), pub.n, pub.n_squared
    assert sw._sliding_window_powmod(b, e, mod, False) == pow(b, e, mod)
    t_py = timeit(lambda: sw._sliding_window_powmod(b, e, mod, False), 3)
    t_pow = timeit(lambda: pow(b, e, mod), 3)
    t_gmp = timeit(lambda: gmpy2.powmod(b, e, mod), 5)
    return {
        "gmpy2_installed_so_sliding_window_never_runs": GMPY2_AVAILABLE,
        "pure_python_sliding_window_ms": round(t_py * 1e3, 2),
        "builtin_pow_ms": round(t_pow * 1e3, 2),
        "gmpy2_powmod_ms": round(t_gmp * 1e3, 2),
        "sliding_vs_pow_speedup": round(t_pow / t_py, 2),
        "readme_claim": "15-30% faster than pow()",
    }


# ------------------------------------------------------------ "optimisations"
@check("precompute_cache_determinism")
def c_determinism(pub):
    from agniya.core.precomputation import PrecomputationTable
    t = time.perf_counter()
    tbl = PrecomputationTable(pub, max_cache_size=5000)
    init = time.perf_counter() - t
    a, b = tbl.get_or_encrypt(42), tbl.get_or_encrypt(42)
    fresh1, fresh2 = P.encrypt(pub, 42), P.encrypt(pub, 42)
    n = 200_000
    t = time.perf_counter()
    for i in range(n):
        tbl.get_or_encrypt(i % 1000 + 1)
    lookups = n / (time.perf_counter() - t)
    d = {}
    t = time.perf_counter()
    for i in range(n):
        d.get(i % 1000 + 1)
    dict_rate = n / (time.perf_counter() - t)
    return {
        "init_precompute_1001_values_s": round(init, 2),
        "cache_returns_identical_ciphertext": a == b,
        "plain_paillier_returns_identical_ciphertext": fresh1 == fresh2,
        "cached_lookups_per_sec": round(lookups),
        "plain_python_dict_get_per_sec": round(dict_rate),
        "readme_claims": "1000x / 74,426x / 6.7M ops/sec",
        "_tbl": tbl,
    }


@check("rns_compression_roundtrip")
def c_rns(pub, priv):
    from agniya.compression.rns_compression import RNSCompressor
    rc = RNSCompressor(bit_size=pub.bit_length, num_primes=32)
    m = 31337
    c = P.encrypt(pub, m)
    blob = rc.compress(c)
    back = rc.decompress(blob)
    try:
        dec = P.decrypt_crt(pub, priv, back)
    except Exception as e:
        dec = f"error {e}"
    return {
        "ciphertext_bytes": (c.bit_length() + 7) // 8,
        "compressed_bytes": len(blob),
        "M_bits(info_capacity)": int(rc.M).bit_length(),
        "roundtrip_equal": back == c,
        "decrypts_to_original": dec == m,
        "decrypted_value": str(dec)[:40],
        "readme_claim": "50% lossless, zero security loss",
    }


@check("lsh_dedup_on_real_ciphertexts")
def c_dedup(pub, tbl):
    from agniya.storage.deduplication import CiphertextDeduplicator
    vals = [random.randint(1, 10) for _ in range(300)]  # only 10 distinct plaintexts
    d1 = CiphertextDeduplicator()
    d1.add_batch([P.encrypt(pub, v) for v in vals])
    d2 = CiphertextDeduplicator()
    d2.add_batch([tbl.get_or_encrypt(v) for v in vals])
    return {
        "distinct_plaintexts": len(set(vals)), "rows": len(vals),
        "dedup_saved_pct_with_proper_paillier": round(d1.get_stats()["storage_saved_pct"], 1),
        "dedup_saved_pct_with_agniya_cache": round(d2.get_stats()["storage_saved_pct"], 1),
        "readme_claim": "60-80% savings, works with probabilistic encryption",
    }


@check("batch_packing_overflow")
def c_packing(pub, priv):
    from agniya.core.batch_packing import BatchedAggregator
    agg = BatchedAggregator(pub, priv)
    small = [random.randint(1, 1000) for _ in range(500)]
    # salaries in cents, 20k rows: per-slot sums exceed 2^32
    big = [random.randint(3_000_000, 15_000_000) for _ in range(20_000)]
    t = time.perf_counter(); got_small = agg.sum_values(small); ts = time.perf_counter() - t
    got_big = agg.sum_values(big)
    return {
        "slots_per_ciphertext": agg.batch_size,
        "small_values_correct": got_small == sum(small), "small_500_values_s": round(ts, 3),
        "large_values_expected": sum(big), "large_values_got": got_big,
        "large_values_correct": got_big == sum(big),
    }


@check("multi_level_cache_key_downgrade")
def c_multilevel(pub, priv):
    from agniya.storage.multi_level_cache import MultiLevelCache
    mlc = MultiLevelCache(pub, priv, max_cache_size=1000, verbose=False)
    vals = list(range(1, 150))
    assert mlc.smart_sum(vals) == sum(vals)
    return {"low_key_bits_used_for_queries_over_100_rows": mlc.low_pub.n.bit_length(),
            "storage_key_bits": pub.n.bit_length()}


@check("jit_encryptor")
def c_jit(pub):
    from agniya.core.paillier_jit import JITEncryptor
    JITEncryptor(pub).encrypt_batch([1, 2, 3])
    return {"ran": True}


@check("gpu_int64_representation")
def c_gpu(pub):
    import numpy as np
    try:
        np.int64(pub.n)
        return {"fits_int64": True}
    except OverflowError as e:
        return {"fits_int64": False, "note": "paillier_gpu/oram_gpu cast n to cp.int64 -> init fails, silently CPU", "err": str(e)}


@check("parallel_tree_vs_sequential")
def c_tree(pub, priv):
    from agniya.core.ultimate_system import UltimateOptimizedDatabase
    db = UltimateOptimizedDatabase.__new__(UltimateOptimizedDatabase)
    db.pub, db.priv = pub, priv
    base = [P.encrypt(pub, i) for i in range(64)]
    cts = base * 32  # 2048 ciphertexts
    n2 = pub.n_squared

    def seq():
        acc = 1
        for c in cts:
            acc = acc * c % n2
        return acc
    mcts, mn2 = [gmpy2.mpz(c) for c in cts], gmpy2.mpz(n2)

    def seq_gmpy2():  # same loop, GMP integers, one thread
        acc = gmpy2.mpz(1)
        for c in mcts:
            acc = acc * c % mn2
        return acc
    assert int(seq_gmpy2()) == seq()
    t_seq = timeit(seq, 3)
    t_gmp = timeit(seq_gmpy2, 3)
    t_par = timeit(lambda: db.sum_encrypted_parallel(cts, 4), 3)
    return {"n": len(cts), "sequential_python_int_ms": round(t_seq * 1e3, 1),
            "sequential_gmpy2_single_thread_ms": round(t_gmp * 1e3, 1), "parallel_tree_ms": round(t_par * 1e3, 1),
            "tree_vs_python_seq": round(t_seq / t_par, 2), "tree_vs_gmpy2_seq": round(t_gmp / t_par, 2),
            "readme_claim": "1.5-3x"}


def _enc_chunk(args):  # top-level so ProcessPool can pickle it
    n, vals = args
    n2 = gmpy2.mpz(n) ** 2
    return [int((1 + v * n) * gmpy2.powmod(secrets.randbelow(n - 1) + 1, n, n2) % n2) for v in vals]


@check("batch_encrypt_threads_vs_processes")
def c_parallel(pub):
    from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
    vals = list(range(1, 161))
    t = time.perf_counter(); [P.encrypt(pub, v) for v in vals]; t_seq = time.perf_counter() - t
    t = time.perf_counter()
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda v: P.encrypt(pub, v), vals))  # what precomputation.py does
    t_thr = time.perf_counter() - t
    w = os.cpu_count() or 4
    chunks = [(pub.n, vals[i::w]) for i in range(w)]
    with ProcessPoolExecutor(w) as ex:
        list(ex.map(_enc_chunk, [(pub.n, [1])] * w * 2))  # warm up every worker (Windows spawn+import)
        t = time.perf_counter(); list(ex.map(_enc_chunk, chunks)); t_proc = time.perf_counter() - t
    return {"n": len(vals), "sequential_s": round(t_seq, 2), "threadpool8_s": round(t_thr, 2),
            "processpool_g_shortcut_s": round(t_proc, 2),
            "thread_speedup": round(t_seq / t_thr, 2), "process_speedup": round(t_seq / t_proc, 2)}


@check("honest_precompute_randomness_pool")
def c_pool(pub, priv):
    """IND-CPA-safe alternative to the plaintext->ciphertext cache: precompute r^n offline, use each once."""
    n, n2 = pub.n, pub.n_squared
    g2 = gmpy2.mpz(n2)
    k = 200
    t = time.perf_counter()
    pool = [int(gmpy2.powmod(secrets.randbelow(n - 1) + 1, n, g2)) for _ in range(k)]
    t_off = (time.perf_counter() - t) / k
    vals = [random.randint(1, 10**6) for _ in range(k)]
    t = time.perf_counter()
    cts = [(1 + v * n) * pool.pop() % n2 for v in vals]
    t_on = (time.perf_counter() - t) / k
    assert all(P.decrypt_crt(pub, priv, c) == v for c, v in zip(cts[:5], vals[:5]))
    return {"offline_ms_per_r^n": round(t_off * 1e3, 3), "online_us_per_encryption": round(t_on * 1e6, 2),
            "online_encryptions_per_sec": round(1 / t_on), "ciphertexts_all_distinct": len(set(cts)) == k}


@check("plaintext_baseline")
def c_plain():
    vals = [random.randint(1, 100000) for _ in range(10_000)]
    t = timeit(lambda: sum(vals), 20)
    return {"python_sum_10k_ms": round(t * 1e3, 3),
            "note": "sum_query() takes plaintext and holds the private key; compare against this"}


# ------------------------------------------------------------ the web server path
@check("server_end_to_end_sum")
def c_server():
    import io, pandas as pd
    sys.path.insert(0, os.path.join(ROOT, "api"))
    import server_optimized as srv
    app = srv.app.test_client()
    csv = os.path.join(ROOT, "data", "insurance_real.csv")
    df = pd.read_csv(csv)
    col = "charges" if "charges" in df.columns else df.select_dtypes("number").columns[-1]
    with open(csv, "rb") as f:
        r = app.post("/api/upload", data={"file": (io.BytesIO(f.read()), "insurance_real.csv")},
                     content_type="multipart/form-data")
    up = r.get_json()
    fname = up.get("filename", "insurance_real.csv")
    schema = [{"name": c, "encryption": "Paillier-2048" if c == col else "AES-256"} for c in df.columns]
    t = time.perf_counter()
    enc = app.post("/api/encrypt", json={"filename": fname, "schema": schema}).get_json()
    t_enc = time.perf_counter() - t
    q = app.post("/api/query", json={"filename": fname, "type": "SUM", "column": col}).get_json()
    a = app.post("/api/query", json={"filename": fname, "type": "AVG", "column": col}).get_json()
    exact = int(df[col].fillna(0).astype(int).sum())
    return {
        "column": col, "rows": len(df),
        "encrypt_endpoint_s": round(t_enc, 2), "encrypt_reported_encrypt_time_s": enc.get("encrypt_time_seconds"),
        "exact_sum": exact, "server_sum": q.get("result"),
        "sum_rel_error_pct": round(abs(q.get("result", 0) - exact) / exact * 100, 3),
        "exact_avg": round(exact / len(df), 2), "server_avg": a.get("result"),
        "server_reported_cache_hit_rate": q.get("cache_hit_rate"),
        "server_reported_ops_per_sec": q.get("ops_per_sec"),
        "loaded_committed_private_key_from_repo": os.path.exists(os.path.join(ROOT, "cache", "paillier_cache_2048bit.pkl")),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key-bits", type=int, default=2048)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--skip-server", action="store_true")
    a = ap.parse_args()
    n = 5 if a.quick else 20
    R["env"] = {"python": sys.version.split()[0], "platform": platform.platform(),
                "cpu": platform.processor(), "gmpy2": gmpy2.version(), "cpus": os.cpu_count()}
    random.seed(1)
    c_keygen(a.key_bits)
    pub, priv = R["keygen"].pop("_keys")
    c_encrypt(pub, priv, n); c_decrypt(pub, priv, n); c_add(pub, priv); c_sliding(pub)
    c_determinism(pub)
    tbl = R["precompute_cache_determinism"].pop("_tbl", None)
    c_rns(pub, priv)
    if tbl is not None:
        c_dedup(pub, tbl)
    c_packing(pub, priv); c_multilevel(pub, priv); c_jit(pub); c_gpu(pub)
    c_tree(pub, priv); c_parallel(pub); c_pool(pub, priv); c_plain()
    if not a.skip_server:
        c_server()
    out = os.path.join(ROOT, "tools", "verify_claims_results.json")
    with open(out, "w") as f:
        json.dump(R, f, indent=2, default=str)
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()
