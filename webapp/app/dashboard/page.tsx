'use client';

import { useState, useRef, useEffect } from 'react';
import { AlertCircle, ArrowRight, ChevronDown, KeyRound, Lock, Play, Upload } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import Link from 'next/link';
import { Sheet, SheetHeader, inkButton, navLink, paperButton } from '@/components/paper';
import { apiService, API_BASE_URL } from '@/lib/api';
import { parseCsv, type Spread } from '@/lib/agniya-browser';
import { CryptoWorker } from '@/lib/agniya-worker-client';

const PAILLIER: string[] = ['Paillier-2048', 'OPE+Paillier'];
type Aggregate = 'SUM' | 'AVG' | 'COUNT';  // GROUP BY and SUM paths: order statistics are routed before them
type Operation = Aggregate | 'MIN' | 'MAX' | 'MEDIAN' | 'VARIANCE' | 'STDDEV';
const ORDER_STATS: Partial<Record<Operation, number>> = { MIN: 0, MEDIAN: 0.5, MAX: 1 };  // quantile q
const SPREAD: Operation[] = ['VARIANCE', 'STDDEV'];  // need a "^2" copy (sum of squares), built on first use
const GROUP_MAX_VALUES = 64;

/** One-click questions a bank asks of its customer data (columns of data/bank_customers.csv, from
 *  tools/make_bank_data.py); each runs as an ordinary encrypted query. */
interface Preset { title: string; op: Operation; field: string; group?: string; group2?: string; filter?: string; min?: string; max?: string }
const BANK_PRESETS: Preset[] = [
  { title: 'Loan exposure by risk band', op: 'SUM', field: 'loan_amount', group: 'risk_band' },
  { title: 'Default rate by segment', op: 'AVG', field: 'default_flag', group: 'segment' },
  { title: 'Median balance by region', op: 'MEDIAN', field: 'balance', group: 'region' },
  { title: 'Spend volatility by segment', op: 'STDDEV', field: 'monthly_spend', group: 'segment' },
  { title: 'Sub-prime exposure by product', op: 'SUM', field: 'loan_amount', group: 'product', filter: 'credit_score', min: '300', max: '600' },
  { title: 'Loan exposure by region and segment', op: 'SUM', field: 'loan_amount', group: 'region', group2: 'segment' },
];
const presetSql = (p: Preset) => `${p.op}(${p.field})` + (p.filter ? ` WHERE ${p.filter} BETWEEN ${p.min} AND ${p.max}` : '')
  + (p.group ? ` GROUP BY ${p.group}${p.group2 ? `, ${p.group2}` : ''}` : '');  // as api/server_optimized.py: GROUP BY copies for columns with 2-64 distinct values

/** {field: [group columns]} from stored column names, where "a#g" is a packed by g ("a#g|w" also filters on w). */
const groupsFromNames = (names: string[]): Record<string, string[]> => {
  const out: Record<string, string[]> = {};
  for (const n of names) {
    const i = n.indexOf('#');
    if (i > 0 && !/[|@^]/.test(n.slice(i))) (out[n.slice(0, i)] ??= []).push(n.slice(i + 1));  // "@p": later pages, "^2": squares
  }
  return out;
};

interface Field {
  name: string;
  type: string;
  encryption: 'Plaintext' | 'AES-256' | 'Paillier-2048' | 'OPE+Paillier';
}

interface UploadedData {
  filename: string;
  records: number;
  fields: number;
  schema: Field[];
  sample_data?: Record<string, unknown>[];
}

interface EncryptionResult {
  success?: boolean;
  message?: string;
  records_encrypted?: number;
  time_seconds?: number;
  throughput?: number;
  ciphertexts?: number;
}

interface QueryResult {
  operation?: string;
  field?: string;
  result?: number | null;  // null: MIN / MAX / MEDIAN of no rows
  time_ms?: number;
  setup_ms?: number;  // first use only: building the encrypted copy this query needs, not counted in time_ms
  count_note?: string;  // a plain COUNT on the server: the stored row count, nothing decrypted
  records_processed?: number;
  // New fields from advanced server
  success?: boolean;
  column?: string;
  query_time_ms?: number;
  ciphertexts_aggregated?: number;
  filter_applied?: boolean;
  filter_column?: string;
  group_by?: string;
  groups?: Array<{ group: string | number; sum?: number; count: number; avg?: number; result: number | null }>;
  range?: { min: number | null; max: number | null };
  records_before_filter?: number;
  filter_selectivity?: number;
  security_note?: string;
  query_plan?: {
    strategy: string;
    estimated_cost_ms: number | null;
    actual_cost_ms: number;
    estimated_rows: number | null;
  };
  encryption_proof?: {
    ciphertext_samples: string[];
    ciphertext_bit_lengths: number[];
    modulus_n_bit_length: number;
    verification: string;
    computation_type: string;
    encrypted_result_preview?: string;
    encrypted_result_bit_length?: number;
    note?: string;
  };
}

export default function Dashboard() {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isEncrypting, setIsEncrypting] = useState(false);
  const [uploadData, setUploadData] = useState<UploadedData | null>(null);
  const [encryptionResult, setEncryptionResult] = useState<EncryptionResult | null>(null);
  const [schema, setSchema] = useState<Field[]>([]);
  const [activeTab, setActiveTab] = useState('upload');
  
  // Query state
  const [queries, setQueries] = useState<QueryResult[]>([]);
  const [isQuerying, setIsQuerying] = useState(false);
  const [selectedField, setSelectedField] = useState('');
  const [selectedOperation, setSelectedOperation] = useState<Operation>('SUM');
  const [rangeMin, setRangeMin] = useState('');
  const [rangeMax, setRangeMax] = useState('');
  const [filterBy, setFilterBy] = useState('');  // '' = filter on the queried field itself
  const [groupBy, setGroupBy] = useState('');  // '' = no GROUP BY
  const [groupBy2, setGroupBy2] = useState('');  // optional second GROUP BY column
  const [groupable, setGroupable] = useState<Record<string, string[]>>({});  // field -> columns it can be grouped by
  const groupOptions = groupable[selectedField] ?? [];
  const thenOptions = groupOptions.filter(g => g !== groupBy && !g.includes(','));
  // "a,b" = GROUP BY a, b: one label "x, y" per row, packed like any GROUP BY copy (built on first use)
  const activeGroupBy = !groupOptions.includes(groupBy) ? ''
    : thenOptions.includes(groupBy2) && !groupBy.includes(',') ? `${groupBy},${groupBy2}` : groupBy;

  const [error, setError] = useState<string | null>(null);

  // Browser mode: the CSV is parsed here and encrypted in a Web Worker that holds the keys (/api/v2).
  const [browserMode, setBrowserMode] = useState(true);
  const csvRef = useRef<{ header: string[]; rows: string[][] } | null>(null);
  const workerRef = useRef<CryptoWorker | null>(null);
  const groupCopies = useRef(new Set<string>());
  const byCopies = useRef(new Set<string>());  // "a|b" copies (a in b's order, for WHERE b in range)  // "a#g" GROUP BY copies the worker has (g may be "b,c")
  const filteredCopies = useRef(new Set<string>());  // "a#g|w" copies the worker has (GROUP BY g WHERE w in range)
  const squareCopies = useRef(new Set<string>());  // copies that also have "^2" (VARIANCE / STDDEV)
  const sortedCopies = useRef(new Set<string>());  // "a#g^sorted" (and "...|w") copies: MIN / MAX / MEDIAN GROUP BY g

  const dropWorker = () => { workerRef.current?.terminate(); workerRef.current = null; };  // drops the key
  useEffect(() => () => workerRef.current?.terminate(), []);  // leaving the page drops the key too
  const [presetRun, setPresetRun] = useState(0);  // a preset sets the builder, then this runs the query

  // Key file: the worker encrypts its keys under scrypt(password) + AES-GCM (same format as agniya/client.py).
  const [keyPassword, setKeyPassword] = useState('');
  const [keyBusy, setKeyBusy] = useState(false);
  const [restoreFile, setRestoreFile] = useState<File | null>(null);

  const downloadKeyFile = async () => {
    if (!workerRef.current) return;
    setKeyBusy(true); setError(null);
    try {
      const { text, dataset } = await workerRef.current.save(keyPassword);
      const url = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `${dataset}.agniya-key`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setKeyPassword('');
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setKeyBusy(false);
    }
  };

  const restoreFromKeyFile = async () => {
    if (!restoreFile) return;
    setKeyBusy(true); setError(null);
    const worker = new CryptoWorker();
    try {
      const info = await worker.load(API_BASE_URL, await restoreFile.text(), keyPassword);
      dropWorker();
      workerRef.current = worker;
      // "a|b" = copy of a in b order, "a#g" = a packed by group g (Python client): not fields of their own
      const restored: Field[] = info.columns.filter(c => !/[|#^]/.test(c.name)).map(c => ({
        name: c.name, type: c.scale === 1 ? 'int' : 'float', encryption: c.rangeFilter ? 'OPE+Paillier' : 'Paillier-2048' }));
      // GROUP BY copies "a#g" count whole ciphertexts (padding included), not rows
      const records = Math.max(0, ...info.columns.filter(c => !/#[^|]*$/.test(c.name)).map(c => c.count));
      setUploadData({ filename: info.dataset, records, fields: restored.length, schema: restored });
      setSchema(restored);
      setEncryptionResult({ success: true, records_encrypted: records, message: 'Restored from key file' });
      setQueries([]);
      setSelectedField(restored[0]?.name ?? ''); setFilterBy(''); setGroupBy(''); setGroupBy2('');
      setGroupable(groupsFromNames(info.columns.map(c => c.name)));
      filteredCopies.current = new Set(info.columns.map(c => c.name).filter(n => /#.*\|/.test(n) && !n.endsWith('^2')));
      groupCopies.current = new Set(info.columns.map(c => c.name).filter(n => /#[^|@^]*$/.test(n)));
      byCopies.current = new Set(info.columns.map(c => c.name).filter(n => /^[^#^]*\|[^#^]*$/.test(n)));
      squareCopies.current = new Set(info.columns.map(c => c.name).filter(n => n.endsWith('^2')).map(n => n.slice(0, -2)));
      sortedCopies.current = new Set(info.columns.map(c => c.name).filter(n => n.includes('^sorted')));
      setKeyPassword(''); setRestoreFile(null);
      setActiveTab('query');
    } catch (err) {
      worker.terminate();
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setKeyBusy(false);
    }
  };

  const switchMode = (browser: boolean) => {
    setBrowserMode(browser);
    setFile(null); setUploadData(null); setEncryptionResult(null); setSchema([]); setQueries([]);
    setSelectedField(''); setRangeMin(''); setRangeMax(''); setFilterBy(''); setGroupBy(''); setGroupBy2(''); setGroupable({});
    csvRef.current = null;
    dropWorker();
    setActiveTab('upload');
  };

  const decimalsOf = (name: string) => (columnValues(name).every(Number.isInteger) ? 0 : 4);  // as encryptLocally
  const columnValues = (name: string): number[] => {
    const { header, rows } = csvRef.current!;
    const i = header.indexOf(name);
    return rows.map(r => (r[i] ?? '').trim()).filter(v => v !== '').map(Number);
  };

  /** One entry per CSV row (null where empty), so two columns line up row by row. */
  const rowValues = (name: string): Array<number | null> => {
    const { header, rows } = csvRef.current!;
    const i = header.indexOf(name);
    return rows.map(r => ((r[i] ?? '').trim() === '' ? null : Number(r[i])));
  };

  /** Raw CSV labels, one per row (null where empty), for GROUP BY. */
  /** One label per row; for "a,b" (GROUP BY several columns) "x, y", or null when a part is missing. */
  const rowLabels = (name: string): Array<string | null> => {
    const { header, rows } = csvRef.current!;
    const idx = name.split(',').map(n => header.indexOf(n));
    return rows.map(r => {
      const parts = idx.map(i => (r[i] ?? '').trim());
      return parts.every(Boolean) ? parts.join(', ') : null;
    });
  };

  const parseLocally = async (f: File): Promise<UploadedData> => {
    const csv = parseCsv(await f.text());
    csvRef.current = csv;
    const schema: Field[] = csv.header.map(name => {
      const vals = columnValues(name);
      const numeric = vals.length > 0 && vals.every(Number.isFinite);
      const integer = numeric && vals.every(Number.isInteger);
      const id = ['id', 'user_id', 'customer_id'].includes(name.toLowerCase());
      return { name, type: integer ? 'int' : numeric ? 'float' : 'str',
               encryption: id ? 'Plaintext' : numeric ? 'Paillier-2048' : 'AES-256' };
    });
    const sample_data = csv.rows.slice(0, 3).map(r => Object.fromEntries(csv.header.map((h, i) => [h, r[i] ?? ''])));
    return { filename: f.name, records: csv.rows.length, fields: csv.header.length, schema, sample_data };
  };

  const encryptLocally = async (): Promise<EncryptionResult> => {
    const t0 = performance.now();
    const fields = schema.filter(f => PAILLIER.includes(f.encryption));
    if (!fields.length) throw new Error('Choose Paillier-2048 or OPE+Paillier for at least one numeric field.');
    dropWorker();  // re-encrypting starts a fresh key pair
    const worker = new CryptoWorker();
    workerRef.current = worker;
    filteredCopies.current = new Set();
    groupCopies.current = new Set();
    byCopies.current = new Set();
    squareCopies.current = new Set();
    sortedCopies.current = new Set();
    await worker.init(API_BASE_URL, `${uploadData!.filename}-${crypto.randomUUID().slice(0, 8)}`);
    let ciphertexts = 0;
    const decimals: Record<string, number> = {};
    for (const f of fields) {
      const vals = columnValues(f.name);
      if (!vals.every(Number.isFinite)) throw new Error(`${f.name} is not numeric`);
      decimals[f.name] = vals.every(Number.isInteger) ? 0 : 4;
      ciphertexts += (await worker.upload(f.name, vals, decimals[f.name], f.encryption === 'OPE+Paillier')).ciphertexts;
    }
    // Copies for "WHERE other column in range" and GROUP BY (columns with 2-64 distinct values) are built
    // the first time a query needs them: building every pair up front made encryption slow on wide tables.
    const groupCols = csvRef.current!.header.filter(g => {
      const n = new Set(rowLabels(g).filter(v => v !== null)).size;
      return n >= 2 && n <= GROUP_MAX_VALUES;
    });
    setGroupable(Object.fromEntries(fields.map(a => [a.name, groupCols.filter(g => g !== a.name)])));
    const secs = (performance.now() - t0) / 1000;
    const records = csvRef.current!.rows.length;
    return { success: true, records_encrypted: records, time_seconds: secs, throughput: records / secs, ciphertexts };
  };

  /** GROUP BY several columns: at most GROUP_MAX_VALUES label combinations, as on the server. */
  const checkGroups = () => {
    const n = new Set(rowLabels(activeGroupBy).filter(v => v !== null)).size;
    if (n > GROUP_MAX_VALUES) throw new Error(`GROUP BY ${activeGroupBy.replace(',', ', ')} has ${n} groups; up to ${GROUP_MAX_VALUES} are supported`);
  };

  const queryGroupsLocally = async (minVal?: number, maxVal?: number): Promise<QueryResult> => {
    const worker = workerRef.current!, fc = filterBy || selectedField;
    const filtered = minVal !== undefined || maxVal !== undefined;
    const spread = SPREAD.includes(selectedOperation);
    const copy = `${selectedField}#${activeGroupBy}` + (filtered ? `|${fc}` : '');
    const s0 = performance.now();
    if (filtered ? !filteredCopies.current.has(copy) || (spread && !squareCopies.current.has(copy))
                 : !groupCopies.current.has(copy) || (spread && !squareCopies.current.has(copy))) {
      // A copy packed in fc order (and/or with squares), built on first use: one per field x group x filter up front would be too many.
      if (!csvRef.current) throw new Error(`${filtered ? `GROUP BY ${activeGroupBy} with a range on ${fc}` : selectedOperation} needs the CSV: upload it and encrypt again`);
      checkGroups();
      await worker.uploadGrouped(selectedField, rowValues(selectedField), activeGroupBy, rowLabels(activeGroupBy), decimalsOf(selectedField),
                                 filtered ? fc : undefined, filtered ? rowValues(fc) : undefined, filtered ? decimalsOf(fc) : 0, spread);
      if (filtered) filteredCopies.current.add(copy); else groupCopies.current.add(copy);
      if (spread) squareCopies.current.add(copy);
    }
    const t0 = performance.now(), setup_ms = t0 - s0;
    const a = await worker.queryGroups(selectedField, activeGroupBy, minVal, maxVal, filtered ? fc : undefined);
    const pick = (g: Spread & { sum: number; count: number; avg: number }) =>
      ({ SUM: g.sum, AVG: g.avg, COUNT: g.count, VARIANCE: g.variance ?? null, STDDEV: g.std ?? null })[selectedOperation as Aggregate | 'VARIANCE' | 'STDDEV'];
    const sum = a.groups.reduce((s, g) => s + g.sum, 0), count = a.groups.reduce((s, g) => s + g.count, 0);
    return {
      operation: selectedOperation, field: selectedField, column: selectedField, group_by: activeGroupBy,
      groups: a.groups.map(g => ({ ...g, result: pick(g) })),
      result: spread ? null : pick({ sum, count, avg: count ? sum / count : 0 }),  // per group only
      time_ms: performance.now() - t0, setup_ms, records_processed: count, ciphertexts_aggregated: a.ciphertextsUsed,
      ...(filtered && { filter_applied: true, filter_column: fc, range: { min: minVal ?? null, max: maxVal ?? null },
                        records_before_filter: a.total, filter_selectivity: a.total ? count / a.total : 0 }),
      security_note: (filtered
        ? `The server compared OPE tags of ${fc} (it learns their order) and multiplied ciphertexts; this browser decrypted the product once plus the <=2 edge ciphertexts`
        : 'One product of the ciphertexts, one decryption in this browser')
        + (a.pages > 1 ? ` for each of ${a.pages} pages of groups (they do not share one plaintext)` : '')
        + (filtered ? '. ' : ': every group sum and count comes out of its own slots. ') + 'The server never saw the labels.',
      encryption_proof: {
        ciphertext_samples: [], ciphertext_bit_lengths: a.ciphertextBits, modulus_n_bit_length: 2048,
        verification: `Server multiplied ${a.ciphertextsUsed} ciphertexts in ${a.serverMs} ms without any key; decrypted in this browser`
          + (a.verified ? ', which also checked the integrity tags: this is the honest result over the uploaded data' : ''),
        computation_type: 'Paillier homomorphic addition',
      },
    };
  };

  const queryOrderLocally = async (minVal?: number, maxVal?: number): Promise<QueryResult> => {
    const t0 = performance.now();
    const a = await workerRef.current!.quantiles(selectedField, [ORDER_STATS[selectedOperation]!], minVal, maxVal);
    const filtered = minVal !== undefined || maxVal !== undefined;
    return {
      operation: selectedOperation, field: selectedField, column: selectedField, filter_column: selectedField,
      result: a.values[0], time_ms: performance.now() - t0, records_processed: a.count, ciphertexts_aggregated: a.ciphertextsUsed,
      filter_applied: filtered, range: { min: minVal ?? null, max: maxVal ?? null },
      records_before_filter: a.total, filter_selectivity: a.total ? a.count / a.total : 0,
      security_note: `${selectedField} is packed in sorted order, so the server sent the ciphertext holding that row`
        + ' (two for an interpolated median) and this browser decrypted it, which also shows the other values in it. OPE tags reveal the order of values.',
      encryption_proof: {
        ciphertext_samples: [], ciphertext_bit_lengths: a.ciphertextBits, modulus_n_bit_length: 2048,
        verification: `Server picked ${a.ciphertextsUsed} ciphertext(s) by sorted position in ${a.serverMs} ms without any key; decrypted in this browser`
          + (a.verified ? ', which also checked the integrity tags: this is the honest result over the uploaded data' : ''),
        computation_type: 'Order statistic on a sorted packed column',
      },
    };
  };

  const queryOrderGroupsLocally = async (minVal?: number, maxVal?: number): Promise<QueryResult> => {
    const worker = workerRef.current!, fc = filterBy || selectedField;
    const filtered = minVal !== undefined || maxVal !== undefined;
    const copy = `${selectedField}#${activeGroupBy}^sorted` + (filtered ? `|${fc}` : '');
    const s0 = performance.now();
    if (!sortedCopies.current.has(copy)) {  // a copy sorted within each group (by fc with a range), built on first use
      if (!csvRef.current) throw new Error(`${selectedOperation} GROUP BY ${activeGroupBy} needs the CSV: upload it and encrypt again`);
      checkGroups();
      await worker.uploadSortedGroups(selectedField, rowValues(selectedField), activeGroupBy, rowLabels(activeGroupBy), decimalsOf(selectedField),
                                      filtered ? fc : undefined, filtered ? rowValues(fc) : undefined, filtered ? decimalsOf(fc) : 0);
      sortedCopies.current.add(copy);
    }
    const t0 = performance.now(), setup_ms = t0 - s0;
    const a = await worker.groupQuantiles(selectedField, activeGroupBy, [ORDER_STATS[selectedOperation]!], minVal, maxVal,
                                          filtered ? fc : undefined);
    return {
      operation: selectedOperation, field: selectedField, column: selectedField, group_by: activeGroupBy,
      groups: a.groups.map(g => ({ group: g.group, count: g.count, result: g.values[0] })), result: null,
      time_ms: performance.now() - t0, setup_ms, records_processed: a.groups.reduce((n, g) => n + g.count, 0), ciphertexts_aggregated: a.ciphertextsUsed,
      ...(filtered && { filter_applied: true, filter_column: fc, range: { min: minVal ?? null, max: maxVal ?? null },
                        records_before_filter: a.total, filter_selectivity: a.total ? a.groups.reduce((n, g) => n + g.count, 0) / a.total : 0 }),
      security_note: `A copy of ${selectedField} sorted within each group` + (filtered ? ` (by ${fc}, with OPE tags of group and ${fc})` : '') + `: the server sent the ciphertexts holding each group's answer`
        + ' and this browser decrypted them. The labels and group sizes stay here, but the server sees which ciphertexts were read, so roughly where groups start and end.',
      encryption_proof: {
        ciphertext_samples: [], ciphertext_bit_lengths: a.ciphertextBits.slice(0, 3), modulus_n_bit_length: 2048,
        verification: `Server sent ${a.ciphertextsUsed} stored ciphertext(s) without any key; decrypted in this browser`
          + (a.verified ? ', which also checked the integrity tags: this is the honest result over the uploaded data' : ''),
        computation_type: 'Order statistic per group on a copy sorted within groups',
      },
    };
  };

  const queryLocally = async (minVal?: number, maxVal?: number): Promise<QueryResult> => {
    const fc = filterBy || selectedField, worker = workerRef.current!;
    const cross = fc !== selectedField, spread = SPREAD.includes(selectedOperation);
    const copy = cross ? `${selectedField}|${fc}` : selectedField;
    const s0 = performance.now();
    if ((cross && !byCopies.current.has(copy)) || (spread && !squareCopies.current.has(copy))) {
      // built on first use: a copy in fc's order and/or the "^2" copy (re-uploads the column with it)
      if (!csvRef.current) throw new Error(`${cross ? `Filtering ${selectedField} by ${fc}` : selectedOperation} needs the CSV: upload it and encrypt again`);
      if (cross) {
        await worker.uploadBy(selectedField, rowValues(selectedField), fc, rowValues(fc), decimalsOf(selectedField), decimalsOf(fc), spread);
        byCopies.current.add(copy);
      } else {
        await worker.upload(selectedField, columnValues(selectedField), decimalsOf(selectedField),
                            schema.find(f => f.name === selectedField)?.encryption === 'OPE+Paillier', true);
      }
      if (spread) squareCopies.current.add(copy);
    }
    const t0 = performance.now(), setup_ms = t0 - s0;
    const a = await worker.query(selectedField, minVal, maxVal, fc);
    const time_ms = performance.now() - t0;
    const total = a.total;
    const filtered = minVal !== undefined || maxVal !== undefined;
    return {
      operation: selectedOperation, field: selectedField, column: selectedField, filter_column: fc,
      result: { SUM: a.sum, AVG: a.avg, COUNT: a.count, VARIANCE: a.variance ?? null, STDDEV: a.std ?? null }[
        selectedOperation as Aggregate | 'VARIANCE' | 'STDDEV'],
      time_ms, setup_ms, records_processed: a.count, ciphertexts_aggregated: a.ciphertextsUsed,
      filter_applied: filtered, range: { min: minVal ?? null, max: maxVal ?? null },
      records_before_filter: total, filter_selectivity: total ? a.count / total : 0,
      security_note: 'The server compared OPE tags (it learns their order) and multiplied ciphertexts; the edge ciphertexts were decrypted in this browser.',
      encryption_proof: {
        ciphertext_samples: [], ciphertext_bit_lengths: a.ciphertextBits.slice(0, 3), modulus_n_bit_length: 2048,
        verification: `Server multiplied ${a.ciphertextsUsed} ciphertexts in ${a.serverMs} ms without any key; decrypted in this browser`
          + (a.verified ? ', which also checked the integrity tags: this is the honest result over the uploaded data' : ''),
        computation_type: 'Paillier homomorphic addition',
      },
    };
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && (droppedFile.type === 'text/csv' || droppedFile.name.toLowerCase().endsWith('.csv'))) {
      setFile(droppedFile);
      handleUpload(droppedFile);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      handleUpload(selectedFile);
    }
  };

  const handleUpload = async (fileToUpload: File) => {
    setIsUploading(true);
    setError(null);
    
    try {
      if (browserMode) {
        const local = await parseLocally(fileToUpload);
        setUploadData(local);
        setSchema(local.schema);
        setActiveTab('configure');
        return;
      }
      const response = await apiService.uploadFile(fileToUpload);
      // Convert schema format to Field format
      const convertedSchema: Field[] = response.schema.map(s => ({
        name: s.name,
        type: s.type,
        encryption: s.encryption as Field['encryption']
      }));
      setUploadData({ filename: response.filename, records: response.records, fields: response.fields,
                      schema: convertedSchema, sample_data: response.sample_data });
      setSchema(convertedSchema);
      setActiveTab('configure');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleEncrypt = async () => {
    if (!uploadData) return;
    
    setIsEncrypting(true);
    setError(null);
    
    try {
      const response = browserMode ? await encryptLocally() : await apiService.encryptDataset(
        uploadData.filename,
        schema.map(f => ({ name: f.name, encryption: f.encryption }))
      );
      setEncryptionResult(response);
      if (!browserMode && 'fields' in response && response.fields) {
        setGroupable(Object.fromEntries(Object.entries(response.fields).map(([n, f]) => [n, f.group_by ?? []])));
      }
      setActiveTab('query');
      
      // Set first numeric field for queries
      const numericField = schema.find(f => PAILLIER.includes(f.encryption));
      if (numericField) {
        setSelectedField(numericField.name);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Encryption failed');
    } finally {
      setIsEncrypting(false);
    }
  };

  // presets that fit the loaded columns; ones whose range needs an OPE+Paillier column say so
  const encryptedAs = (n: string) => schema.find(f => f.name === n)?.encryption;
  const presets = BANK_PRESETS.filter(p => [p.field, p.group, p.group2, p.filter].every(c => !c || schema.some(f => f.name === c))
                                       && PAILLIER.includes(encryptedAs(p.field) ?? ''));
  const presetBlocker = (p: Preset) => (p.filter && encryptedAs(p.filter) !== 'OPE+Paillier'
    ? `Set ${p.filter} to Paillier + range (step 2) to filter on it` : null);
  const runPreset = (p: Preset) => {
    setSelectedOperation(p.op); setSelectedField(p.field); setGroupBy(p.group ?? ''); setGroupBy2(p.group2 ?? '');
    setFilterBy(p.filter ?? ''); setRangeMin(p.min ?? ''); setRangeMax(p.max ?? '');
    setPresetRun(n => n + 1);
  };
  useEffect(() => {
    if (presetRun) void handleQuery();
  }, [presetRun]);  // eslint-disable-line react-hooks/exhaustive-deps -- runs with the state the preset just set

  const handleQuery = async () => {
    if (!uploadData || !selectedField) return;
    
    setIsQuerying(true);
    setError(null);
    
    try {
      // Parse range values (convert to numbers or undefined)
      const minVal = rangeMin.trim() !== '' ? parseFloat(rangeMin) : undefined;
      const maxVal = rangeMax.trim() !== '' ? parseFloat(rangeMax) : undefined;
      
      // Validate range if both are provided
      if (minVal !== undefined && maxVal !== undefined && minVal > maxVal) {
        setError('Invalid range: minimum must be less than or equal to maximum');
        setIsQuerying(false);
        return;
      }
      
      const order = ORDER_STATS[selectedOperation] !== undefined;
      if (order && !activeGroupBy && ((filterBy && filterBy !== selectedField)
                                       || schema.find(f => f.name === selectedField)?.encryption !== 'OPE+Paillier')) {
        setError(`${selectedOperation} needs an OPE+Paillier field filtered by itself, or a GROUP BY`);
        setIsQuerying(false);
        return;
      }
      const response = order && browserMode ? await (activeGroupBy ? queryOrderGroupsLocally(minVal, maxVal) : queryOrderLocally(minVal, maxVal))
        : activeGroupBy
        ? (browserMode ? await queryGroupsLocally(minVal, maxVal)
                       : await apiService.executeQuery(selectedOperation, selectedField, uploadData.filename,
                                                       minVal, maxVal, filterBy || undefined, activeGroupBy))
        : browserMode ? await queryLocally(minVal, maxVal) : await apiService.executeQuery(
        selectedOperation,
        selectedField,
        uploadData.filename,
        minVal,
        maxVal,
        filterBy || undefined
      );
      setQueries([response as QueryResult, ...queries]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Query failed');
    } finally {
      setIsQuerying(false);
    }
  };

  const updateFieldEncryption = (index: number, encryption: Field['encryption']) => {
    const newSchema = [...schema];
    newSchema[index].encryption = encryption;
    setSchema(newSchema);
  };

  const PROTECTION: Array<{ value: Field['encryption']; label: string; hint: string }> = [
    { value: 'Plaintext', label: 'Plain', hint: 'ids only, not encrypted' },
    { value: 'AES-256', label: 'AES-256', hint: 'text: sealed, not computed on' },
    { value: 'Paillier-2048', label: 'Paillier', hint: 'SUM, AVG, spread, GROUP BY' },
    { value: 'OPE+Paillier', label: 'Paillier + range', hint: 'also ranges, MIN, MAX, MEDIAN' },
  ];
  const fmt = (v: number | null | undefined) => (v == null ? 'no rows' : v.toLocaleString('en-GB', { maximumFractionDigits: 3 }));
  const steps = [
    { value: 'upload', label: 'Load data', enabled: true },
    { value: 'configure', label: 'Choose protection', enabled: !!uploadData },
    { value: 'query', label: 'Ask questions', enabled: !!encryptionResult },
    { value: 'results', label: 'Log', enabled: queries.length > 0 },
  ];
  const fieldSelect = 'h-11 w-full appearance-none border border-input bg-card px-3 pr-9 text-[0.98rem] text-ink focus-visible:outline-2';
  const label = 'mb-1.5 block text-[0.875rem] font-semibold text-ink';

  const renderSlip = (q: QueryResult, key: number) => {
    const proof = q.encryption_proof;
    const checked = !!proof && /checked the integrity tags/.test(proof.verification);
    const sorted = q.groups ? [...q.groups].sort((x, y) => String(x.group).localeCompare(String(y.group), undefined, { numeric: true })) : null;
    return (
      <article key={key} className="feed-in border-b border-dashed border-band-line px-5 py-6 md:px-7">
        <header className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
          <code className="font-mono text-[0.92rem] font-semibold text-ink">
            {q.operation}({q.field || q.column}){q.filter_applied && ` WHERE ${q.filter_column || q.field} BETWEEN ${q.range?.min ?? '…'} AND ${q.range?.max ?? '…'}`}
            {q.group_by && ` GROUP BY ${q.group_by.replace(',', ', ')}`}
          </code>
          <span className="font-mono text-[0.875rem] text-ink-2">
            {(q.time_ms || q.query_time_ms || 0).toFixed(1)} ms
            {(q.setup_ms ?? 0) >= 1 && (
              <span title="First use only: the encrypted copy of the column this query needs. Later runs reuse it; answers are never cached.">
                {' '}+ {Math.round(q.setup_ms!)} ms one-time setup
              </span>
            )}
          </span>
        </header>

        {sorted ? (
          <table className="mt-4 w-full border-collapse">
            <tbody>
              {sorted.map((g, i) => (
                <tr key={String(g.group)} className={i % 2 ? '' : 'bg-band/70'}>
                  <th scope="row" className="py-2 pl-3 pr-4 text-left text-[1.1rem] font-medium">{String(g.group)}</th>
                  <td className="py-2 pr-4 text-right font-mono text-[clamp(1.2rem,1.9vw,1.6rem)] font-semibold">{fmt(g.result)}</td>
                  <td className="whitespace-nowrap py-2 pr-3 text-right font-mono text-[0.875rem] text-ink-2">{g.count.toLocaleString('en-GB')} rows</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="mt-3 font-mono text-[clamp(2.2rem,4vw,3.4rem)] font-semibold leading-none tracking-[-0.03em]">{fmt(q.result)}</div>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-[0.88rem] text-ink-2">
          <span>{(q.records_processed || 0).toLocaleString('en-GB')} encrypted rows</span>
          {q.filter_applied && <span>{Math.round((q.filter_selectivity || 0) * 100)}% of {(q.records_before_filter || 0).toLocaleString('en-GB')} in range</span>}
          {!!q.ciphertexts_aggregated && <span>{q.ciphertexts_aggregated.toLocaleString('en-GB')} ciphertexts</span>}
          {checked && <span className="stamp ml-auto text-ok">Checked: integrity tags match</span>}
          {proof && !checked && <span className="stamp ml-auto text-ink-2">Decrypted by the server</span>}
        </div>
        {q.count_note && <p className="mt-3 text-[0.88rem] text-ink-2">{q.count_note}</p>}
        {proof && <p className="mt-3 max-w-[70ch] text-[0.875rem] leading-relaxed text-ink-2">{proof.verification}.</p>}
      </article>
    );
  };

  return (
    <div className="min-h-[100dvh] bg-paper text-ink">
      <SheetHeader>
        <span className={`hidden border px-3 py-1.5 font-mono text-[0.875rem] md:inline-block ${browserMode ? 'border-ok text-ok' : 'border-ribbon text-ribbon'}`}>
          {browserMode ? 'key held in this browser' : 'server holds the key'}
        </span>
        <Link href="/" className={navLink}>Home</Link>
      </SheetHeader>

      <main className="mx-auto max-w-[1320px] pb-16 pt-6 md:px-6">
        <Sheet className="pb-12 pt-6">
        <div className="px-3 md:px-6">
        {error && (
          <div role="alert" className="mb-6 flex items-start gap-3 border-2 border-ribbon bg-card px-4 py-3 text-ribbon">
            <AlertCircle className="mt-0.5 size-5 shrink-0" strokeWidth={2} />
            <p className="text-[0.98rem] font-medium">{error}</p>
            <button type="button" onClick={() => setError(null)} className="ml-auto text-[0.9rem] font-semibold underline">Dismiss</button>
          </div>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab} className="gap-0">
          <TabsList className="grid h-auto w-full grid-cols-2 gap-px rounded-none border border-band-line bg-band-line p-0 md:grid-cols-4">
            {steps.map((s, i) => (
              <TabsTrigger key={s.value} value={s.value} disabled={!s.enabled}
                           className="h-auto justify-start gap-3 rounded-none border-0 bg-card px-4 py-3 text-left text-[0.98rem] font-semibold text-ink-2 shadow-none data-[state=active]:bg-ink data-[state=active]:text-paper data-[state=active]:shadow-none disabled:opacity-45">
                <span className="font-mono text-[0.875rem]">{i + 1}</span>{s.label}
              </TabsTrigger>
            ))}
          </TabsList>

          {/* 1: LOAD DATA */}
          <TabsContent value="upload" className="mt-8 space-y-8">
            <fieldset>
              <legend className="semi-wide mb-3 text-[1.15rem] font-bold">Who holds the key?</legend>
              <div className="grid gap-px border border-band-line bg-band-line md:grid-cols-2">
                {[
                  { on: true, title: 'This browser', tag: 'use this for the demo',
                    text: 'The CSV is read and encrypted in this tab. The server receives only ciphertexts and order tags. Close the tab and the key is gone, unless you save a key file.' },
                  { on: false, title: 'The server', tag: 'comparison only',
                    text: 'The CSV is uploaded and the server makes and holds the key. Useful to compare speed; it is not the privacy model.' },
                ].map(m => (
                  <button key={m.title} type="button" onClick={() => switchMode(m.on)} aria-pressed={browserMode === m.on}
                          className={`flex flex-col gap-2 p-5 text-left transition-colors ${browserMode === m.on ? 'bg-ink text-paper' : 'bg-card text-ink hover:bg-band'}`}>
                    <span className="flex items-baseline justify-between gap-3">
                      <span className="text-[1.1rem] font-bold">{m.title}</span>
                      <span className={`font-mono text-[0.875rem] ${browserMode === m.on ? 'text-band' : 'text-ink-2'}`}>{m.tag}</span>
                    </span>
                    <span className={`text-[0.95rem] leading-relaxed ${browserMode === m.on ? 'text-[#d9e3d6]' : 'text-ink-2'}`}>{m.text}</span>
                  </button>
                ))}
              </div>
            </fieldset>

            <div
              className={`relative flex flex-col items-center justify-center border-2 border-dashed px-6 py-14 text-center transition-colors ${isDragging ? 'border-ok bg-band' : 'border-[#9fb79a] bg-card'}`}
              onDrop={handleDrop}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
            >
              <input type="file" accept=".csv" className="hidden" id="file-upload" onChange={handleFileSelect} />
              {isUploading ? (
                <p className="semi-wide text-[1.3rem] font-bold">Reading the CSV…</p>
              ) : (
                <>
                  <p className="semi-wide text-[clamp(1.3rem,2.2vw,1.8rem)] font-bold">{file ? file.name : 'Drop a CSV here'}</p>
                  <p className="mt-2 text-[0.98rem] text-ink-2">
                    {file ? `${(file.size / 1024).toFixed(1)} KB` : 'Demo data: data/bank_customers.csv, 2,000 synthetic customers'}
                  </p>
                  <label htmlFor="file-upload" className={`${inkButton} mt-6 cursor-pointer`}>
                    <Upload className="size-4" strokeWidth={2.2} /> Choose a file
                  </label>
                </>
              )}
            </div>

            {browserMode && (
              <details className="group border border-band-line bg-card">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-4">
                  <span>
                    <span className="block text-[1.02rem] font-bold">Reopen a saved session</span>
                    <span className="block text-[0.9rem] text-ink-2">Encrypted earlier and saved a key file? Open it to query the same encrypted data again; nothing is uploaded twice.</span>
                  </span>
                  <ChevronDown className="size-5 shrink-0 transition-transform group-open:rotate-180" strokeWidth={2} />
                </summary>
                <div className="grid gap-4 border-t border-band-line px-5 py-5 md:grid-cols-[1fr_1fr_auto] md:items-end">
                  <div>
                    <label htmlFor="restore-file" className={label}>Key file (.agniya-key)</label>
                    <input id="restore-file" type="file" accept=".agniya-key,application/json"
                           className="block w-full border border-input bg-paper px-3 py-2 text-[0.92rem] file:mr-3 file:border-0 file:bg-band file:px-3 file:py-1 file:font-semibold"
                           onChange={(e) => setRestoreFile(e.target.files?.[0] ?? null)} />
                  </div>
                  <div>
                    <label htmlFor="restore-password" className={label}>Its password</label>
                    <input id="restore-password" type="password" value={keyPassword} onChange={(e) => setKeyPassword(e.target.value)}
                           className="h-11 w-full border border-input bg-paper px-3" />
                  </div>
                  <button type="button" onClick={restoreFromKeyFile} disabled={!restoreFile || !keyPassword || keyBusy} className={inkButton}>
                    <KeyRound className="size-4" strokeWidth={2.2} /> {keyBusy ? 'Unlocking…' : 'Open session'}
                  </button>
                </div>
              </details>
            )}

            {uploadData && (
              <section className="border border-band-line bg-card">
                <div className="flex flex-wrap items-center gap-x-8 gap-y-2 px-5 py-4">
                  <span className="font-mono text-[1.4rem] font-semibold">{uploadData.records.toLocaleString('en-GB')} <span className="text-[0.875rem] font-normal text-ink-2">rows</span></span>
                  <span className="font-mono text-[1.4rem] font-semibold">{uploadData.fields} <span className="text-[0.875rem] font-normal text-ink-2">columns</span></span>
                  <button type="button" onClick={() => setActiveTab('configure')} className={`${inkButton} ml-auto`}>
                    Choose protection <ArrowRight className="size-4" strokeWidth={2.2} />
                  </button>
                </div>
                {uploadData.sample_data && uploadData.sample_data.length > 0 && (
                  <div className="overflow-x-auto border-t border-band-line">
                    <table className="w-full border-collapse text-[0.875rem]">
                      <thead>
                        <tr>{Object.keys(uploadData.sample_data[0]).map(k => <th key={k} className="whitespace-nowrap px-4 py-2 text-left font-mono font-semibold">{k}</th>)}</tr>
                      </thead>
                      <tbody>
                        {uploadData.sample_data.slice(0, 3).map((row, i) => (
                          <tr key={i} className={i % 2 ? '' : 'bg-band/70'}>
                            {Object.values(row).map((v, j) => <td key={j} className="whitespace-nowrap px-4 py-2 font-mono text-ink-2">{String(v)}</td>)}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            )}
          </TabsContent>

          {/* 2: CHOOSE PROTECTION */}
          <TabsContent value="configure" className="mt-8 space-y-6">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <h2 className="semi-wide text-[1.4rem] font-bold">How each column is protected</h2>
                <p className="mt-1 max-w-[62ch] text-[0.98rem] text-ink-2">
                  Paillier columns can be summed while encrypted. Add range to filter by value or ask MIN, MAX and MEDIAN; the server then learns the order of that column.
                </p>
              </div>
              <span className="font-mono text-[0.875rem] text-ink-2">{schema.filter(f => f.encryption !== 'Plaintext').length} of {schema.length} encrypted</span>
            </div>

            <div className="overflow-x-auto border border-band-line bg-card">
              <table className="w-full min-w-[720px] border-collapse">
                <thead>
                  <tr className="border-b-2 border-ink text-left">
                    <th className="px-4 py-3 text-[0.875rem] font-semibold">Column</th>
                    <th className="px-4 py-3 text-[0.875rem] font-semibold">Type</th>
                    <th className="px-4 py-3 text-[0.875rem] font-semibold">Protection</th>
                  </tr>
                </thead>
                <tbody>
                  {schema.map((field, index) => (
                    <tr key={field.name} className={index % 2 ? '' : 'bg-band/60'}>
                      <th scope="row" className="px-4 py-2.5 text-left font-mono text-[0.95rem] font-semibold">{field.name}</th>
                      <td className="px-4 py-2.5 font-mono text-[0.875rem] text-ink-2">{field.type}</td>
                      <td className="px-4 py-2">
                        <div role="radiogroup" aria-label={`Protection for ${field.name}`} className="inline-flex border border-input">
                          {PROTECTION.map(p => {
                            const numericOnly = p.value === 'Paillier-2048' || p.value === 'OPE+Paillier';
                            const disabled = numericOnly && field.type === 'str';
                            const on = field.encryption === p.value;
                            return (
                              <button key={p.value} type="button" role="radio" aria-checked={on} disabled={disabled} title={p.hint}
                                      onClick={() => updateFieldEncryption(index, p.value)}
                                      className={`border-r border-input px-3 py-1.5 text-[0.875rem] font-semibold last:border-r-0 disabled:cursor-not-allowed disabled:text-[#a9b4ac] ${on ? 'bg-ink text-paper' : 'bg-card text-ink hover:bg-band'}`}>
                                {p.label}
                              </button>
                            );
                          })}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <button type="button" onClick={handleEncrypt} disabled={isEncrypting} className={`${inkButton} h-12 px-6 text-[1rem]`}>
                <Lock className="size-4" strokeWidth={2.2} />
                {isEncrypting ? (browserMode ? 'Making a key and encrypting in this browser…' : 'Encrypting on the server…')
                              : `Encrypt ${uploadData?.records.toLocaleString('en-GB') ?? ''} rows`}
              </button>
              <span className="text-[0.9rem] text-ink-2">{PROTECTION.map(p => `${p.label}: ${p.hint}`).join('. ')}.</span>
            </div>

            {encryptionResult && (
              <section className="border-2 border-ink bg-card">
                <div className="flex flex-wrap items-baseline gap-x-10 gap-y-3 px-5 py-5">
                  <span className="stamp text-ok">Encrypted</span>
                  <span className="font-mono text-[1.5rem] font-semibold">{(encryptionResult.records_encrypted || 0).toLocaleString('en-GB')} <span className="text-[0.875rem] font-normal text-ink-2">rows</span></span>
                  {encryptionResult.time_seconds != null && <span className="font-mono text-[1.5rem] font-semibold">{encryptionResult.time_seconds.toFixed(2)} <span className="text-[0.875rem] font-normal text-ink-2">s</span></span>}
                  {encryptionResult.ciphertexts != null && <span className="font-mono text-[1.5rem] font-semibold">{encryptionResult.ciphertexts.toLocaleString('en-GB')} <span className="text-[0.875rem] font-normal text-ink-2">ciphertexts stored</span></span>}
                  <button type="button" onClick={() => setActiveTab('query')} className={`${inkButton} ml-auto`}>
                    Ask questions <ArrowRight className="size-4" strokeWidth={2.2} />
                  </button>
                </div>
                {browserMode && (
                  <div className="grid gap-3 border-t border-band-line px-5 py-4 md:grid-cols-[1fr_auto] md:items-end">
                    <div>
                      <label htmlFor="key-password" className={label}>Save the key: without it this data cannot be decrypted after the tab closes</label>
                      <input id="key-password" type="password" placeholder="Choose a password for the key file" value={keyPassword}
                             onChange={(e) => setKeyPassword(e.target.value)} className="h-11 w-full border border-input bg-paper px-3" />
                    </div>
                    <button type="button" onClick={downloadKeyFile} disabled={!keyPassword || keyBusy} className={paperButton}>
                      <KeyRound className="size-4" strokeWidth={2.2} /> {keyBusy ? 'Encrypting the key…' : 'Download key file'}
                    </button>
                  </div>
                )}
              </section>
            )}
          </TabsContent>

          {/* 3: ASK QUESTIONS */}
          <TabsContent value="query" className="mt-8">
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(320px,400px)_minmax(0,1fr)]">
              <div className="min-w-0 space-y-8">
                {presets.length > 0 && (
                  <section>
                    <h2 className="semi-wide text-[1.15rem] font-bold">Bank questions</h2>
                    <p className="mt-1 text-[0.9rem] text-ink-2">One click: the server computes with no key, this browser decrypts and checks.</p>
                    <ul className="mt-4 border-t border-band-line">
                      {presets.map(p => {
                        const blocker = presetBlocker(p);
                        return (
                          <li key={p.title}>
                            <button type="button" disabled={!!blocker || isQuerying} onClick={() => runPreset(p)} title={blocker ?? undefined}
                                    className="group flex w-full items-start justify-between gap-3 border-b border-band-line px-1 py-3 text-left hover:bg-band disabled:cursor-not-allowed disabled:opacity-55">
                              <span>
                                <span className="block text-[1.02rem] font-semibold leading-snug">{p.title}</span>
                                <span className="mt-0.5 block font-mono text-[0.875rem] leading-relaxed text-ink-2">{presetSql(p)}</span>
                                {blocker && <span className="mt-1 block text-[0.875rem] font-medium text-ribbon">{blocker}</span>}
                              </span>
                              <Play className="mt-1 size-4 shrink-0 text-ink-2 group-hover:text-ink" strokeWidth={2.2} />
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  </section>
                )}

                <section className="border border-band-line bg-card p-5">
                  <h2 className="semi-wide text-[1.15rem] font-bold">Your own query</h2>
                  <div className="mt-4 space-y-4">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label htmlFor="q-op" className={label}>Operation</label>
                        <div className="relative">
                          <select id="q-op" value={selectedOperation} onChange={(e) => setSelectedOperation(e.target.value as Operation)} className={fieldSelect}>
                            {(['SUM', 'AVG', 'COUNT', 'MIN', 'MAX', 'MEDIAN', 'VARIANCE', 'STDDEV'] as Operation[]).map(o => <option key={o} value={o}>{o}</option>)}
                          </select>
                          <ChevronDown className="pointer-events-none absolute right-3 top-3.5 size-4" strokeWidth={2} />
                        </div>
                      </div>
                      <div>
                        <label htmlFor="q-field" className={label}>Column</label>
                        <div className="relative">
                          <select id="q-field" value={selectedField} onChange={(e) => setSelectedField(e.target.value)} className={fieldSelect}>
                            {!selectedField && <option value="">Choose…</option>}
                            {schema.filter(f => PAILLIER.includes(f.encryption)).map(f => <option key={f.name} value={f.name}>{f.name}</option>)}
                          </select>
                          <ChevronDown className="pointer-events-none absolute right-3 top-3.5 size-4" strokeWidth={2} />
                        </div>
                      </div>
                    </div>

                    {groupOptions.length > 0 && (
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label htmlFor="q-group" className={label}>Group by</label>
                          <div className="relative">
                            <select id="q-group" value={groupOptions.includes(groupBy) ? groupBy : ''} onChange={(e) => setGroupBy(e.target.value)} className={fieldSelect}>
                              <option value="">No grouping</option>
                              {groupOptions.map(g => <option key={g} value={g}>{g.replace(',', ', ')}</option>)}
                            </select>
                            <ChevronDown className="pointer-events-none absolute right-3 top-3.5 size-4" strokeWidth={2} />
                          </div>
                        </div>
                        {activeGroupBy && !groupBy.includes(',') && thenOptions.length > 0 && (
                          <div>
                            <label htmlFor="q-group2" className={label}>Then by</label>
                            <div className="relative">
                              <select id="q-group2" value={thenOptions.includes(groupBy2) ? groupBy2 : ''} onChange={(e) => setGroupBy2(e.target.value)} className={fieldSelect}>
                                <option value="">Only {groupBy}</option>
                                {thenOptions.map(g => <option key={g} value={g}>{g}</option>)}
                              </select>
                              <ChevronDown className="pointer-events-none absolute right-3 top-3.5 size-4" strokeWidth={2} />
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {schema.some(f => f.encryption === 'OPE+Paillier') && (
                      <div>
                        <label htmlFor="q-filter" className={label}>Range filter on</label>
                        <div className="relative">
                          <select id="q-filter" value={filterBy && filterBy !== selectedField ? filterBy : ''} onChange={(e) => setFilterBy(e.target.value)} className={fieldSelect}>
                            <option value="">{selectedField || 'the column'} itself</option>
                            {schema.filter(f => f.encryption === 'OPE+Paillier' && f.name !== selectedField).map(f => <option key={f.name} value={f.name}>{f.name}</option>)}
                          </select>
                          <ChevronDown className="pointer-events-none absolute right-3 top-3.5 size-4" strokeWidth={2} />
                        </div>
                      </div>
                    )}

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label htmlFor="q-min" className={label}>From (optional)</label>
                        <input id="q-min" type="number" value={rangeMin} onChange={(e) => setRangeMin(e.target.value)} className="h-11 w-full border border-input bg-card px-3 font-mono" />
                      </div>
                      <div>
                        <label htmlFor="q-max" className={label}>To (optional)</label>
                        <input id="q-max" type="number" value={rangeMax} onChange={(e) => setRangeMax(e.target.value)} className="h-11 w-full border border-input bg-card px-3 font-mono" />
                      </div>
                    </div>

                    <button type="button" onClick={handleQuery} disabled={!selectedField || isQuerying} className={`${inkButton} w-full justify-center`}>
                      {isQuerying ? 'Computing on ciphertexts…' : 'Run on encrypted data'}
                    </button>
                  </div>
                </section>
              </div>

              {/* The printout roll: newest message on top. */}
              <section aria-live="polite" aria-label="Results" className="relative min-h-[420px] self-start border border-band-line bg-[#fbfcf8]">
                <div className="flex items-center justify-between border-b-2 border-ink px-5 py-3 md:px-7">
                  <h2 className="semi-wide text-[1.05rem] font-bold">Results</h2>
                  <span className="font-mono text-[0.875rem] text-ink-2">{queries.length} printed · newest first</span>
                </div>
                {isQuerying && (
                  <div className="border-b border-dashed border-band-line bg-band px-5 py-4 font-mono text-[0.9rem] md:px-7">
                    printing: the server multiplies ciphertexts, then this browser decrypts…
                  </div>
                )}
                {queries.length === 0 && !isQuerying ? (
                  <div className="greenbar flex min-h-[360px] flex-col items-start justify-center px-7 py-10 [--bar:60px]">
                    <p className="semi-wide text-[1.3rem] font-bold">Nothing printed yet</p>
                    <p className="mt-2 max-w-[44ch] text-[0.98rem] text-ink-2">Click a bank question on the left, or build your own query. Each answer arrives here with its timing and its check.</p>
                  </div>
                ) : (
                  <div className="max-h-[calc(100dvh-14rem)] overflow-y-auto">
                    {queries.map((q, i) => renderSlip(q, queries.length - i))}
                  </div>
                )}
              </section>
            </div>
          </TabsContent>

          {/* 4: LOG */}
          <TabsContent value="results" className="mt-8">
            <div className="overflow-x-auto border border-band-line bg-card">
              <table className="w-full min-w-[640px] border-collapse">
                <thead>
                  <tr className="border-b-2 border-ink text-left text-[0.875rem]">
                    <th className="px-4 py-3 font-semibold">Query</th>
                    <th className="px-4 py-3 text-right font-semibold">Result</th>
                    <th className="px-4 py-3 text-right font-semibold">Time</th>
                    <th className="px-4 py-3 text-right font-semibold">Rows</th>
                  </tr>
                </thead>
                <tbody>
                  {queries.map((q, i) => (
                    <tr key={i} className={i % 2 ? '' : 'bg-band/60'}>
                      <td className="px-4 py-2.5 font-mono text-[0.875rem]">{q.operation}({q.field || q.column}){q.group_by && ` GROUP BY ${q.group_by.replace(',', ', ')}`}</td>
                      <td className="px-4 py-2.5 text-right font-mono text-[1rem] font-semibold">{q.groups ? `${q.groups.length} groups` : fmt(q.result)}</td>
                      <td className="px-4 py-2.5 text-right font-mono text-[0.9rem]">{(q.time_ms || q.query_time_ms || 0).toFixed(1)} ms</td>
                      <td className="px-4 py-2.5 text-right font-mono text-[0.9rem]">{(q.records_processed || 0).toLocaleString('en-GB')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </TabsContent>
        </Tabs>
        </div>
        </Sheet>
      </main>
    </div>
  );
}
