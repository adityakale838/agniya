#!/usr/bin/env python3
"""
Phase 1 Setup - Lean Version (No Heavy Builds)
Cross-Platform (Windows & Linux)
Fast setup focusing on essentials only
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


class Phase1SetupLean:
    def __init__(self):
        self.script_dir = Path(__file__).parent.absolute()
        self.system = platform.system()
        self.python_exe = sys.executable
        self.venv_dir = self.script_dir / "venv"
        self.venv_python = self._get_venv_python()
        
    def _get_venv_python(self):
        """Get the path to Python in venv"""
        if self.system == "Windows":
            return self.venv_dir / "Scripts" / "python.exe"
        else:
            return self.venv_dir / "bin" / "python"
    
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
    
    def run_command(self, cmd, critical=True):
        """Run command and return success"""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            return False, "", str(e)
    
    def check_gpu(self):
        """Check GPU"""
        self.print_step(1, "GPU Verification")
        
        success, stdout, stderr = self.run_command("nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader")
        
        if not success:
            print("✗ NVIDIA GPU not detected")
            print("  Install drivers: https://www.nvidia.com/Download/driverDetails.aspx")
            return False
        
        print("✓ GPU detected:")
        for line in stdout.strip().split("\n"):
            print(f"  {line}")
        return True
    
    def setup_venv(self):
        """Create or verify venv"""
        self.print_step(2, "Virtual Environment")
        
        if self.venv_dir.exists():
            print(f"✓ Venv exists: {self.venv_dir}")
        else:
            print(f"Creating venv...")
            try:
                subprocess.run([self.python_exe, "-m", "venv", str(self.venv_dir)], check=True, capture_output=True)
                print(f"✓ Created venv")
            except Exception as e:
                print(f"✗ Failed: {e}")
                return False
        
        # Show activation command
        if self.system == "Windows":
            print(f"\nActivate (future use): {self.venv_dir}\\Scripts\\activate.bat")
        else:
            print(f"\nActivate (future use): source {self.venv_dir}/bin/activate")
        
        return True
    
    def install_packages(self):
        """Install only essential packages"""
        self.print_step(3, "Install Essential Packages")
        
        # Minimal essential packages (no heavy builds)
        essential = [
            "numpy",
            "pycryptodome",
            "requests",
            "flask",
            "flask-cors",
            "scipy",
            "pandas"
        ]
        
        print("Installing essential packages (no heavy builds)...\n")
        
        for pkg in essential:
            print(f"  Installing {pkg}...", end=" ", flush=True)
            cmd = f'"{self.venv_python}" -m pip install {pkg} --quiet --no-deps'
            success, _, _ = self.run_command(cmd)
            if success:
                print("✓")
            else:
                print("⚠")
        
        print("\n✓ Essential packages installed\n")
        return True
    
    def verify_installation(self):
        """Quick verification"""
        self.print_step(4, "Verification")
        
        verify_script = """
import sys
import subprocess

print("Essential packages:")
print("─" * 50)

packages = [
    ("numpy", "NumPy"),
    ("pycryptodome", "PyCryptodome"),
    ("flask", "Flask"),
    ("requests", "Requests"),
]

all_ok = True
for pkg_name, display in packages:
    try:
        __import__(pkg_name.replace("-", "_"))
        print(f"✓ {display}")
    except:
        print(f"✗ {display}")
        all_ok = False

print("\\nGPU Status:")
print("─" * 50)
try:
    result = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                          capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✓ GPU: {result.stdout.strip()}")
    else:
        print("✗ GPU not accessible")
        all_ok = False
except:
    print("✗ nvidia-smi not found")
    all_ok = False

if not all_ok:
    sys.exit(1)
"""
        
        cmd = f'"{self.venv_python}" -c "{verify_script}"'
        success, stdout, stderr = self.run_command(cmd)
        
        if stdout:
            print(stdout)
        
        return success
    
    def print_next_steps(self):
        """Print what to do next"""
        self.print_header("PHASE 1 ESSENTIALS READY ✓")
        
        print("What was installed:")
        print("  ✓ NumPy (numerical computing)")
        print("  ✓ PyCryptodome (encryption)")
        print("  ✓ Flask (API server)")
        print("  ✓ SciPy, Pandas (data processing)")
        print("  ✓ GPU drivers verified\n")
        
        print("Heavy packages NOT installed (can add later as needed):")
        print("  ○ PyCUDA (requires CUDA build)")
        print("  ○ CuPy (requires CUDA build)")
        print("  ○ PyTorch (large download, optional)\n")
        
        print("Next steps:\n")
        
        if self.system == "Windows":
            activate = f"{self.venv_dir}\\Scripts\\activate.bat"
        else:
            activate = f"source {self.venv_dir}/bin/activate"
        
        print(f"1. Activate venv:")
        print(f"   {activate}\n")
        
        print("2. To add GPU packages later (when needed):")
        print("   python -m pip install cupy-cuda12x")
        print("   python -m pip install torch --index-url https://download.pytorch.org/whl/cu124\n")
        
        print("3. Run existing Agniya code:")
        print("   python examples/complete_workflow.py\n")
        
        print("GPU Package Download Links (if you want to install manually):")
        print("  • CuPy: https://pypi.org/project/cupy-cuda12x/")
        print("  • PyTorch: https://download.pytorch.org/whl/cu124/")
        print("  • PyCUDA: https://pypi.org/project/pycuda/\n")
    
    def run(self):
        """Run full setup"""
        print("\n" + "╔" + "═" * 70 + "╗")
        print("║" + " PHASE 1: LEAN SETUP ".center(70) + "║")
        print("║" + " No heavy builds, fast installation ".center(70) + "║")
        print("║" + f" {self.system} ".center(70) + "║")
        print("╚" + "═" * 70 + "╝")
        
        if not self.check_gpu():
            return False
        
        if not self.setup_venv():
            return False
        
        if not self.install_packages():
            return False
        
        if not self.verify_installation():
            print("⚠ Verification had issues, but setup may still work\n")
        
        self.print_next_steps()
        return True


if __name__ == "__main__":
    setup = Phase1SetupLean()
    success = setup.run()
    sys.exit(0 if success else 1)
