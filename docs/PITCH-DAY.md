# Pitch day: running AGNIYA live

Everything here was run on the development laptop (Intel i5-1145G7, Windows 11). The deck is
`docs/AGNIYA-banking-pitch.pptx`; keep a copy offline in case the venue has no internet.

## The day before

1. Charge the laptop and present on AC power (timings drop on battery).
2. Get the latest code: `git pull` on the `integrity` branch (until it is merged into `main`).
3. Run `.\start.ps1` and do the whole walkthrough below once, start to finish.
4. Check the GitHub page you will show: until PR #7 is merged, `main` still has the old README. Link to the
   `integrity` branch instead, or ask Aditya to merge first.

## 30 minutes before

1. `.\start.ps1` (or double-click `start.bat`). It starts the API (port 5000) and the dashboard (port 3000),
   waits until both answer, and opens `http://localhost:3000/dashboard`. Leave both server windows open.
2. Dashboard, **Upload**: choose `data/bank_customers.csv` (2,000 synthetic customers, no real data).
3. **Configure**: set `credit_score` to **OPE+Paillier** (needed for the sub-prime use case). Keep the
   default "Encrypt in this browser" mode. Click **Encrypt**: about 3.5 s.
4. **Query**: click each of the six banking use cases once. The first run of each builds its encrypted copy
   (0.3–1.5 s); after that each answers in 0.2–0.4 s.
5. Optional: save a key file (button after encrypting) with a password you will remember.

## While presenting

- Click two or three use cases. Point at the result card's last line: the server multiplied ciphertexts
  "without any key", and the browser "checked the integrity tags".
- Good ones to show: *Loan exposure by risk band* (GROUP BY, one decryption), *Median balance by region*
  (MEDIAN per group), *Sub-prime exposure by product* (a range filter plus GROUP BY).
- Don't close or reload the browser tab: the key lives in it. If it happens, upload and encrypt again (3.5 s).
- Don't switch to "Server-side demo" mode: there the server holds the key, which is not the story you are
  telling.

## If something goes wrong

| Problem | Fix |
|---|---|
| `start.ps1` says the API did not answer | Read its window; a port already in use means an old server is running: close it and run again |
| Dashboard shows an error after a reload | The key was lost with the tab: upload and encrypt again |
| A use case button is greyed out | `credit_score` wasn't set to OPE+Paillier before encrypting: set it, encrypt again |
| No time or no network | Show slide 8 of the deck: the same six questions with their measured times |

## Numbers you can quote (all measured, see `tools/bench_results.json`)

- Encrypt 1 million values: 6.4 µs per value; SUM over them in 130 ms. Tested up to 10 million values
  (encrypt 57 s, SUM 1.3 s). Storage 7–11 bytes per value.
- 2,000 bank customers encrypt in 3.5 s in the browser; each use case answers in 0.2–0.4 s.
- Microsoft SEAL (BFV) computes the same SUM and GROUP BY totals: identical results
  (`tests/test_integration/test_seal_crosscheck.py`). SEAL encrypts about 6x faster per value.

For questions you are likely to get, use the Q&A prep sheet.
