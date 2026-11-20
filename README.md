# AGNIYA

Encrypted aggregation for tabular data: SUM / AVG / COUNT (and OPE range filters) computed on
**Paillier-2048** ciphertexts, with a Flask API and a Next.js dashboard.

```python
import agniya as ag

db = ag.Database()                    # 2048-bit Paillier key pair
cts = db.encrypt([100, 200, 300])     # randomized: same value -> different ciphertexts
db.sum(cts, encrypted=True)           # 600, computed by multiplying ciphertexts

col = db.encrypt_column(list(range(1, 20_001)))   # packed: ~60-200 values per ciphertext
db.sum_column(col)                    # 200010000, one ciphertext product + one decryption
```

## Measured performance

Intel i5-1145G7 (4 cores), Windows 11, Python 3.12, gmpy2 2.3.2, 2048-bit keys.
Every number comes from `python -X utf8 tools/bench.py` (raw output: `tools/bench_results.json`).

| Operation | Result |
|---|---|
| Key generation | 0.15 s |
| Encrypt one value | 15 ms |
| Decrypt (CRT) | 3.9 ms |
| Encrypt using a precomputed rⁿ (online part) | 32 µs; rⁿ costs 6.1 ms offline on all cores |
| Homomorphic additions (gmpy2) | 88k ciphertexts/s |
| Packed column, 20,000 values: encrypt | 2.35 s (8.5k values/s, 62 values/ciphertext) |
| Packed column, 20,000 values: SUM | 10 ms (exact) |
| API, `insurance_real.csv` (1,338 rows): encrypt `charges` / SUM query | 0.50 s / 4.2 ms, error 0.003 (4-decimal fixed point) |
| Reference: Microsoft SEAL BFV via TenSEAL, 4,096 values | 7.4 ms (1.8 µs/value) |

Lattice FHE (SEAL) encrypts bulk data much faster; Paillier's strengths are exact integer sums,
small per-value ciphertexts and simplicity. The plan for closing the gap is in
[docs/PROJECT_REVIEW.md §9](docs/PROJECT_REVIEW.md).

## How it works

- **Paillier** with `g = n+1`, fresh randomness `r` for every ciphertext, CRT decryption (`agniya/core/paillier.py`).
- **Randomness pool**: the expensive `rⁿ mod n²` is plaintext-independent, so it is precomputed offline across all cores; each value is used once (`agniya/core/precomputation.py`).
- **Packing**: many integers per plaintext in fixed slots, sized with enough headroom that slot sums cannot overflow; negatives via a public offset (`agniya/core/batch_packing.py`).
- **OPE + Paillier** for range filters: each row gets an order-preserving tag plus its own Paillier ciphertext (`api/server_optimized.py`, `agniya/hybrid/ope_paillier.py`).
- **AES-256-GCM** for non-numeric columns (`agniya/hybrid/aes_cipher.py`).

## Security model and limitations (read this)

- The API server generates and holds the private key (in memory only). In this demo it is the **data owner**, not an untrusted cloud server. A deployment against an untrusted server must keep the private key on the client and send the server only the public key and ciphertexts; `sum_encrypted` and `BatchedAggregator.sum_column`'s first step need only the public key.
- Paillier is IND-CPA secure (DCR assumption) but **not post-quantum**.
- Packed ciphertexts reveal the number of rows. The fixed-point scale and the column offset are public.
- **OPE tags leak the order of values** and more (Boldyreva et al. 2011; Naveed et al., CCS 2015). Use `OPE+Paillier` only for columns where that is acceptable.
- No authentication or rate limiting on the API; it binds to `127.0.0.1` by default.

## Setup

Requires Python 3.12 (wheels for gmpy2/numba) and Node.js 18+.

```powershell
py -3.12 -m venv envb
.\envb\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
cd webapp; npm install; cd ..
```

Run:

```powershell
.\start.ps1                                  # API on 127.0.0.1:5000 + dashboard on localhost:3000
python -m pytest tests                       # unit tests
python -X utf8 tools\bench.py                # benchmarks (writes tools/bench_results.json)
```

API server options (environment variables): `AGNIYA_HOST` (default `127.0.0.1`),
`AGNIYA_DEBUG=1` (Werkzeug debugger; never on a network), `AGNIYA_CORS_ORIGINS`
(default `http://localhost:3000`).

## API

| Endpoint | Body | Returns |
|---|---|---|
| `GET /api/health` | | features |
| `POST /api/upload` | multipart `file` (CSV) | schema suggestion, record count |
| `POST /api/encrypt` | `{filename, schema: [{name, encryption: "Paillier-2048" \| "OPE+Paillier" \| "AES-256" \| "Plaintext"}], sample_size?}` | records, seconds, ciphertext counts per field |
| `POST /api/query` | `{filename, type: "SUM" \| "AVG" \| "COUNT", column, rangeMin?, rangeMax?}` | result, time_ms, ciphertexts aggregated |
| `GET /api/databases` | | encrypted datasets in memory |

## Layout

```
agniya/core/       paillier.py, precomputation.py (rⁿ pool), batch_packing.py, ultimate_system.py (Database)
agniya/hybrid/     AES-GCM, key wrapping, schema, OPE+Paillier, hybrid row storage
agniya/storage/    generic data structures (Bloom/Cuckoo filters, LSM tree, wavelet tree, erasure coding)
api/               server_optimized.py (Flask)
webapp/            Next.js dashboard
tools/             bench.py (current numbers), verify_claims.py (audit of the pre-cleanup main branch)
docs/              PROJECT_REVIEW.md
data/              sample and real datasets
```

## History

Before the `phase0-honest-baseline` cleanup, this README advertised figures such as
"6.7M ops/sec", "1000×/74,426× caching" and "6,034× faster than SEAL". They came from a
deterministic plaintext→ciphertext cache (which broke Paillier's security), hard-coded benchmark
stubs, and GPU/JIT paths that could not run with 2048-bit integers. The audit and the measurements
are in [docs/PROJECT_REVIEW.md](docs/PROJECT_REVIEW.md).

## License

MIT
