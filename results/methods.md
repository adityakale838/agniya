# AGNIYA Benchmark Methodology

## Overview

This document describes the methodology for reproducing all benchmark results for patent filing purposes.

## Environment Setup

### Hardware Requirements
- CPU: Modern multi-core processor (tested on 10 cores)
- RAM: Minimum 8 GB (tested with 31.63 GB)
- Storage: Minimum 10 GB free space

### Software Requirements
- Python 3.10+
- Required packages: numpy, pandas, gmpy2, pycryptodome
- Git for version control

### Installation

```bash
# Clone repository
git clone https://github.com/adityakale838/agniya.git
cd agniya

# Create virtual environment
python -m venv envb
.\envb\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Benchmark Configurations

### Key Sizes
- 2048 bits (standard)
- 3072 bits (high security)
- 4096 bits (maximum security)

### Dataset Sizes
- 10^4 rows (small)
- 10^5 rows (medium)
- 10^6 rows (large)

### Distributions
- Uniform: Random values uniformly distributed
- Zipf(1.2): Skewed distribution
- High Unique: Mostly unique values

## Metrics Collection

### Latency
- Measured using `time.perf_counter()` for high precision
- Reported as p50, p90, p99 percentiles
- Units: milliseconds

### Throughput
- Calculated as 1 / mean_latency
- Units: operations per second

### Storage
- Ciphertext size in bytes
- Compression ratio
- Bandwidth reduction percentage

## Running Benchmarks

```bash
python scripts\patent_grade_benchmark.py
```

Results will be saved in `results/` directory.

## Statistical Rigor

- Each benchmark runs 1000 iterations
- Percentiles calculated using NumPy
- Outliers included (realistic worst-case)
- No warmup discarded (conservative measurement)

## Reproducibility Checklist

- [ ] Environment captured in `env/environment.txt`
- [ ] Git commit hash recorded
- [ ] All dependencies listed with versions
- [ ] Hardware specifications documented
- [ ] Random seeds fixed where applicable
- [ ] Raw data saved in CSV format
- [ ] Methodology documented

