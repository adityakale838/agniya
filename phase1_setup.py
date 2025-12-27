#!/usr/bin/env python3
"""
Phase 1 Setup Script - Cross-Platform (Windows & Linux)
RTX 4070 Laptop GPU Foundation Setup
"""

import os
import sys
import subprocess
import platform
import shutil
import json
from pathlib import Path


class Phase1Setup:
    def __init__(self):
        self.script_dir = Path(__file__).parent.absolute()
        self.system = platform.system()  # 'Windows', 'Linux', 'Darwin'
        self.python_exe = sys.executable
        self.venv_dir = self.script_dir / "venv"
        self.venv_python = self._get_venv_python()
        self.is_in_venv = self._check_venv()
        
    def _get_venv_python(self):
        """Get the path to Python in venv"""
        if self.system == "Windows":
            return self.venv_dir / "Scripts" / "python.exe"
        else:
            return self.venv_dir / "bin" / "python"
    
    def _check_venv(self):
        """Check if we're already in a venv"""
        return hasattr(sys, 'real_prefix') or (
            hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
        )
    
    def print_header(self, title):
        """Print formatted header"""
        print("\n" + "╔" + "═" * 70 + "╗")
        print("║ " + title.center(68) + " ║")
        print("╚" + "═" * 70 + "╝\n")
    
    def print_step(self, step_num, title):
        """Print step header"""
        print(f"\n{'─' * 72}")
        print(f"STEP {step_num}: {title}")
        print(f"{'─' * 72}\n")
    
    def run_command(self, cmd, description, critical=True, show_output=False):
        """Run a command and return success status"""
        try:
            if show_output:
                result = subprocess.run(cmd, shell=True)
                return result.returncode == 0
            else:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0 and critical:
                    print(f"✗ {description}")
                    if result.stderr:
                        print(f"  Error: {result.stderr[:200]}")
                    return False
                print(f"✓ {description}")
                return True
        except Exception as e:
            print(f"✗ {description}: {str(e)}")
            return critical
    
    def check_gpu(self):
        """Check if GPU and drivers are available"""
        self.print_step(1, "GPU Verification")
        
        # Check nvidia-smi
        result = subprocess.run(
            "nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print("✗ NVIDIA GPU not detected")
            print("  Please install NVIDIA drivers from:")
            print("  https://www.nvidia.com/Download/driverDetails.aspx")
            return False
        
        print("✓ GPU detected:")
        for line in result.stdout.strip().split("\n"):
            print(f"  {line}")
        return True
    
    def setup_venv(self):
        """Create or verify virtual environment"""
        self.print_step(2, "Python Virtual Environment")
        
        if self.venv_dir.exists():
            print(f"✓ Virtual environment exists at: {self.venv_dir}")
        else:
            print(f"Creating virtual environment at: {self.venv_dir}")
            try:
                subprocess.run(
                    [self.python_exe, "-m", "venv", str(self.venv_dir)],
                    check=True
                )
                print(f"✓ Virtual environment created")
            except Exception as e:
                print(f"✗ Failed to create venv: {e}")
                return False
        
        # Print activation command
        if self.system == "Windows":
            activate_cmd = f"{self.venv_dir}\\Scripts\\activate.bat"
            print(f"\nTo activate in future sessions, run:")
            print(f"  {activate_cmd}")
        else:
            activate_cmd = f"source {self.venv_dir}/bin/activate"
            print(f"\nTo activate in future sessions, run:")
            print(f"  {activate_cmd}")
        
        return True
    
    def upgrade_pip(self):
        """Upgrade pip, setuptools, wheel"""
        self.print_step(3, "Upgrade pip and tools")
        
        print("Upgrading pip, setuptools, wheel...")
        cmd = f'"{self.venv_python}" -m pip install --upgrade pip setuptools wheel'
        return self.run_command(cmd, "Updated pip tools", critical=False, show_output=False)
    
    def install_packages(self):
        """Install required packages"""
        self.print_step(4, "Install Python Packages")
        
        # Base packages
        base_packages = [
            "numpy",
            "pycryptodome",
            "numba",
            "nvidia-ml-py3",
            "gpustat",
            "requests",
            "flask",
            "flask-cors"
        ]
        
        print("Installing base packages...")
        for pkg in base_packages:
            cmd = f'"{self.venv_python}" -m pip install {pkg} --quiet'
            self.run_command(cmd, f"  ✓ {pkg}", critical=False)
        
        # GPU-specific packages
        print("\nInstalling GPU packages...")
        
        # PyCUDA
        print("  Installing PyCUDA...")
        cmd = f'"{self.venv_python}" -m pip install pycuda --quiet'
        if not self.run_command(cmd, "    ✓ PyCUDA", critical=False):
            print("    ⚠ PyCUDA installation skipped (optional)")
        
        # CuPy
        print("  Installing CuPy...")
        # Try CUDA 12.x first, then fallback
        cmd = f'"{self.venv_python}" -m pip install cupy-cuda12x --quiet'
        if not self.run_command(cmd, "    ✓ CuPy (CUDA 12.x)", critical=False):
            cmd = f'"{self.venv_python}" -m pip install cupy --quiet'
            if not self.run_command(cmd, "    ✓ CuPy (generic)", critical=False):
                print("    ⚠ CuPy installation skipped (optional)")
        
        # PyTorch with CUDA
        print("  Installing PyTorch...")
        if self.system == "Windows":
            # Windows PyTorch with CUDA
            cmd = f'"{self.venv_python}" -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --quiet'
        else:
            # Linux PyTorch with CUDA
            cmd = f'"{self.venv_python}" -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --quiet'
        
        if not self.run_command(cmd, "    ✓ PyTorch", critical=False):
            print("    ⚠ PyTorch installation skipped (optional)")
        
        print("\n✓ Package installation complete")
        return True
    
    def verify_installation(self):
        """Verify all installations"""
        self.print_step(5, "Verify Installation")
        
        verification_script = """
import sys
import subprocess

results = {"success": [], "warning": [], "error": []}

# Test basic packages
print("Basic packages:")
print("─" * 50)

packages_basic = [
    ("numpy", "NumPy"),
    ("pycryptodome", "PyCryptodome"),
    ("flask", "Flask"),
]

for pkg_name, pkg_display in packages_basic:
    try:
        __import__(pkg_name.replace("-", "_"))
        print(f"✓ {pkg_display}")
        results["success"].append(pkg_name)
    except:
        print(f"✗ {pkg_display}")
        results["error"].append(pkg_name)

# Test GPU packages
print("\\nGPU packages:")
print("─ * 50)

try:
    import pycuda.driver
    pycuda.driver.init()
    device_count = pycuda.driver.Device.count()
    print(f"✓ PyCUDA ({device_count} device(s))")
    results["success"].append("pycuda")
except Exception as e:
    print(f"⚠ PyCUDA: {str(e)[:40]}")
    results["warning"].append("pycuda")

try:
    import cupy
    print(f"✓ CuPy {cupy.__version__}")
    results["success"].append("cupy")
except:
    print("⚠ CuPy: not available")
    results["warning"].append("cupy")

try:
    import torch
    cuda_available = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_available else "N/A"
    status = "✓" if cuda_available else "⚠"
    print(f"{status} PyTorch {torch.__version__} (CUDA: {cuda_available})")
    if cuda_available:
        print(f"   └─ Device: {device_name}")
    results["success"].append("torch")
except:
    print("⚠ PyTorch: not available")
    results["warning"].append("torch")

# Check GPU status
print("\\nGPU Status:")
print("─" * 50)
try:
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total", "--format=csv,noheader"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        for line in result.stdout.strip().split("\\n"):
            if line:
                print(f"GPU: {line}")
    results["success"].append("nvidia-smi")
except:
    print("⚠ nvidia-smi: not accessible")
    results["warning"].append("nvidia-smi")

# Summary
print("\\nSummary:")
print("─" * 50)
print(f"✓ Working: {len(results['success'])} items")
print(f"⚠ Warnings: {len(results['warning'])} items")
if results["error"]:
    print(f"✗ Failed: {len(results['error'])} items")
    sys.exit(1)
"""
        
        # Run verification in venv
        cmd = f'"{self.venv_python}" -c "{verification_script}"'
        return self.run_command(cmd, "Verification passed", critical=False, show_output=True)
    
    def print_summary(self):
        """Print completion summary"""
        self.print_header("PHASE 1 SETUP COMPLETE ✓")
        
        print("Next steps:\n")
        
        if self.system == "Windows":
            venv_activate = f"cd /d {self.venv_dir}\\..\\.. && {self.venv_dir}\\Scripts\\activate.bat"
        else:
            venv_activate = f"source {self.venv_dir}/bin/activate"
        
        print("1. Activate virtual environment:")
        print(f"   {venv_activate}\n")
        
        print("2. Test GPU memory manager:")
        print(f"   python phase1_gpu_memory_manager.py\n")
        
        print("3. Test CPU-GPU bridge:")
        print(f"   python phase1_cpu_gpu_bridge.py\n")
        
        print("4. Run GPU benchmarks:")
        print(f"   python phase1_benchmark_rtx4070.py\n")
        
        print("GPU foundation is ready for Phase 2 (Compact Recursive ORAM)")
    
    def run(self):
        """Run full setup"""
        print("\n" + "╔" + "═" * 70 + "╗")
        print("║" + " PHASE 1: GPU FOUNDATION SETUP ".center(70) + "║")
        print("║" + " RTX 4070 Laptop (8GB VRAM) ".center(70) + "║")
        print("║" + f" {self.system} Environment ".center(70) + "║")
        print("╚" + "═" * 70 + "╝")
        
        # Run steps
        if not self.check_gpu():
            return False
        
        if not self.setup_venv():
            return False
        
        if not self.upgrade_pip():
            print("⚠ pip upgrade had issues, continuing anyway...\n")
        
        if not self.install_packages():
            return False
        
        if not self.verify_installation():
            print("\n⚠ Some warnings during verification, but may still work\n")
        
        self.print_summary()
        return True


if __name__ == "__main__":
    setup = Phase1Setup()
    success = setup.run()
    sys.exit(0 if success else 1)
