# AGNIYA for banks: from tool to deployment

AGNIYA lets a bank run exact analytics (SUM, COUNT, AVG, VARIANCE, STDDEV, MIN, MAX, MEDIAN and
quantiles, with range filters and GROUP BY one or two columns) on customer data that stays encrypted
everywhere except inside the bank. The machine that stores and computes never has a key, and every
answer it returns is checked before anyone sees it.

Every number below was measured on one laptop (Intel i5-1145G7, 4 cores, 16 GB; 2048-bit keys) with
`tools/bench.py` or in the dashboard, and every result was checked against pandas. Treat them as
development numbers, not a sizing guarantee.

## 1. The problem it addresses

Banks increasingly want analytics to run somewhere other than the system that holds the data: a cloud
analytics platform, an outsourced or offshore team, a fintech partner, another department. Each of
those copies of customer data is a breach and compliance risk, so today the usual answers are
"don't do it", or masking and aggregation by hand before the data leaves.

AGNIYA's answer: the data leaves only as ciphertexts. The remote side computes the aggregates on the
ciphertexts without being able to read them, and the bank decrypts only the results.

## 2. How it works

```
Bank (holds the keys)                       Analytics server (no keys)
---------------------                       --------------------------
1. pick columns and how to protect them
   (Paillier for sums/stats; OPE+Paillier
   for range filters; AES for text)
2. encrypt locally, upload  ------------->  stores packed ciphertexts, OPE tags
3. ask: SUM(loan_amount) GROUP BY risk_band
   ------------------------------------->  multiplies ciphertexts (homomorphic addition)
                          <-------------  returns encrypted totals
4. decrypt, check integrity tags, show
```

- **Keys stay with the bank:** in the Python client (`agniya.client.AgniyaClient`) or in the browser
  (the dashboard's default mode), saved as a password-protected key file.
- **The server can't read the data,** and can't change answers unnoticed: each answer is checked
  against integrity tags the server never sees, so a wrong, partial or replayed answer is rejected.
- **Only the key holder can upload, query or delete a dataset** (dataset tokens).
- **Results are exact:** no approximation, unlike CKKS-style schemes.

## 3. Use cases, as shown in the demo

The dashboard ships with six one-click use cases on a synthetic bank dataset (`data/bank_customers.csv`,
2,000 generated customers, `tools/make_bank_data.py`; no real data):

| Question | Query | Time in the browser (first run / after) |
|---|---|---|
| Loan exposure by risk band | `SUM(loan_amount) GROUP BY risk_band` | 0.5 s / 0.2 s |
| Default rate by segment | `AVG(default_flag) GROUP BY segment` | 0.3 s / 0.2 s |
| Median balance by region | `MEDIAN(balance) GROUP BY region` | 0.4 s / 0.2 s |
| Spend volatility by segment | `STDDEV(monthly_spend) GROUP BY segment` | 1.5 s / 0.3 s |
| Sub-prime exposure by product | `SUM(loan_amount) WHERE credit_score BETWEEN 300 AND 600 GROUP BY product` | 1.5 s / 0.3 s |
| Exposure by region and segment | `SUM(loan_amount) GROUP BY region, segment` | 0.9 s / 0.4 s |

Encrypting the 2,000 customers (7 encrypted columns) takes 3.5 s in the browser. The first run of a
query builds the encrypted copy it needs (grouped or range-ordered); later runs reuse it.

Where this fits in a bank:

- **Risk and finance reporting on a cloud or shared platform:** exposure, default rates and balance
  statistics computed where the bank does not want plaintext.
- **Working with partners and vendors:** a fintech or analytics vendor runs the computation and never
  receives readable customer data.
- **Least privilege inside the bank:** analysts and dashboards get aggregates; row-level data stays
  encrypted.
- **Testing and development:** realistic pipelines on encrypted data instead of copies of production.

## 4. Performance (measured)

| | |
|---|---|
| Encrypt 1,000,000 values (all cores) | 6.39 s = 6.4 µs per value |
| SUM over 1,000,000 encrypted values | 130 ms = 7.7M values per second, exact |
| Encrypt 10,000,000 values (all cores) | 57.3 s = 5.7 µs per value |
| SUM over 10,000,000 encrypted values | 1.32 s = 7.6M values per second, exact |
| Storage | 7–11 bytes per value (values packed into ciphertexts) |
| GROUP BY region, 1,338 rows (4 groups, one decryption) | 3.5 ms (server-side) / 3.9 ms (keys on the client) |
| MEDIAN with a range, 706 rows | 6.1 ms / 5.9 ms |
| Reference: Microsoft SEAL (lattice FHE), same laptop | encrypts at 1.1 µs per value, about 6x faster than AGNIYA |
| SUM GROUP BY region, 1,338 rows: AGNIYA vs SEAL | 4.0 ms vs 478 ms: AGNIYA about 120x faster to query |
| Storage: AGNIYA vs SEAL | 7–11 vs at least 53 bytes per value (one 432 KB SEAL ciphertext holds up to 8,192 values) |
| Independent check: SEAL computes the same SUM and GROUP BY | identical totals (`tests/test_integration/test_seal_crosscheck.py`, and checked in every benchmark run) |

AGNIYA is not the fastest homomorphic scheme at encrypting; it is exact, simple to operate, small per
value, and has the query features above (filters, GROUP BY, statistics, integrity checks) built in.

## 5. Security model, plainly

- Paillier with 2048-bit keys: about 112-bit security, IND-CPA under the decisional composite
  residuosity assumption. Not post-quantum.
- What the server learns: row counts, ciphertext sizes, and, for columns the bank marks
  OPE+Paillier (range filters), the order of those values. GROUP BY copies hide labels and group sizes;
  quantile queries per group show roughly where groups start. The README lists every case.
- What the server cannot do: read values, or return a wrong result without the bank's client
  rejecting it.

## 6. Path to production at a bank

**Ready today:** the cryptography and query engine, client-held keys (Python and browser), integrity
checks, dataset tokens, a test suite of 300+ tests running in CI, reproducible benchmarks.

**Needed for a bank deployment** (none of this exists yet):

| Gap | What it means | Rough effort |
|---|---|---|
| Key management | Keys in the bank's HSM or cloud KMS instead of password-protected key files | 2–4 weeks |
| Identity and access | SSO, per-user roles, per-dataset permissions on the server | 2–3 weeks |
| Audit trail | Who ran which query when, kept tamper-evident | 1–2 weeks |
| Incremental data | Append new rows without re-uploading a column | 2–3 weeks |
| Scale-out | Store and compute across several servers; tested on tens of millions of rows | 4–6 weeks |
| Independent security review | Threat model, code review, penetration test | external |

Efforts are estimates for a small team and depend on the bank's existing platforms.

**A pilot that would prove it (about 6 weeks):**

1. **Weeks 1–2:** pick three to five existing reports (e.g. exposure by risk band); run them in a
   sandbox on synthetic or masked data; compare results to the existing reports exactly.
2. **Weeks 3–4:** connect one real pipeline (batch upload from the warehouse with the Python client);
   keys in a test KMS; measure time and cost against the current process.
3. **Weeks 5–6:** security review of the deployment; decision on a production rollout.

Success criteria: results identical to today's reports, no plaintext customer data outside the
bank's boundary, query times acceptable for the report's users.

## 7. Roadmap beyond a pilot

- Encryption speed in the browser: faster randomness (as in the Python client) and parallel OPE tagging.
- Queries across several banks or entities (each keeps its data private): needs threshold
  decryption, a research-grade extension.
- Two range filters at once, COUNT DISTINCT, larger GROUP BYs (over 64 groups).
- 3072-bit keys (128-bit security) as an option: measured at about 2x lower throughput.
