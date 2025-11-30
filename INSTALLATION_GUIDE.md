# AGNIYA Library - Quick Installation Guide

## What Changed?

AGNIYA is now a **proper Python library** that you can import like NumPy or Pandas!

```python
import agniya as ag  # Just like numpy/pandas!

db = ag.Database()
result = db.sum([1, 2, 3, 4, 5])
print(result)  # 15
```

---

## Installation

### Option 1: Install from Source (Recommended)

```bash
# Navigate to project directory
cd g:\agniya

# Install in development mode
pip install -e .

# Or with all dependencies
pip install -e ".[all]"
```

### Option 2: Install Dependencies Only

```bash
pip install -r requirements_full.txt
```

---

## Usage

### Import AGNIYA

```python
import agniya as ag

# Initialize database
db = ag.Database(key_size=2048)

# Encrypt data
encrypted = db.encrypt([10, 20, 30])

# Perform operations
total = db.sum([10, 20, 30, 40, 50])
average = db.average([10, 20, 30, 40, 50])

print(f"Total: {total}")
print(f"Average: {average}")
```

### Run Examples

```bash
# Library usage examples
python examples_library_usage.py

# Unified test suite
python test_suite.py

# System verification
python verify_system.py
```

---

## File Structure

### What's New

```
agniya/
├── agniya/__init__.py          ← NEW: Main library API (like numpy)
├── setup.py                    ← NEW: pip installation
├── pyproject.toml              ← NEW: Modern Python packaging
├── test_suite.py               ← NEW: Unified tests (replaces 9 test files)
├── examples_library_usage.py   ← NEW: Usage examples
├── LIBRARY_USAGE.md            ← NEW: Library documentation
└── INSTALLATION_GUIDE.md       ← NEW: This file
```

### Removed (Consolidated)

```
✅ test_datetime_fix.py          → test_suite.py
✅ test_datetime_fix_detailed.py → test_suite.py
✅ test_entropy_simple.py        → test_suite.py
✅ test_entropy_aware.py         → test_suite.py
✅ test_novel_features.py        → test_suite.py
✅ test_tier2_fix.py             → test_suite.py
✅ test_upload_fix.py            → test_suite.py
✅ verify_all_fixes.py           → test_suite.py
✅ verify_end_to_end.py          → test_suite.py
```

### Kept

```
✅ verify_system.py              (System health check)
✅ test_suite.py                 (Unified test suite)
✅ tests/                        (Unit tests)
```

---

## API Overview

### High-Level API (Easy to Use)

```python
import agniya as ag

db = ag.Database()

# Basic operations
db.encrypt(value)
db.decrypt(ciphertext)
db.sum(data)
db.average(data)
db.count(data)
db.compress(ciphertext)
db.decompress(compressed)
db.warm_cache(values)
db.stats()
```

### Low-Level API (Advanced)

```python
from agniya.core.paillier import generate_keypair, encrypt, decrypt_crt
from agniya.compression.rns_compression import RNSCompression
from agniya.core.ultimate_system import UltimateOptimizedDatabase

# Manual key generation
public_key, private_key = generate_keypair(2048)

# Manual encryption
ciphertext = encrypt(public_key, 42)
plaintext = decrypt_crt(public_key, private_key, ciphertext)
```

---

## Node.js Frontend (Still Works!)

The web interface still works alongside the Python library:

```bash
# Terminal 1: Start Python API
cd api
python server_advanced.py

# Terminal 2: Start Next.js frontend
cd webapp
npm run dev
```

Open http://localhost:3000

---

## Testing

### Run Unified Test Suite

```bash
python test_suite.py
```

Tests cover:
- ✅ Key generation
- ✅ Encryption/decryption
- ✅ Homomorphic operations
- ✅ Caching
- ✅ RNS compression
- ✅ Entropy detection
- ✅ Aggregations (sum, average)
- ✅ Parallel processing
- ✅ Security properties
- ✅ Performance benchmarks

### Run System Verification

```bash
python verify_system.py
```

Checks:
- ✅ Python modules
- ✅ File structure
- ✅ Documentation
- ✅ Dependencies
- ✅ Frontend build

---

## Examples

### Example 1: Basic Usage

```python
import agniya as ag

db = ag.Database(key_size=2048)

# Encrypt
encrypted = db.encrypt(42)
print(f"Encrypted: {str(encrypted)[:50]}...")

# Decrypt
decrypted = db.decrypt(encrypted)
print(f"Decrypted: {decrypted}")
```

### Example 2: Privacy-Preserving Analytics

```python
# Hospital scenario
patient_ages = [25, 34, 45, 56, 67, 78, 23, 45, 56, 34]

# Compute average without revealing individual ages
avg_age = db.average(patient_ages)
print(f"Average age: {avg_age:.1f}")  # No individual data exposed!
```

### Example 3: Performance (Caching)

```python
# Warm cache with common values
common_prices = [9.99, 19.99, 29.99, 49.99, 99.99]
db.warm_cache(common_prices)

# Now queries are 1000× faster!
sales = common_prices * 100
total = db.sum(sales)  # Super fast!
```

---

## Documentation

- **Library Usage**: `LIBRARY_USAGE.md`
- **Installation**: `INSTALLATION_GUIDE.md` (this file)
- **Examples**: `examples_library_usage.py`
- **API Reference**: `agniya/__init__.py` (docstrings)
- **Research**: `RESEARCH_AND_PATENT_SUMMARY.md`
- **Security**: `SECURITY_ANALYSIS_SUMMARY.md`
- **C++ Performance**: `CPP_PERFORMANCE_ANALYSIS.md`
- **Python vs C++**: `docs/WHY_PYTHON_NOT_CPP.md`

---

## Quick Start Checklist

1. **Install library**:
   ```bash
   pip install -e .
   ```

2. **Run tests**:
   ```bash
   python test_suite.py
   ```

3. **Try examples**:
   ```bash
   python examples_library_usage.py
   ```

4. **Use in your code**:
   ```python
   import agniya as ag
   db = ag.Database()
   result = db.sum([1, 2, 3, 4, 5])
   ```

5. **Start web interface** (optional):
   ```bash
   python api/server_advanced.py  # Terminal 1
   cd webapp && npm run dev        # Terminal 2
   ```

---

## Troubleshooting

### Import Error: "No module named 'agniya'"

```bash
# Solution: Install in development mode
pip install -e .
```

### GMPY2 Installation Issues

```bash
# Windows
pip install gmpy2

# If fails, download wheel from:
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#gmpy
pip install gmpy2‑2.1.5‑cp311‑cp311‑win_amd64.whl
```

### Test Failures

```bash
# Check system health first
python verify_system.py

# Then run tests
python test_suite.py
```

---

## Summary

**Before**: 9 scattered test files, no pip installation, manual imports

**After**: 
- ✅ One unified `test_suite.py`
- ✅ `pip install` support
- ✅ Simple API: `import agniya as ag`
- ✅ NumPy/Pandas-style usage
- ✅ Comprehensive examples
- ✅ Full documentation

**Use it like**:
```python
import agniya as ag  # Just like numpy!
db = ag.Database()
result = db.sum([1, 2, 3, 4, 5])
```

---

**🎉 AGNIYA is now a proper Python library!**
