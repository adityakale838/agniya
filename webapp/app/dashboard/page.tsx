'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, Lock, ArrowLeft, FileText, Zap, Database, Search, Calculator, Filter, TrendingUp, AlertCircle } from 'lucide-react';
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
import { apiService } from '@/lib/api';

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
  records_encrypted: number;
  time_seconds: number;
  throughput: number;
  speedup: number;
  encryption_breakdown: {
    plaintext_fields: number;
    aes_fields: number;
    paillier_fields: number;
  };
}

interface QueryResult {
  operation: string;
  field: string;
  result: number;
  time_ms: number;
  records_processed: number;
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
      const response = await apiService.uploadFile(fileToUpload);
      setUploadData(response);
      setSchema(response.schema);
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
      const response = await apiService.encryptDataset(
        uploadData.filename,
        schema.map(f => ({ name: f.name, encryption: f.encryption }))
      );
      setEncryptionResult(response);
      setActiveTab('query');
      
      // Set first numeric field for queries
      const numericField = schema.find(f => f.type === 'int' || f.type === 'Integer');
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
      const response = await apiService.executeQuery(
        selectedOperation,
        selectedField,
        uploadData.filename
      );
      setQueries([response, ...queries]);
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
              <Card
                className={`p-12 border-2 border-dashed transition-all duration-300 glass-morphism ${
                  isDragging
                    ? 'border-primary bg-primary/10 scale-105'
                    : 'border-border/50'
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
                      <label htmlFor="file-upload">
                        <Button variant="outline" className="cursor-pointer gradient-primary text-white border-0">
                          <FileText className="w-4 h-4 mr-2" />
                          Select CSV File
                        </Button>
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
                      Encrypting with Paillier-2048...
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
                        <div className="text-3xl font-bold text-primary">{encryptionResult.records_encrypted}</div>
                        <div className="text-sm text-muted-foreground">Records Encrypted</div>
                      </div>
                      <div className="p-4 rounded-lg bg-white/50 dark:bg-black/20">
                        <div className="text-3xl font-bold text-primary">{encryptionResult.time_seconds.toFixed(2)}s</div>
                        <div className="text-sm text-muted-foreground">Time Taken</div>
                      </div>
                      <div className="p-4 rounded-lg bg-white/50 dark:bg-black/20">
                        <div className="text-3xl font-bold text-primary">{encryptionResult.throughput.toFixed(0)}/s</div>
                        <div className="text-sm text-muted-foreground">Throughput</div>
                      </div>
                      <div className="p-4 rounded-lg bg-white/50 dark:bg-black/20">
                        <div className="text-3xl font-bold text-green-600">{encryptionResult.speedup.toFixed(1)}x</div>
                        <div className="text-sm text-muted-foreground">Speedup</div>
                      </div>
                    </div>

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
                          {schema.filter(f => f.type === 'int' || f.type === 'Integer' || f.type === 'float').map(field => (
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
                              {query.operation}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              {query.time_ms.toFixed(2)} ms
                            </span>
                          </div>
                          <div className="font-mono text-sm mb-1">
                            <span className="text-muted-foreground">{query.operation}(</span>
                            <span className="font-semibold">{query.field}</span>
                            <span className="text-muted-foreground">)</span>
                          </div>
                          <div className="text-2xl font-bold text-primary">
                            {query.result.toLocaleString()}
                          </div>
                          <div className="text-xs text-muted-foreground mt-1">
                            {query.records_processed} records processed (encrypted)
                          </div>
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
                            {query.operation}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-mono">{query.field}</TableCell>
                        <TableCell className="text-right font-bold text-primary text-lg">
                          {query.result.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right font-mono">{query.time_ms.toFixed(2)}</TableCell>
                        <TableCell className="text-right">{query.records_processed}</TableCell>
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
