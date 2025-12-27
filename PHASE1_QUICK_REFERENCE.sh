#!/bin/bash
# PHASE 1 QUICK REFERENCE CARD

cat << 'EOF'

╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║          PHASE 1: AGGRESSIVE ORAM GPU FOUNDATION - QUICK START           ║
║          RTX 4070 Laptop (8GB) on Linux                                  ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝


█ QUICK START (3 Steps)
═══════════════════════════════════════════════════════════════════════════

1. Make script executable:
   chmod +x /home/aditya/Documents/Agniya/agniya/phase1_complete_setup.sh

2. Run complete setup:
   cd /home/aditya/Documents/Agniya/agniya
   ./phase1_complete_setup.sh

3. Wait for all tests to pass (15-30 minutes)
   Look for: ✓ PHASE 1 SETUP COMPLETE AND VERIFIED!


█ WHAT GETS INSTALLED
═══════════════════════════════════════════════════════════════════════════

✓ CUDA 12.4 (if not present)
✓ cuDNN 8.9.7
✓ PyCUDA
✓ CuPy
✓ PyTorch with CUDA 12.4
✓ GPU utilities and profiling tools


█ GPU MEMORY ALLOCATION (8GB Total)
═══════════════════════════════════════════════════════════════════════════

ORAM Tree ................. 2.00GB (28%)
Hot Cache ................. 2.00GB (28%)
Batch Buffers ............. 1.50GB (21%)
Crypto Staging ............ 1.00GB (14%)
Position Map .............. 0.13GB (2%)
Eviction Queue ............ 0.50GB (7%)
─────────────────────────────────
Total Used ................ 7.13GB

Free Margin (Safety) ...... 0.50GB
─────────────────────────────────
Total System ............. 12.00GB


█ EXPECTED PERFORMANCE (From Benchmarks)
═══════════════════════════════════════════════════════════════════════════

Memory Bandwidth .......... 40-50 GB/s
Sync Latency .............. 0.2-0.5 ms
Stream Speedup ............ 3-4× (concurrent)
PCIe Bandwidth ............ 12-16 GB/s
Memory Clock .............. 2505 MHz


█ KEY FILES CREATED
═══════════════════════════════════════════════════════════════════════════

phase1_gpu_memory_manager.py ....... Core memory allocation
phase1_cpu_gpu_bridge.py ........... Async data transfers
phase1_benchmark_rtx4070.py ........ Performance testing
phase1_complete_setup.sh ........... Automated installation
PHASE_1_GUIDE.md ................... Detailed documentation


█ TESTING & VERIFICATION
═══════════════════════════════════════════════════════════════════════════

Check NVIDIA drivers:
  nvidia-smi

Check CUDA installation:
  nvcc --version

Verify GPU packages (after setup):
  python3 -c "import pycuda; import cupy; import torch; print('✓ OK')"

Run GPU Memory Manager test:
  cd /home/aditya/Documents/Agniya/agniya
  python3 phase1_gpu_memory_manager.py

Run CPU-GPU Bridge test:
  python3 phase1_cpu_gpu_bridge.py

Benchmark RTX 4070:
  python3 phase1_benchmark_rtx4070.py


█ TROUBLESHOOTING
═══════════════════════════════════════════════════════════════════════════

Problem: "No NVIDIA GPU detected"
→ Solution: Update drivers (nvidia-driver-550+)

Problem: "CUDA not found"
→ Solution: nvcc --version (if empty, CUDA not installed)

Problem: "PyCUDA ImportError"
→ Solution: pip install --verbose pycuda

Problem: "Out of GPU memory"
→ Solution: Reduce test sizes in benchmark script

Problem: cupy-cuda12x not found
→ Solution: pip install cupy-cuda12x (or pip install cupy)

See PHASE_1_GUIDE.md for detailed troubleshooting


█ NEXT STEPS (After Phase 1 Complete)
═══════════════════════════════════════════════════════════════════════════

Phase 1 creates foundation:
  ✓ GPU memory manager (8GB allocated)
  ✓ CPU-GPU bridge (async transfers)
  ✓ Benchmarking framework (performance tracking)

Phase 2 builds ORAM:
  → python3 phase2_compact_recursive_oram.py
  → Implements 2-level recursive ORAM
  → Target: 0.15-0.2ms per CPU access

Phase 3 accelerates with GPU:
  → GPU AES kernel
  → Parallel tree traversal
  → Target: 5-10× GPU speedup

Phase 4 integrates everything:
  → Multi-tier hybrid caching
  → Adaptive query planning
  → Target: 1.6× overhead (vs current)

Phase 5 final tuning:
  → NVIDIA Nsight profiling
  → Kernel optimization
  → Target: 15,000 ops/sec


█ ENVIRONMENT VARIABLES (After Setup)
═══════════════════════════════════════════════════════════════════════════

These are automatically added to ~/.bashrc:

export CUDA_HOME=/usr/local/cuda-12.4
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

To use immediately after setup:
  source ~/.bashrc


█ PERFORMANCE EXPECTATIONS
═══════════════════════════════════════════════════════════════════════════

Current Agniya: 20,000 ops/sec (0.41ms latency)

After Phase 1 baseline: CPU only
  → ORAM Foundation ready

After Phase 2 (CPU ORAM): 
  → 4,000 ops/sec (0.25ms latency)
  → CPU-optimized Path ORAM

After Phase 3 (GPU Acceleration):
  → 50,000 ops/sec potential (GPU-only)
  → But must integrate with caching

After Phase 4 (Hybrid ORAM):
  → 15,000 ops/sec (0.67ms latency)
  → Only 1.6× slower than current!

After Phase 5 (Tuned):
  → 15,000-18,000 ops/sec
  → Near-perfect frequency obliviousness
  → 1.2-1.6× overhead


█ SYSTEM REQUIREMENTS
═══════════════════════════════════════════════════════════════════════════

Hardware:
  ✓ RTX 4070 Laptop (8GB VRAM) - you have this
  ✓ CPU with 8+ cores
  ✓ 16GB+ system RAM
  ✓ SSD with 500GB space

Software:
  ✓ Linux (Ubuntu 20.04+, Debian, Fedora)
  ✓ Python 3.8+
  ✓ NVIDIA drivers 550+

Network:
  ✓ Internet for downloading CUDA & packages (~2GB)


█ FILE LOCATIONS
═══════════════════════════════════════════════════════════════════════════

Base directory:
  /home/aditya/Documents/Agniya/agniya

Phase 1 files:
  phase1_complete_setup.sh ........... Main setup script
  phase1_gpu_memory_manager.py ....... Core component
  phase1_cpu_gpu_bridge.py ........... Transfer bridge
  phase1_benchmark_rtx4070.py ........ Benchmarks
  PHASE_1_GUIDE.md ................... Full documentation

Virtual environment:
  /home/aditya/Documents/Agniya/agniya/venv/

Logs (if setup fails):
  Check terminal output for specific errors


█ SUPPORT & REFERENCE
═══════════════════════════════════════════════════════════════════════════

Read full documentation:
  cat PHASE_1_GUIDE.md

CUDA Documentation:
  https://docs.nvidia.com/cuda/

NVIDIA GPU Computing:
  https://developer.nvidia.com/cuda-toolkit

PyCUDA Documentation:
  https://documen.tician.de/pycuda/

RTX 4070 Specs:
  https://www.nvidia.com/en-us/geforce/graphics-cards/40-series/


█ VERIFICATION CHECKLIST
═══════════════════════════════════════════════════════════════════════════

After running phase1_complete_setup.sh, verify:

□ CUDA installed:          nvcc --version
□ nvidia-smi works:        nvidia-smi
□ PyCUDA installed:        python3 -c "import pycuda; print('OK')"
□ CuPy installed:          python3 -c "import cupy; print('OK')"
□ PyTorch installed:       python3 -c "import torch; print(torch.cuda.is_available())"
□ Memory manager works:    python3 phase1_gpu_memory_manager.py
□ Bridge works:            python3 phase1_cpu_gpu_bridge.py
□ Benchmarks run:          python3 phase1_benchmark_rtx4070.py


█ COMMAND REFERENCE
═══════════════════════════════════════════════════════════════════════════

# Setup
chmod +x phase1_complete_setup.sh
./phase1_complete_setup.sh

# Activate virtual environment
source venv/bin/activate

# Test GPU
nvidia-smi
python3 -c "import torch; print(torch.cuda.is_available())"

# Run individual tests
python3 phase1_gpu_memory_manager.py
python3 phase1_cpu_gpu_bridge.py
python3 phase1_benchmark_rtx4070.py

# Check GPU memory
gpu-memory-usage  # or equivalent command
nvidia-smi --query-gpu=memory.used,memory.free --format=csv

# Next phase
python3 phase2_compact_recursive_oram.py


═══════════════════════════════════════════════════════════════════════════
                    Ready to build aggressive ORAM? 🚀
═══════════════════════════════════════════════════════════════════════════

EOF
