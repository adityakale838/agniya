# Comprehensive Benchmark Results

## 🚫 Large Files Not Included in Git

The following directories contain generated files that are **excluded from version control**:

- `csv/` - CSV data files (~0.01 MB each)
- `plots/` - Publication-quality PNG images (~0.1-0.3 MB each)
- `json/` - JSON data files (~0.01 MB each)
- `latex/` - LaTeX table files (~0.01 MB each)

**Total excluded:** ~1.5 MB of regenerable benchmark results

---

## 🔄 How to Regenerate Results

To reproduce all benchmark results on your machine:

### Prerequisites

```bash
# Activate virtual environment
.\envb\Scripts\Activate.ps1

# Install required packages (if not already installed)
pip install scipy matplotlib seaborn psutil
pip install tenseal pyfhel  # For competitor comparison
```

### Run Benchmark

```bash
# Run comprehensive benchmark suite
python benchmark_patent_evidence.py
```

**Time Required:** ~10-15 minutes depending on your CPU

### Output Generated

After running, you'll have:

- ✅ **6 CSV files** in `csv/` directory
- ✅ **5 PNG plots** in `plots/` directory (300 DPI, publication-ready)
- ✅ **LaTeX tables** in `latex/` directory
- ✅ **JSON data** in `json/` directory
- ✅ **Executive Summary** (EXECUTIVE_SUMMARY.md)

---

## 📊 What's Benchmarked

1. **Cryptographic Performance** - Key generation, encryption, decryption across 4 key sizes
2. **Caching Efficiency** - Cache speedup vs data uniqueness (1% to 99%)
3. **Query Performance** - SUM, COUNT, AVG operations (10 to 5,000 records)
4. **Scalability** - Performance from 100 to 10,000 records
5. **Competitor Comparison** - AGNIYA vs TenSEAL (Microsoft SEAL) and PyFHEL
6. **Real-World Performance** - Insurance and bank datasets

---

## 🎓 Usage in Research Paper

All outputs are **research-grade** and ready for publication:

- **CSV files** → Import into R/Python/Excel for analysis
- **PNG plots** → Insert directly into paper (300 DPI)
- **LaTeX tables** → Copy-paste into paper
- **EXECUTIVE_SUMMARY.md** → Overview for paper introduction

---

## 📝 Notes

- Results may vary slightly between runs due to system load
- Each test is repeated **5 times** for statistical significance
- **95% confidence intervals** are calculated
- Raw data is available in JSON format for custom analysis

---

## ⚠️ Why Files Are Excluded

These files are excluded from Git because:

1. **Regenerable** - Can be recreated by running the benchmark
2. **Large Binary Files** - PNG images are ~1.5 MB total
3. **System-Specific** - Results vary by CPU/memory
4. **Keeps Repo Clean** - Reduces repository size

To share results with collaborators, run the benchmark and send the `output/comprehensive_benchmark/` folder directly.
