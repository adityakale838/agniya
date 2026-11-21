/*
 * Web Worker that owns the BrowserClient: key generation, encryption, OPE tagging, the
 * /api/v2 calls and decryption all run here, off the page's main thread. The private key
 * and OPE keys exist only in this worker; the page sees query answers.
 * Message protocol: { id, op: 'init' | 'upload' | 'query', args } -> { id, result } | { id, error }.
 */
import { BrowserClient, httpPost } from './agniya-browser';

let client: BrowserClient | null = null;

self.onmessage = async (e: MessageEvent<{ id: number; op: string; args: Record<string, unknown> }>) => {
  const { id, op, args } = e.data;
  try {
    let result: unknown;
    if (op === 'init') {
      client = new BrowserClient(httpPost(args.baseUrl as string), args.dataset as string);
      result = { modulusBits: client.pub.n.toString(2).length };
    } else if (!client) {
      throw new Error('Worker not initialised');
    } else if (op === 'upload') {
      result = await client.upload(args.column as string, args.values as number[], args.decimals as number,
                                   args.rangeFilter as boolean);
    } else if (op === 'query') {
      const column = args.column as string;
      const answer = await client.query(column, args.lo as number | undefined, args.hi as number | undefined);
      result = { ...answer, total: client.columns.get(column)!.count };
    } else {
      throw new Error(`Unknown op ${op}`);
    }
    self.postMessage({ id, result });
  } catch (err) {
    self.postMessage({ id, error: err instanceof Error ? err.message : String(err) });
  }
};
