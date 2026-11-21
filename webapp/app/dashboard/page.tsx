'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, Lock, ArrowLeft, FileText, Zap, Database, Search, Calculator, Filter, TrendingUp, AlertCircle, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import Link from 'next/link';
import { apiService, API_BASE_URL } from '@/lib/api';
import { parseCsv } from '@/lib/agniya-browser';
import { CryptoWorker } from '@/lib/agniya-worker-client';

const PAILLIER: string[] = ['Paillier-2048', 'OPE+Paillier'];

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
  sample_data?: any[];
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
  result?: number;
  time_ms?: number;
  records_processed?: number;
  // New fields from advanced server
  success?: boolean;
  column?: string;
  query_time_ms?: number;
  ciphertexts_aggregated?: number;
  filter_applied?: boolean;
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
  const [selectedOperation, setSelectedOperation] = useState<'SUM' | 'AVG' | 'COUNT'>('SUM');
  const [rangeMin, setRangeMin] = useState('');
  const [rangeMax, setRangeMax] = useState('');
  
  const [error, setError] = useState<string | null>(null);

  // Browser mode: the CSV is parsed here and encrypted in a Web Worker that holds the keys (/api/v2).
  const [browserMode, setBrowserMode] = useState(true);
  const csvRef = useRef<{ header: string[]; rows: string[][] } | null>(null);
  const workerRef = useRef<CryptoWorker | null>(null);

  const dropWorker = () => { workerRef.current?.terminate(); workerRef.current = null; };  // drops the key
  useEffect(() => () => workerRef.current?.terminate(), []);  // leaving the page drops the key too

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
      const restored: Field[] = info.columns.map(c => ({
        name: c.name, type: c.scale === 1 ? 'int' : 'float', encryption: c.rangeFilter ? 'OPE+Paillier' : 'Paillier-2048' }));
      const records = Math.max(0, ...info.columns.map(c => c.count));
      setUploadData({ filename: info.dataset, records, fields: restored.length, schema: restored });
      setSchema(restored);
      setEncryptionResult({ success: true, records_encrypted: records, message: 'Restored from key file' });
      setQueries([]);
      setSelectedField(restored[0]?.name ?? '');
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
    setSelectedField(''); setRangeMin(''); setRangeMax('');
    csvRef.current = null;
    dropWorker();
    setActiveTab('upload');
  };

  const columnValues = (name: string): number[] => {
    const { header, rows } = csvRef.current!;
    const i = header.indexOf(name);
    return rows.map(r => (r[i] ?? '').trim()).filter(v => v !== '').map(Number);
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
    await worker.init(API_BASE_URL, `${uploadData!.filename}-${crypto.randomUUID().slice(0, 8)}`);
    let ciphertexts = 0;
    for (const f of fields) {
      const vals = columnValues(f.name);
      if (!vals.every(Number.isFinite)) throw new Error(`${f.name} is not numeric`);
      const decimals = vals.every(Number.isInteger) ? 0 : 4;
      ciphertexts += (await worker.upload(f.name, vals, decimals, f.encryption === 'OPE+Paillier')).ciphertexts;
    }
    const secs = (performance.now() - t0) / 1000;
    const records = csvRef.current!.rows.length;
    return { success: true, records_encrypted: records, time_seconds: secs, throughput: records / secs, ciphertexts };
  };

  const queryLocally = async (minVal?: number, maxVal?: number): Promise<QueryResult> => {
    const t0 = performance.now();
    const a = await workerRef.current!.query(selectedField, minVal, maxVal);
    const time_ms = performance.now() - t0;
    const total = a.total;
    const filtered = minVal !== undefined || maxVal !== undefined;
    return {
      operation: selectedOperation, field: selectedField, column: selectedField,
      result: { SUM: a.sum, AVG: a.avg, COUNT: a.count }[selectedOperation],
      time_ms, records_processed: a.count, ciphertexts_aggregated: a.ciphertextsUsed,
      filter_applied: filtered, range: { min: minVal ?? null, max: maxVal ?? null },
      records_before_filter: total, filter_selectivity: total ? a.count / total : 0,
      security_note: 'The server compared OPE tags (it learns their order) and multiplied ciphertexts; the edge ciphertexts were decrypted in this browser.',
      encryption_proof: {
        ciphertext_samples: [], ciphertext_bit_lengths: a.ciphertextBits.slice(0, 3), modulus_n_bit_length: 2048,
        verification: `Server multiplied ${a.ciphertextsUsed} ciphertexts in ${a.serverMs} ms without any key; decrypted in this browser`,
        computation_type: 'Paillier homomorphic addition',
      },
    };
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type === 'text/csv') {
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
      setUploadData(response as any);
      // Convert schema format to Field format
      const convertedSchema = response.schema.map(s => ({
        name: s.name,
        type: s.type as any,
        encryption: s.encryption as any
      }));
      setSchema(convertedSchema as any);
      setActiveTab('configure');
    } catch (err: any) {
      setError(err.message || 'Upload failed');
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
      setActiveTab('query');
      
      // Set first numeric field for queries
      const numericField = schema.find(f => PAILLIER.includes(f.encryption));
      if (numericField) {
        setSelectedField(numericField.name);
      }
    } catch (err: any) {
      setError(err.message || 'Encryption failed');
    } finally {
      setIsEncrypting(false);
    }
  };

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
      
      const response = browserMode ? await queryLocally(minVal, maxVal) : await apiService.executeQuery(
        selectedOperation,
        selectedField,
        uploadData.filename,
        minVal,
        maxVal
      );
      setQueries([response as any, ...queries]);
    } catch (err: any) {
      setError(err.message || 'Query failed');
    } finally {
      setIsQuerying(false);
    }
  };

  const updateFieldEncryption = (index: number, encryption: Field['encryption']) => {
    const newSchema = [...schema];
    newSchema[index].encryption = encryption;
    setSchema(newSchema);
  };

  const encryptionColors = {
    'Plaintext': 'bg-gray-500/10 text-gray-600 border-gray-500/20',
    'AES-256': 'bg-blue-500/10 text-blue-600 border-blue-500/20',
    'Paillier-2048': 'bg-purple-500/10 text-purple-600 border-purple-500/20',
    'OPE+Paillier': 'bg-primary/10 text-primary border-primary/20'
  };

  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      <div className="fixed inset-0 gradient-mesh -z-10" />
      
      {/* Navigation */}
      <nav className="glass-morphism sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <Link href="/" className="flex items-center gap-2">
                <Lock className="w-6 h-6 text-primary" />
                <span className="text-xl font-bold tracking-tight">AGNIYA</span>
              </Link>
              <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20">
                Live Encryption Dashboard
              </Badge>
            </div>
            
            <Link href="/">
              <Button variant="ghost" size="sm" className="gap-2">
                <ArrowLeft className="w-4 h-4" />
                Home
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="container mx-auto px-6 py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-6xl mx-auto"
        >
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-2 text-gradient">Encrypted Analytics Dashboard</h1>
            <p className="text-muted-foreground">
              Upload CSV, encrypt with Paillier-2048 & AES-256, run queries on encrypted data
            </p>
          </div>

          {/* Error Display */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="mb-6"
              >
                <Card className="p-4 bg-destructive/10 border-destructive/20">
                  <div className="flex items-center gap-3">
                    <AlertCircle className="w-5 h-5 text-destructive" />
                    <p className="text-sm text-destructive">{error}</p>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setError(null)}
                      className="ml-auto"
                    >
                      Dismiss
                    </Button>
                  </div>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>

          <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="upload">
                <Upload className="w-4 h-4 mr-2" />
                Upload
              </TabsTrigger>
              <TabsTrigger value="configure" disabled={!uploadData}>
                <Lock className="w-4 h-4 mr-2" />
                Configure
              </TabsTrigger>
              <TabsTrigger value="query" disabled={!encryptionResult}>
                <Database className="w-4 h-4 mr-2" />
                Query
              </TabsTrigger>
              <TabsTrigger value="results" disabled={queries.length === 0}>
                <TrendingUp className="w-4 h-4 mr-2" />
                Results
              </TabsTrigger>
            </TabsList>

            {/* UPLOAD TAB */}
            <TabsContent value="upload" className="space-y-6">
              <Card className="p-4 glass-morphism">
                <div className="flex flex-col md:flex-row md:items-center gap-3">
                  <div className="flex gap-2">
                    <Button size="sm" variant={browserMode ? 'default' : 'outline'} onClick={() => switchMode(true)}>
                      <Shield className="w-4 h-4 mr-2" />
                      Encrypt in this browser
                    </Button>
                    <Button size="sm" variant={browserMode ? 'outline' : 'default'} onClick={() => switchMode(false)}>
                      <Database className="w-4 h-4 mr-2" />
                      Server-side demo
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {browserMode
                      ? 'The CSV is read and encrypted here. The server receives only ciphertexts and OPE tags; the private key stays in this tab unless you download a password-protected key file.'
                      : 'The CSV is uploaded and the server generates and holds the private key: the server is the data owner.'}
                  </p>
                </div>
              </Card>

              {browserMode && (
                <Card className="p-4 glass-morphism">
                  <div className="flex flex-col md:flex-row md:items-end gap-3">
                    <div className="flex-1">
                      <Label htmlFor="restore-file">Restore from key file</Label>
                      <Input id="restore-file" type="file" accept=".agniya-key,application/json"
                             onChange={(e) => setRestoreFile(e.target.files?.[0] ?? null)} />
                    </div>
                    <div className="flex-1">
                      <Label htmlFor="restore-password">Key file password</Label>
                      <Input id="restore-password" type="password" value={keyPassword}
                             onChange={(e) => setKeyPassword(e.target.value)} />
                    </div>
                    <Button onClick={restoreFromKeyFile} disabled={!restoreFile || !keyPassword || keyBusy}>
                      <Lock className="w-4 h-4 mr-2" />
                      {keyBusy ? 'Unlocking...' : 'Restore'}
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    Reopen data you encrypted earlier: the key file is decrypted in this browser; the ciphertexts are already on the server.
                  </p>
                </Card>
              )}

              <Card
                className={`p-12 border-2 border-dashed transition-all duration-300 glass-morphism ${
                  isDragging
                    ? 'border-primary bg-primary/10 scale-105'
                    : 'border-zinc-300 dark:border-zinc-700'
                }`}
                onDrop={handleDrop}
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
              >
                <div className="text-center">
                  {isUploading ? (
                    <>
                      <Zap className="w-16 h-16 mx-auto mb-4 text-primary animate-pulse" />
                      <h3 className="text-xl font-semibold mb-2">Uploading...</h3>
                      <p className="text-muted-foreground">Parsing CSV and detecting schema...</p>
                    </>
                  ) : (
                    <>
                      <Upload className="w-16 h-16 mx-auto mb-4 text-primary" />
                      <h3 className="text-xl font-semibold mb-2">
                        {file ? file.name : 'Drop your CSV file here'}
                      </h3>
                      <p className="text-muted-foreground mb-6">
                        {file ? `${(file.size / 1024).toFixed(2)} KB` : 'or click to browse'}
                      </p>
                      <input
                        type="file"
                        accept=".csv"
                        className="hidden"
                        id="file-upload"
                        onChange={handleFileSelect}
                      />
                      <label htmlFor="file-upload" className="inline-block">
                        <div className="cursor-pointer px-6 py-2 rounded-lg bg-gradient-to-r from-primary to-primary/80 text-white font-medium inline-flex items-center gap-2 hover:opacity-90 transition-opacity">
                          <FileText className="w-4 h-4" />
                          Select CSV File
                        </div>
                      </label>
                    </>
                  )}
                </div>
              </Card>

              {uploadData && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  <Card className="p-6 glass-morphism">
                    <h4 className="font-semibold text-lg mb-4">Dataset Information</h4>
                    <div className="grid grid-cols-3 gap-4 mb-6">
                      <div className="p-4 rounded-lg bg-primary/5 border border-primary/10">
                        <Database className="w-5 h-5 text-primary mb-2" />
                        <div className="text-2xl font-bold">{uploadData.records}</div>
                        <div className="text-sm text-muted-foreground">Records</div>
                      </div>
                      <div className="p-4 rounded-lg bg-primary/5 border border-primary/10">
                        <FileText className="w-5 h-5 text-primary mb-2" />
                        <div className="text-2xl font-bold">{uploadData.fields}</div>
                        <div className="text-sm text-muted-foreground">Fields</div>
                      </div>
                      <div className="p-4 rounded-lg bg-primary/5 border border-primary/10">
                        <Lock className="w-5 h-5 text-primary mb-2" />
                        <div className="text-2xl font-bold">Ready</div>
                        <div className="text-sm text-muted-foreground">Status</div>
                      </div>
                    </div>

                    {uploadData.sample_data && uploadData.sample_data.length > 0 && (
                      <div>
                        <h5 className="font-semibold mb-3">Sample Data (First 3 rows)</h5>
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead className="border-b">
                              <tr>
                                {Object.keys(uploadData.sample_data[0]).map(key => (
                                  <th key={key} className="text-left py-2 px-3 font-medium">{key}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {uploadData.sample_data.slice(0, 3).map((row, i) => (
                                <tr key={i} className="border-b">
                                  {Object.values(row).map((val: any, j) => (
                                    <td key={j} className="py-2 px-3 font-mono text-xs">{String(val)}</td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    <Button
                      onClick={() => setActiveTab('configure')}
                      className="w-full mt-6 gradient-primary text-white"
                      size="lg"
                    >
                      Configure Encryption
                      <ArrowLeft className="w-4 h-4 ml-2 rotate-180" />
                    </Button>
                  </Card>
                </motion.div>
              )}
            </TabsContent>

            {/* CONFIGURE TAB */}
            <TabsContent value="configure" className="space-y-6">
              <Card className="p-6 glass-morphism">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h3 className="text-xl font-semibold mb-1">Configure Encryption Schema</h3>
                    <p className="text-sm text-muted-foreground">
                      Choose encryption type for each field
                    </p>
                  </div>
                  <Badge variant="outline" className="gap-2 bg-primary/5 border-primary/20">
                    <Lock className="w-3 h-3" />
                    {schema.filter(f => f.encryption !== 'Plaintext').length} fields encrypted
                  </Badge>
                </div>

                <div className="border rounded-lg overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Field Name</TableHead>
                        <TableHead>Data Type</TableHead>
                        <TableHead>Encryption Type</TableHead>
                        <TableHead className="w-32">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {schema.map((field, index) => (
                        <TableRow key={index}>
                          <TableCell className="font-mono font-semibold">{field.name}</TableCell>
                          <TableCell className="text-muted-foreground">{field.type}</TableCell>
                          <TableCell>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  className={`w-full justify-start ${encryptionColors[field.encryption]}`}
                                >
                                  {field.encryption}
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="start" className="w-64">
                                {(['Plaintext', 'AES-256', 'Paillier-2048', 'OPE+Paillier'] as const).map((type) => (
                                  <DropdownMenuItem
                                    key={type}
                                    onClick={() => updateFieldEncryption(index, type)}
                                    className="flex flex-col items-start gap-1 py-3"
                                  >
                                    <span className="font-medium">{type}</span>
                                    <span className="text-xs text-muted-foreground">
                                      {type === 'Plaintext' && 'No encryption - for IDs'}
                                      {type === 'AES-256' && 'Fast symmetric - for strings'}
                                      {type === 'Paillier-2048' && 'Homomorphic - for SUM/AVG'}
                                      {type === 'OPE+Paillier' && 'Dual-mode - range queries + aggregation'}
                                    </span>
                                  </DropdownMenuItem>
                                ))}
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className={encryptionColors[field.encryption]}>
                              {field.encryption === 'Plaintext' ? '⚠️' : '🔒'}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                <Button
                  onClick={handleEncrypt}
                  disabled={isEncrypting}
                  className="w-full mt-6 h-12 gradient-primary text-white"
                  size="lg"
                >
                  {isEncrypting ? (
                    <>
                      <Zap className="w-5 h-5 mr-2 animate-pulse" />
                      {browserMode ? 'Generating key and encrypting in this browser...' : 'Encrypting with Paillier-2048...'}
                    </>
                  ) : (
                    <>
                      <Lock className="w-5 h-5 mr-2" />
                      Encrypt Dataset ({uploadData?.records} records)
                    </>
                  )}
                </Button>
              </Card>

              {encryptionResult && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  <Card className="p-6 bg-gradient-to-br from-primary/10 to-primary/5 border-primary/20">
                    <div className="flex items-center gap-3 mb-6">
                      <div className="p-3 rounded-xl bg-primary/20">
                        <Zap className="w-6 h-6 text-primary" />
                      </div>
                      <div>
                        <h4 className="font-bold text-lg">Encryption Complete!</h4>
                        <p className="text-sm text-muted-foreground">Your data is now encrypted and ready for queries</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-4 gap-4">
                      <div className="p-4 rounded-lg bg-white/50 dark:bg-black/20">
                        <div className="text-3xl font-bold text-primary">
                          {encryptionResult.records_encrypted || 0}
                        </div>
                        <div className="text-sm text-muted-foreground">Records Encrypted</div>
                      </div>
                      <div className="p-4 rounded-lg bg-white/50 dark:bg-black/20">
                        <div className="text-3xl font-bold text-primary">
                          {encryptionResult.time_seconds?.toFixed(2) ?? 'N/A'}s
                        </div>
                        <div className="text-sm text-muted-foreground">Time Taken</div>
                      </div>
                      <div className="p-4 rounded-lg bg-white/50 dark:bg-black/20">
                        <div className="text-3xl font-bold text-primary">
                          {encryptionResult.throughput?.toFixed(0) ?? 'N/A'}/s
                        </div>
                        <div className="text-sm text-muted-foreground">Throughput</div>
                      </div>
                      <div className="p-4 rounded-lg bg-white/50 dark:bg-black/20">
                        <div className="text-3xl font-bold text-green-600">
                          {encryptionResult.ciphertexts ?? 'N/A'}
                        </div>
                        <div className="text-sm text-muted-foreground">Ciphertexts stored</div>
                      </div>
                    </div>

                    {browserMode && (
                      <div className="mt-6 p-4 rounded-lg bg-white/50 dark:bg-black/20">
                        <Label htmlFor="key-password">
                          Save the key: without it the data cannot be decrypted after this tab closes
                        </Label>
                        <div className="flex gap-2 mt-2">
                          <Input id="key-password" type="password" placeholder="Password for the key file"
                                 value={keyPassword} onChange={(e) => setKeyPassword(e.target.value)} />
                          <Button onClick={downloadKeyFile} disabled={!keyPassword || keyBusy} variant="outline">
                            {keyBusy ? 'Encrypting key...' : 'Download key file'}
                          </Button>
                        </div>
                      </div>
                    )}

                    <Button
                      onClick={() => setActiveTab('query')}
                      variant="secondary"
                      className="w-full mt-6"
                      size="lg"
                    >
                      Start Querying Encrypted Data
                      <ArrowLeft className="w-4 h-4 ml-2 rotate-180" />
                    </Button>
                  </Card>
                </motion.div>
              )}
            </TabsContent>

            {/* QUERY TAB */}
            <TabsContent value="query" className="space-y-6">
              <div className="grid md:grid-cols-2 gap-6">
                {/* Query Builder */}
                <Card className="p-6 glass-morphism">
                  <h3 className="text-xl font-semibold mb-6 flex items-center gap-2">
                    <Calculator className="w-5 h-5 text-primary" />
                    Homomorphic Query Builder
                  </h3>

                  <div className="space-y-4">
                    <div>
                      <Label>Operation</Label>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="outline" className="w-full justify-between">
                            {selectedOperation}
                            <Filter className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent className="w-full">
                          <DropdownMenuItem onClick={() => setSelectedOperation('SUM')}>
                            SUM - Total sum of values
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setSelectedOperation('AVG')}>
                            AVG - Average of values
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setSelectedOperation('COUNT')}>
                            COUNT - Number of records
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>

                    <div>
                      <Label>Field</Label>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="outline" className="w-full justify-between">
                            {selectedField || 'Select field...'}
                            <Database className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent className="w-full">
                          {schema.filter(f => PAILLIER.includes(f.encryption)).map(field => (
                            <DropdownMenuItem key={field.name} onClick={() => setSelectedField(field.name)}>
                              {field.name} ({field.encryption})
                            </DropdownMenuItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label>Min Value (optional)</Label>
                        <Input
                          type="number"
                          placeholder="25"
                          value={rangeMin}
                          onChange={(e) => setRangeMin(e.target.value)}
                        />
                      </div>
                      <div>
                        <Label>Max Value (optional)</Label>
                        <Input
                          type="number"
                          placeholder="50"
                          value={rangeMax}
                          onChange={(e) => setRangeMax(e.target.value)}
                        />
                      </div>
                    </div>

                    <Button
                      onClick={handleQuery}
                      disabled={!selectedField || isQuerying}
                      className="w-full gradient-primary text-white"
                      size="lg"
                    >
                      {isQuerying ? (
                        <>
                          <Zap className="w-5 h-5 mr-2 animate-pulse" />
                          Computing on Encrypted Data...
                        </>
                      ) : (
                        <>
                          <Search className="w-5 h-5 mr-2" />
                          Execute Query
                        </>
                      )}
                    </Button>
                  </div>
                </Card>

                {/* Recent Queries */}
                <Card className="p-6 glass-morphism">
                  <h3 className="text-xl font-semibold mb-6 flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-primary" />
                    Query Results
                  </h3>

                  {queries.length === 0 ? (
                    <div className="text-center py-12 text-muted-foreground">
                      <Search className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p>No queries yet. Run your first homomorphic query!</p>
                    </div>
                  ) : (
                    <div className="space-y-3 max-h-96 overflow-y-auto">
                      {queries.map((query, i) => (
                        <motion.div
                          key={i}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          className="p-4 rounded-lg bg-primary/5 border border-primary/10"
                        >
                          <div className="flex items-center justify-between mb-2">
                            <Badge className="bg-primary/20 text-primary border-primary/30">
                              {query.operation || query.column}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              {(query.time_ms || query.query_time_ms || 0).toFixed(2)} ms
                            </span>
                          </div>
                          <div className="font-mono text-sm mb-1">
                            <span className="text-muted-foreground">{query.operation || query.column}(</span>
                            <span className="font-semibold">{query.field || query.column}</span>
                            <span className="text-muted-foreground">)</span>
                          </div>
                          <div className="text-2xl font-bold text-primary">
                            {(query.result || 0).toLocaleString()}
                          </div>
                          <div className="text-xs text-muted-foreground mt-1">
                            {query.records_processed || 0} records processed (encrypted)
                            {query.filter_applied && (
                              <div className="text-blue-600 dark:text-blue-400 mt-1">
                                🔍 Range filter: [{query.range?.min} - {query.range?.max}] 
                                ({Math.round((query.filter_selectivity || 0) * 100)}% of data)
                              </div>
                            )}
                          </div>
                          
                          {/* Range Filter Info */}
                          {query.filter_applied && (
                            <div className="mt-3 p-2 bg-blue-500/10 border border-blue-500/30 rounded text-xs">
                              <div className="font-semibold text-blue-600 mb-1 flex items-center gap-1">
                                <Filter className="w-3 h-3" />
                                OPE Range Filter Applied
                              </div>
                              <div className="space-y-1 text-muted-foreground">
                                <div>📊 Total records: {query.records_before_filter || 0}</div>
                                <div>✅ Filtered records: {query.records_processed || 0}</div>
                                <div>🎯 Selectivity: {Math.round((query.filter_selectivity || 0) * 100)}%</div>
                                <div>🔐 {query.security_note}</div>
                              </div>
                            </div>
                          )}
                          
                          {/* Encryption Proof */}
                          {query.encryption_proof && (
                            <div className="mt-3 p-2 bg-green-500/10 border border-green-500/30 rounded text-xs">
                              <div className="font-semibold text-green-600 mb-1 flex items-center gap-1">
                                <Shield className="w-3 h-3" />
                                Encrypted Computation Verified
                              </div>
                              <div className="space-y-1 text-muted-foreground">
                                <div>🔐 Ciphertext sizes: {query.encryption_proof.ciphertext_bit_lengths?.join(', ')} bits</div>
                                {query.encryption_proof.encrypted_result_bit_length && (
                                  <div>🔐 Encrypted result: {query.encryption_proof.encrypted_result_bit_length} bits</div>
                                )}
                                <div>✅ {query.encryption_proof.verification}</div>
                              </div>
                            </div>
                          )}
                        </motion.div>
                      ))}
                    </div>
                  )}
                </Card>
              </div>
            </TabsContent>

            {/* RESULTS TAB */}
            <TabsContent value="results">
              <Card className="p-6 glass-morphism">
                <h3 className="text-xl font-semibold mb-6">All Query Results</h3>
                
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Operation</TableHead>
                      <TableHead>Field</TableHead>
                      <TableHead className="text-right">Result</TableHead>
                      <TableHead className="text-right">Time (ms)</TableHead>
                      <TableHead className="text-right">Records</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {queries.map((query, i) => (
                      <TableRow key={i}>
                        <TableCell>
                          <Badge className="bg-primary/20 text-primary border-primary/30">
                            {query.operation || query.column}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-mono">{query.field || query.column}</TableCell>
                        <TableCell className="text-right font-bold text-primary text-lg">
                          {(query.result || 0).toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right font-mono">{(query.time_ms || query.query_time_ms || 0).toFixed(2)}</TableCell>
                        <TableCell className="text-right">{query.records_processed || 0}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Card>
            </TabsContent>
          </Tabs>
        </motion.div>
      </div>
    </div>
  );
}
