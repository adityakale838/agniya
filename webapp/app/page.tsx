'use client';

import { motion } from 'framer-motion';
import { Upload, Lock, Zap, Database, BarChart3, Shield, ArrowRight, Sparkles, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      {/* Gradient Mesh Background */}
      <div className="fixed inset-0 gradient-mesh -z-10" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_120%,rgba(120,119,198,0.1),rgba(255,255,255,0))] -z-10" />
      
      {/* Navigation */}
      <motion.nav
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="sticky top-0 z-50 glass-morphism"
      >
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2 group">
              <div className="relative">
                <Lock className="w-6 h-6 text-primary transition-transform group-hover:rotate-12 duration-300" />
                <div className="absolute -inset-2 bg-primary/20 rounded-full blur-lg opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              </div>
              <span className="text-xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/70">
                AGNIYA
              </span>
            </Link>
            
            <div className="hidden md:flex items-center gap-8">
              <Link href="#features" className="text-sm font-medium text-muted-foreground hover:text-primary transition-colors">
                Features
              </Link>
              <Link href="#performance" className="text-sm font-medium text-muted-foreground hover:text-primary transition-colors">
                Performance
              </Link>
              <Link href="https://github.com/adityakale838/agniya" target="_blank" className="text-sm font-medium text-muted-foreground hover:text-primary transition-colors">
                GitHub
              </Link>
            </div>
            
            <Link href="/dashboard">
              <Button className="gradient-primary text-white shadow-lg shadow-primary/25 hover:shadow-xl hover:shadow-primary/30 transition-all duration-300 group">
                Launch Dashboard
                <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
              </Button>
            </Link>
          </div>
        </div>
      </motion.nav>

      {/* Hero Section */}
      <section className="container mx-auto px-6 pt-20 pb-32">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center mb-12"
          >
            <Badge variant="outline" className="mb-6 px-4 py-2 gap-2 bg-primary/5 border-primary/20 text-primary hover:bg-primary/10 transition-colors">
              <Sparkles className="w-4 h-4" />
              <span className="font-semibold">143x Faster Than Traditional Encryption</span>
            </Badge>
            
            <h1 className="text-6xl md:text-7xl font-bold tracking-tight mb-6 leading-[1.1]">
              <span className="text-gradient">Compute on Encrypted Data</span>
              <br />
              <span className="text-foreground/90">Without Decryption</span>
            </h1>

            <p className="text-xl text-muted-foreground mb-12 max-w-3xl mx-auto leading-relaxed">
              Run analytics on sensitive data while it stays encrypted. AGNIYA combines 
              <span className="text-primary font-semibold"> Paillier-2048</span>, 
              <span className="text-primary font-semibold"> AES-256-GCM</span>, and 
              <span className="text-primary font-semibold"> OPE</span> to deliver unprecedented performance.
            </p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="flex flex-col sm:flex-row items-center justify-center gap-4"
            >
              <Link href="/dashboard">
                <Button size="lg" className="gradient-primary text-white shadow-2xl shadow-primary/30 hover:shadow-primary/40 h-14 px-8 text-lg group">
                  <Upload className="w-5 h-5 mr-2" />
                  Upload Dataset
                  <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
                </Button>
              </Link>
              <Link href="#performance">
                <Button size="lg" variant="outline" className="h-14 px-8 text-lg glass-morphism hover:bg-primary/5 border-primary/20">
                  <BarChart3 className="w-5 h-5 mr-2" />
                  View Benchmarks
                </Button>
              </Link>
            </motion.div>
          </motion.div>

          {/* Stats Grid */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="grid md:grid-cols-3 gap-6 mt-20"
          >
            {[
              { icon: Zap, label: 'Performance', value: '143.9x', description: 'Speedup over pure Paillier' },
              { icon: Shield, label: 'Security', value: '2048-bit', description: 'Military-grade encryption' },
              { icon: Database, label: 'Throughput', value: '2,190/s', description: 'Records processed per second' },
            ].map((stat, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.4 + i * 0.1 }}
              >
                <Card className="p-6 glass-morphism hover:shadow-xl hover:shadow-primary/5 transition-all duration-300 group cursor-pointer border-border/50">
                  <div className="flex items-start justify-between mb-4">
                    <div className="p-3 rounded-xl bg-primary/10 group-hover:bg-primary/15 transition-colors">
                      <stat.icon className="w-6 h-6 text-primary" />
                    </div>
                  </div>
                  <div className="text-3xl font-bold mb-1 text-foreground">{stat.value}</div>
                  <div className="text-sm font-semibold text-foreground/90 mb-1">{stat.label}</div>
                  <div className="text-sm text-muted-foreground">{stat.description}</div>
                </Card>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="container mx-auto px-6 py-24">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <Badge variant="outline" className="mb-4 bg-primary/5 border-primary/20 text-primary">
              How It Works
            </Badge>
            <h2 className="text-4xl md:text-5xl font-bold mb-4">
              Three Steps to <span className="text-gradient">Encrypted Analytics</span>
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Upload, configure, and query—all while your data remains encrypted end-to-end.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                step: '01',
                icon: Upload,
                title: 'Upload Dataset',
                description: 'Drag and drop your CSV file. We automatically detect field types and suggest optimal encryption schemes.',
                features: ['Auto-schema detection', 'CSV/Excel support', 'Instant preview']
              },
              {
                step: '02',
                icon: Lock,
                title: 'Configure Encryption',
                description: 'Choose encryption for each field: Paillier for computations, AES for speed, or OPE for range queries.',
                features: ['4 encryption types', 'Per-field control', 'Visual configuration']
              },
              {
                step: '03',
                icon: BarChart3,
                title: 'Run Analytics',
                description: 'Execute SUM, AVG, COUNT, and range queries directly on encrypted data. Get results in milliseconds.',
                features: ['Homomorphic queries', 'Real-time results', 'Performance metrics']
              },
            ].map((feature, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <Card className="p-8 glass-morphism hover:shadow-2xl hover:shadow-primary/10 transition-all duration-300 group border-border/50 h-full">
                  <div className="flex items-center gap-4 mb-6">
                    <span className="text-5xl font-bold text-primary/20 group-hover:text-primary/30 transition-colors">
                      {feature.step}
                    </span>
                    <div className="p-4 rounded-xl bg-primary/10 group-hover:bg-primary/15 transition-colors">
                      <feature.icon className="w-7 h-7 text-primary" />
                    </div>
                  </div>
                  <h3 className="text-2xl font-bold mb-3">{feature.title}</h3>
                  <p className="text-muted-foreground mb-6 leading-relaxed">{feature.description}</p>
                  <div className="space-y-2">
                    {feature.features.map((item, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-sm">
                        <CheckCircle2 className="w-4 h-4 text-primary" />
                        <span className="text-muted-foreground">{item}</span>
                      </div>
                    ))}
                  </div>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Performance Section */}
      <section id="performance" className="container mx-auto px-6 py-24">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <Badge variant="outline" className="mb-4 bg-primary/5 border-primary/20 text-primary">
              Benchmarks
            </Badge>
            <h2 className="text-4xl md:text-5xl font-bold mb-4">
              <span className="text-gradient">Unmatched Performance</span>
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Our hybrid architecture delivers 143.9x speedup while maintaining military-grade security.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 gap-8">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
            >
              <Card className="p-8 glass-morphism border-border/50">
                <h3 className="text-2xl font-bold mb-6">Operation Latency</h3>
                <div className="space-y-4">
                  {[
                    { operation: 'Encryption', time: '0.52 ms', color: 'bg-primary' },
                    { operation: 'SUM Query', time: '0.18 ms', color: 'bg-chart-2' },
                    { operation: 'AVG Query', time: '0.19 ms', color: 'bg-chart-3' },
                    { operation: 'COUNT Query', time: '0.03 ms', color: 'bg-chart-4' },
                    { operation: 'Range Query', time: '0.15 ms', color: 'bg-chart-5' },
                  ].map((item, i) => (
                    <div key={i} className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium">{item.operation}</span>
                        <span className="text-muted-foreground font-mono">{item.time}</span>
                      </div>
                      <div className="h-2 bg-muted rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          whileInView={{ width: `${(parseFloat(item.time) / 0.52) * 100}%` }}
                          viewport={{ once: true }}
                          transition={{ duration: 1, delay: i * 0.1 }}
                          className={`h-full ${item.color} rounded-full`}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
            >
              <Card className="p-8 glass-morphism border-border/50 h-full flex flex-col justify-center">
                <div className="text-center mb-6">
                  <div className="text-7xl font-bold text-gradient mb-2">143.9x</div>
                  <p className="text-xl font-semibold text-foreground/80 mb-1">Faster Execution</p>
                  <p className="text-muted-foreground">vs. Pure Paillier Encryption</p>
                </div>
                <div className="grid grid-cols-2 gap-4 mt-8">
                  <div className="text-center p-4 rounded-xl bg-muted/50">
                    <div className="text-2xl font-bold text-destructive">5.24 min</div>
                    <div className="text-sm text-muted-foreground mt-1">Pure Paillier</div>
                  </div>
                  <div className="text-center p-4 rounded-xl bg-primary/10">
                    <div className="text-2xl font-bold text-primary">2.19 sec</div>
                    <div className="text-sm text-muted-foreground mt-1">Hybrid System</div>
                  </div>
                </div>
              </Card>
            </motion.div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-6 py-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="max-w-4xl mx-auto"
        >
          <Card className="gradient-primary p-12 md:p-16 text-center relative overflow-hidden">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_120%,rgba(255,255,255,0.1),transparent)] pointer-events-none" />
            <div className="relative z-10">
              <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
                Ready to Encrypt Your Data?
              </h2>
              <p className="text-xl text-white/80 mb-8 max-w-2xl mx-auto">
                Start running analytics on encrypted data today. No credit card required.
              </p>
              <Link href="/dashboard">
                <Button size="lg" variant="secondary" className="h-14 px-8 text-lg shadow-xl hover:shadow-2xl transition-all group">
                  <Zap className="w-5 h-5 mr-2" />
                  Launch Dashboard
                  <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
                </Button>
              </Link>
            </div>
          </Card>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/40 bg-card/30 backdrop-blur-sm">
        <div className="container mx-auto px-6 py-12">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-2">
              <Lock className="w-5 h-5 text-primary" />
              <span className="font-semibold">AGNIYA</span>
              <span className="text-muted-foreground">·</span>
              <span className="text-sm text-muted-foreground">Homomorphic Encryption Platform</span>
            </div>
            <div className="flex items-center gap-6 text-sm text-muted-foreground">
              <Link href="https://github.com/adityakale838/agniya" target="_blank" className="hover:text-primary transition-colors">
                GitHub
              </Link>
              <Link href="/docs" className="hover:text-primary transition-colors">
                Documentation
              </Link>
              <Link href="/research" className="hover:text-primary transition-colors">
                Research
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
