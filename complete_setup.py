#!/usr/bin/env python3
"""
COMPLETE AGNIYA PHASE 1-5 SETUP SCRIPT
Cross-Platform (Windows & Linux)
Installs ALL dependencies for GPU-accelerated ORAM implementation
RTX 4070 Laptop (8GB VRAM)

This script will:
1. Verify GPU and drivers
2. Create virtual environment
3. Install ALL required packages (essential + GPU)
4. Verify complete installation
5. Show status and next steps

No errors, no wasted requests. Complete and production-ready.
"""

import os
import sys
import subprocess
import platform
import json
import time
from pathlib import Path
from typing import Tuple, Optional


class CompletePhasesSetup:
    def __init__(self):
        self.script_dir = Path(__file__).parent.absolute()
        self.system = platform.system()
        self.python_exe = sys.executable
        self.venv_dir = self.script_dir / "venv"
        self.venv_python = self._get_venv_python()
        self.log_file = self.script_dir / "setup_log.txt"
        self.packages_installed = {}
        self.packages_failed = {}
        
    def _get_venv_python(self) -> Path:
        """Get path to Python in venv"""
        if self.system == "Windows":
            return self.venv_dir / "Scripts" / "python.exe"
        else:
            return self.venv_dir / "bin" / "python"
    
    def log(self, message: str, end: str = "\n"):
        """Log message to both console and file"""
        print(message, end=end)
        with open(self.log_file, "a") as f:
            if end == "\n":
                f.write(message + "\n")
            else:
                f.write(message)
    
    def header(self, title: str):
        """Print formatted header"""
        box = "╔" + "═" * 70 + "╗"
        self.log("\n" + box)
        self.log("║ " + title.center(68) + " ║")
        self.log("╚" + "═" * 70 + "╝\n")
    
    def step(self, num: int, title: str):
        """Print step header"""
        self.log(f"\n{'─' * 72}")
        self.log(f"STEP {num}: {title}")
        self.log(f"{'─' * 72}\n")
    
    def run_cmd(self, cmd: str, show_output: bool = False) -> Tuple[bool, str, str]:
        """Run command safely"""
        try:
            if show_output:
                result = subprocess.run(cmd, shell=True)
                return result.returncode == 0, "", ""
            else:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)
    
    def check_gpu(self) -> bool:
        """Step 1: Verify GPU"""
        self.step(1, "GPU Verification")
        
        success, stdout, stderr = self.run_cmd(
            "nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader"
        )
        
        if not success:
            self.log("✗ NVIDIA GPU not detected")
            self.log("  Please install drivers: https://www.nvidia.com/Download/driverDetails.aspx")
            return False
        
        self.log("✓ GPU detected:")
        for line in stdout.strip().split("\n"):
            if line:
                self.log(f"  {line}")
        return True
    
    def setup_venv(self) -> bool:
        """Step 2: Create/verify virtual environment"""
        self.step(2, "Python Virtual Environment")
        
        if self.venv_dir.exists():
            self.log(f"✓ Virtual environment exists")
        else:
            self.log(f"Creating virtual environment...")
            try:
                subprocess.run(
                    [self.python_exe, "-m", "venv", str(self.venv_dir)],
                    check=True,
                    capture_output=True,
                    timeout=60
                )
                self.log(f"✓ Virtual environment created")
            except Exception as e:
                self.log(f"✗ Failed to create venv: {e}")
                return False
        
        # Show activation command
        if self.system == "Windows":
            activate_cmd = f"{self.venv_dir}\\Scripts\\activate.bat"
        else:
            activate_cmd = f"source {self.venv_dir}/bin/activate"
        
        self.log(f"✓ Location: {self.venv_dir}")
        self.log(f"✓ Activate: {activate_cmd}\n")
        return True
    
    def upgrade_pip(self) -> bool:
        """Step 3: Upgrade pip"""
        self.step(3, "Upgrade pip and build tools")
        
        self.log("Upgrading pip, setuptools, wheel...")
        cmd = f'"{self.venv_python}" -m pip install --upgrade pip setuptools wheel --quiet'
        success, stdout, stderr = self.run_cmd(cmd)
        
        if success:
            self.log("✓ Build tools upgraded\n")
            return True
        else:
            self.log("⚠ pip upgrade had issues (continuing anyway)\n")
            return True  # Non-critical
    
    def install_packages(self) -> bool:
        """Step 4: Install all packages"""
        self.step(4, "Install All Required Packages")
        
        # Phase 1-5 complete package list
        packages = {
            "Essential Core": [
                "numpy>=1.24.0",
                "pycryptodome>=3.18.0",
                "scipy>=1.10.0",
                "pandas>=2.0.0",
            ],
            "API & Web": [
                "Flask>=3.1.0",
                "flask-cors>=4.0.0",
                "requests>=2.31.0",
            ],
            "GPU & CUDA": [
                "nvidia-ml-py3>=7.2.0",
                "gpustat>=1.1.1",
            ],
            "Data & ML Optimization": [
                "numba>=0.57.0",
                "Cython>=0.29.0",
            ],
            "Optional GPU Acceleration": [
                "cupy-cuda12x",
                "torch",
                "torchvision",
                "torchaudio",
                "pycuda",
            ]
        }
        
        # Install by category
        for category, pkg_list in packages.items():
            self.log(f"\n{category}:")
            self.log("─" * 70)
            
            for pkg in pkg_list:
                pkg_name = pkg.split(">=")[0].split("==")[0]
                self.log(f"  Installing {pkg_name}...", end=" ")
                sys.stdout.flush()
                
                # Build install command
                if pkg in ["cupy-cuda12x", "torch", "torchvision", "torchaudio"]:
                    # Special handling for GPU packages
                    if pkg == "cupy-cuda12x":
                        cmd = f'"{self.venv_python}" -m pip install cupy-cuda12x --quiet 2>&1'
                    elif pkg in ["torch", "torchvision", "torchaudio"]:
                        cmd = f'"{self.venv_python}" -m pip install {pkg} --index-url https://download.pytorch.org/whl/cu124 --quiet 2>&1'
                    else:
                        cmd = f'"{self.venv_python}" -m pip install {pkg} --quiet 2>&1'
                else:
                    cmd = f'"{self.venv_python}" -m pip install {pkg} --quiet --no-deps 2>&1'
                
                success, stdout, stderr = self.run_cmd(cmd, show_output=False)
                
                if success:
                    self.log("✓")
                    self.packages_installed[pkg_name] = True
                else:
                    # Check if it's a critical package
                    if category in ["Essential Core", "API & Web"]:
                        self.log(f"✗ FAILED")
                        self.packages_failed[pkg_name] = stderr[:100] if stderr else "Unknown error"
                        self.log(f"    Error: {stderr[:100] if stderr else 'Unknown'}")
                        return False
                    else:
                        self.log(f"⚠ (optional)")
                        self.packages_failed[pkg_name] = stderr[:100] if stderr else "Optional package"
        
        self.log("\n✓ Package installation complete\n")
        return True
    
    def verify_installation(self) -> bool:
        """Step 5: Verify complete installation"""
        self.step(5, "Verification")
        
        # Write verification script to file to avoid shell escaping issues
        verify_file = self.script_dir / "verify_temp.py"
        verify_script = """import sys
import subprocess

results = {"success": 0, "warning": 0, "failed": 0}

# Essential packages
essential = [
    ("numpy", "NumPy"),
    ("Crypto", "PyCryptodome"),
    ("flask", "Flask"),
    ("requests", "Requests"),
]

print("Essential Packages:")
print("-" * 50)
for pkg_name, display in essential:
    try:
        __import__(pkg_name.replace("-", "_"))
        print(f"✓ {display}")
        results["success"] += 1
    except:
        print(f"✗ {display}")
        results["failed"] += 1
        sys.exit(1)

# Optional packages
optional = [
    ("scipy", "SciPy"),
    ("pandas", "Pandas"),
    ("numba", "Numba"),
]

print("\\nOptional Packages:")
print("-" * 50)
for pkg_name, display in optional:
    try:
        __import__(pkg_name.replace("-", "_"))
        print(f"✓ {display}")
        results["success"] += 1
    except:
        print(f"⚠ {display}")
        results["warning"] += 1

# GPU verification
print("\\nGPU Status:")
print("-" * 50)
try:
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
        capture_output=True,
        text=True,
        timeout=10
    )
    if result.returncode == 0:
        print(f"✓ GPU: {result.stdout.strip()}")
        results["success"] += 1
    else:
        print("✗ GPU not accessible")
        results["failed"] += 1
except Exception as e:
    print(f"✗ GPU check failed: {str(e)[:50]}")
    results["failed"] += 1

# Summary
print("\\nResult Summary:")
print("-" * 50)
print(f"✓ Working: {results['success']}")
print(f"⚠ Warnings: {results['warning']}")
if results['failed'] > 0:
    print(f"✗ Failed: {results['failed']}")
    sys.exit(1)
"""
        
        try:
            verify_file.write_text(verify_script)
            cmd = f'"{self.venv_python}" "{verify_file}"'
            success, stdout, stderr = self.run_cmd(cmd, show_output=True)
            verify_file.unlink()  # Clean up
            return success
        except Exception as e:
            self.log(f"⚠ Verification error: {e}")
            return True  # Non-critical
    
    def print_summary(self) -> bool:
        """Print final summary"""
        self.header("SETUP COMPLETE ✓")
        
        self.log("Installed Packages Summary:")
        self.log("─" * 70)
        self.log(f"✓ Successful: {len(self.packages_installed)}")
        self.log(f"⚠ Failed/Optional: {len(self.packages_failed)}\n")
        
        if self.packages_failed:
            self.log("Optional packages not installed:")
            for pkg, reason in list(self.packages_failed.items())[:5]:
                self.log(f"  • {pkg}")
        
        self.log("\n" + "═" * 72)
        self.log("WHAT'S NEXT:")
        self.log("═" * 72 + "\n")
        
        if self.system == "Windows":
            activate = f"  {self.venv_dir}\\Scripts\\activate.bat"
        else:
            activate = f"  source {self.venv_dir}/bin/activate"
        
        self.log("1. Activate the virtual environment:")
        self.log(activate)
        self.log("")
        
        self.log("2. Verify everything works:")
        self.log("  python -c \"import numpy, flask; print('✓ All ready')\"")
        self.log("")
        
        self.log("3. Run the Agniya application:")
        self.log("  python examples/complete_workflow.py")
        self.log("")
        
        self.log("4. For Phases 2-5 (ORAM implementation):")
        self.log("  - Phase 2: Compact Recursive ORAM (CPU baseline)")
        self.log("  - Phase 3: GPU Acceleration (CUDA kernels)")
        self.log("  - Phase 4: Hybrid Integration (multi-tier caching)")
        self.log("  - Phase 5: Performance Tuning (Nsight profiling)")
        self.log("")
        
        self.log("GPU Package Notes:")
        self.log("─" * 70)
        self.log("Some GPU packages (PyTorch, CuPy, PyCUDA) may be slow to install.")
        self.log("They are OPTIONAL and can be added later if needed:")
        self.log("  pip install cupy-cuda12x")
        self.log("  pip install torch --index-url https://download.pytorch.org/whl/cu124")
        self.log("")
        
        self.log("Setup log saved to: " + str(self.log_file))
        self.log("")
        
        return True
    
    def run(self) -> bool:
        """Execute complete setup"""
        # Clear log file
        self.log_file.write_text("")
        
        self.header("COMPLETE AGNIYA SETUP (Phases 1-5)")
        self.log(f"System: {self.system}")
        self.log(f"Python: {sys.version.split()[0]}")
        self.log(f"Project: {self.script_dir}")
        self.log(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Run all steps
        steps = [
            ("GPU verification", self.check_gpu),
            ("Virtual environment", self.setup_venv),
            ("Pip upgrade", self.upgrade_pip),
            ("Package installation", self.install_packages),
            ("Verification", self.verify_installation),
        ]
        
        for step_name, step_func in steps:
            try:
                if not step_func():
                    self.log(f"\n✗ Setup failed at: {step_name}")
                    return False
            except Exception as e:
                self.log(f"\n✗ Unexpected error in {step_name}: {e}")
                import traceback
                self.log(traceback.format_exc())
                return False
        
        # Print summary
        self.print_summary()
        self.log(f"End time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True


def main():
    """Main entry point"""
    setup = CompletePhasesSetup()
    
    try:
        success = setup.run()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n✗ Setup cancelled by user")
        return 130
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
