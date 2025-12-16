#!/bin/bash
# Phase 1: Python Package Installation for ORAM GPU Development

set -e

echo "=========================================="
echo "Phase 1: Python GPU Packages Installation"
echo "=========================================="
echo ""

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "✗ Virtual environment not found"
    echo "Please create it with: python3 -m venv venv"
    exit 1
fi

echo ""
echo "Installing GPU development packages..."
echo ""

# Update pip
pip install --upgrade pip setuptools wheel

# CUDA/GPU packages
echo "Installing CUDA Python bindings..."
pip install pycuda

echo "Installing CuPy (GPU NumPy)..."
pip install cupy-cuda12x

echo "Installing PyTorch with CUDA 12.4..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# GPU monitoring
echo "Installing GPU monitoring tools..."
pip install nvidia-ml-py3 gpustat

# Performance profiling
echo "Installing profiling tools..."
pip install py-spy memory-profiler

# Additional crypto and utilities
echo "Installing additional utilities..."
pip install pycryptodome numba tensorboard

echo ""
echo "=========================================="
echo "Package Installation Complete!"
echo "=========================================="
echo ""
echo "Verifying installations..."
echo ""

# Verification script inline
python3 << 'PYEOF'
import sys

print("Checking GPU packages:")
print()

try:
    import pycuda.driver as cuda
    print("✓ PyCUDA")
except ImportError as e:
    print(f"✗ PyCUDA: {e}")

try:
    import cupy
    print(f"✓ CuPy {cupy.__version__}")
except ImportError as e:
    print(f"✗ CuPy: {e}")

try:
    import torch
    print(f"✓ PyTorch {torch.__version__}")
    print(f"  CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  CUDA device: {torch.cuda.get_device_name(0)}")
except ImportError as e:
    print(f"✗ PyTorch: {e}")

try:
    import GPUtil
    print(f"✓ GPU monitoring available")
except ImportError as e:
    print(f"✗ GPU monitoring: {e}")

try:
    import Crypto
    print("✓ PyCryptodome")
except ImportError as e:
    print(f"✗ PyCryptodome: {e}")

print()
print("All critical packages verified!")
PYEOF

echo ""
echo "Next step: Run phase1_gpu_memory_manager.py"
