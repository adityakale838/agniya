# 🚀 AGNIYA Setup Guide for Teammates

## Quick Start (5 minutes)

### Option 1: CPU-Only Mode (No GPU Required)
```bash
# Clone the repo
git clone <your-repo-url>
cd agniya

# Install dependencies
pip install -r requirements.txt

# Test the system
python test_all.py --quick
```

**Performance**: 17K ops/sec (excellent for most use cases)

---

### Option 2: Full GPU Acceleration (Recommended for Production)

#### Step 1: Install CUDA Toolkit
- **Download**: https://developer.nvidia.com/cuda-downloads
- **Check GPU**: Run `nvidia-smi` to verify GPU and CUDA version
- **CUDA 11.x or 12.x**: Note which version you have

#### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

#### Step 3: Install CuPy (GPU Library)
```bash
# For CUDA 11.x:
pip install cupy-cuda11x

# For CUDA 12.x:
pip install cupy-cuda12x
```

#### Step 4: Verify GPU Setup
```bash
python -c "import cupy as cp; print(f'GPU: {cp.cuda.Device().name}')"
```

#### Step 5: Run Tests
```bash
python test_all.py --quick
```

**Performance**: 6.7M ops/sec cache lookups (400× faster than CPU)

---

## 📦 What's Included

### Core Features
- ✅ **2048-bit Paillier Encryption**: Fully homomorphic addition
- ✅ **Multi-level Caching**: 251× speedup on repeated queries
- ✅ **SIMD Vectorization**: 2-4× array operation speedup (AVX2)
- ✅ **Batch Packing**: 28× speedup for bulk operations
- ✅ **Smart Precomputation**: 1000× speedup for powers

### GPU Optimizations (if GPU available)
- ✅ **GPU-Accelerated Encryption**: 5-10× faster operations
- ✅ **GPU ORAM**: 10-50× faster than CPU ORAM
- ✅ **GPU Pipeline**: Zero-copy memory transfers

### JIT Compilation
- ✅ **Numba JIT**: Automatic acceleration for compatible operations
- ⚠️ **Note**: Limited for 2048-bit integers, gracefully degrades

---

## 🔧 Troubleshooting

### "No module named 'cupy'"
**Solution**: CuPy is optional. System will auto-fallback to CPU mode (17K ops/sec).
```bash
# Install CuPy if you have a GPU:
pip install cupy-cuda11x  # or cupy-cuda12x
```

### "CUDA not found"
**Solution**: Install CUDA Toolkit from https://developer.nvidia.com/cuda-downloads

### "JIT compilation failed"
**Solution**: This is expected for 2048-bit operations. System continues with other optimizations.

### "gmpy2 installation failed"
**Solution**: 
- **Windows**: Download wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#gmpy
- **Linux**: `sudo apt-get install libgmp-dev libmpfr-dev libmpc-dev`
- **Mac**: `brew install gmp mpfr libmpc`

---

## 🏃 Running the System

### 1. Run Tests
```bash
# Quick test (5 tests, ~30 seconds)
python test_all.py --quick

# Full benchmark (includes performance tests)
python test_all.py --benchmark
```

### 2. Start Flask API Server
```bash
cd api
python server_optimized.py
```
Server runs on http://localhost:5000

### 3. Start Web Dashboard
```bash
cd webapp
npm install
npm run dev
```
Dashboard runs on http://localhost:3000

---

## 📊 Performance Expectations

| Configuration | Cache Lookups | Encryption Ops | ORAM Ops |
|--------------|---------------|----------------|----------|
| **CPU Only** | 17K/sec | 450/sec | 1K/sec |
| **CPU + JIT** | 85K/sec | 2K/sec | 1K/sec |
| **GPU + All** | 6.7M/sec | 5K/sec | 50K/sec |

---

## 🔒 Security Features

- ✅ **2048-bit Paillier**: Military-grade encryption
- ✅ **Path ORAM**: Access pattern obfuscation
- ✅ **Constant-time operations**: Side-channel resistant
- ✅ **Memory-safe**: Automatic cleanup of sensitive data

---

## 🌐 Deployment Options

See [HOSTING_OPTIONS.md](HOSTING_OPTIONS.md) for:
- Free tier options (Vercel, Render, Railway)
- GPU hosting (Azure, DigitalOcean)
- GitHub Student Pack benefits ($100-$200 credits)

---

## 📚 Documentation

- **Main README**: [README.md](README.md)
- **Hosting Guide**: [HOSTING_OPTIONS.md](HOSTING_OPTIONS.md)
- **API Documentation**: See `api/server_optimized.py`

---

## 🤝 Contributing

1. Install dev dependencies: `pip install pytest pytest-cov black flake8`
2. Run tests before committing: `python test_all.py`
3. Format code: `black .`
4. Check style: `flake8 agniya/`

---

## ❓ FAQ

**Q: Do I need a GPU?**  
A: No! System works great on CPU (17K ops/sec). GPU is optional for 400× speedup.

**Q: Which Python version?**  
A: Python 3.8+ required. Python 3.10+ recommended.

**Q: Can I run this in Docker?**  
A: Yes! Use nvidia/cuda base image for GPU support.

**Q: How much RAM needed?**  
A: Minimum 4GB. Recommended 8GB+ for large datasets.

**Q: Will it work on Mac M1/M2?**  
A: Yes, CPU mode works perfectly. GPU acceleration not available on Apple Silicon.

---

## 📞 Support

- **Issues**: Open a GitHub issue
- **Questions**: Check README.md and this guide first
- **Performance**: Run `python test_all.py --benchmark` and share results

---

## ✅ Quick Verification Checklist

After setup, verify:
- [ ] `python test_all.py --quick` passes all tests
- [ ] System shows "GPU enabled: True" or "CPU mode" message
- [ ] Flask API starts without errors
- [ ] Web dashboard loads correctly
- [ ] Can encrypt and query data successfully

**Setup complete!** 🎉
