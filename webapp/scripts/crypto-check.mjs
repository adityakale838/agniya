// Runs lib/agniya-browser.ts under Node for tests/test_integration/test_browser_crypto.py.
// Usage: node scripts/crypto-check.mjs <job.json>; prints one JSON result. Needs Node >= 22.18 (type stripping).
import { readFileSync } from 'node:fs';
import * as A from '../lib/agniya-browser.ts';

const job = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const big = s => BigInt(s);
const out = {};

if (job.paillier) {  // fresh key: encrypt; given key: decrypt and encrypt
  const t = performance.now();
  const keys = job.paillier.p ? A.keypairFromPrimes(big(job.paillier.p), big(job.paillier.q)) : A.generateKeypair(2048);
  out.keygen_ms = performance.now() - t;
  const t2 = performance.now();
  out.ciphertexts = job.paillier.encrypt.map(m => A.encrypt(keys.pub, keys.priv, big(m)).toString());
  out.encrypt_ms_each = (performance.now() - t2) / Math.max(1, job.paillier.encrypt.length);
  out.decrypted = (job.paillier.decrypt || []).map(c => A.decrypt(keys.priv, big(c)).toString());
  out.p = keys.priv.p.toString();
  out.q = keys.priv.q.toString();
}
if (job.layout) {
  const keys = A.keypairFromPrimes(big(job.layout.p), big(job.layout.q));
  out.layout = job.layout.cases.map(([max, count]) => A.layout(keys.pub, big(max), count));
}
if (job.ope) {
  const t = performance.now();
  const ope = new A.OPE(Uint8Array.from(Buffer.from(job.ope.key_hex, 'hex')), big(job.ope.top));
  const tags = await ope.encryptMany(job.ope.values.map(big));
  out.ope_ms = performance.now() - t;
  out.tags = job.ope.values.map(v => tags.get(big(v)).toString());
}
if (job.client) {  // end to end against a running server
  const c = new A.BrowserClient(A.httpPost(job.client.url), job.client.dataset);
  for (const col of job.client.columns) await c.upload(col.name, col.values, col.decimals, col.range);
  out.answers = [];
  for (const [col, lo, hi] of job.client.queries) out.answers.push(await c.query(col, lo ?? undefined, hi ?? undefined));
  out.p = c.priv.p.toString();
}
console.log(JSON.stringify(out));
