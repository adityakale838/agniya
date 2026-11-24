/*
 * AGNIYA in the browser: the data owner's side of /api/v2, so the server never sees keys
 * or plaintext. Mirrors the Python modules it must agree with:
 *   Paillier + CRT decryption ........ agniya/core/paillier.py
 *   slot layout / range decryption ... agniya/core/batch_packing.py (layout, decrypt_range, group_layout)
 *   OPE tags ......................... pyope 0.2.2 + agniya/hybrid/fast_ope.py (same scheme;
 *                                      tests/test_integration/test_browser_crypto.py checks
 *                                      tags and ciphertexts against the Python side)
 *   integrity tags / checks .......... agniya/core/integrity.py (ColumnMac, range_cuts)
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
export function layout(pub: PublicKey, maxValue: bigint, count: number, reserve = 0): [number, number] {
  const usable = bitLength(pub.n) - 1 - reserve;
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

/** (slotBits, lanes, perPage) for GROUP BY packing (as Python group_layout): each of up to perPage groups
 *  gets `lanes` value slots plus one count slot per ciphertext. Groups are split into pages of perPage, each
 *  its own run of ciphertexts and decryption: one page whenever all groups fit, else the fewest ciphertexts
 *  counting each decryption a page adds to a query as 16. */
export function groupLayout(pub: PublicKey, maxValue: bigint, sizes: number[],
                            decryptionsPerPage = 1, reserve = 0): [number, number, number] {
  const usable = bitLength(pub.n) - 1 - reserve, k = Math.max(sizes.length, 1), biggest = Math.max(0, ...sizes);
  const fit = (lanes: number) => {  // [slot bits, groups per plaintext, ciphertexts per page]
    const m = Math.max(1, Math.ceil(biggest / lanes));
    const bits = bitLength([maxValue * BigInt(m), BigInt(lanes * m), 1n].reduce((a, b) => (a > b ? a : b)));
    return [bits, Math.floor(usable / ((lanes + 1) * bits)), m];
  };
  for (let lanes = Math.max(1, Math.floor(Math.floor(usable / (bitLength(maxValue > 1n ? maxValue : 1n) + 1)) / k) - 1); lanes > 0; lanes--) {
    const [bits, per] = fit(lanes);
    if (per >= k) return [bits, lanes, k];
  }
  let best: number[] | null = null;
  for (let lanes = 1; ; lanes++) {
    const [bits, per, m] = fit(lanes);
    if (per < 1) break;
    const pages = Math.ceil(k / per), cost = pages * m + 16 * decryptionsPerPage * pages;
    if (!best || cost < best[0]) best = [cost, bits, lanes, per];
  }
  if (!best) throw new Error('Values too large for one plaintext; use a larger key');
  return [best[1], best[2], best[3]];
}

export function decryptRange(priv: PrivateKey, product: bigint | null, edges: Array<[bigint, number, number]>,
                             slotBits: number, slots: number, dec = (c: bigint) => decrypt(priv, c)): bigint {
  const mask = (1n << BigInt(slotBits)) - 1n;
  let total = 0n;
  const parts: Array<[bigint, number, number]> = product !== null ? [[product, 0, slots], ...edges] : edges;
  for (const [ct, lo, hi] of parts) {
    const m = dec(ct);
    for (let k = lo; k < hi; k++) total += (m >> BigInt(k * slotBits)) & mask;
  }
  return total;
}

// ---------------------------------------------------------------- integrity (as agniya/core/integrity.py)
const MAC_P = (1n << 127n) - 1n;
export const RESERVE = 159;  // bits above the data: a 127-bit tag summed over up to 2^32 ciphertexts

/** Per-column key for integrity tags: plaintext m of page p, ciphertext c carries (alpha*m + beta(p, c)) mod P
 *  above the data, so the client can check that an answer is the honest product of the stored ciphertexts. */
export class ColumnMac {
  readonly key: Uint8Array;
  readonly shift: number;
  private readonly aes: Promise<CryptoKey>;
  private readonly hmac: Promise<CryptoKey>;
  private alphaP?: Promise<bigint>;
  constructor(n: bigint, key: Uint8Array = webcrypto.getRandomValues(new Uint8Array(32))) {
    this.key = key;  // stored in key files; tags and cut MACs use subkeys of it (as Python)
    this.shift = bitLength(n) - 1 - RESERVE;
    const hmacAlg = { name: 'HMAC', hash: 'SHA-256' };
    const base = webcrypto.subtle.importKey('raw', key as BufferSource, hmacAlg, false, ['sign']);
    const sub = async (label: string) =>
      webcrypto.subtle.sign('HMAC', await base, new TextEncoder().encode(label));
    this.aes = sub('tags').then(k => webcrypto.subtle.importKey('raw', k, 'AES-CTR', false, ['encrypt']));
    this.hmac = sub('cuts').then(k => webcrypto.subtle.importKey('raw', k, hmacAlg, false, ['sign']));
  }

  /** n values < 2^127: AES-256-CTR keystream blocks start..start+n-1 (as Python _blocks). */
  private async blocks(start: bigint, n: number): Promise<bigint[]> {
    const counter = new Uint8Array(16);
    for (let k = 15, x = start; k >= 0; k--, x >>= 8n) counter[k] = Number(x & 255n);
    const ks = new Uint8Array(await webcrypto.subtle.encrypt({ name: 'AES-CTR', counter, length: 128 }, await this.aes,
      new Uint8Array(16 * n)));
    const out: bigint[] = [];
    for (let k = 0; k < n; k++) {
      let v = 0n;
      for (let b = 0; b < 16; b++) v = (v << 8n) | BigInt(ks[16 * k + b]);
      out.push(v >> 1n);
    }
    return out;
  }

  private alpha(): Promise<bigint> {
    return (this.alphaP ??= this.blocks(1n << 127n, 1).then(b => b[0]));
  }

  private async betaSum(page: number, first: number, n: number): Promise<bigint> {
    return n ? (await this.blocks((BigInt(page) << 64n) + BigInt(first), n)).reduce((a, b) => a + b, 0n) : 0n;
  }

  /** Plaintexts (pages of equal length, page-major) with their tags above the data. */
  async tag(plain: bigint[], pages = 1): Promise<bigint[]> {
    const m = Math.floor(plain.length / Math.max(pages, 1)), alpha = await this.alpha(), shift = BigInt(this.shift);
    const out: bigint[] = [];
    for (let p = 0; p < pages && m; p++) {
      const betas = await this.blocks(BigInt(p) << 64n, m);
      betas.forEach((b, c) => { const x = plain[p * m + c]; out.push(x + (((alpha * x + b) % MAC_P) << shift)); });
    }
    return out;
  }

  /** plaintext = product of ciphertexts first..first+n-1 of the page, decrypted. */
  async check(plaintext: bigint, page: number, first: number, n: number): Promise<boolean> {
    const shift = BigInt(this.shift), low = plaintext & ((1n << shift) - 1n);
    return (plaintext >> shift) % MAC_P === (await this.alpha() * low + await this.betaSum(page, first, n)) % MAC_P;
  }

  async tagsMac(page: number, c: number, tags: string[]): Promise<string> {
    const d = new Uint8Array(await webcrypto.subtle.sign('HMAC', await this.hmac,
      new TextEncoder().encode(`${page}:${c}:${tags.join(',')}`)));
    return [...d.subarray(0, 16)].map(b => b.toString(16).padStart(2, '0')).join('');
  }

  async tagMacs(page: number, tags: string[], slots: number): Promise<string[]> {
    const out: string[] = [];
    for (let k = 0; k < tags.length; k += slots) out.push(await this.tagsMac(page, k / slots, tags.slice(k, k + slots)));
    return out;
  }

  /** Rows i..j-1 are exactly the rows with loTag <= tag <= hiTag (tags are sorted). */
  async checkCut(page: number, slots: number, count: number, i: number, j: number, witnesses: Witness[],
                 loTag: bigint, hiTag: bigint): Promise<boolean> {
    const seen = new Map<number, bigint>();
    for (const w of witnesses) {
      if (await this.tagsMac(page, w.index, w.tags) !== w.mac) return false;
      w.tags.forEach((t, k) => seen.set(w.index * slots + k, BigInt(t)));
    }
    const at = (r: number) => { const t = seen.get(r); if (t === undefined) throw new Error('missing'); return t; };
    try {
      return 0 <= i && i <= j && j <= count && (i === 0 || at(i - 1) < loTag) && (j === count || at(j) > hiTag)
        && (i === j || (at(i) >= loTag && at(j - 1) <= hiTag));
    } catch {
      return false;  // a needed row was not sent
    }
  }
}

/** Ciphertexts wholly inside rows i..j-1, and the (at most two) cut ones as [index, firstSlot, endSlot]. */
export function rangeCuts(slots: number, count: number, i: number, j: number): [number[], Array<[number, number, number]>] {
  const full: number[] = [], edges: Array<[number, number, number]> = [];
  if (i < j) {
    for (let c = Math.floor(i / slots); c <= Math.floor((j - 1) / slots); c++) {
      const lo = Math.max(i, c * slots) - c * slots, hi = Math.min(j, (c + 1) * slots, count) - c * slots;
      if (lo === 0 && hi === Math.min(slots, count - c * slots)) full.push(c); else edges.push([c, lo, hi]);
    }
  }
  return [full, edges];
}

/** Quantile q of sorted rows i..j-1 (i < j) as pandas computes it (as Python quantile_rows): rows a <= b and
 *  frac, value = v[a] + (v[b] - v[a]) * frac. q = 0 is MIN, 0.5 MEDIAN, 1 MAX. */
export function quantileRows(i: number, j: number, q: number): [number, number, number] {
  const pos = q * (j - i - 1);
  return [i + Math.floor(pos), i + Math.ceil(pos), pos - Math.floor(pos)];
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

// ---------------------------------------------------------------- scrypt (RFC 7914)
const rotl = (a: number, b: number) => (a << b) | (a >>> (32 - b));

function salsa208(B: Uint32Array, x: Uint32Array) {
  x.set(B);
  for (let i = 0; i < 8; i += 2) {
    x[4] ^= rotl(x[0] + x[12], 7); x[8] ^= rotl(x[4] + x[0], 9); x[12] ^= rotl(x[8] + x[4], 13); x[0] ^= rotl(x[12] + x[8], 18);
    x[9] ^= rotl(x[5] + x[1], 7); x[13] ^= rotl(x[9] + x[5], 9); x[1] ^= rotl(x[13] + x[9], 13); x[5] ^= rotl(x[1] + x[13], 18);
    x[14] ^= rotl(x[10] + x[6], 7); x[2] ^= rotl(x[14] + x[10], 9); x[6] ^= rotl(x[2] + x[14], 13); x[10] ^= rotl(x[6] + x[2], 18);
    x[3] ^= rotl(x[15] + x[11], 7); x[7] ^= rotl(x[3] + x[15], 9); x[11] ^= rotl(x[7] + x[3], 13); x[15] ^= rotl(x[11] + x[7], 18);
    x[1] ^= rotl(x[0] + x[3], 7); x[2] ^= rotl(x[1] + x[0], 9); x[3] ^= rotl(x[2] + x[1], 13); x[0] ^= rotl(x[3] + x[2], 18);
    x[6] ^= rotl(x[5] + x[4], 7); x[7] ^= rotl(x[6] + x[5], 9); x[4] ^= rotl(x[7] + x[6], 13); x[5] ^= rotl(x[4] + x[7], 18);
    x[11] ^= rotl(x[10] + x[9], 7); x[8] ^= rotl(x[11] + x[10], 9); x[9] ^= rotl(x[8] + x[11], 13); x[10] ^= rotl(x[9] + x[8], 18);
    x[12] ^= rotl(x[15] + x[14], 7); x[13] ^= rotl(x[12] + x[15], 9); x[14] ^= rotl(x[13] + x[12], 13); x[15] ^= rotl(x[14] + x[13], 18);
  }
  for (let i = 0; i < 16; i++) B[i] = B[i] + x[i];  // Uint32Array wraps mod 2^32
}

function blockMix(B: Uint32Array, Y: Uint32Array, X: Uint32Array, tmp: Uint32Array, r: number) {
  X.set(B.subarray((2 * r - 1) * 16, 2 * r * 16));
  for (let i = 0; i < 2 * r; i++) {
    for (let k = 0; k < 16; k++) X[k] ^= B[i * 16 + k];
    salsa208(X, tmp);
    Y.set(X, ((i & 1) ? r + (i >> 1) : i >> 1) * 16);  // even blocks first, then odd
  }
  B.set(Y);
}

async function pbkdf2(password: Uint8Array, salt: Uint8Array, bytes: number): Promise<Uint8Array> {
  const k = await webcrypto.subtle.importKey('raw', password as BufferSource, 'PBKDF2', false, ['deriveBits']);
  return new Uint8Array(await webcrypto.subtle.deriveBits(
    { name: 'PBKDF2', hash: 'SHA-256', salt: salt as BufferSource, iterations: 1 }, k, bytes * 8));
}

/** scrypt(password, salt, N, r, p) -> dkLen bytes, as Python's hashlib.scrypt. Memory: 128 * r * N bytes. */
export async function scrypt(password: string, salt: Uint8Array, N: number, r: number, p: number,
                             dkLen = 32): Promise<Uint8Array> {
  const pw = new TextEncoder().encode(password);
  const B = await pbkdf2(pw, salt, p * 128 * r);
  const words = 32 * r, X = new Uint32Array(words), Y = new Uint32Array(words);
  const T = new Uint32Array(16), tmp = new Uint32Array(16), V = new Uint32Array(words * N);
  const view = new DataView(B.buffer, B.byteOffset, B.byteLength);
  for (let b = 0; b < p; b++) {
    const base = b * 128 * r;
    for (let k = 0; k < words; k++) X[k] = view.getUint32(base + 4 * k, true);
    for (let i = 0; i < N; i++) { V.set(X, i * words); blockMix(X, Y, T, tmp, r); }
    for (let i = 0; i < N; i++) {
      const j = X[(2 * r - 1) * 16] & (N - 1);
      for (let k = 0; k < words; k++) X[k] ^= V[j * words + k];
      blockMix(X, Y, T, tmp, r);
    }
    for (let k = 0; k < words; k++) view.setUint32(base + 4 * k, X[k], true);
  }
  return pbkdf2(pw, B, dkLen);
}

// ---------------------------------------------------------------- key file (same format as agniya/client.py)
export const KEY_FILE_FORMAT = 'agniya-client-key/1';
const KEY_SCRYPT = { n: 2 ** 17, r: 8, p: 1 };  // 128 MiB, ~1 s: slows password guessing

const b64 = (u: Uint8Array) => { let s = ''; for (const c of u) s += String.fromCharCode(c); return btoa(s); };
const unb64 = (s: string) => Uint8Array.from(atob(s), c => c.charCodeAt(0));

/** Python json.dumps(v, sort_keys=True) for the (ASCII) header: the AES-GCM associated data must match byte for byte. */
function pyDumpsSorted(v: unknown): string {
  if (typeof v === 'string') return JSON.stringify(v);
  if (typeof v === 'number') return String(v);
  const o = v as Record<string, unknown>;
  return '{' + Object.keys(o).sort().map(k => `${JSON.stringify(k)}: ${pyDumpsSorted(o[k])}`).join(', ') + '}';
}

function safeNum(x: bigint): number {
  if (x > BigInt(Number.MAX_SAFE_INTEGER) || x < -BigInt(Number.MAX_SAFE_INTEGER)) throw new Error('Value too large for the key file');
  return Number(x);
}

async function gcmKey(password: string, salt: Uint8Array, kdf: { n: number; r: number; p: number }) {
  const raw = await scrypt(password, salt, kdf.n, kdf.r, kdf.p);
  return webcrypto.subtle.importKey('raw', raw as BufferSource, 'AES-GCM', false, ['encrypt', 'decrypt']);
}

// ---------------------------------------------------------------- client for /api/v2
type Post = (path: string, body: unknown) => Promise<Record<string, unknown>>;
interface Witness { index: number; tags: string[]; mac: string }
interface AggregateResponse {
  count: number; product: string | null; ciphertexts_used: number; time_ms: number;
  edges: Array<{ ciphertext: string; first_slot: number; end_slot: number }>;
  rows?: [number, number]; witnesses?: Witness[];
}
interface QuantilesResponse {
  count: number; time_ms: number; cells: Array<{ row: number; ciphertext: string }>;
  rows?: [number, number]; witnesses?: Witness[];
}

/** Access token for a dataset on /api/v2 (as agniya.client.dataset_token): only the private key's holder
 *  can compute it; the server keeps its SHA-256. */
export async function datasetToken(priv: PrivateKey, dataset: string): Promise<string> {
  const p = priv.p < priv.q ? priv.p : priv.q;
  const d = await webcrypto.subtle.digest('SHA-256', new TextEncoder().encode(`agniya/v2 dataset token\0${p}\0${dataset}`));
  return [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, '0')).join('');
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
  fscale?: number;  // scale of the filter values when they differ (Python upload_by columns "a|b")
  lanes?: number; labels?: Array<string | number>;  // GROUP BY copies "a#g" (Python upload_grouped)
  pages?: number;  // ... stored as server columns "a#g", "a#g@1", ... when the groups need several plaintexts
  macKey?: Uint8Array;  // integrity tags (absent in key files from before them: answers are not checked)
  shift?: bigint;  // "name^2" copies: they hold (x - shift)^2
  sizes?: number[];  // "a#g^sorted" copies: rows per label, in label order
  wspan?: bigint; woff?: bigint;  // ... "a#g^sorted|w": OPE keys are group * wspan + w - woff
}

/** Sample variance (ddof=1, as pandas and SQL VARIANCE) of n fixed-point values from their sum s1 and
 *  s2 = sum((x - c)^2), as agniya.core.batch_packing.sample_variance; null for fewer than 2 values. */
export function sampleVariance(n: bigint, s1: bigint, s2: bigint, c: bigint, scale: number): number | null {
  if (n < 2n) return null;
  const d = s1 - n * c, num = n * s2 - d * d;
  if (num < 0n) throw new Error('Integrity check failed: the sum of squares is below the square of the sum');
  return Number(num) / Number(n * (n - 1n) * BigInt(scale) ** 2n);  // ponytail: two roundings, ~1e-16 relative
}

/** (x - c)^2 for each fixed-point x, and c (about the mean), as agniya.core.batch_packing.squares. */
function squares(ints: bigint[]): [bigint[], bigint] {
  const n = BigInt(Math.max(ints.length, 1)), t = ints.reduce((a, b) => a + b, 0n);
  const c = t / n - (t % n < 0n ? 1n : 0n);  // floor, as Python //
  return [ints.map(x => (x - c) ** 2n), c];
}

export interface Spread { variance?: number | null; std?: number | null }  // with a "^2" copy (squares)

export interface QueryAnswer extends Spread {
  sum: number; count: number; avg: number;
  ciphertextsUsed: number; ciphertextBits: number[]; serverMs: number;
  verified: boolean;  // checked against the integrity tags of the uploaded data
}

export interface GroupAnswer {
  groups: Array<{ group: string | number; sum: number; count: number; avg: number } & Spread>;
  ciphertextsUsed: number; ciphertextBits: number[]; serverMs: number; pages: number;
  verified: boolean;
}

export interface QuantileAnswer {
  values: Array<number | null>;  // one per q; null when no row is in range
  count: number; ciphertextsUsed: number; ciphertextBits: number[]; serverMs: number; verified: boolean;
}

export interface GroupQuantileAnswer {
  groups: Array<{ group: string | number; count: number; values: number[] }>;  // one value per q
  ciphertextsUsed: number; ciphertextBits: number[]; serverMs: number; verified: boolean;
}

/** int(round(v * scale)) exactly as Python: round half to even. Data with one more decimal than the
 *  scale (e.g. 12268.63225 at 4 decimals) hits exact .5 often, where Math.round would round up. */
export function fixedPoint(v: number, scale: number): bigint {
  const x = v * scale, f = Math.floor(x), d = x - f;
  return BigInt(d > 0.5 || (d === 0.5 && f % 2 !== 0) ? f + 1 : f);
}

const cmp = (a: bigint, b: bigint) => (a < b ? -1 : a > b ? 1 : 0);
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

  private tokenP?: Promise<string>;

  /** POST to /api/v2 with this dataset's name and token (as AgniyaClient._v2). */
  private async v2(path: string, body: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.post(path, { ...body, dataset: this.dataset, token: await (this.tokenP ??= datasetToken(this.priv, this.dataset)) });
  }

  /** Encrypt here; the server receives n, packed ciphertexts, slots, count and (optionally) sorted OPE tags.
   *  With squares, also "column^2" for VARIANCE / STDDEV (as AgniyaClient.upload(..., squares=True)). */
  async upload(column: string, values: number[], decimals: number, rangeFilter: boolean, squares = false): Promise<{ ciphertexts: number }> {
    const scale = 10 ** decimals;
    const ints = values.map(v => fixedPoint(v, scale));
    if (rangeFilter) ints.sort(cmp);  // sorted packing: a range is a run of slots
    return this.put(column, ints, scale, rangeFilter ? ints : null, scale, squares);
  }

  /** For SUM(column) WHERE by in range: a copy of `column` packed in `by` order, stored as "column|by"
   *  (as AgniyaClient.upload_by). values[i] and byValues[i] are one row; rows missing either are skipped. */
  async uploadBy(column: string, values: Array<number | null>, by: string, byValues: Array<number | null>,
                 decimals: number, byDecimals: number, squares = false): Promise<{ ciphertexts: number }> {
    const scale = 10 ** decimals, fscale = 10 ** byDecimals;
    const rows: Array<[bigint, bigint]> = [];
    values.forEach((a, i) => {
      const b = byValues[i];
      if (a !== null && b !== null && Number.isFinite(a) && Number.isFinite(b)) rows.push([fixedPoint(b, fscale), fixedPoint(a, scale)]);
    });
    rows.sort((x, y) => cmp(x[0], y[0]) || cmp(x[1], y[1]));
    return this.put(`${column}|${by}`, rows.map(r => r[1]), scale, rows.map(r => r[0]), fscale, squares);
  }

  /** For SUM / COUNT / AVG(column) GROUP BY by: `column` packed by label, stored as "column#by" (as
   *  AgniyaClient.upload_grouped). Row r of group g goes to ciphertext r / lanes, lane r % lanes of g's
   *  block, and each block counts its rows, so one product and one decryption give every group. The labels
   *  stay here; the server sees slots per ciphertext and the number of ciphertexts. Rows missing either are skipped.
   *  Groups that do not share one plaintext are split into pages, stored as "column#by", "column#by@1", ...
   *  With `where`, the copy ("column#by|where") is packed in where order with OPE tags of where, so
   *  queryGroups(..., lo, hi, where) groups only rows with lo <= where <= hi (as encrypt_sorted_groups). */
  async uploadGrouped(column: string, values: Array<number | null>, by: string, byValues: Array<string | null>,
                      decimals: number, where?: string, whereValues?: Array<number | null>,
                      whereDecimals = 0, sq = false): Promise<{ ciphertexts: number; pages: number }> {
    const scale = 10 ** decimals, fscale = 10 ** whereDecimals;
    const rows: Array<[bigint, bigint, string]> = [];  // [where key (0 without where), value, label]
    values.forEach((a, i) => {
      const g = byValues[i], w = where !== undefined ? whereValues![i] : 0;
      if (a !== null && Number.isFinite(a) && g !== null && g !== '' && w !== null && Number.isFinite(w)) {
        rows.push([fixedPoint(w, fscale), fixedPoint(a, scale), g]);
      }
    });
    if (!rows.length) throw new Error(where !== undefined ? `No rows have ${column}, ${by} and ${where}` : `No rows have both ${column} and ${by}`);
    const labels = [...new Set(rows.map(r => r[2]))].sort();
    const name = `${column}#${by}` + (where !== undefined ? `|${where}` : '');
    let tags: string[] | null = null, ope = {};
    if (where !== undefined) {
      rows.sort((x, y) => cmp(x[0], y[0]) || cmp(x[1], y[1]));
      ({ tags, ...ope } = await this.opeTags(rows.map(r => r[0])));
    }
    const jobs: Array<[string, bigint[], number, Partial<ColumnMeta>]> = [[name, rows.map(r => r[1]), scale, {}]];
    if (sq) {
      const [sqs, shift] = squares(jobs[0][1]);
      jobs.push([`${name}^2`, sqs, scale * scale, { shift }]);
    }
    let out: { ciphertexts: number; pages: number } | null = null;
    for (const [col, vals, sc, extra] of jobs) {
      const offset = vals.reduce((m, v) => (v < m ? v : m), 0n);
      const top = vals.reduce((m, v) => (v > m ? v : m), vals[0]) - offset;
      const mac = new ColumnMac(this.pub.n);
      const meta: ColumnMeta = { scale: sc, slotBits: 0, slots: 0, offset, count: rows.length, labels, macKey: mac.key, ...extra };
      let plain: bigint[], body: Record<string, unknown>, m: number, pages: number;  // m = ciphertexts per page
      if (where === undefined) {
        const byLabel = new Map(labels.map(l => [l, [] as bigint[]]));
        rows.forEach(([, , g], r) => byLabel.get(g)!.push(vals[r] - offset));
        const sizes = labels.map(l => byLabel.get(l)!.length);
        const [bits, lanes, per] = groupLayout(this.pub, top, sizes, 1, RESERVE);
        m = Math.max(1, Math.ceil(Math.max(...sizes) / lanes));
        pages = Math.ceil(labels.length / per);
        plain = Array(pages * m).fill(0n);
        labels.forEach((l, gi) => {
          const first = Math.floor(gi / per) * m, base = (gi % per) * (lanes + 1), vs = byLabel.get(l)!;
          vs.forEach((v, r) => { plain[first + Math.floor(r / lanes)] |= v << BigInt((base + r % lanes) * bits); });
          for (let c = 0; c < m; c++) {
            plain[first + c] |= BigInt(Math.min(lanes, Math.max(0, vs.length - c * lanes))) << BigInt((base + lanes) * bits);
          }
        });
        Object.assign(meta, { slotBits: bits, lanes, pages, slots: per * (lanes + 1) });
        meta.count = meta.slots * m;  // count of each server column: every ciphertext whole
        body = { slots: meta.slots, count: meta.count };
      } else {
        const index = new Map(labels.map((l, i) => [l, i]));
        const [bits, lanes, per] = groupLayout(this.pub, top + 1n, labels.map(() => rows.length), 3, RESERVE);  // product + <=2 edges
        m = Math.ceil(rows.length / lanes);
        pages = Math.ceil(labels.length / per);
        plain = Array(pages * m).fill(0n);
        rows.forEach(([, , g], r) => {  // lane holds value - offset + 1, so 0 marks a lane of another group
          const gi = index.get(g)!, base = (gi % per) * (lanes + 1);
          plain[Math.floor(gi / per) * m + Math.floor(r / lanes)] +=
            ((vals[r] - offset + 1n) << BigInt((base + r % lanes) * bits)) + (1n << BigInt((base + lanes) * bits));
        });
        Object.assign(meta, { slotBits: bits, lanes, pages, slots: per * (lanes + 1), ...ope });
        if (fscale !== sc) meta.fscale = fscale;
        body = { slots: lanes, count: rows.length, ope_tags: tags };  // the server cuts each page like a sorted column
      }
      const tagged = await mac.tag(plain, pages);
      for (let p = 0; p < pages; p++) {
        await this.v2('/api/v2/columns', { column: col + (p ? `@${p}` : ''), n: hex(this.pub.n),
          ...body, ...(tags && { tag_macs: await mac.tagMacs(p, tags, meta.lanes!) }),
          ciphertexts: tagged.slice(p * m, (p + 1) * m).map(x => hex(encrypt(this.pub, this.priv, x))) });
      }
      this.columns.set(col, meta);
      out ??= { ciphertexts: plain.length, pages };
    }
    return out!;
  }

  /** Every group's SUM, COUNT and AVG of `column` by `by` (needs uploadGrouped): one decryption here per page
   *  of groups. With `where`, only rows with lo <= where <= hi (plus up to two edge ciphertexts per page);
   *  empty groups are left out. Copies uploaded with squares also give each group's variance and std. */
  async queryGroups(column: string, by: string, lo?: number, hi?: number, where?: string): Promise<GroupAnswer> {
    const name = `${column}#${by}` + (where ? `|${where}` : ''), m = this.columns.get(name);
    if (!m?.labels || !m.lanes) throw new Error(`No GROUP BY copy of ${column} by ${by}` + (where ? ` filtered by ${where}` : ''));
    let rng: Record<string, string> | null = null;
    if (where) {
      rng = await this.rangeTags(m, lo, hi);
      if (!rng) return { groups: [], ciphertextsUsed: 0, ciphertextBits: [], serverMs: 0, pages: m.pages ?? 1, verified: !!m.macKey };
    }
    const parts = [await this.groupSums(name, rng)];
    if (this.columns.has(`${name}^2`)) parts.push(await this.groupSums(`${name}^2`, rng));
    const [a, sq] = parts;
    const groups = m.labels.map((group, gi) => {
      const n = Number(a.counts[gi]), sum = Number(a.totals[gi]) / m.scale;
      const g = { group, sum, count: n, avg: n ? sum / n : 0 };
      return sq && n ? { ...g, ...this.spread(name, a.counts[gi], a.totals[gi], sq.totals[gi], sq.counts[gi]) } : g;
    }).filter(g => g.count > 0);
    return { groups, ciphertextsUsed: parts.reduce((t, x) => t + x.ciphertextsUsed, 0), pages: a.pages,
             serverMs: parts.reduce((t, x) => t + x.serverMs, 0), ciphertextBits: parts.flatMap(x => x.ciphertextBits),
             verified: !!m.macKey };
  }

  /** Each group's fixed-point total and count in server column(s) `name` (one per page), checked. */
  private async groupSums(name: string, rng: Record<string, string> | null) {
    const m = this.columns.get(name)!;
    const rs = await Promise.all(Array.from({ length: m.pages ?? 1 }, (_, p) =>
      this.v2('/api/v2/aggregate', { ...(rng ?? {}), column: name + (p ? `@${p}` : '') }) as unknown as Promise<AggregateResponse>));
    const plain = new Map<bigint, bigint>();
    for (let p = 0; p < rs.length; p++) for (const [c, x] of await this.answer(m, name, rs[p], p, rng)) plain.set(c, x);
    if (rng && new Set(rs.map(r => String(r.rows))).size > 1) throw new Error(`Integrity check failed: the pages of ${name} were cut at different rows`);
    const bits = BigInt(m.slotBits), mask = (1n << bits) - 1n, lanes = m.lanes!, per = Math.floor(m.slots / (lanes + 1));
    const slot = (p: bigint, s: number) => (p >> (BigInt(s) * bits)) & mask;
    const sums = m.labels!.map(() => 0n), counts = m.labels!.map(() => 0n), decrypted: bigint[] = [];
    rs.forEach((r, page) => {
      const own = m.labels!.map((_, gi) => gi).filter(gi => Math.floor(gi / per) === page);
      const at = (gi: number) => (gi % per) * (lanes + 1);  // first slot of gi's block
      if (r.product) {
        decrypted.push(unhex(r.product));
        const p = plain.get(unhex(r.product))!;
        for (const gi of own) {
          const c = slot(p, at(gi) + lanes);
          let s = 0n;
          for (let k = 0; k < lanes; k++) s += slot(p, at(gi) + k);
          sums[gi] += rng ? s - c : s;  // filtered copies hold value - offset + 1
          counts[gi] += c;
        }
      }
      for (const e of r.edges) {  // only filtered copies have edges
        const ct = unhex(e.ciphertext), p = plain.get(ct)!;
        decrypted.push(ct);
        for (const gi of own) {
          for (let k = Math.max(0, e.first_slot); k < Math.min(e.end_slot, lanes); k++) {
            const v = slot(p, at(gi) + k);
            if (v) { sums[gi] += v - 1n; counts[gi] += 1n; }  // 0 = a row of another group
          }
        }
      }
    });
    return { totals: sums.map((x, gi) => x + m.offset * counts[gi]), counts, pages: rs.length,
             ciphertextsUsed: rs.reduce((n, r) => n + r.ciphertexts_used, 0), serverMs: rs.reduce((t, r) => t + r.time_ms, 0),
             ciphertextBits: decrypted.map(bitLength) };
  }

  /** variance and std from the fixed-point sum of `name` and (sum, count) of its "name^2" copy. */
  private spread(name: string, n: bigint, s1: bigint, s2: bigint, n2: bigint): Spread {
    if (n2 !== n) throw new Error(`Integrity check failed: ${name} and ${name}^2 were summed over different rows`);
    const m = this.columns.get(name)!, v = sampleVariance(n, s1, s2, this.columns.get(`${name}^2`)!.shift!, m.scale);
    return { variance: v, std: v === null ? null : Math.sqrt(v) };
  }

  /** ciphertext -> plaintext for one /api/v2/aggregate answer (page `page` of column `name`), after checking it
   *  is the product and edges of the stored ciphertexts for the rows the range selects (as AgniyaClient._answer). */
  private async answer(m: ColumnMeta, name: string, r: AggregateResponse, page: number,
                       rng: Record<string, string> | null): Promise<Map<bigint, bigint>> {
    if (rng && m.macKey && !r.rows) {
      throw new Error(`Integrity check failed: the server sent no rows to check ${name} against; it predates integrity checks (update the server before the clients)`);
    }
    const plain = new Map<bigint, bigint>();
    let ok = false;
    try {  // a malformed answer is a failed check too
      const product = r.product ? unhex(r.product) : null, edges = r.edges.map(e => unhex(e.ciphertext));
      for (const c of product !== null ? [product, ...edges] : edges) plain.set(c, decrypt(this.priv, c));
      if (!m.macKey) return plain;  // uploaded before integrity tags: not checked
      const mac = new ColumnMac(this.pub.n, m.macKey);
      const s = m.lanes && m.ope ? m.lanes : m.slots;  // values per ciphertext on the server
      const [i, j] = rng ? [Number(r.rows![0]), Number(r.rows![1])] : [0, m.count];
      const [full, cuts] = rangeCuts(s, m.count, i, j);
      ok = r.count === j - i && (product === null) === !full.length && cuts.length === edges.length
        && cuts.every(([, lo, hi], k) => r.edges[k].first_slot === lo && r.edges[k].end_slot === hi)
        && (!full.length || await mac.check(plain.get(product!)!, page, full[0], full.length));
      for (let k = 0; ok && k < cuts.length; k++) ok = await mac.check(plain.get(edges[k])!, page, cuts[k][0], 1);
      if (ok && rng) ok = await mac.checkCut(page, s, m.count, i, j, r.witnesses!, BigInt(rng.lo_tag), BigInt(rng.hi_tag));
    } catch {
      ok = false;
    }
    if (!ok) throw new Error(`Integrity check failed: the server's answer for ${name} does not match the uploaded data`);
    return plain;
  }

  /** OPE tags (decimal strings) for sorted `keys` under a fresh key, and what is needed to make more. */
  private async opeTags(keys: bigint[]) {
    const opeOffset = keys[0], last = keys[keys.length - 1];
    const opeTop = last - opeOffset > 1n ? last - opeOffset : 1n;
    const ope = new OPE(webcrypto.getRandomValues(new Uint8Array(32)), opeTop);
    const tags = await ope.encryptMany(keys.map(v => v - opeOffset));
    return { ope, opeOffset, opeTop, tags: keys.map(v => tags.get(v - opeOffset)!.toString()) };
  }

  /** lo_tag / hi_tag for lo <= value <= hi on a column with OPE tags; null when the range is empty. */
  private async rangeTags(m: ColumnMeta, lo?: number, hi?: number): Promise<Record<string, string> | null> {
    const fs = m.fscale ?? m.scale;
    const loS = lo !== undefined ? fixedPoint(lo, fs) - m.opeOffset! : 0n;
    const hiS = hi !== undefined ? fixedPoint(hi, fs) - m.opeOffset! : m.opeTop!;
    if (loS > m.opeTop! || hiS < 0n || loS > hiS) return null;  // never reaches the server
    const a = loS > 0n ? loS : 0n, b = hiS < m.opeTop! ? hiS : m.opeTop!;
    const tags = await m.ope!.encryptMany([a, b]);
    return { lo_tag: tags.get(a)!.toString(), hi_tag: tags.get(b)!.toString() };
  }

  /** Pack `ints` (already in row order); `keys` (sorted, same length) become OPE tags when given. With sq,
   *  also "column^2" holding (x - c)^2 in the same order with the same tags (as AgniyaClient._upload). */
  private async put(column: string, ints: bigint[], scale: number, keys: bigint[] | null,
                    fscale: number, sq = false): Promise<{ ciphertexts: number }> {
    let tags: string[] | null = null, ope = {};
    if (keys && keys.length) ({ tags, ...ope } = await this.opeTags(keys));
    const jobs: Array<[string, bigint[], number, Partial<ColumnMeta>]> = [[column, ints, scale, {}]];
    if (sq && ints.length) {
      const [sqs, shift] = squares(ints);
      jobs.push([`${column}^2`, sqs, scale * scale, { shift }]);
    }
    let ciphertexts = 0;
    for (const [name, vals, sc, extra] of jobs) {
      const mac = new ColumnMac(this.pub.n);
      const offset = vals.reduce((m, v) => (v < m ? v : m), 0n);
      const shifted = vals.map(v => v - offset);
      const [bits, slots] = layout(this.pub, shifted.reduce((m, v) => (v > m ? v : m), 0n), shifted.length, RESERVE);
      const plain: bigint[] = [];
      for (let i = 0; i < shifted.length; i += slots) {
        let acc = 0n;
        shifted.slice(i, i + slots).forEach((v, j) => { acc |= v << BigInt(j * bits); });
        plain.push(acc);
      }
      const cts = (await mac.tag(plain)).map(x => hex(encrypt(this.pub, this.priv, x)));
      await this.v2('/api/v2/columns', { column: name, n: hex(this.pub.n), ciphertexts: cts, slots, count: vals.length,
        ...(tags && { ope_tags: tags, tag_macs: await mac.tagMacs(0, tags, slots) }) });
      this.columns.set(name, { scale: sc, slotBits: bits, slots, offset, count: vals.length, macKey: mac.key, ...ope, ...extra,
                               ...(fscale !== sc && { fscale }) });
      ciphertexts ||= cts.length;
    }
    return { ciphertexts };
  }

  /** SUM / COUNT / AVG, optionally only rows with lo <= value <= hi (of `by`, default `column`); decrypted here.
   *  Columns uploaded with squares also give variance and std (ddof=1, as pandas; null for fewer than 2 rows). */
  async query(column: string, lo?: number, hi?: number, by?: string): Promise<QueryAnswer> {
    const cross = by && by !== column;
    const m = this.columns.get(cross ? `${column}|${by}` : column);
    if (!m) throw new Error(cross ? `Filtering ${column} by ${by} needs ${by} encrypted as OPE+Paillier` : `${column} is not encrypted`);
    if (cross) column = `${column}|${by}`;
    const sq = this.columns.has(`${column}^2`);
    const empty: QueryAnswer = { sum: 0, count: 0, avg: 0, ciphertextsUsed: 0, ciphertextBits: [], serverMs: 0, verified: !!m.macKey,
                                 ...(sq && { variance: null, std: null }) };
    let rng: Record<string, string> | null = null;
    if (lo !== undefined || hi !== undefined) {
      if (!m.ope) throw new Error(`Range filters need ${column} encrypted as OPE+Paillier`);
      rng = await this.rangeTags(m, lo, hi);
      if (!rng) return empty;
    }
    const parts = [await this.sum(column, rng)];
    if (sq) parts.push(await this.sum(`${column}^2`, rng));
    const [a, b] = parts;
    const sum = Number(a.total) / m.scale;  // ponytail: exact while |total| < 2^53; BigInt division if columns get bigger
    return {
      sum, count: a.count, avg: a.count ? sum / a.count : 0,
      ...(b && this.spread(column, BigInt(a.count), a.total, b.total, BigInt(b.count))),
      ciphertextsUsed: parts.reduce((t, x) => t + x.ciphertextsUsed, 0), ciphertextBits: parts.flatMap(x => x.ciphertextBits),
      serverMs: parts.reduce((t, x) => t + x.serverMs, 0), verified: !!m.macKey,
    };
  }

  /** Fixed-point total and count of server column `name` over the rows `rng` selects (all without), checked. */
  private async sum(name: string, rng: Record<string, string> | null) {
    const m = this.columns.get(name)!;
    const r = await this.v2('/api/v2/aggregate', { column: name, ...(rng ?? {}) }) as unknown as AggregateResponse;
    const plain = await this.answer(m, name, r, 0, rng);
    const product = r.product ? unhex(r.product) : null;
    const edges = r.edges.map(
      e => [unhex(e.ciphertext), Math.max(0, e.first_slot), Math.min(e.end_slot, m.slots)] as [bigint, number, number]);
    return {
      total: decryptRange(this.priv, product, edges, m.slotBits, m.slots, c => plain.get(c)!) + m.offset * BigInt(r.count),
      count: r.count, ciphertextsUsed: r.ciphertexts_used, serverMs: r.time_ms,
      ciphertextBits: [product, ...edges.map(e => e[0])].filter((x): x is bigint => x !== null).map(bitLength),
    };
  }

  /** Quantiles of a column uploaded with rangeFilter, as pandas computes them (as AgniyaClient.quantiles):
   *  q = 0 is MIN, 0.5 MEDIAN, 1 MAX; optionally only rows with lo <= value <= hi. The column is packed sorted,
   *  so each quantile reads one or two rows, whose ciphertexts are decrypted and checked here. */
  async quantiles(column: string, qs: number[], lo?: number, hi?: number): Promise<QuantileAnswer> {
    const m = this.columns.get(column);
    if (!m?.ope || m.lanes || /[|#]/.test(column)) throw new Error(`${column} is not encrypted as OPE+Paillier (sorted)`);
    const none = (count: number): QuantileAnswer =>
      ({ values: qs.map(() => null), count, ciphertextsUsed: 0, ciphertextBits: [], serverMs: 0, verified: !!m.macKey });
    let rng: Record<string, string> | null = null;
    if (lo !== undefined || hi !== undefined) {
      rng = await this.rangeTags(m, lo, hi);
      if (!rng) return none(0);
    }
    const r = await this.v2('/api/v2/quantiles', { column, q: qs, ...(rng ?? {}) }) as unknown as QuantilesResponse;
    if (rng && m.macKey && !r.rows) {
      throw new Error(`Integrity check failed: the server sent no rows to check ${column} against; update the server`);
    }
    const s = m.slots, plain = new Map<bigint, bigint>(), cells = new Map<number, bigint>();
    let ok = false, i = 0, j = 0;
    try {  // the cells must be exactly the rows these quantiles need, from the stored ciphertexts
      [i, j] = rng ? [Number(r.rows![0]), Number(r.rows![1])] : [0, m.count];
      const want = i < j ? [...new Set(qs.flatMap(q => quantileRows(i, j, q).slice(0, 2)))].sort((a, b) => a - b) : [];
      for (const c of r.cells) cells.set(Number(c.row), unhex(c.ciphertext));
      for (const ct of cells.values()) if (!plain.has(ct)) plain.set(ct, decrypt(this.priv, ct));
      const got = [...cells.keys()].sort((a, b) => a - b);
      ok = r.count === j - i && 0 <= i && i <= j && j <= m.count && got.length === want.length && got.every((x, k) => x === want[k]);
      if (ok && m.macKey) {
        const mac = new ColumnMac(this.pub.n, m.macKey);
        for (const x of want) if (ok) ok = await mac.check(plain.get(cells.get(x)!)!, 0, Math.floor(x / s), 1);
        if (ok && rng) ok = await mac.checkCut(0, s, m.count, i, j, r.witnesses!, BigInt(rng.lo_tag), BigInt(rng.hi_tag));
      }
    } catch {
      ok = false;
    }
    if (!ok) throw new Error(`Integrity check failed: the server's answer for ${column} does not match the uploaded data`);
    if (i === j) return none(0);
    const bits = BigInt(m.slotBits), mask = (1n << bits) - 1n;
    const value = (x: number) => Number(((plain.get(cells.get(x)!)! >> (BigInt(x % s) * bits)) & mask) + m.offset);
    const cts = [...new Set(cells.values())];
    return {
      values: qs.map(q => { const [a, b, f] = quantileRows(i, j, q); return (value(a) + (value(b) - value(a)) * f) / m.scale; }),
      count: j - i, ciphertextsUsed: cts.length, ciphertextBits: cts.map(bitLength), serverMs: r.time_ms, verified: !!m.macKey,
    };
  }

  /** `column` sorted within each group of `by`, stored as "column#by^sorted" (as AgniyaClient.upload_sorted_groups),
   *  for groupQuantiles. Rows missing either are skipped. Labels and group sizes stay here, but reading a quantile
   *  shows the server which ciphertexts hold it, so roughly where each group starts and ends. With `where`
   *  ("column#by^sorted|where"), sorted by where within each group, with OPE tags of (group, where) for ranges. */
  async uploadSortedGroups(column: string, values: Array<number | null>, by: string, byValues: Array<string | null>,
                           decimals: number, where?: string, whereValues?: Array<number | null>,
                           whereDecimals = 0): Promise<{ ciphertexts: number }> {
    if (where === column && !whereValues) [whereValues, whereDecimals] = [values, decimals];
    const scale = 10 ** decimals, fscale = 10 ** whereDecimals, groups = new Map<string, Array<[bigint, bigint]>>();
    values.forEach((a, i) => {
      const g = byValues[i], w = where !== undefined ? whereValues![i] : 0;
      if (a !== null && Number.isFinite(a) && g !== null && g !== '' && w !== null && Number.isFinite(w)) {
        if (!groups.has(g)) groups.set(g, []);
        groups.get(g)!.push([fixedPoint(w, fscale), fixedPoint(a, scale)]);
      }
    });
    if (!groups.size) throw new Error(`No rows have ${column}, ${by}` + (where !== undefined ? ` and ${where}` : ''));
    const labels = [...groups.keys()].sort(), name = `${column}#${by}^sorted` + (where !== undefined ? `|${where}` : '');
    const rows = labels.flatMap((l, gi) => groups.get(l)!.sort((x, y) => cmp(x[0], y[0]) || cmp(x[1], y[1])).map(([w, a]) => [gi, w, a] as const));
    const extra: Partial<ColumnMeta> = { labels, sizes: labels.map(l => groups.get(l)!.length) };
    let keys: bigint[] | null = null;
    if (where !== undefined) {
      const woff = rows.reduce((m, r) => (r[1] < m ? r[1] : m), rows[0][1]);
      const wspan = rows.reduce((m, r) => (r[1] > m ? r[1] : m), rows[0][1]) - woff + 1n;
      Object.assign(extra, { woff, wspan });
      keys = rows.map(([gi, w]) => BigInt(gi) * wspan + w - woff);  // sorted: (group, where)
    }
    const r = await this.put(name, rows.map(x => x[2]), scale, keys, fscale);
    Object.assign(this.columns.get(name)!, extra);
    return r;
  }

  /** Every group's quantiles (q = 0 MIN, 0.5 MEDIAN, 1 MAX; pandas' linear interpolation) of `column` by `by`
   *  (needs uploadSortedGroups): the server sends the ciphertexts holding those rows, checked and decrypted here.
   *  With `where`, only rows with lo <= where <= hi; groups with none are left out. */
  async groupQuantiles(column: string, by: string, qs: number[], lo?: number, hi?: number, where?: string): Promise<GroupQuantileAnswer> {
    const name = `${column}#${by}^sorted` + (where ? `|${where}` : ''), m = this.columns.get(name);
    if (!m?.sizes) throw new Error(`No copy of ${column} sorted within groups of ${by}` + (where ? ` and by ${where}` : ''));
    if (!where && (lo !== undefined || hi !== undefined)) throw new Error('A range needs where (the column it applies to)');
    let spans = new Map<string | number, [number, number]>();
    m.sizes.reduce((i, n, g) => { spans.set(m.labels![g], [i, i + n]); return i + n; }, 0);
    if (where) spans = await this.groupRanges(m, name, spans, lo, hi);
    const inOrder = !where || where === column;  // rows in range sorted by value: read only the quantile rows
    const want = [...new Set([...spans.values()].flatMap(([i, j]) =>
      inOrder ? qs.flatMap(q => quantileRows(i, j, q).slice(0, 2)) : Array.from({ length: j - i }, (_, k) => i + k)))].sort((a, b) => a - b);
    const index = [...new Set(want.map(x => Math.floor(x / m.slots)))];
    const cts: string[] = [];
    let serverMs = 0;
    for (let k = 0; k < index.length; k += 4096) {
      const r = await this.v2('/api/v2/ciphertexts', { column: name, index: index.slice(k, k + 4096) }) as { ciphertexts: string[]; time_ms?: number };
      cts.push(...r.ciphertexts);
      serverMs += r.time_ms ?? 0;
    }
    const bits = BigInt(m.slotBits), mask = (1n << bits) - 1n, plain = new Map<number, bigint>();
    let ok = false;
    try {  // each must be the stored ciphertext at its index
      ok = cts.length === index.length;
      const mac = m.macKey && new ColumnMac(this.pub.n, m.macKey);
      for (let k = 0; ok && k < index.length; k++) {
        const p = decrypt(this.priv, unhex(cts[k]));
        plain.set(index[k], p);
        if (mac) ok = await mac.check(p, 0, index[k], 1);
      }
    } catch {
      ok = false;
    }
    if (!ok) throw new Error(`Integrity check failed: the server's answer for ${name} does not match the uploaded data`);
    const value = (x: number) => Number(((plain.get(Math.floor(x / m.slots))! >> (BigInt(x % m.slots) * bits)) & mask) + m.offset);
    return {
      groups: [...spans].map(([group, [i, j]]) => {
        const sorted = inOrder ? null : Array.from({ length: j - i }, (_, k) => value(i + k)).sort((a, b) => a - b);
        const v = (x: number) => (sorted ? sorted[x - i] : value(x));
        return { group, count: j - i, values: qs.map(q => { const [a, b, f] = quantileRows(i, j, q); return (v(a) + (v(b) - v(a)) * f) / m.scale; }) };
      }),
      ciphertextsUsed: index.length, ciphertextBits: cts.map(c => bitLength(unhex(c))), serverMs, verified: !!m.macKey,
    };
  }

  /** Each group's rows with lo <= where <= hi, from the server and checked (as AgniyaClient._group_ranges). */
  private async groupRanges(m: ColumnMeta, name: string, spans: Map<string | number, [number, number]>,
                            lo?: number, hi?: number): Promise<Map<string | number, [number, number]>> {
    const fs = m.fscale ?? m.scale, span = m.wspan!, top = m.opeTop!;
    let a0 = lo !== undefined ? fixedPoint(lo, fs) - m.woff! : 0n, b0 = hi !== undefined ? fixedPoint(hi, fs) - m.woff! : span - 1n;
    if (a0 < 0n) a0 = 0n;
    if (b0 > span - 1n) b0 = span - 1n;
    const asked: Array<[string | number, bigint, bigint]> = [];
    [...spans.keys()].forEach((label, gi) => {
      let a = BigInt(gi) * span + a0 - m.opeOffset!, b = BigInt(gi) * span + b0 - m.opeOffset!;
      if (a < 0n) a = 0n;
      if (b > top) b = top;
      if (a0 <= b0 && a <= b) asked.push([label, a, b]);
    });
    const out = new Map<string | number, [number, number]>();
    if (!asked.length) return out;
    const tags = await m.ope!.encryptMany(asked.flatMap(([, a, b]) => [a, b]));
    const ranges = asked.map(([, a, b]) => ({ lo_tag: tags.get(a)!.toString(), hi_tag: tags.get(b)!.toString() }));
    const r = await this.v2('/api/v2/ranges', { column: name, ranges }) as { ranges: Array<{ rows: [number, number]; witnesses: Witness[] }> };
    let ok = false;
    try {
      ok = r.ranges.length === asked.length;
      const mac = m.macKey && new ColumnMac(this.pub.n, m.macKey);
      for (let k = 0; ok && k < asked.length; k++) {
        const [i, j] = [Number(r.ranges[k].rows[0]), Number(r.ranges[k].rows[1])], [gi, gj] = spans.get(asked[k][0])!;
        ok = gi <= i && i <= j && j <= gj
          && (!mac || await mac.checkCut(0, m.slots, m.count, i, j, r.ranges[k].witnesses, BigInt(ranges[k].lo_tag), BigInt(ranges[k].hi_tag)));
        if (i < j) out.set(asked[k][0], [i, j]);
      }
    } catch {
      ok = false;
    }
    if (!ok) throw new Error(`Integrity check failed: the server's ranges for ${name} do not match the uploaded data`);
    return out;
  }

  /** Every secret this client holds (primes, OPE keys, column layouts), encrypted with AES-256-GCM under
   *  scrypt(password). Same format as AgniyaClient.save, so either side can load the other's file. */
  async saveKeyFile(password: string): Promise<string> {
    if (!password) throw new Error('A password is required');
    const columns: Record<string, Record<string, unknown>> = {};
    for (const [name, m] of this.columns) {
      const c: Record<string, unknown> = { scale: m.scale, slot_bits: m.slotBits, slots: m.slots,
                                           offset: safeNum(m.offset), count: m.count };
      if (m.fscale !== undefined) c.fscale = m.fscale;
      if (m.labels) Object.assign(c, { lanes: m.lanes, labels: m.labels, pages: m.pages ?? 1 });
      if (m.ope) Object.assign(c, { ope_key: b64(m.ope.key), ope_offset: safeNum(m.opeOffset!), ope_top: safeNum(m.opeTop!) });
      if (m.macKey) c.mac_key = b64(m.macKey);
      if (m.shift !== undefined) c.shift = safeNum(m.shift);
      if (m.sizes) c.sizes = m.sizes;
      if (m.wspan !== undefined) Object.assign(c, { wspan: safeNum(m.wspan), woff: safeNum(m.woff!) });
      columns[name] = c;
    }
    const secret = JSON.stringify({ dataset: this.dataset, p: hex(this.priv.p), q: hex(this.priv.q), columns });
    const salt = webcrypto.getRandomValues(new Uint8Array(16)), nonce = webcrypto.getRandomValues(new Uint8Array(12));
    const header = { format: KEY_FILE_FORMAT, kdf: { name: 'scrypt', ...KEY_SCRYPT, salt: b64(salt) } };
    const ct = await webcrypto.subtle.encrypt(
      { name: 'AES-GCM', iv: nonce, additionalData: new TextEncoder().encode(pyDumpsSorted(header)) },
      await gcmKey(password, salt, KEY_SCRYPT), new TextEncoder().encode(secret));
    return JSON.stringify({ ...header, nonce: b64(nonce), ciphertext: b64(new Uint8Array(ct)) });
  }

  /** Restore a client from a key file written by saveKeyFile or AgniyaClient.save. */
  static async loadKeyFile(text: string, password: string, post: Post): Promise<BrowserClient> {
    const d = JSON.parse(text);
    if (d.format !== KEY_FILE_FORMAT || d.kdf?.name !== 'scrypt') throw new Error('Not an AGNIYA client key file');
    const { n, r, p } = d.kdf;
    if (!(Number.isInteger(n) && n > 1 && (n & (n - 1)) === 0 && n <= 2 ** 20 && r >= 1 && r <= 16 && p >= 1 && p <= 4)) {
      throw new Error('Unsupported scrypt parameters in key file');  // also caps memory use
    }
    let plain: ArrayBuffer;
    try {
      plain = await webcrypto.subtle.decrypt(
        { name: 'AES-GCM', iv: unb64(d.nonce), additionalData: new TextEncoder().encode(pyDumpsSorted({ format: d.format, kdf: d.kdf })) },
        await gcmKey(password, unb64(d.kdf.salt), d.kdf), unb64(d.ciphertext));
    } catch {
      throw new Error('Wrong password or modified key file');
    }
    const s = JSON.parse(new TextDecoder().decode(plain));
    const client = new BrowserClient(post, s.dataset, keypairFromPrimes(unhex(s.p), unhex(s.q)));
    for (const [name, c] of Object.entries(s.columns as Record<string, Record<string, number | string>>)) {
      const meta: ColumnMeta = { scale: c.scale as number, slotBits: c.slot_bits as number, slots: c.slots as number,
                                 offset: BigInt(c.offset), count: (c.count as number) ?? 0 };
      if (c.fscale !== undefined) meta.fscale = c.fscale as number;
      if (c.labels !== undefined) {
        meta.lanes = c.lanes as number;
        meta.labels = c.labels as unknown as Array<string | number>;
        meta.pages = (c.pages as number | undefined) ?? 1;  // files from before pages: one
      }
      if (c.mac_key !== undefined) meta.macKey = unb64(c.mac_key as string);
      if (c.shift !== undefined) meta.shift = BigInt(c.shift);
      if (c.sizes !== undefined) meta.sizes = c.sizes as unknown as number[];
      if (c.wspan !== undefined) [meta.wspan, meta.woff] = [BigInt(c.wspan), BigInt(c.woff)];
      if (c.ope_key !== undefined) {
        meta.ope = new OPE(unb64(c.ope_key as string), BigInt(c.ope_top));
        meta.opeOffset = BigInt(c.ope_offset);
        meta.opeTop = BigInt(c.ope_top);
      }
      client.columns.set(name, meta);
    }
    return client;
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
