// Page-side handle to lib/agniya-worker.ts: one worker = one key pair. terminate() drops the key.
import type { QueryAnswer } from './agniya-browser';

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

  query(column: string, lo?: number, hi?: number) { return this.call<WorkerAnswer>('query', { column, lo, hi }); }

  terminate() { this.worker.terminate(); }
}
