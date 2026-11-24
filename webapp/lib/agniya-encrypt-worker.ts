/*
 * Helper worker started by agniya-worker.ts to encrypt in parallel: { id, p, q, plains } -> { id, cts } (hex).
 * It gets the primes from its parent worker and dies with it, so the key still never leaves this browser tab.
 */
import { encrypt, keypairFromPrimes } from './agniya-browser';

let keys: ReturnType<typeof keypairFromPrimes> | null = null;
let forP = '';

self.onmessage = (e: MessageEvent<{ id: number; p: string; q: string; plains: string[] }>) => {
  const { id, p, q, plains } = e.data;
  if (forP !== p) [keys, forP] = [keypairFromPrimes(BigInt(p), BigInt(q)), p];
  self.postMessage({ id, cts: plains.map(x => encrypt(keys!.pub, keys!.priv, BigInt(x)).toString(16)) });
};
