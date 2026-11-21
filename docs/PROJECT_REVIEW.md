# AGNIYA: Project Review

**Date:** 2026-11-21 · **Commit reviewed:** `main` @ `340c4cd` · **Machine:** Intel i5-1145G7 (4C/8T, AVX-512), 16 GB, Iris Xe (no CUDA), Windows 11, Python 3.12.10, gmpy2 2.3.2

Every number below was measured on this machine with `tools/verify_claims.py`. Raw output is in `tools/verify_claims_results.json`. Re-run it after every optimization so the README and this document can only quote numbers the script produces.

---

## 0. Status update: Phase 0 done on branch `phase0-honest-baseline`

Sections 1–8 describe `main` @ `340c4cd`. On the branch:

| Finding | Status |
|---|---|
| Private key committed (§5.2) | `cache/` removed and ignored; keys never written to disk. **The old key stays in git history: treat it as burned.** |
| Deterministic cache (§5.1) | Replaced by a one-time rⁿ pool (`precomputation.py`): online encryption 32 µs, every ciphertext distinct |
| Server stores plaintext, quantized SUM (§5.3, §6.2) | `/api/encrypt` encrypts packed columns; SUM on insurance charges is exact to the 4-decimal fixed point (error 0.003 vs 43,256) |
| 1024/512-bit keys (§5.4) | Removed; `PaillierCryptosystem`/`Database` refuse < 2048 bits |
| Packing overflow (§6.1) | Slots sized with headroom; tests with saturated slots and 5k cent-valued salaries |
| RNS, LSH dedup, GPU, JIT, SIMD, ORAM, multi-level cache, planners, 3 extra servers, 8 stub benchmarks | Deleted (110 files, ~29k lines); recoverable from `main` |
| Keygen 2047-bit / slow (§6.5) | Exact length, sieve + gmpy2: 2.0 s → 0.15 s |
| Fabricated UI/API metrics | Removed; README numbers come from `tools/bench.py` |
| OPE hard-coded key, `hash(plaintext)` stored | Fixed |
| Tests / types | 87 tests pass, incl. API exactness + OPE range filters (was 91 + 1 failing + 2 broken files); `tsc` errors 10 → 0 |

Current numbers are in `README.md` and `tools/bench_results.json`. Phase 1 (§9) starts from them.

## 0b. Status update: Phase 1 on branch `phase1-fast-encryption`

Both runs: same laptop (i5-1145G7, 16 GB, Windows 11, Python 3.12.10, gmpy2 2.3.2), clean git tree, 25 repetitions, medians, every result checked exact. Baseline: `tools/bench_baseline_phase0.json` @ `be09265`. Phase 1: `tools/bench_results.json` @ `04a2969`.

| Metric | Phase 0 | Phase 1 | Change |
|---|---|---|---|
| rⁿ generation, 1 core | 10.69 ms | **0.672 ms** | 15.9× |
| Encrypt 1,000,000 packed values (all cores) | 66.0 s (standard rⁿ, same run) | **6.28 s = 6.3 µs/value** | 10.5× |
| Encrypt 100,000 packed values | 5.76 s | **1.40 s** | 4.1× (single core: below the parallel threshold) |
| SUM over 1,000,000 encrypted values | — | **127 ms = 7.9M values/s** | |
| API, insurance with OPE per-row column: encrypt | 5.65 s | **2.13 s** | 2.7× |
| Storage | 8.8–9.9 bytes/value packed | same | |
| Gap to SEAL BFV (1.15 µs/value, same harness) | ~56× | **~5.5×** | |

**What changed:** `agniya/core/djn.py` computes rⁿ as `hsᵅ`, where `hs = hⁿ`, `h = −x² mod n` and `α` is |n|/2 = 1,024 bits, using a window-8 comb table (17 MB, built in 0.19 s). `RandomnessPool` uses it by default, with a persistent worker pool. The exponent length is deliberately the conservative |n|/2. The scratchpad probe showed a 448-bit `α` would be ~2.3× faster again, but don't shorten it without a written security argument.

**Security assumption:** with the default `AGNIYA_RN_METHOD=djn`, IND-CPA rests on DCR **plus** the DJN short-exponent assumption. `AGNIYA_RN_METHOD=standard` restores DCR-only randomness at the Phase 0 speed. Any publication must state which one was used. **Before relying on DJN, confirm the exponent length and the construction of `h` against Damgård–Jurik–Nielsen (2010) directly.**

### How to quote numbers (applies to README, slides, papers, the patent draft)

1. Only numbers from `tools/bench.py` output, with the machine line from the JSON `meta` and the git commit.
2. Per-value cost (µs/value) or throughput (values/s), never a bare "N× faster". A ratio is fine only when both sides come from the same run of the same harness (as in the table above).
3. Say whether a cost is **online** (20–23 µs per ciphertext with a precomputed rⁿ) or **end to end** (6.3 µs/value at 1M rows, packing included). Don't present online cost as encryption cost.
4. Say which rⁿ method (DJN or standard) and which key size (2048-bit, ~112-bit security).
5. Laptop numbers vary ±10–20% between sessions (thermal state, background load). Official numbers should come from one fixed, rentable machine; laptop numbers are for development.

### Next optimizations (measured candidates, in order of value)

1. ~~**OPE per-row columns**~~: done, see §0c.
2. **Owner/server split:** move the private key to the client. This is a security property, not speed, but every number should eventually be measured in that topology.
3. **GROUP BY via slot packing:** one decryption for many groups.
4. **3072-bit keys (128-bit security):** measure end-to-end cost; expect ~2.5× per value.
5. **Native backends**, only if profiling shows the comb multiplications dominate: Intel's Paillier library (AVX-512 IFMA is available on this CPU) or a small C/Rust extension.

## 0c. Status update: OPE columns (commit `bee2832`, same branch)

Results: `tools/bench_results.json` @ `bee2832`, clean tree, same laptop. The "before" column is the Phase 1 run @ `04a2969`. Paths this change did not touch came out ~7% slower in this run (e.g. 1M-row encrypt 6.75 s vs 6.28 s), which is laptop variance (rule 5 above).

| `insurance_real.csv`, 1,338 rows, via the API | Phase 1 | Now |
|---|---|---|
| Encrypt `charges` (packed) + `age` as OPE+Paillier | 2.13 s, 1,369 ciphertexts | **0.335 s, 31 ciphertexts** |
| Encrypt `charges` as OPE+Paillier (1,337 distinct values, 4 decimals) | not measured (profiled: ~3.3 s OPE + 0.9 s per-row Paillier) | **1.54 s, 24 ciphertexts** |
| Range SUM `age` 30–45 (421 rows) / `charges` 5,000–20,000.5 (706 rows), exact | not measured | **12.4 ms / 14.6 ms** |

**What changed:**
- **Faster OPE tags:** `agniya/hybrid/fast_ope.py` subclasses pyope and produces **bit-identical tags** (tested against pyope with the same key). It generates the AES-CTR coin tape with C-level iteration and encrypts a batch in one walk of the OPE tree, so each node's hypergeometric sample is computed once and each distinct value is tagged once. Profiled on 1,338 rows: `age` went from 0.67 s to 0.004 s, `charges` from 3.09 s to 0.99 s. The rest is pyope's pure-Python hypergeometric sampler.
- **Sorted packing:** OPE+Paillier columns are packed in **sorted order**, and the per-row Paillier ciphertexts are gone. A range is a contiguous run of slots. `BatchedAggregator.sum_range` multiplies the ciphertexts wholly inside the range, decrypts that product once, and decrypts the at most two edge ciphertexts separately.

**Security delta:**
- **Server:** sorted order reveals nothing to the server beyond what the OPE tags already reveal (the order).
- **Key holder:** the key holder now sees the individual values in the two edge ciphertexts, up to 2 × slots ≈ 100–150 values. In the current topology the key holder is the data owner. With delegated decryption it would be a leak; fix that by masking edge slots, or by keeping per-row ciphertexts for edge chunks only.

**Next in this area:**
- Parallelize FastOPE across processes for high-cardinality columns. This is worth it only above roughly 10k distinct values, because of the ~1 s Windows process start-up.
- Replace pyope's sampler only behind an identical-output test.

---

## 1. Verdict in one paragraph

AGNIYA is a Python Paillier (additively homomorphic) library with a Flask API and a Next.js dashboard. The Paillier core works: keygen, encrypt, decrypt and CRT decrypt are textbook-correct and 91 of 92 unit tests pass. Almost every headline number in the README comes from one of these instead:

- a **plaintext→ciphertext dictionary**, which makes encryption deterministic and breaks Paillier's security guarantee;
- **hard-coded constants**, as in 8 of the 12 "evaluation suite" benchmarks;
- **code paths that never run**: the GPU, JIT and sliding-window paths all silently fall back to CPU/gmpy2.

The web server does not encrypt the uploaded data at all. It keeps plaintext, rounds the values into the range 1–1000, and returns a SUM that is off by 0.24% on the bundled insurance dataset. The private key is committed to the public GitHub repo. None of this is fatal, because the honest version of this project is buildable and the measurements below show real speedups to chase. But the current claims cannot be used in a patent, a paper or a pitch.

---

## 2. Setup status (done)

| Item | State |
|---|---|
| Repo | Fresh clone of `github.com/adityakale838/agniya`, branch `main` |
| Python env | `envb/` venv, Python 3.12 (3.15 lacks wheels for numba/gmpy2), editable install `pip install -e .` |
| `requirements.txt` | Was a **committed folder containing `desktop.ini`**, so the README install step failed. Replaced with a real pinned file (uncommitted change). |
| Frontend | `webapp/` `npm install` OK; `tsc --noEmit` reports **10 type errors** (`app/dashboard/page.tsx` uses fields missing from `QueryResult`; `lib/api.ts` compares number to string). `next dev` still runs (type errors don't block dev). |
| Tests | `pytest tests`: **91 passed, 1 failed**, plus 2 files that fail to import (`tests/test_initials.py`, `tests/test_math_utils.py` import modules deleted long ago). The failure passes `enable_tiered_cache=`, which `UltimateOptimizedDatabase` no longer accepts; `run_ultimate_benchmark()` has the same bug. |
| GPU | Not testable here (no NVIDIA GPU). The code-level analysis in §5.6 shows the GPU path cannot work for 2048-bit keys on any GPU. |

Run it:

```powershell
.\envb\Scripts\Activate.ps1
python -m pytest tests --ignore=tests/test_initials.py --ignore=tests/test_math_utils.py
python -X utf8 tools\verify_claims.py            # ~2 min; --skip-server to skip the API check
python api\server_optimized.py                    # what start.ps1 launches (port 5000)
cd webapp; npm run dev                            # port 3000
```

### Branches: nothing to merge

There are 6 remote branches: `main`, `aditya`, `feature/setup`, `cleaned-main`, `main-backup`, `HEAD`. The other branches show "48 commits ahead" only because history was rewritten with `filter-branch` (`f5fae87 Temp commit before filter-branch`), so the same commits exist twice with different hashes. I checked every code-file blob on every branch against all of `main`'s history, and **each one already exists in `main`'s history**. The branches are older snapshots. They also contain a committed virtualenv (`envb/`, ~8,400 files).

The only thing they hold that today's `main` tree lacks is root-level scripts that `main` **deliberately deleted** in `9215e14` (2025-12-27): `benchmark_vs_competitors.py`, `security_analysis.py`, `demo_entropy_aware.py`, `prove_encrypted_computation.py`, `comprehensive_security_audit.py` and the `docs/*.md` set. The README still tells users to run 13 of these deleted files (see §7). **Recommendation:** delete the four stale branches once the team agrees; they are a source of confusion, not code.

---

## 3. What the system actually does (as implemented)

```
Browser ──CSV──► /api/upload  (pandas reads file)
        ──────► /api/encrypt  → builds UltimateOptimizedDatabase (keygen + 1,001 encryptions, ~17-33 s)
                                 loads cache/paillier_cache_2048bit.pkl (committed private key) if present
                                 stores the column as PLAINTEXT ("lazy encryption"), encrypts nothing
        ──────► /api/query    → rescales plaintext values to integers 1..1000
                                 counts them, raises cached E(v) to the count, multiplies, decrypts
                                 rescales back → approximate SUM/AVG
```

Key design facts:

1. **The server holds the private key and the plaintext.** `UltimateOptimizedDatabase.sum_query(values)` takes plaintext ints, encrypts them, sums them, decrypts and returns plaintext, all in one process. There is no party the encryption protects anything from, and the right baseline for every speed claim is `sum(values)`: **0.096 ms for 10k values**.
2. A real encrypted-aggregation design is: client encrypts with the public key → server stores ciphertexts and multiplies them (it never has the private key) → client decrypts the aggregate. Nothing in the repo implements this split.
3. The library is ~36k lines of Python (core 10.1k, storage 4.9k, scripts 7.3k, examples 2.9k, evaluation 2.9k, api 2.4k), with 4 API servers, 3 ORAM implementations, 6 GPU/Paillier variants, and 3 modules nothing imports (`gpu_paillier_hybrid.py`, `gpu_paillier_old_multiprecision.py`, `parallel_executor.py`).

---

## 4. Claims vs measurements

2048-bit keys. "Agniya encrypt" is `agniya.core.paillier.encrypt`, which uses gmpy2 because it is installed.

| # | README / code claim | Measured here | Verdict |
|---|---|---|---|
| 1 | Baseline Paillier encryption **285 ms** | **19.4 ms** (agniya, gmpy2); 104.8 ms textbook with built-in `pow`; 17.7 ms python-paillier (`phe`) | Baseline inflated ~15×. Agniya ≈ `phe`, no faster. |
| 2 | Sliding-window exponentiation **15–30% faster than pow()** | Pure-Python sliding window: 101 ms vs `pow` 105 ms (1.04×). With gmpy2 installed the sliding-window code **never runs**; `optimized_powmod` just calls `gmpy2.powmod` (12.7 ms, 8.3× faster). | The gain is gmpy2's, misattributed. |
| 3 | Smart cache: **1000× / 74,426× / 10M ops/s / 6.7M ops/s** | 2.3M cached lookups/s; a bare `dict.get` does 9.4M/s. Same plaintext returns the **identical ciphertext** every time. | Real speed, but it's a dict lookup that turns Paillier into deterministic encryption (§5.1). Not an encryption speedup. |
| 4 | "Optimized" single encryption **0.24 ms (1188×)** | Only reachable through the deterministic cache | Same as #3 |
| 5 | CRT decryption **100 → 25 ms (4×)** | 17.3 → **6.0 ms (2.9×)** | **Real**, standard technique |
| 6 | Homomorphic addition **33,772 ops/s** | 18.9k/s with Python ints; ~120k/s with gmpy2 `mpz` (2,048 mults in 17 ms) | Real operation; claim is machine-dependent; 6× is free with gmpy2 |
| 7 | RNS compression **50%, lossless, zero security loss** | 512 B → 128 B, but the CRT modulus M has 993 bits and the ciphertext ~4,096. **Round-trip ≠ original; decrypts to garbage.** The repo's own benchmark "verifies" `orig % M == decompressed`. | **False.** You cannot store 4,096 bits in 993. |
| 8 | LSH dedup **60–80% storage savings, works with probabilistic encryption** | 300 rows, 10 distinct values: **0.0%** saved with proper Paillier; 96.7% only with the deterministic cache. The "MinHash" is 100 SHA-256s of the whole ciphertext, i.e. an exact-match hash. The repo's own `comparison_summary.txt` also says `0.0% storage reduction`. | **False as stated.** It only works because #3 broke the encryption. |
| 9 | Batch packing **28×**, exact | 32 values/ciphertext; exact for small values; **wrong for realistic sums**: 20k salaries in cents → expected 179,703,269,645, got 42,264,316,204 (slot overflow, no headroom) | Real, well-known technique with a correctness bug (§6.1) |
| 10 | Multi-level cache **251×** | For any query > 100 rows it silently switches to **1024-bit Paillier keys** (~80-bit security) | The speedup is a security downgrade plus the deterministic cache |
| 11 | Parallel tree aggregation **1.5–3×** | 86.5 ms vs 103 ms Python-int loop (1.2×), but a **single-thread gmpy2 loop does it in 17.1 ms**: the tree is **5× slower** than the simple fix | Pessimization. Threads can't beat the GIL; the gain is from gmpy2. |
| 12 | ThreadPool batch encryption (used in `precomputation.py`) | 8 threads: 1.06× | GIL-bound. A process pool gives **4.05×** on this laptop. |
| 13 | GPU **5–10× / 255× / 6.7M ops/s** | `cp.int64(n)` with a 2048-bit `n` raises `OverflowError`; init is caught, `gpu_available=False`, CPU used, while verbose mode still prints "GPU-accelerated encryption enabled" | **No working GPU path exists** for real key sizes (§5.6) |
| 14 | JIT (Numba) **2–5×** | `JITEncryptor.encrypt_batch` → `ValueError: high is out of bounds for uint64`; JIT decryptor fails to compile ("Int value is too large") | Broken: Numba has no bignum type |
| 15 | ORAM hides access patterns, **1.5–3× overhead** | `sum_query_oram` writes `str(ct)[:356]` of only 5–10 sample ciphertexts into an in-process ORAM, reads them back and **discards** them; the sum uses the unprotected values. New-block writes skip the tree path (observable). | Theater: no access pattern is hidden |
| 16 | **"6,034× faster than SEAL"**, 2.56M QPS, 8.9M QPS scaling, 5,000 clients, IND-CPA secure | `evaluation_suite/benchmarks/02,03,06,07,09,10,11,12_*.py` are 10-line stubs **returning hard-coded constants** (`ind_cpa_secure: True` is a literal). Measured SEAL BFV (TenSEAL 0.3.18, N=8192): **8.0 ms for 4,096 values = 1.96 µs/value** vs Agniya 19.4 ms/value | **Inverted:** SEAL bulk-encrypts ~**9,900× faster** per value |
| 17 | Server: "17K encrypted ops/s", "100% cache hit", exact results | `insurance_real.csv` (1,338 rows, `charges`): exact SUM 17,755,165 → server **17,798,421 (+0.244%)**; AVG 13,269.93 → 13,302.26. `/api/encrypt` reports `encrypt_time_seconds: 0` because it encrypts nothing. The hit rate is hard-coded to `100.0` (falls back to `0.0` because the `hasattr` check fails). `/api/benchmark` returns constants. | Wrong results; reported metrics fabricated |
| 18 | 2048-bit keys | `generate_prime` sets only the top bit, so `n` is sometimes **2047 bits** (observed); keygen 2.0–2.5 s (no small-prime sieve) | Minor bug |

---

## 5. Security findings (ordered by severity)

### 5.1 CRITICAL: Deterministic "encryption" via the plaintext→ciphertext cache
`PrecomputationTable` (`agniya/core/precomputation.py`) maps `plaintext → one fixed ciphertext` and precomputes 0..1000 at start-up. Paillier's security (IND-CPA) depends on fresh randomness `r` per encryption. With the cache, equal plaintexts produce equal ciphertexts, so anyone who sees the stored data learns which rows are equal, the full frequency histogram, and (with any known row) the value of every matching row. This is exactly the leakage exploited in Naveed, Kamara & Wright, *"Inference Attacks on Property-Preserving Encrypted Databases"* (CCS 2015). Every "1000×" claim, the dedup claim and the 17K ops/s figure depend on it. The README's own threat-model section admits this ("Deterministic Encryption … equality observable") while the headline calls the system "complete security".

**Fix:** delete the cache, or re-randomize on every use (`c·rⁿ mod n²`, which costs one `rⁿ`, so the speedup disappears). The honest speedup is a **pool of one-time `rⁿ` values precomputed offline** (measured below, §9).

### 5.2 CRITICAL: Private key committed to the public repo
`cache/paillier_cache_2048bit.pkl` (tracked since `3c32329`) contains `p, q, λ, μ` plus the 1..1000 lookup table. I inspected it with `pickletools` without executing it. `server_optimized.py` **loads this file whenever it exists**, so every deployment shares one public private key. `cache/tier2_cache_512bit_*.dat` and `cache/tier2_cache_2048bit_*.dat` (17 MB) are also tracked.

**Fix:** delete `cache/` from the repo, add it to `.gitignore`, treat that key as burned, and never persist private keys next to data (at minimum, a separate path with OS permissions; ideally the server never sees the key, see §3).

### 5.3 HIGH: The server never encrypts uploaded data
`/api/encrypt` stores the plaintext DataFrame and column lists in a global dict (`'encrypted_data': encrypted_fields  # Plaintext for lazy encryption`). Every query re-encrypts plaintext with the server's own key and decrypts it again.

### 5.4 HIGH: Silent security downgrades
- `MultiLevelCache.smart_sum` uses **1024-bit** Paillier for any query > 100 rows (`use_low_security = len(values) > 100`). NIST deprecated 1024-bit RSA-class moduli in 2013.
- `AdaptiveKeySelector` recommends **512-bit** keys for "small values" if `min_security` is lowered. Key size protects the *factoring problem*, not the plaintext range, so it must never depend on data size.

### 5.5 MEDIUM: OPE leaks order and roughly half the bits
`OrderPreservingPaillier` uses `pyope` (Boldyreva et al. scheme). That scheme is known to leak more than order (Boldyreva, Chenette, O'Neill, *"Order-Preserving Encryption Revisited"*, CRYPTO 2011) and is the main target of the CCS 2015 attacks above. Acceptable only if documented as a deliberate trade-off.

### 5.6 MEDIUM: GPU, JIT and ORAM claims describe non-working code
- **GPU** (`paillier_gpu.py`, `oram_gpu.py`, `gpu_pipeline.py`): all arithmetic uses `cp.int64`. A 2048-bit modulus doesn't fit, so construction throws, is swallowed, and execution falls back to CPU. Real GPU Paillier needs multi-precision kernels (e.g. NVIDIA's CGBN-style big-number libraries); `multiprecision_gpu.py` is a start but is not wired in.
- **JIT** (`paillier_jit.py`): Numba has no arbitrary-precision ints; it also draws randomness from `np.random` (not cryptographically secure) when it does run.
- **ORAM**: see #15 above. Also, Path ORAM only makes sense when the *client* hides its accesses from an untrusted *server*; here both sides are the same process.

### 5.7 LOW
- AES-GCM (`hybrid/aes_cipher.py`) is implemented correctly: random 96-bit nonce, tag verified. `MultiLevelCache._decrypt_aes` calls it with the wrong signature (dict instead of 3 args), so the AES→Paillier "lazy conversion" path would crash.
- No authentication, rate limiting or upload sanitising on the API beyond `secure_filename`; CORS is open. Acceptable for a demo, not "Production-Ready".

---

## 6. Correctness bugs (separate from security)

1. **Batch packing overflow** (`core/batch_packing.py`): 32-bit slots with no carry headroom. Each slot accumulates `rows/32` values; when that partial sum exceeds 2³², the carry spills into the next slot and the top slot's carry is masked off. **Fix:** `slot_bits = value_bits + ceil(log2(rows_per_slot)) + 1`, and size `batch_size` from `n.bit_length() - 1` instead of a fixed 0.75 factor capped at 32.
2. **Server quantization** (`api/server_optimized.py:488–525`): values are mapped to `int(1 + (v-min)/range·999)` and mapped back as `scaled·scale + offset·n`. That is lossy (floor) and biased by `+n·scale`, giving +0.244% on the insurance data and worse on wide-range columns. Delete it.
3. **`UltimateOptimizedDatabase`**: `sum_query_oram` imports `EncryptedNumber` from `paillier.py`, which doesn't exist (ImportError on that path). `run_ultimate_benchmark()` and the integration test pass a removed kwarg. On every instantiation it pays ~17 s precomputing 1,001 encryptions, then the server throws them away by swapping in the pickled key.
4. **`decrypt_crt`** recomputes `q⁻¹ mod p` and `p⁻¹ mod q` on every call (precompute once, a small win).
5. **Keygen** can yield a 2047-bit `n`; there's no trial division, and Python `pow` is used in Miller-Rabin even though gmpy2 is available (`gmpy2.next_prime`/`is_prime` is ~10× faster).
6. `README` examples call `db.compress/db.decompress` and claim "~75% saved", which is the broken RNS path.

---

## 7. Code and documentation health

- **README** (1,875 lines) references **13 files that don't exist** (`test_suite.py`, `examples_library_usage.py`, `benchmark_vs_competitors.py`, `verify_all_fixes.py`, `verify_end_to_end.py`, `test_novel_features.py`, `test_entropy_simple.py`, `demo_entropy_aware.py`, `run.sh`, `HOSTING_OPTIONS.md`, `IMPLEMENTATION_SUMMARY.md`, `docs/REAL_WORLD_DATASETS.md`, `docs/ENTROPY_AWARE_EXECUTION.md`). It contains a broken code block (lines 212–226) and contradictory numbers (6.7M vs 10.01M vs 2.56M ops/s; RNS 50% vs the repo's own 16.9%).
- **Stray files:** `=1.1.1` (an unquoted `pip install x>=1.1.1` redirect), `benchmark_run.log`, `security_audit.log`, `benchmark_output.log`, 17 MB of `cache/`, `data/real_datasets/intel_sensors.txt.gz`.
- **Duplication:** `server.py`, `server_advanced.py`, `server_enhanced.py`, `server_optimized.py`; `oram.py`/`oram_optimized.py`/`oram_gpu.py`; `paillier.py`/`optimized_paillier.py`/`gpu_paillier*.py`/`paillier_gpu.py`/`paillier_jit.py`/`multiprecision_gpu.py`; `precomputation.py`/`tiered_precomputation.py`/`encryption_cache.py`/`persistent_cache.py`; `query_planner.py`/`probabilistic_planner.py`. The README says `server_advanced.py` is main; `start.ps1` runs `server_optimized.py`.
- **"Query planning over encrypted statistics"** (`probabilistic_planner.py`, `query_planner.py`) samples **plaintext** values (`len(set(sample))`). The planner reads plaintext, so the "encrypted histogram" claim is not implemented.
- **Tests** check arithmetic correctness only. None checks ciphertext randomness, compression round-trip, packing overflow, or the API's numeric results; that's why all of §4–§6 slipped through.

---

## 8. Where this sits in the market (honest positioning)

| | Paillier (AGNIYA, python-paillier) | Lattice FHE (SEAL / OpenFHE BFV/CKKS) | Deterministic/OPE DBs (CryptDB-style) |
|---|---|---|---|
| Ops on ciphertexts | add, scalar-multiply | add, multiply (bounded depth), SIMD slots | equality / order on server |
| Per-value bulk encrypt (measured) | 19.4 ms (1 value/ct); ~0.6 ms amortized with 32-slot packing | **~2 µs** (4,096 values/ct) | µs |
| Ciphertext per value | 512 B (2048-bit key) | ~105 B at N=8192 (432 KB / 4,096) | 16–32 B |
| Exactness | exact integers | BFV exact (mod t), CKKS approximate | exact |
| Security | IND-CPA (if randomized!), not post-quantum | IND-CPA, post-quantum (RLWE) | leaks equality/order |
| Maturity | simple, many libs | industrial, heavily optimized C++ | broken by inference attacks |

**Where Paillier still wins:** a small ciphertext per *single* value, exact integer SUM/COUNT/AVG without parameter tuning, simple keys, cheap homomorphic add (~120k/s per core with gmpy2), and well-understood security. Real deployments in this niche include e-voting tallies, secure aggregation of counters/model updates, and privacy-preserving advertising/attribution measurements.

**Where AGNIYA could be relevant:** a *clean, honest, fast* client-encrypts / server-aggregates library for SUM/COUNT/AVG/GROUP-BY over integer columns, with packing, offline randomness, a CSV-to-dashboard demo, and reproducible benchmarks against `phe` and SEAL. That's a credible student/startup project. The current "6,034× faster than SEAL, production-ready, patent-worthy" framing will not survive a reviewer who runs the code.

**Novelty notes for the patent/paper plans:** packing several plaintexts into one Paillier ciphertext is long-established (e.g. Ge & Zdonik, VLDB 2007); CRT decryption is in Paillier's original 1999 paper; multi-layer "onion" encryption is CryptDB (Popa et al., SOSP 2011); Path ORAM is Stefanov et al. (CCS 2013); short-exponent / fixed-base Paillier variants are in Damgård-Jurik-Nielsen (2010). "Prior art: none identified" in the README is not accurate for these.

---

## 9. Optimization roadmap (what to do in the next days)

Fix correctness and security first, because every later speedup has to be measured on an honest baseline.

### Phase 0: make it honest (½–1 day)
1. Remove `cache/` from git, `.gitignore` it, burn the key. Delete `=1.1.1` and the committed logs.
2. Delete the plaintext→ciphertext cache, RNS compression, LSH dedup, 1024-bit "multi-level" path, the ORAM wrapper in `sum_query_oram`, and the GPU/JIT stubs (keep them on a branch if wanted).
3. Delete server quantization; `/api/encrypt` must actually encrypt; remove hard-coded metrics and `/api/benchmark` constants.
4. Replace the 8 stub evaluation benchmarks with real ones, or delete them. Generate README numbers from `tools/verify_claims_results.json`.
5. Fix packing headroom, keygen bit length and the test suite. Add tests for: ciphertext randomness (same plaintext → different ciphertexts), packing with large sums, and API SUM exactness.
6. Pick one server and one ORAM (or none) and delete the rest.

### Phase 1: real speedups, measured on this laptop (2048-bit)

| Technique | Measured | Gain | Notes |
|---|---|---|---|
| gmpy2 `mpz` everywhere (aggregation loop) | 103 ms → **17.1 ms** for 2,048 ct-adds | **6×** | Trivial; replaces the "parallel tree" |
| CRT encryption on the data owner's side (rⁿ mod p², q²) | 19.4 → **10.5 ms** | **1.85×** | Owner holds p, q; never on the server |
| `g = n+1` → `gᵐ = 1 + m·n` | avoids one modexp; only matters for large m | up to ~2× for large m | Free |
| Process pool (not threads) for batch encrypt | 2.68 s → **0.66 s** for 160 values | **4×** (4 cores) | Threads give 1.06× (GIL) |
| Offline rⁿ pool, one-time use (IND-CPA-safe replacement for the cache) | online **34.5 µs/encryption = ~29k/s**; offline 17 ms per rⁿ | **~560× online** | The honest version of the "1000× cache" |
| Packing with correct headroom (~32 values/ct) | 1 encryption per 32 values; 1 ct-mult per 32 values | **~32×** on encrypt and aggregate | Already implemented; fix the overflow |
| Precompute CRT inverses in `decrypt_crt` | small | ~5–10% | Free |

**Projected end-to-end target** (from the measured components, to be verified): offline rⁿ via CRT on 4 processes ≈ 2.6 ms each ≈ 380/s; with 32-slot packing ≈ **12k values/s fully encrypted** offline throughput per laptop. Server-side SUM ≈ 120k ct-mults/s × 32 slots ≈ **~3.8M values/s aggregated on ciphertexts**, honestly IND-CPA. That beats the current "17K ops/s" with real encryption, and it's a number a reviewer can reproduce.

### Phase 2: bigger levers (evaluate, then decide)
- **Fixed-base / short-exponent rⁿ (Damgård-Jurik-Nielsen style):** precompute powers of a fixed `h = r₀ⁿ` and use a ~448-bit random exponent. Typically several × faster per rⁿ. Needs a careful security write-up.
- **Native big-int backends:** Intel's Paillier library (IPCL, AVX-512 IFMA; this i5-1145G7 supports IFMA) or a small C/Rust extension for modexp batches. Benchmark against gmpy2 before committing.
- **Real GPU Paillier:** multi-precision kernels (CGBN-style). This is a multi-week project. Only worth it after Phase 1 shows gmpy2 + processes is the bottleneck.
- **Hybrid with lattice FHE:** for bulk analytics, compare against TenSEAL BFV packing (already installed in `envb`). Paillier may be the wrong tool for million-row SUMs; picking per workload is itself a defensible "adaptive" contribution.

---

## 10. What is genuinely good and worth keeping

- `paillier.py` core: correct, readable, CRT decryption, secure randomness (`secrets`).
- `hybrid/aes_cipher.py`: correct AES-256-GCM.
- `batch_packing.py`: the right idea, needs the headroom fix.
- The end-to-end product idea (CSV → choose per-column encryption → query dashboard) is a good demo vehicle.
- Real datasets under `data/` and the evaluation-suite *structure* (config, runner, plots) can host honest benchmarks.

---

## Appendix A: Reproduce every number

```powershell
.\envb\Scripts\python.exe -X utf8 tools\verify_claims.py
```

Checks, in order: keygen, encrypt latency (agniya / textbook / g-shortcut / CRT / `phe`), decrypt latency, homomorphic add, sliding window vs `pow` vs gmpy2, cache determinism + lookup rate, RNS round-trip, LSH dedup on proper vs cached ciphertexts, packing overflow, multi-level key size, JIT, GPU int64 representability, tree vs sequential sum, thread vs process batch encryption, offline rⁿ pool, plaintext baseline, and the full Flask `/api/upload → /api/encrypt → /api/query` round-trip on `data/insurance_real.csv`.

The TenSEAL/SEAL reference number is stored under `tenseal_bfv_reference` in the JSON. It was measured with BFV, `poly_modulus_degree=8192`, `plain_modulus=1032193`, 4,096 values per ciphertext.

## Appendix B: Branch map

| Branch | What it is |
|---|---|
| `main` | Current; superset of everything below |
| `cleaned-main` | `main` as of 2025-12-01 (pre-rewrite), plus committed `envb/` |
| `aditya` | 2025-11-21 snapshot (probabilistic filters, erasure coding, LSM, wavelet tree), all in `main` |
| `feature/setup` | Earliest restructure (hybrid AES+Paillier), all in `main` |
| `main-backup` | Two commits from the initial import |
