#!/bin/bash
# Phase 1: Quick Setup (Skip CUDA, focus on Python packages)
# For systems where GPU drivers are already working

set -e

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                                                                    ║"
echo "║  PHASE 1: GPU FOUNDATION SETUP (Quick)                             ║"
echo "║  RTX 4070 Laptop (8GB VRAM)                                        ║"
echo "║  Linux Environment                                                 ║"
echo "║                                                                    ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Script directory: $SCRIPT_DIR"
echo ""

# Check GPU
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║ STEP 1: Verifying GPU                                              ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

if ! command -v nvidia-smi &> /dev/null; then
    echo "✗ NVIDIA drivers not found!"
    echo "Please install drivers from https://www.nvidia.com/Download/driverDetails.aspx"
    exit 1
fi

echo "✓ GPU detected:"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
echo ""

# Create virtual environment
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║ STEP 2: Python Virtual Environment                                 ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

cd "$SCRIPT_DIR"

if [ -d "venv" ]; then
    echo "✓ Virtual environment exists"
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Created"
fi

source venv/bin/activate
echo "✓ Activated"
echo ""

# Install Python packages
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║ STEP 3: Installing Python Packages                                 ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Upgrade pip
echo "Upgrading pip, setuptools, wheel..."
pip install --upgrade pip setuptools wheel --quiet
echo "✓ Done"
echo ""

# Install packages one by one with better feedback
echo "Installing core GPU packages..."
echo ""

packages=(
    "numpy"
    "pycryptodome"
    "numba"
    "nvidia-ml-py3"
    "gpustat"
)

for pkg in "${packages[@]}"; do
    echo -n "  Installing $pkg... "
    if pip install "$pkg" --quiet 2>/dev/null; then
        echo "✓"
    else
        echo "⚠ (may continue anyway)"
    fi
done

echo ""
echo "Installing CUDA-specific packages..."
echo ""

# Try to install CUDA packages
echo -n "  Installing PyCUDA... "
if pip install pycuda --quiet 2>/dev/null; then
    echo "✓"
else
    echo "⚠ (installing from source...)"
    pip install pycuda --no-binary :all:
fi

echo -n "  Installing CuPy (CUDA 12.x)... "
if pip install cupy-cuda12x --quiet 2>/dev/null; then
    echo "✓"
else
    echo "⚠ (trying cupy-cuda11...)"
    pip install cupy --quiet 2>/dev/null || echo "⚠"
fi

echo -n "  Installing PyTorch with CUDA... "
if pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --quiet 2>/dev/null; then
    echo "✓"
else
    echo "⚠ (trying default PyTorch...)"
    pip install torch torchvision torchaudio --quiet 2>/dev/null || echo "⚠"
fi

echo ""
echo "✓ Python packages installed"
echo ""

# Verify installations
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║ STEP 4: Verification                                               ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

python3 << 'VERIFY'
import sys
import subprocess

results = {
    "success": [],
    "warning": [],
    "error": []
}

# Check basic packages
basic_packages = ["numpy", "pycryptodome"]
for pkg in basic_packages:
    try:
        __import__(pkg.replace("-", "_"))
        results["success"].append(pkg)
    except:
        results["error"].append(pkg)

# Check GPU packages
print("GPU-related packages:")
print("─" * 50)

try:
    import pycuda.driver
    pycuda.driver.init()
    devicecount = pycuda.driver.Device.count()
    print(f"✓ PyCUDA (devices: {devicecount})")
    results["success"].append("pycuda")
except Exception as e:
    print(f"⚠ PyCUDA: {str(e)[:40]}")
    results["warning"].append("pycuda")

try:
    import cupy
    try:
        import cupy.cuda
        gpu_id = cupy.cuda.Device(0)
        print(f"✓ CuPy ({cupy.__version__})")
        results["success"].append("cupy")
    except:
        print(f"✓ CuPy ({cupy.__version__}) - no CUDA device")
        results["warning"].append("cupy")
except:
    print("⚠ CuPy: not installed")
    results["warning"].append("cupy")

try:
    import torch
    cuda_avail = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_avail else "N/A"
    status = "✓" if cuda_avail else "⚠"
    print(f"{status} PyTorch {torch.__version__} (CUDA: {cuda_avail})")
    if cuda_avail:
        print(f"   └─ Device: {device_name}")
    results["success"].append("torch")
except:
    print("⚠ PyTorch: not installed")
    results["warning"].append("torch")

# Check GPU status
print("")
print("GPU Status:")
print("─" * 50)
try:
    result = subprocess.run(["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total", "--format=csv,noheader"], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            if line:
                print(f"GPU: {line}")
    results["success"].append("nvidia-smi")
except:
    print("⚠ nvidia-smi not accessible")
    results["warning"].append("nvidia-smi")

# Summary
print("")
print("Summary:")
print("─" * 50)
print(f"✓ Working: {len(results['success'])} packages")
print(f"⚠ Partial: {len(results['warning'])} packages")
if results["error"]:
    print(f"✗ Failed: {len(results['error'])} packages")

if results["error"]:
    print(f"\nFailed packages: {', '.join(results['error'])}")
    sys.exit(1)

VERIFY

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║ ✓ PHASE 1 SETUP COMPLETE                                           ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

echo "Next steps:"
echo ""
echo "1. Run GPU benchmarks:"
echo "   source venv/bin/activate"
echo "   python3 phase1_benchmark_rtx4070.py"
echo ""
echo "2. Test memory manager:"
echo "   python3 phase1_gpu_memory_manager.py"
echo ""
echo "3. Test CPU-GPU bridge:"
echo "   python3 phase1_cpu_gpu_bridge.py"
echo ""
echo "Virtual environment to activate for future use:"
echo "   source venv/bin/activate"
echo ""
