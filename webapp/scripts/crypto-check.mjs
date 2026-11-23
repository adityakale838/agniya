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
  out.groupLayout = (job.layout.group_cases ?? []).map(([max, sizes, dpp]) => A.groupLayout(keys.pub, big(max), sizes, dpp));
}
if (job.ope) {
  const t = performance.now();
  const ope = new A.OPE(Uint8Array.from(Buffer.from(job.ope.key_hex, 'hex')), big(job.ope.top));
  const tags = await ope.encryptMany(job.ope.values.map(big));
  out.ope_ms = performance.now() - t;
  out.tags = job.ope.values.map(v => tags.get(big(v)).toString());
}
if (job.fixed) out.fixed = job.fixed.values.map(v => A.fixedPoint(v, job.fixed.scale).toString());
if (job.client) {  // end to end against a running server
  const c = new A.BrowserClient(A.httpPost(job.client.url), job.client.dataset);
  for (const col of job.client.columns) await c.upload(col.name, col.values, col.decimals, col.range);
  for (const x of job.client.by ?? []) await c.uploadBy(x.column, x.values, x.by, x.by_values, x.decimals, x.by_decimals);
  for (const x of job.client.grouped ?? []) {
    await c.uploadGrouped(x.column, x.values, x.by, x.by_values, x.decimals, x.where, x.where_values, x.where_decimals);
  }
  out.answers = [];
  for (const [col, lo, hi, by] of job.client.queries) out.answers.push(await c.query(col, lo ?? undefined, hi ?? undefined, by));
  out.groups = [];
  for (const [col, by, lo, hi, where] of job.client.group_queries ?? []) {
    out.groups.push(await c.queryGroups(col, by, lo ?? undefined, hi ?? undefined, where));
  }
  out.quantiles = [];
  for (const [col, qs, lo, hi] of job.client.quantiles ?? []) out.quantiles.push(await c.quantiles(col, qs, lo ?? undefined, hi ?? undefined));
  for (const [mode, kind, ...args] of job.client.tamper ?? []) {  // a server that changes its answers
    const post = c.post;
    c.post = async (path, body) => {
      const r = await post(path, body);
      if (mode === 'drop-cell' && path === '/api/v2/quantiles') r.cells.pop();
      if (path !== '/api/v2/aggregate') return r;
      if (mode === 'double' && r.product) r.product = (BigInt('0x' + r.product) ** 2n % c.pub.nSquared).toString(16);
      if (mode === 'no-witnesses') r.witnesses = [];
      if (mode === 'malformed') r.product = 'zz';
      return r;
    };
    const run = { groups: c.queryGroups, quantiles: c.quantiles, query: c.query }[kind].bind(c);
    (out.tampered ??= []).push(await run(...args.map(x => x ?? undefined)).then(() => 'accepted', e => e.message));
    c.post = post;
  }
  out.p = c.priv.p.toString();
  if (job.client.save_password) out.keyfile = await c.saveKeyFile(job.client.save_password);
}
if (job.scrypt) {
  const s = job.scrypt, t = performance.now();
  const dk = await A.scrypt(s.password, Uint8Array.from(Buffer.from(s.salt_hex, 'hex')), s.n, s.r, s.p, s.dklen);
  out.scrypt_ms = performance.now() - t;
  out.scrypt = Buffer.from(dk).toString('hex');
}
if (job.load) {  // restore from a key file (either side's), then query
  try {
    const c = await A.BrowserClient.loadKeyFile(job.load.keyfile, job.load.password, A.httpPost(job.load.url));
    out.dataset = c.dataset;
    out.columns = [...c.columns].map(([name, m]) => ({ name, count: m.count, range: !!m.ope }));
    out.answers = [];
    for (const [col, lo, hi] of job.load.queries) out.answers.push(await c.query(col, lo ?? undefined, hi ?? undefined));
    out.groups = [];
    for (const [col, by, lo, hi, where] of job.load.group_queries ?? []) {
      out.groups.push(await c.queryGroups(col, by, lo ?? undefined, hi ?? undefined, where));
    }
  } catch (e) {
    out.error = e.message;
  }
}
console.log(JSON.stringify(out));
