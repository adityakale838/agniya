# AGNIYA Comprehensive Evaluation Suite

## For Patent Application & Conference Paper Submission

This evaluation suite provides rigorous, publication-quality benchmarks demonstrating AGNIYA's performance advantages, novel contributions, and production readiness.

**Target Venues:** USENIX Security, IEEE S&P, NDSS, ACM CCS

---

## Directory Structure

```
evaluation_suite/
├── README.md                      # This file
├── run_all_benchmarks.py          # Main orchestrator
├── config.yaml                    # Configuration settings
├── benchmarks/                    # Individual benchmark modules
│   ├── 01_micro_benchmarks.py     # Component-level tests
│   ├── 02_end_to_end.py           # System-level queries
│   ├── 03_comparative_seal.py     # vs Microsoft SEAL
│   ├── 04_rns_validation.py       # RNS compression analysis
│   ├── 05_oram_evaluation.py      # ORAM overhead & security
│   ├── 06_gpu_acceleration.py     # GPU scaling tests
│   ├── 07_batch_packing.py        # Batch encoding analysis
│   ├── 08_real_datasets.py        # Real-world workloads
│   ├── 09_scalability.py          # Horizontal/vertical scaling
│   ├── 10_stress_chaos.py         # Robustness testing
│   ├── 11_security_analysis.py    # Side-channel resistance
│   ├── 12_ablation_study.py       # Component removal impact
│   └── utils.py                   # Shared utilities
├── visualization/                  # Graph generation
│   ├── generate_all_graphs.py     # Create all 60+ graphs
│   ├── graph_templates.py         # Reusable plotting functions
│   └── paper_ready.py             # LaTeX-ready outputs
├── results/                        # Benchmark outputs
│   ├── raw_data/                  # JSON/CSV results
│   ├── graphs/                    # PDF/SVG visualizations
│   ├── tables/                    # LaTeX tables
│   └── summary_report.md          # Human-readable summary
└── datasets/                       # Test datasets
    ├── generate_datasets.py       # Synthetic data generation
    └── real/                      # Real-world data (if available)
```

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements_evaluation.txt
```

### 2. Run Full Evaluation Suite

```bash
# Run all benchmarks (4-6 hours on high-end workstation)
python evaluation_suite/run_all_benchmarks.py --full

# Quick validation run (30 minutes)
python evaluation_suite/run_all_benchmarks.py --quick

# Specific benchmark category
python evaluation_suite/run_all_benchmarks.py --category micro
```

### 3. Generate Visualizations

```bash
# Create all 60+ graphs
python evaluation_suite/visualization/generate_all_graphs.py

# Paper-ready outputs (PDF, LaTeX tables)
python evaluation_suite/visualization/paper_ready.py
```

---

## Benchmark Categories

### Part 1: Core Performance (Graphs 1-4)
- Micro-benchmarks: Individual component performance
- End-to-end: Query latency, sustained throughput
- **Critical Metrics:** 6.7M ops/sec, 255× speedup, 91.7% cache hit rate

### Part 2: Comparative Analysis (Graphs 5-7)
- vs Microsoft SEAL (head-to-head)
- vs TenSEAL, OpenFHE (if available)
- **Critical Metrics:** 2× faster encryption, competitive homomorphic ops

### Part 3: Novel Contributions (Graphs 8-15)
- **RNS Compression:** 70-90% reduction, 149K ops/sec
- **Hybrid ORAM:** <2× overhead vs 100-1000× traditional
- **GPU Acceleration:** 10-50× speedup, multi-GPU scaling
- **Batch Packing:** 8-32× efficiency

### Part 4: Real-World Datasets (Graphs 16-18)
- Insurance data (7K rows)
- Financial transactions (50K rows)
- Healthcare records (100K rows, synthetic)
- IoT sensor data (1M rows)

### Part 5: Scalability (Graphs 19-20)
- Horizontal: 1-16 server nodes
- Vertical: CPU cores, RAM, GPU count

### Part 6: Robustness (Graphs 21-23)
- Stress testing: 10-10K concurrent clients
- Chaos testing: Failures, corruption, recovery
- Memory pressure, cache thrashing

### Part 7: Security (Table + Graph 24)
- Information leakage analysis
- Side-channel resistance
- Cryptographic strength validation

### Part 8-10: Additional Analysis (Graphs 25-60+)
- Cost-benefit analysis
- Usability metrics
- Ablation studies
- Competitive positioning

---

## Statistical Rigor

All benchmarks follow strict methodology:
- **Repetitions:** 10 runs minimum per test
- **Warmup:** 5 iterations discarded (JIT/cache cold start)
- **Confidence Interval:** 95%
- **Outlier Detection:** Remove >3 standard deviations
- **Hardware Isolation:** Dedicated machines, no background processes
- **Reporting:** Mean, Median, Std Dev, Min, Max, P95, P99

---

## Reproducibility Package

Each benchmark generates:
- Raw data (JSON/CSV with timestamps)
- Metadata (hardware specs, software versions)
- Analysis scripts (Jupyter notebooks)
- Visualizations (PDF/SVG, 300 DPI)
- Docker container specification
- Seed values for RNG

---

## Critical Success Metrics

### For Conference Paper:
1. ✅ 255× speedup on real workload (insurance data)
2. ✅ 6.7M ops/sec (cache lookups)
3. ✅ 91.7% cache hit rate
4. ✅ 2× faster encryption than SEAL
5. ✅ Competitive homomorphic operations

### For Patent (RNS Compression):
- 70-90% compression across key sizes (2048, 3072, 4096-bit)
- 149K compress ops/sec, 139K decompress ops/sec
- Mathematical proof: zero information loss
- Bandwidth savings in distributed systems

### For Patent (Hybrid ORAM):
- <2× overhead across all access patterns
- Lazy eviction efficiency
- IND-ORAM security proof
- Automatic mode selection validation

---

## Execution Timeline

### Week 1: Core Benchmarks
- Days 1-3: Micro-benchmarks, SEAL comparison
- Days 4-5: RNS compression, ORAM validation
- Days 6-7: GPU scaling, batch packing

### Week 2: Real-World Evaluation
- Days 8-10: Dataset evaluation (4 datasets)
- Days 11-12: Cache effectiveness, query performance
- Days 13-14: Sustained load, ablation studies

### Week 3: Scalability & Security
- Days 15-17: Horizontal/vertical scaling
- Days 18-19: Stress testing, chaos engineering
- Days 20-21: Security analysis, side-channel tests

### Week 4: Finalization
- Days 22-24: Polish graphs, statistical validation
- Days 25-27: Reproducibility package, Docker
- Days 28-30: Paper results section, artifact prep

---

## Output Formats

### Graphs:
- **Format:** PDF/SVG (vector, 300 DPI)
- **Colors:** Colorblind-friendly palette
- **Fonts:** Embedded, readable at paper size
- **Legends:** Clear, outside plot area
- **Error bars:** On all performance charts

### Tables:
- **LaTeX:** For paper inclusion
- **CSV:** For data analysis
- **Markdown:** For documentation

### Raw Data:
- **JSON:** Structured results with metadata
- **CSV:** Tabular data for analysis
- **Timestamps:** All measurements tagged
- **Metadata:** Hardware, software versions, seeds

---

## Hardware Requirements

### Minimum (Quick Tests):
- CPU: 4 cores, 2.5+ GHz
- RAM: 16GB
- Disk: 50GB SSD
- GPU: Optional (NVIDIA with CUDA 12.0+)

### Recommended (Full Suite):
- CPU: 16+ cores, 3.5+ GHz (AVX2 support)
- RAM: 64GB
- Disk: 500GB NVMe SSD
- GPU: NVIDIA RTX 3080+ or A100 (multiple GPUs for scaling tests)

### Ideal (Complete Evaluation):
- CPU: AMD EPYC or Intel Xeon (32+ cores)
- RAM: 128GB+
- Disk: 1TB NVMe SSD
- GPU: 4× NVIDIA A100 or V100
- Network: 10Gbps for distributed tests

---

## Contact & Support

For questions about the evaluation suite:
- **Documentation:** See individual benchmark files
- **Issues:** Check results/error_log.txt
- **Reproducibility:** Docker containers in evaluation_suite/docker/

---

## Citation

If you use this evaluation suite, please cite:

```bibtex
@inproceedings{agniya2026,
  title={AGNIYA: GPU-Accelerated Homomorphic Encryption with Multi-Level Caching and Novel RNS Compression},
  author={AGNIYA Team},
  booktitle={USENIX Security Symposium},
  year={2026}
}
```

---

## License

MIT License - Same as AGNIYA project
