// Page-side handle to lib/agniya-worker.ts: one worker = one key pair. terminate() drops the key.
import type { GroupAnswer, QueryAnswer } from './agniya-browser';

export type WorkerAnswer = QueryAnswer & { total: number };

export class CryptoWorker {
  private readonly worker: Worker;
  private nextId = 0;
  private readonly pending = new Map<number, { resolve: (v: unknown) => void; reject: (e: Error) => void }>();

  constructor() {
    this.worker = new Worker(new URL('./agniya-worker.ts', import.meta.url), { type: 'module' });
    this.worker.onmessage = (e: MessageEvent<{ id: number; result?: unknown; error?: string }>) => {
      const p = this.pending.get(e.data.id);
      this.pending.delete(e.data.id);
      if (e.data.error !== undefined) p?.reject(new Error(e.data.error)); else p?.resolve(e.data.result);
    };
    this.worker.onerror = e => {  // e.g. the worker script failed to load
      this.pending.forEach(p => p.reject(new Error(e.message || 'Crypto worker failed')));
      this.pending.clear();
    };
  }

  private call<T>(op: string, args: Record<string, unknown>): Promise<T> {
    const id = this.nextId++;
    return new Promise<T>((resolve, reject) => {
      this.pending.set(id, { resolve: resolve as (v: unknown) => void, reject });
      this.worker.postMessage({ id, op, args });
    });
  }

  init(baseUrl: string, dataset: string) { return this.call<{ modulusBits: number }>('init', { baseUrl, dataset }); }

  upload(column: string, values: number[], decimals: number, rangeFilter: boolean) {
    return this.call<{ ciphertexts: number }>('upload', { column, values, decimals, rangeFilter });
  }

  /** Copy of `column` in `by` order for SUM(column) WHERE by in range; values[i], byValues[i] are one row. */
  uploadBy(column: string, values: Array<number | null>, by: string, byValues: Array<number | null>,
           decimals: number, byDecimals: number) {
    return this.call<{ ciphertexts: number }>('uploadBy', { column, values, by, byValues, decimals, byDecimals });
  }

  /** Copy of `column` packed by the labels in byValues (one per row) for GROUP BY `by`; with `where`,
   *  packed in whereValues order so queryGroups can also filter lo <= where <= hi. */
  uploadGrouped(column: string, values: Array<number | null>, by: string, byValues: Array<string | null>, decimals: number,
                where?: string, whereValues?: Array<number | null>, whereDecimals?: number) {
    return this.call<{ ciphertexts: number }>('uploadGrouped', { column, values, by, byValues, decimals, where, whereValues, whereDecimals });
  }

  queryGroups(column: string, by: string, lo?: number, hi?: number, where?: string) {
    return this.call<GroupAnswer & { total: number }>('queryGroups', { column, by, lo, hi, where });
  }

  query(column: string, lo?: number, hi?: number, by?: string) {
    return this.call<WorkerAnswer>('query', { column, lo, hi, by });
  }

  /** Encrypted key file text (scrypt + AES-256-GCM, same format as the Python client). */
  save(password: string) { return this.call<{ text: string; dataset: string }>('save', { password }); }

  /** Restore keys from a key file; this worker then answers queries on that dataset. */
  load(baseUrl: string, text: string, password: string) {
    return this.call<{ dataset: string; columns: Array<{ name: string; count: number; scale: number; rangeFilter: boolean }> }>(
      'load', { baseUrl, text, password });
  }

  terminate() { this.worker.terminate(); }
}
