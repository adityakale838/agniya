'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Shield, Info } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface Field {
  name: string;
  type: string;
  encryption: 'Plaintext' | 'AES-256' | 'Paillier-2048' | 'OPE+Paillier';
}

const encryptionInfo = {
  'Plaintext': 'No encryption - for non-sensitive identifiers',
  'AES-256': 'Fast symmetric encryption - for non-searchable data',
  'Paillier-2048': 'Homomorphic encryption - supports SUM operations',
  'OPE+Paillier': 'Dual-mode - supports range queries + aggregations'
};

const encryptionColors = {
  'Plaintext': 'bg-gray-500/10 text-gray-600 border-gray-500/20',
  'AES-256': 'bg-blue-500/10 text-blue-600 border-blue-500/20',
  'Paillier-2048': 'bg-purple-500/10 text-purple-600 border-purple-500/20',
  'OPE+Paillier': 'bg-primary/10 text-primary border-primary/20'
};

export function SchemaDesigner({ fields }: { fields: Field[] }) {
  const [schema, setSchema] = useState<Field[]>(fields);

  const updateEncryption = (index: number, encryption: Field['encryption']) => {
    const newSchema = [...schema];
    newSchema[index].encryption = encryption;
    setSchema(newSchema);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold mb-1">Configure Encryption</h3>
          <p className="text-sm text-muted-foreground">
            Select encryption type for each field
          </p>
        </div>
        <Badge variant="outline" className="gap-2">
          <Shield className="w-3 h-3" />
          {schema.filter(f => f.encryption !== 'Plaintext').length} fields encrypted
        </Badge>
      </div>

      <div className="border rounded-lg overflow-hidden bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Field Name</TableHead>
              <TableHead>Data Type</TableHead>
              <TableHead>Encryption Type</TableHead>
              <TableHead className="w-16"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {schema.map((field, index) => (
              <TableRow key={index}>
                <TableCell className="font-mono text-sm">{field.name}</TableCell>
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
                    <DropdownMenuContent align="start" className="w-56">
                      {Object.keys(encryptionInfo).map((type) => (
                        <DropdownMenuItem
                          key={type}
                          onClick={() => updateEncryption(index, type as Field['encryption'])}
                          className="flex flex-col items-start gap-1 py-3"
                        >
                          <span className="font-medium">{type}</span>
                          <span className="text-xs text-muted-foreground">
                            {encryptionInfo[type as keyof typeof encryptionInfo]}
                          </span>
                        </DropdownMenuItem>
                      ))}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
                <TableCell>
                  <Info className="w-4 h-4 text-muted-foreground" />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="grid md:grid-cols-4 gap-4">
        {Object.entries(encryptionInfo).map(([type, description]) => (
          <div
            key={type}
            className={`p-4 rounded-lg border ${encryptionColors[type as keyof typeof encryptionColors]}`}
          >
            <div className="font-semibold text-sm mb-1">{type}</div>
            <div className="text-xs opacity-80">{description}</div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
