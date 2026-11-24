/*
 * Web Worker that owns the BrowserClient: key generation, encryption, OPE tagging, the
 * /api/v2 calls and decryption all run here, off the page's main thread. The private key
 * and OPE keys exist only in this worker; the page sees query answers.
 * Message protocol: { id, op: 'init' | 'load' | 'upload' | 'uploadBy' | 'uploadGrouped' | 'save' | 'query' | 'queryGroups' | 'quantiles' | 'uploadSortedGroups' | 'groupQuantiles', args } -> { id, result } | { id, error }.
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
    } else if (op === 'load') {
      client = await BrowserClient.loadKeyFile(args.text as string, args.password as string, httpPost(args.baseUrl as string));
      result = { dataset: client.dataset, columns: [...client.columns].map(([name, m]) =>
        ({ name, count: m.count, scale: m.scale, rangeFilter: !!m.ope })) };
    } else if (!client) {
      throw new Error('Worker not initialised');
    } else if (op === 'upload') {
      result = await client.upload(args.column as string, args.values as number[], args.decimals as number,
                                   args.rangeFilter as boolean, args.squares as boolean);
    } else if (op === 'uploadBy') {
      result = await client.uploadBy(args.column as string, args.values as Array<number | null>, args.by as string,
                                     args.byValues as Array<number | null>, args.decimals as number, args.byDecimals as number,
                                     args.squares as boolean);
    } else if (op === 'uploadGrouped') {
      result = await client.uploadGrouped(args.column as string, args.values as Array<number | null>, args.by as string,
                                          args.byValues as Array<string | null>, args.decimals as number,
                                          args.where as string | undefined, args.whereValues as Array<number | null> | undefined,
                                          args.whereDecimals as number | undefined, args.squares as boolean);
    } else if (op === 'queryGroups') {
      const where = args.where as string | undefined, name = `${args.column}#${args.by}` + (where ? `|${where}` : '');
      const answer = await client.queryGroups(args.column as string, args.by as string, args.lo as number | undefined,
                                              args.hi as number | undefined, where);
      result = { ...answer, total: client.columns.get(name)?.count ?? 0 };
    } else if (op === 'quantiles') {
      const column = args.column as string;
      const answer = await client.quantiles(column, args.qs as number[], args.lo as number | undefined, args.hi as number | undefined);
      result = { ...answer, total: client.columns.get(column)!.count };
    } else if (op === 'uploadSortedGroups') {
      result = await client.uploadSortedGroups(args.column as string, args.values as Array<number | null>, args.by as string,
                                               args.byValues as Array<string | null>, args.decimals as number);
    } else if (op === 'groupQuantiles') {
      const answer = await client.groupQuantiles(args.column as string, args.by as string, args.qs as number[]);
      result = { ...answer, total: client.columns.get(`${args.column}#${args.by}^sorted`)!.count };
    } else if (op === 'save') {
      result = { text: await client.saveKeyFile(args.password as string), dataset: client.dataset };
    } else if (op === 'query') {
      const column = args.column as string, by = args.by as string | undefined;
      const answer = await client.query(column, args.lo as number | undefined, args.hi as number | undefined, by);
      result = { ...answer, total: client.columns.get(by && by !== column ? `${column}|${by}` : column)!.count };
    } else {
      throw new Error(`Unknown op ${op}`);
    }
    self.postMessage({ id, result });
  } catch (err) {
    self.postMessage({ id, error: err instanceof Error ? err.message : String(err) });
  }
};
