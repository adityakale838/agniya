'use client';

import { motion } from 'framer-motion';
import { TrendingUp, Clock, Shield, Zap } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts';

const speedupData = [
  { name: 'Pure Paillier', time: 314400, speedup: 1 },
  { name: 'Hybrid System', time: 2185, speedup: 143.9 },
];

const operationData = [
  { operation: 'Encryption', hybrid: 0.52, paillier: 66.4 },
  { operation: 'SUM', hybrid: 0.18, paillier: 0.21 },
  { operation: 'AVG', hybrid: 0.19, paillier: 0.22 },
  { operation: 'COUNT', hybrid: 0.03, paillier: 0.03 },
  { operation: 'Range Query', hybrid: 0.15, paillier: null },
];

const metrics = [
  {
    label: 'Total Speedup',
    value: '143.9x',
    description: 'Faster than pure Paillier',
    icon: TrendingUp,
    color: 'text-green-600',
  },
  {
    label: 'Encryption Time',
    value: '0.52 ms',
    description: 'Per record (AES-256)',
    icon: Clock,
    color: 'text-blue-600',
  },
  {
    label: 'Security Level',
    value: '2048-bit',
    description: 'Paillier key size',
    icon: Shield,
    color: 'text-purple-600',
  },
  {
    label: 'Throughput',
    value: '2,190 rec/s',
    description: 'On sample dataset',
    icon: Zap,
    color: 'text-primary',
  },
];

export function ResultsDashboard() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      {/* Metrics Grid */}
      <div className="grid md:grid-cols-4 gap-4">
        {metrics.map((metric, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
          >
            <Card className="p-5 bg-card/50 backdrop-blur-sm hover:bg-card transition-colors">
              <metric.icon className={`w-8 h-8 mb-3 ${metric.color}`} />
              <div className="text-2xl font-bold mb-1">{metric.value}</div>
              <div className="text-sm font-medium mb-1">{metric.label}</div>
              <div className="text-xs text-muted-foreground">{metric.description}</div>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Speedup Comparison */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold mb-1">Performance Comparison</h3>
              <p className="text-sm text-muted-foreground">
                Total execution time (seconds)
              </p>
            </div>
            <Badge variant="outline" className="bg-green-500/10 text-green-600 border-green-500/20">
              143.9x Faster
            </Badge>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={speedupData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border/50" />
              <XAxis
                dataKey="name"
                className="text-xs"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
              />
              <YAxis
                className="text-xs"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                }}
              />
              <Bar dataKey="time" fill="hsl(var(--primary))" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Operation Times */}
        <Card className="p-6">
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-1">Operation Latency</h3>
            <p className="text-sm text-muted-foreground">
              Average time per operation (ms)
            </p>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={operationData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border/50" />
              <XAxis
                dataKey="operation"
                className="text-xs"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
              />
              <YAxis
                className="text-xs"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                }}
              />
              <Line
                type="monotone"
                dataKey="hybrid"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                name="Hybrid System"
              />
              <Line
                type="monotone"
                dataKey="paillier"
                stroke="hsl(var(--muted-foreground))"
                strokeWidth={2}
                strokeDasharray="5 5"
                name="Pure Paillier"
              />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Detailed Results */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Benchmark Results</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b">
              <tr>
                <th className="text-left py-3 px-4 font-medium">Operation</th>
                <th className="text-right py-3 px-4 font-medium">Hybrid (ms)</th>
                <th className="text-right py-3 px-4 font-medium">Pure Paillier (ms)</th>
                <th className="text-right py-3 px-4 font-medium">Speedup</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {operationData.map((row, i) => (
                <tr key={i} className="hover:bg-muted/50 transition-colors">
                  <td className="py-3 px-4 font-mono">{row.operation}</td>
                  <td className="py-3 px-4 text-right font-mono text-primary">
                    {row.hybrid.toFixed(2)}
                  </td>
                  <td className="py-3 px-4 text-right font-mono text-muted-foreground">
                    {row.paillier?.toFixed(2) || 'N/A'}
                  </td>
                  <td className="py-3 px-4 text-right">
                    {row.paillier ? (
                      <Badge
                        variant="outline"
                        className="bg-green-500/10 text-green-600 border-green-500/20"
                      >
                        {(row.paillier / row.hybrid).toFixed(1)}x
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="bg-blue-500/10 text-blue-600 border-blue-500/20">
                        Unique
                      </Badge>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </motion.div>
  );
}
