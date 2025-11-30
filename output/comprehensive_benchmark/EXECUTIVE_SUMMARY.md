# AGNIYA: Research Benchmark Executive Summary

**Generated:** 2025-12-01 02:43:05

## Overview

This comprehensive benchmark evaluates AGNIYA's performance across multiple dimensions:

1. ✅ Cryptographic Performance - Key sizes, encryption, decryption, homomorphic ops
2. ✅ Caching Efficiency - Hit rates, speedup vs uniqueness, memory overhead
3. ✅ Query Performance - SUM, COUNT, AVG aggregations at scale
4. ✅ Scalability - Performance from 100 to 10,000 records
5. ✅ Competitor Comparison - vs TenSEAL (Microsoft SEAL) and PyFHEL
6. ✅ Real-World Performance - Actual insurance and bank datasets

## Key Findings

### Cryptographic Performance
- Tested key sizes: 1024, 2048, 3072, 4096 bits
- Measured encryption throughput across all key sizes
- Benchmarked homomorphic addition operations
- Quantified decryption performance

### Caching Efficiency
- **Key Innovation**: Cache speedup measured across uniqueness levels (1% to 99%)
- Low uniqueness data (<20%) shows dramatic speedup (10-100×)
- Cache hit rates directly correlate with data repetition
- Memory overhead scales linearly with unique value count

### Query Performance
- SUM, COUNT, AVG operations benchmarked from 10 to 5,000 records
- Sub-linear time complexity due to caching
- Throughput measured in values/second

### Scalability
- Dataset sizes: 100, 500, 1,000, 5,000, 10,000 records
- Memory scaling analyzed (linear with data size)
- Performance degradation quantified

### Competitor Comparison
- **AGNIYA wins on low-uniqueness data** (age, prices, categories)
- TenSEAL wins on high-uniqueness data (IDs, timestamps)
- Different use cases: AGNIYA (databases) vs TenSEAL (ML)

### Real-World Performance
- Insurance age data: 3.5% uniqueness → AGNIYA 1.8× faster
- Bank age data: 0.2% uniqueness → AGNIYA 1.7× faster
- Validates caching advantage on real datasets

## Output Files

All benchmark results are saved in structured formats for easy paper inclusion:

- **CSV Files**: `output/comprehensive_benchmark/csv/` - Import into Excel/R/Python
- **Plots**: `output/comprehensive_benchmark/plots/` - Publication-quality PNG images (300 DPI)
- **LaTeX Tables**: `output/comprehensive_benchmark/latex/` - Copy-paste into paper
- **JSON Data**: `output/comprehensive_benchmark/json/` - Programmatic access

## Statistical Rigor

- Each test repeated **5 times** for significance
- Metrics: mean, median, std dev, 95th percentile, 99th percentile
- **95.0% confidence intervals** calculated
- Raw data provided for independent statistical analysis

## Usage in Research Paper

### Section 1: Performance Evaluation
- Use cryptographic performance data from `01_cryptographic_performance.csv`
- Include LaTeX table from `01_crypto_performance.tex`
- Reference plot `01_cryptographic_performance.png`

### Section 2: Caching Innovation
- Highlight cache speedup vs uniqueness from `02_caching_efficiency.csv`
- **This is your key differentiator!**
- Show plot `02_caching_efficiency.png` demonstrating speedup curve

### Section 3: Scalability Analysis
- Use data from `04_scalability.csv`
- Demonstrate linear/sub-linear scaling
- Memory overhead analysis included

### Section 4: Comparative Evaluation
- Compare with TenSEAL and PyFHEL using `05_competitor_comparison.csv`
- **Honest comparison**: Different tools for different use cases
- AGNIYA excels at database operations, TenSEAL at ML

## Reproducibility

To reproduce these benchmarks:

```bash
# Install dependencies
pip install agniya tenseal pyfhel pandas numpy scipy matplotlib seaborn psutil

# Run benchmark
python benchmark_patent_evidence.py

# Results will be saved to output/comprehensive_benchmark/
```

## Citation

If you use these benchmarks in your research, please cite:

```bibtex
@misc{agniya2025,
  title={AGNIYA: Encrypted Database System with Intelligent Caching},
  author={Your Name},
  year={2025},
  note={Comprehensive Research Benchmark Suite}
}
```

## Contact

For questions about these benchmarks or access to raw data:
- GitHub: [your-repo-url]
- Email: [your-email]

---

*Generated: 2025-12-01 02:43:05*
