/*
 * AGNIYA in the browser: the data owner's side of /api/v2, so the server never sees keys
 * or plaintext. Mirrors the Python modules it must agree with:
 *   Paillier + CRT decryption ........ agniya/core/paillier.py
 *   slot layout / range decryption ... agniya/core/batch_packing.py (layout, decrypt_range)
 *   OPE tags ......................... pyope 0.2.2 + agniya/hybrid/fast_ope.py (same scheme;
 *                                      tests/test_integration/test_browser_crypto.py checks
 *                                      tags and ciphertexts against the Python side)
 *   upload / query ................... agniya/client.py (AgniyaClient)
 * One file with no imports, so Node can run it directly for those checks.
 */

// ---------------------------------------------------------------- big-integer helpers
const webcrypto: Crypto = globalThis.crypto;

function randomBits(bits: number): bigint {
  const bytes = new Uint8Array(Math.ceil(bits / 8));
  webcrypto.getRandomValues(bytes);
  let x = 0n;
  for (const b of bytes) x = (x << 8n) | BigInt(b);
  return x >> BigInt(bytes.length * 8 - bits);
}

export function modPow(base: bigint, exp: bigint, mod: bigint): bigint {
  let r = 1n;
  base %= mod;
  while (exp > 0n) {
    if (exp & 1n) r = (r * base) % mod;
    base = (base * base) % mod;
    exp >>= 1n;
  }
  return r;
}

function gcd(a: bigint, b: bigint): bigint {
  while (b) [a, b] = [b, a % b];
  return a;
}

function modInv(a: bigint, m: bigint): bigint {
  let [r0, r1, s0, s1] = [((a % m) + m) % m, m, 1n, 0n];
  while (r1) {
    const q = r0 / r1;
    [r0, r1, s0, s1] = [r1, r0 - q * r1, s1, s0 - q * s1];
  }
  if (r0 !== 1n) throw new Error('not invertible');
  return ((s0 % m) + m) % m;
}

const SMALL_PRIMES: bigint[] = (() => {
  const out: bigint[] = [];
  for (let n = 3; n < 2000; n += 2) if (out.every(p => n % Number(p) !== 0)) out.push(BigInt(n));
  return out;
})();

function isProbablePrime(n: bigint, rounds = 40): boolean {
  for (const p of SMALL_PRIMES) if (n % p === 0n) return n === p;
  let d = n - 1n, s = 0;
  while (!(d & 1n)) { d >>= 1n; s++; }
  const bits = n.toString(2).length;
  for (let i = 0; i < rounds; i++) {
    const a = 2n + (randomBits(bits) % (n - 3n));
    let x = modPow(a, d, n);
    if (x === 1n || x === n - 1n) continue;
    let composite = true;
    for (let r = 1; r < s; r++) {
      x = (x * x) % n;
      if (x === n - 1n) { composite = false; break; }
    }
    if (composite) return false;
  }
  return true;
}

function generatePrime(bits: number): bigint {
  for (;;) {  // top two bits set (so p*q has exactly 2*bits bits), odd
    const c = randomBits(bits) | (3n << BigInt(bits - 2)) | 1n;
    if (isProbablePrime(c)) return c;
  }
}

const bitLength = (x: bigint) => (x === 0n ? 0 : x.toString(2).length);

// ---------------------------------------------------------------- Paillier
export interface PublicKey { n: bigint; nSquared: bigint; }
export interface PrivateKey {
  p: bigint; q: bigint; pSquared: bigint; qSquared: bigint; hp: bigint; hq: bigint; qInvP: bigint;
  ep: bigint; eq: bigint; qSqInvPSq: bigint;  // for r^n by CRT: n mod phi(p^2), n mod phi(q^2), (q^2)^-1 mod p^2
}

export function generateKeypair(bits = 2048): { pub: PublicKey; priv: PrivateKey } {
  for (;;) {
    const p = generatePrime(bits / 2), q = generatePrime(bits / 2), n = p * q;
    if (p !== q && bitLength(n) === bits && gcd(n, (p - 1n) * (q - 1n)) === 1n) return keypairFromPrimes(p, q);
  }
}

export function keypairFromPrimes(p: bigint, q: bigint): { pub: PublicKey; priv: PrivateKey } {
  const n = p * q, pSquared = p * p, qSquared = q * q, g = n + 1n;
  const hp = modInv((modPow(g, p - 1n, pSquared) - 1n) / p, p);
  const hq = modInv((modPow(g, q - 1n, qSquared) - 1n) / q, q);
  return { pub: { n, nSquared: n * n }, priv: { p, q, pSquared, qSquared, hp, hq, qInvP: modInv(q, p),
    ep: n % (p * (p - 1n)), eq: n % (q * (q - 1n)), qSqInvPSq: modInv(qSquared, pSquared) } };
}

/** r^n mod n^2 for a uniform r in Z_n*, computed by CRT (the owner knows p, q): same value, ~2x faster. */
function randomRn(pub: PublicKey, priv: PrivateKey): bigint {
  let r: bigint;
  do r = randomBits(bitLength(pub.n)) % pub.n; while (r === 0n || gcd(r, pub.n) !== 1n);
  const { pSquared, qSquared } = priv;
  const a = modPow(r, priv.ep, pSquared), b = modPow(r, priv.eq, qSquared);  // phi(p^2) = p(p-1)
  const t = ((((a - b) * priv.qSqInvPSq) % pSquared) + pSquared) % pSquared;
  return b + qSquared * t;  // < q^2 * p^2 = n^2
}

export function encrypt(pub: PublicKey, priv: PrivateKey, m: bigint): bigint {
  return ((1n + m * pub.n) % pub.nSquared) * randomRn(pub, priv) % pub.nSquared;
}

export function decrypt(priv: PrivateKey, c: bigint): bigint {
  const { p, q, pSquared, qSquared, hp, hq, qInvP } = priv;
  const mp = (((modPow(c, p - 1n, pSquared) - 1n) / p) * hp) % p;
  const mq = (((modPow(c, q - 1n, qSquared) - 1n) / q) * hq) % q;
  return mq + q * ((((mp - mq) * qInvP) % p + p) % p);
}

// ---------------------------------------------------------------- packing
/** (slotBits, slots) so that no slot overflows when all `count` values are summed (as Python). */
export function layout(pub: PublicKey, maxValue: bigint, count: number): [number, number] {
  const usable = bitLength(pub.n) - 1;
  const vb = bitLength(maxValue > 1n ? maxValue : 1n);
  let slots = Math.max(1, Math.floor(usable / (vb + 1)));
  for (;;) {
    const perSlot = Math.ceil(count / slots);
    const bits = vb + bitLength(BigInt(perSlot));
    if (slots * bits <= usable) return [bits, slots];
    if (slots === 1) throw new Error('Sum of values does not fit in one plaintext');
    slots--;
  }
}

export function decryptRange(priv: PrivateKey, product: bigint | null,
                             edges: Array<[bigint, number, number]>, slotBits: number, slots: number): bigint {
  const mask = (1n << BigInt(slotBits)) - 1n;
  let total = 0n;
  const parts: Array<[bigint, number, number]> = product !== null ? [[product, 0, slots], ...edges] : edges;
  for (const [ct, lo, hi] of parts) {
    const m = decrypt(priv, ct);
    for (let k = lo; k < hi; k++) total += (m >> BigInt(k * slotBits)) & mask;
  }
  return total;
}

// ---------------------------------------------------------------- OPE (port of pyope 0.2.2)
class NeedMoreCoins extends Error {}

class Coins {
  private i = 0;
  private readonly bytes: Uint8Array;
  constructor(bytes: Uint8Array) { this.bytes = bytes; }
  bit(): number {
    const k = this.i++;
    if (k >= this.bytes.length * 8) throw new NeedMoreCoins();
    return (this.bytes[k >> 3] >> (7 - (k & 7))) & 1;  // MSB first, as pyope
  }
  draw(): number {  // pyope hgd.PRNG.draw: 32 bits -> [0, 1]
    let out = 0;
    for (let j = 0; j < 32; j++) out = out * 2 + this.bit();
    return out / 4294967295;
  }
}

const LOGGAM_A = [8.333333333333333e-02, -2.777777777777778e-03, 7.936507936507937e-04, -5.952380952380952e-04,
  8.417508417508418e-04, -1.917526917526918e-03, 6.410256410256410e-03, -2.955065359477124e-02,
  1.796443723688307e-01, -1.39243221690590e+00];

function loggam(x: number): number {
  let x0 = x, n = 0;
  if (x === 1.0 || x === 2.0) return 0.0;
  if (x <= 7.0) { n = Math.trunc(7 - x); x0 = x + n; }
  const x2 = 1.0 / (x0 * x0), xp = 2 * Math.PI;
  let gl0 = LOGGAM_A[9];
  for (let k = 8; k >= 0; k--) { gl0 *= x2; gl0 += LOGGAM_A[k]; }
  let gl = gl0 / x0 + 0.5 * Math.log(xp) + (x0 - 0.5) * Math.log(x0) - x0;
  if (x <= 7.0) for (let k = 1; k <= n; k++) { gl -= Math.log(x0 - 1.0); x0 -= 1.0; }
  return gl;
}

const N = (x: bigint) => Number(x);  // = Python float(int): round to nearest, ties to even
const minB = (a: bigint, b: bigint) => (a < b ? a : b);

function hgdHyp(c: Coins, good: bigint, bad: bigint, sample: bigint): bigint {
  const d1 = bad + good - sample, d2 = N(minB(bad, good));
  let Y = d2, K = sample;
  while (Y > 0.0) {
    const U = c.draw();
    Y -= Math.floor(U + Y / N(d1 + K));
    K -= 1n;
    if (K === 0n) break;
  }
  let Z = BigInt(Math.trunc(d2 - Y));
  if (good > bad) Z = sample - Z;
  return Z;
}

function hgdHrua(c: Coins, good: bigint, bad: bigint, sample: bigint): bigint {
  const D1 = 1.7155277699214135, D2 = 0.8989161620588988;
  const mingoodbad = minB(good, bad), popsize = good + bad, maxgoodbad = good > bad ? good : bad;
  const m = minB(sample, popsize - sample);
  const d4 = N(mingoodbad) / N(popsize), d5 = 1.0 - d4, d6 = N(m) * d4 + 0.5;
  const d7 = Math.sqrt(N((popsize - m) * sample) * d4 * d5 / N(popsize - 1n) + 0.5);
  const d8 = D1 * d7 + D2;
  const d9 = BigInt(Math.floor(N(m + 1n) * N(mingoodbad + 1n) / N(popsize + 2n)));
  const lg = (z: bigint) => loggam(N(z + 1n)) + loggam(N(mingoodbad - z + 1n)) + loggam(N(m - z + 1n))
    + loggam(N(maxgoodbad - m + z + 1n));
  const d10 = lg(d9);
  const d11 = Math.min(N(minB(m, mingoodbad)) + 1.0, Math.floor(d6 + 16 * d7));
  let Z = 0n;
  for (;;) {
    const X = c.draw(), Y = c.draw();
    const W = d6 + d8 * (Y - 0.5) / X;
    if (W < 0.0 || W >= d11) continue;
    Z = BigInt(Math.floor(W));
    const T = d10 - lg(Z);
    if (X * (4.0 - X) - 3.0 <= T) break;
    if (X * (X - T) >= 1) continue;
    if (2.0 * Math.log(X) <= T) break;
  }
  if (good > bad) Z = m - Z;
  if (m < sample) Z = good - Z;
  return Z;
}

function sampleHgd(inLo: bigint, inHi: bigint, outLo: bigint, outHi: bigint, nsample: bigint, c: Coins): bigint {
  const inSize = inHi - inLo + 1n, outSize = outHi - outLo + 1n;
  const idx = nsample - outLo + 1n;
  if (inSize === outSize) return inLo + idx - 1n;
  const num = idx > 10n ? hgdHrua(c, inSize, outSize - inSize, idx) : hgdHyp(c, inSize, outSize - inSize, idx);
  return num === 0n ? inLo : inLo + num - 1n;
}

function sampleUniform(lo: bigint, hi: bigint, c: Coins): bigint {
  while (hi > lo) {
    const mid = (lo + hi) / 2n;
    if (c.bit() === 0) hi = mid; else lo = mid + 1n;
  }
  return lo;
}

const ZERO_COUNTER = new Uint8Array(16);

export class OPE {
  readonly key: Uint8Array;
  readonly inHi: bigint;
  readonly outHi: bigint;
  private hmacKey: Promise<CryptoKey>;
  constructor(key: Uint8Array, inHi: bigint, outHi: bigint = (1n << 64n) - 1n) {
    if (inHi < 0n || inHi > outHi) throw new Error('Invalid OPE range');
    this.key = key; this.inHi = inHi; this.outHi = outHi;
    this.hmacKey = webcrypto.subtle.importKey('raw', key as BufferSource, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  }

  /** pyope tape_gen(data): AES-256-CTR keystream (counter 0) under HMAC-SHA256(key, str(data)). */
  private async tape(data: bigint, nbytes: number): Promise<Uint8Array> {
    const digest = await webcrypto.subtle.sign('HMAC', await this.hmacKey, new TextEncoder().encode(data.toString()));
    const aes = await webcrypto.subtle.importKey('raw', digest, 'AES-CTR', false, ['encrypt']);
    return new Uint8Array(await webcrypto.subtle.encrypt({ name: 'AES-CTR', counter: ZERO_COUNTER, length: 128 },
      aes, new Uint8Array(nbytes)));
  }

  private async withCoins<T>(data: bigint, f: (c: Coins) => T): Promise<T> {
    for (let n = 256; ; n *= 4) {  // keystream prefixes agree, so retrying with more bytes is exact
      try { return f(new Coins(await this.tape(data, n))); } catch (e) { if (!(e instanceof NeedMoreCoins)) throw e; }
    }
  }

  /** {value: tag} for all distinct values: one shared walk of the OPE tree (as FastOPE.encrypt_many). */
  async encryptMany(values: bigint[]): Promise<Map<bigint, bigint>> {
    const vals = [...new Set(values)].sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
    if (vals.length && (vals[0] < 0n || vals[vals.length - 1] > this.inHi)) throw new Error('Plaintext out of range');
    const tags = new Map<bigint, bigint>();
    const walk = async (lo: number, hi: number, inLo: bigint, inHi: bigint, outLo: bigint, outHi: bigint): Promise<void> => {
      if (inLo === inHi) {
        tags.set(vals[lo], await this.withCoins(vals[lo], c => sampleUniform(outLo, outHi, c)));
        return;
      }
      const inSize = inHi - inLo + 1n, outSize = outHi - outLo + 1n;
      const inEdge = inLo - 1n, outEdge = outLo - 1n;
      const mid = outEdge + BigInt(Math.ceil(N(outSize) / 2.0));  // float, exactly as pyope
      const x = await this.withCoins(mid, c => sampleHgd(inLo, inHi, outLo, outHi, mid, c));
      let k = lo;
      while (k < hi && vals[k] <= x) k++;
      if (lo < k) await walk(lo, k, inEdge + 1n, x, outEdge + 1n, mid);
      if (k < hi) await walk(k, hi, x + 1n, inEdge + inSize, mid + 1n, outEdge + outSize);
    };
    if (vals.length) await walk(0, vals.length, 0n, this.inHi, 0n, this.outHi);
    return tags;
  }

  async encrypt(v: bigint): Promise<bigint> {
    return (await this.encryptMany([v])).get(v)!;
  }
}

// ---------------------------------------------------------------- client for /api/v2
type Post = (path: string, body: unknown) => Promise<Record<string, unknown>>;
interface AggregateResponse {
  count: number; product: string | null; ciphertexts_used: number; time_ms: number;
  edges: Array<{ ciphertext: string; first_slot: number; end_slot: number }>;
}

export function httpPost(baseUrl: string): Post {
  return async (path, body) => {
    const r = await fetch(baseUrl.replace(/\/$/, '') + path, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    const j = await r.json() as Record<string, unknown>;
    if (!r.ok) throw new Error(String(j.error || `HTTP ${r.status}`));
    return j;
  };
}

interface ColumnMeta {
  scale: number; slotBits: number; slots: number; offset: bigint; count: number;
  ope?: OPE; opeOffset?: bigint; opeTop?: bigint;
}

export interface QueryAnswer {
  sum: number; count: number; avg: number;
  ciphertextsUsed: number; ciphertextBits: number[]; serverMs: number;
}

const hex = (x: bigint) => x.toString(16);
const unhex = (s: string) => BigInt('0x' + s);

export class BrowserClient {
  readonly post: Post;
  readonly dataset: string;
  readonly pub: PublicKey;
  readonly priv: PrivateKey;  // never sent anywhere
  readonly columns = new Map<string, ColumnMeta>();

  constructor(post: Post, dataset: string, keys = generateKeypair(2048)) {
    this.post = post;
    this.dataset = dataset;
    this.pub = keys.pub;
    this.priv = keys.priv;
  }

  /** Encrypt here; the server receives n, packed ciphertexts, slots, count and (optionally) sorted OPE tags. */
  async upload(column: string, values: number[], decimals: number, rangeFilter: boolean): Promise<{ ciphertexts: number }> {
    const scale = 10 ** decimals;
    const ints = values.map(v => BigInt(Math.round(v * scale)));
    const meta: ColumnMeta = { scale, slotBits: 0, slots: 0, offset: 0n, count: ints.length };
    const body: Record<string, unknown> = { dataset: this.dataset, column, n: hex(this.pub.n) };
    if (rangeFilter && ints.length) {
      ints.sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));  // sorted packing: a range is a run of slots
      const off = ints[0], top = ints[ints.length - 1] - off > 1n ? ints[ints.length - 1] - off : 1n;
      const key = new Uint8Array(32);
      webcrypto.getRandomValues(key);
      meta.ope = new OPE(key, top);
      meta.opeOffset = off;
      meta.opeTop = top;
      const tags = await meta.ope.encryptMany(ints.map(v => v - off));
      body.ope_tags = ints.map(v => tags.get(v - off)!.toString());
    }
    const offset = ints.reduce((m, v) => (v < m ? v : m), 0n);
    const shifted = ints.map(v => v - offset);
    const [bits, slots] = layout(this.pub, shifted.reduce((m, v) => (v > m ? v : m), 0n), shifted.length);
    const cts: string[] = [];
    for (let i = 0; i < shifted.length; i += slots) {
      let acc = 0n;
      shifted.slice(i, i + slots).forEach((v, j) => { acc |= v << BigInt(j * bits); });
      cts.push(hex(encrypt(this.pub, this.priv, acc)));
    }
    Object.assign(meta, { slotBits: bits, slots, offset });
    Object.assign(body, { ciphertexts: cts, slots, count: ints.length });
    const r = await this.post('/api/v2/columns', body);
    this.columns.set(column, meta);
    return r as { ciphertexts: number };
  }

  /** SUM / COUNT / AVG, optionally only rows with lo <= value <= hi; decrypted here. */
  async query(column: string, lo?: number, hi?: number): Promise<QueryAnswer> {
    const m = this.columns.get(column);
    if (!m) throw new Error(`${column} is not encrypted`);
    const body: Record<string, unknown> = { dataset: this.dataset, column };
    const empty: QueryAnswer = { sum: 0, count: 0, avg: 0, ciphertextsUsed: 0, ciphertextBits: [], serverMs: 0 };
    if (lo !== undefined || hi !== undefined) {
      if (!m.ope) throw new Error(`Range filters need ${column} encrypted as OPE+Paillier`);
      const loS = lo !== undefined ? BigInt(Math.round(lo * m.scale)) - m.opeOffset! : 0n;
      const hiS = hi !== undefined ? BigInt(Math.round(hi * m.scale)) - m.opeOffset! : m.opeTop!;
      if (loS > m.opeTop! || hiS < 0n || loS > hiS) return empty;  // never reaches the server
      const tags = await m.ope.encryptMany([loS > 0n ? loS : 0n, hiS < m.opeTop! ? hiS : m.opeTop!]);
      body.lo_tag = tags.get(loS > 0n ? loS : 0n)!.toString();
      body.hi_tag = tags.get(hiS < m.opeTop! ? hiS : m.opeTop!)!.toString();
    }
    const r = await this.post('/api/v2/aggregate', body) as unknown as AggregateResponse;
    const product = r.product ? unhex(r.product) : null;
    const edges = r.edges.map(
      e => [unhex(e.ciphertext), Math.max(0, e.first_slot), Math.min(e.end_slot, m.slots)] as [bigint, number, number]);
    const total = decryptRange(this.priv, product, edges, m.slotBits, m.slots) + m.offset * BigInt(r.count);
    const sum = Number(total) / m.scale;  // ponytail: exact while |total| < 2^53; BigInt division if columns get bigger
    return {
      sum, count: r.count, avg: r.count ? sum / r.count : 0, ciphertextsUsed: r.ciphertexts_used,
      ciphertextBits: [product, ...edges.map(e => e[0])].filter((x): x is bigint => x !== null).map(bitLength),
      serverMs: r.time_ms,
    };
  }
}

// ---------------------------------------------------------------- CSV (local parsing)
/** Minimal RFC 4180 parser: quoted fields, "" escapes, CRLF. Returns header + rows of strings. */
export function parseCsv(text: string): { header: string[]; rows: string[][] } {
  const rows: string[][] = [];
  let row: string[] = [], field = '', quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (ch === '"') quoted = false;
      else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ',') { row.push(field); field = ''; }
    else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && text[i + 1] === '\n') i++;
      row.push(field); field = '';
      if (row.length > 1 || row[0] !== '') rows.push(row);
      row = [];
    } else field += ch;
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }
  return { header: rows[0] ?? [], rows: rows.slice(1) };
}
