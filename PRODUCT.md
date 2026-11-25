# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Presenters (primary for the dashboard):** the AGNIYA team (CSE DS B, Vishwakarma Institute of Technology, Pune) running a live demo on a laptop and projector for judges and visiting bank staff (Barclays fintech). The screen must read from across a room and prove, at a glance, that data stayed encrypted and every answer was checked.
- **Evaluators (primary for the home page):** judges and bank technologists, a mixed technical and business audience, deciding whether the project is real, sound and worth a pilot.
- **Bank analysts and engineers (later):** would run reports with the Python client or the dashboard on their own data.

## Product Purpose

AGNIYA runs exact analytics (SUM, COUNT, AVG, VARIANCE, STDDEV, MIN, MAX, MEDIAN and quantiles, range filters, GROUP BY one or two columns) on customer data that stays encrypted everywhere outside the bank. The machine that stores and computes never holds a key; the bank (or the browser tab) decrypts only the totals and checks every answer against integrity tags. Success: an evaluator believes the data never left in readable form, sees results match a plaintext calculation exactly, and asks for a pilot.

## Positioning

Paillier with packed ciphertexts, so a query over a column is one multiplication pass and one decryption, with integrity tags inside every plaintext so a wrong, partial or replayed answer from the server is rejected. Against a general FHE library (Microsoft SEAL, measured on the same laptop): SEAL encrypts about 6x faster per value, AGNIYA answers a GROUP BY about 120x faster (4.0 ms vs 478 ms) and stores data about 5x smaller (7-11 vs at least 53 bytes per value), with filters, grouping, statistics and checks built in. Not post-quantum.

## Operating Context

- Live demo: `start.ps1` starts the Flask API (port 5000) and the Next.js dashboard (port 3000); the presenter uploads `data/bank_customers.csv` (2,000 synthetic customers), sets `credit_score` to OPE+Paillier, encrypts in the browser (about 3.5 s), and clicks six one-click banking use cases (0.2-0.4 s each after the first run).
- Two modes: "Encrypt in this browser" (key stays in the tab; the server only sees ciphertexts) is the story; "Server-side demo" (server holds the key) exists for comparison and must never be the default.
- Proof moves: browser DevTools Network tab shows only hex ciphertexts; the server's SQLite store holds no private key; an Excel pivot of the same CSV matches to the last digit.
- Companion materials: pitch deck (`docs/AGNIYA-banking-pitch.pptx`), one-page brief, Q&A sheet, `docs/BANKING.md`, `docs/PITCH-DAY.md`.

## Capabilities and Constraints

- Operations: SUM, COUNT, AVG, VARIANCE, STDDEV, MIN, MAX, MEDIAN; range filter on an OPE+Paillier column (the column itself or another one); GROUP BY one or two columns, 2-64 groups.
- Encryption types per column: Paillier-2048, OPE+Paillier, AES-256 (text), Plaintext (ids).
- Key file: password-protected (AES-256-GCM, scrypt), opens in both Python and the browser; "Restore from key file" re-attaches a browser session to its stored dataset.
- First use of some queries builds an encrypted copy (sorted, grouped, squared); shown as one-time setup, never cached answers.
- Stack: Next.js 16, React 19, TypeScript, Tailwind v4, Radix primitives, framer-motion, lucide-react; Flask + SQLite API; crypto in TypeScript BigInt Web Workers.
- Must keep working offline on localhost (fonts self-hosted through next/font).

## Brand Commitments

- Name: AGNIYA. Team line: "CSE DS B · Vishwakarma Institute of Technology, Pune". Licence: Apache 2.0. Repository: github.com/adityakale838/agniya.
- The web app gets its own visual identity (the user chose a free hand rather than copying the pitch deck).
- Voice: plain, exact, measured. Every number shown must come from `tools/bench_results.json`, the dashboard itself, or `docs/BANKING.md`.

## Evidence on Hand

- Measured (Intel i5-1145G7 laptop, 16 GB, 2048-bit keys, `tools/bench.py`, every result checked exact): encrypt 1,000,000 values in 6.39 s (6.4 µs per value); SUM over 1,000,000 values in 130 ms; 10,000,000 values: encrypt 57.3 s, SUM 1.32 s; storage 7-11 bytes per value; GROUP BY region over 1,338 rows 3.5-4.0 ms; MEDIAN with a range over 706 rows about 6 ms; 10.3x faster than the project's own first honest baseline.
- SEAL comparison as above; SEAL computes identical SUM and GROUP BY totals (`tests/test_integration/test_seal_crosscheck.py`).
- Banking demo: 2,000 synthetic customers encrypted in 3.5 s in the browser; six use cases at 0.2-0.4 s, all matching pandas.
- 319 automated tests, CI on every change.
- Absent: customers, pilots, partnerships, security audit, pricing. Never imply any of them. The old home page claims ("143x faster", "0.52 ms encryption", "No credit card required", "unprecedented performance") are unverified and must not return.

## Product Principles

1. Prove, don't claim: every screen shows the mechanism working (ciphertexts, a key that never leaves, a check that passed) rather than adjectives.
2. Exact or nothing: show real measured numbers with their conditions; no rounding up, no invented precision.
3. Honest about limits: what the server sees, not post-quantum, no independent review yet.
4. The key holder is the hero: the bank (or the browser tab) holds the key; the server is shown as blind.

## Accessibility & Inclusion

Projector use: results and key states must stay legible at a distance and in a bright room (strong contrast, large result figures). Keyboard operable; respects reduced motion.
