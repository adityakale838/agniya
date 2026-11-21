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

2048-bit keys. The table below is **generated** by `python -X utf8 tools/bench.py` (do not edit by hand);
every timed operation is checked for an exact result, and p10/p90 plus all dataset sizes are in
`tools/bench_results.json`. Numbers depend on hardware: always quote them with the machine line under the table.

<!-- BENCH:START -->
<!-- BENCH:END -->

Lattice FHE (SEAL) still encrypts bulk data faster per value; Paillier's strengths are exact integer sums,
small per-value ciphertexts and simplicity. The plan for closing the gap is in
[docs/PROJECT_REVIEW.md §9](docs/PROJECT_REVIEW.md).

## How it works

- **Paillier** with `g = n+1`, fresh randomness `r` for every ciphertext, CRT decryption (`agniya/core/paillier.py`).
- **Randomness pool**: the expensive `rⁿ mod n²` is plaintext-independent, so it is precomputed offline across all cores; each value is used once (`agniya/core/precomputation.py`).
- **Fast rⁿ (DJN)**: by default rⁿ is computed as `hsᵅ` for a fixed public base `hs = hⁿ` and a random |n|/2-bit `α`, using a precomputed comb table (`agniya/core/djn.py`). This is the Damgård–Jurik–Nielsen optimization; its security relies on an extra short-exponent assumption on top of DCR. Set `AGNIYA_RN_METHOD=standard` for textbook randomness (DCR only).
- **Packing**: many integers per plaintext in fixed slots, sized with enough headroom that slot sums cannot overflow; negatives via a public offset (`agniya/core/batch_packing.py`).
- **OPE + Paillier** for range filters: each row gets an order-preserving tag plus its own Paillier ciphertext (`api/server_optimized.py`, `agniya/hybrid/ope_paillier.py`).
- **AES-256-GCM** for non-numeric columns (`agniya/hybrid/aes_cipher.py`).

## Security model and limitations (read this)

- The API server generates and holds the private key (in memory only). In this demo it is the **data owner**, not an untrusted cloud server. A deployment against an untrusted server must keep the private key on the client and send the server only the public key and ciphertexts; `sum_encrypted` and `BatchedAggregator.sum_column`'s first step need only the public key.
- Paillier is IND-CPA secure under DCR with `AGNIYA_RN_METHOD=standard`; the default DJN randomness additionally assumes short exponents are indistinguishable (Damgård, Jurik, Nielsen 2010). Neither is **post-quantum**.
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
