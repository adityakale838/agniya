#!/usr/bin/env python3
"""
Manual GPU Package Installation Guide
For users who want to add GPU acceleration after Phase 1
"""

import sys
import platform


def main():
    system = platform.system()
    
    print("\n" + "╔" + "═" * 70 + "╗")
    print("║" + " GPU PACKAGE INSTALLATION GUIDE ".center(70) + "║")
    print("║" + f" {system} ".center(70) + "║")
    print("╚" + "═" * 70 + "╝\n")
    
    print("These packages are OPTIONAL and can be added later if needed.")
    print("They take time to build from source.\n")
    
    print("╔ OPTION 1: Auto-Install from PyPI ════════════════════════════════╗\n")
    
    print("If you want pip to try installing (may fail on compilation):\n")
    
    if system == "Windows":
        print("  python -m pip install cupy-cuda12x")
        print("  python -m pip install torch --index-url https://download.pytorch.org/whl/cu124\n")
    else:
        print("  python -m pip install cupy-cuda12x")
        print("  python -m pip install torch --index-url https://download.pytorch.org/whl/cu124\n")
    
    print("Note: CuPy may take 10-30 minutes to compile from source.\n")
    
    print("╔ OPTION 2: Download Pre-Built Wheels (RECOMMENDED) ═══════════════╗\n")
    
    print("Pre-built wheels are faster and more reliable:\n")
    
    print("PyTorch (Official PyPI - pre-built):")
    print("  Link: https://download.pytorch.org/whl/cu124/")
    print("  On Windows: Download torch-*.whl matching your Python version")
    print("  On Linux: Download torch-*.whl matching your Python version")
    print("  Install: pip install /path/to/downloaded/torch-*.whl\n")
    
    print("CuPy (Conda recommended for pre-built):")
    print("  Link: https://anaconda.org/conda-forge/cupy")
    print("  If you use Conda: conda install -c conda-forge cupy cuda-12\n")
    
    print("╔ OPTION 3: Skip GPU Packages (Phase 1 Works Without Them) ════════╗\n")
    
    print("Phase 1 foundation works fine with just the essential packages:")
    print("  ✓ NumPy")
    print("  ✓ PyCryptodome")
    print("  ✓ Flask")
    print("  ✓ GPU drivers (nvidia-smi)\n")
    
    print("GPU packages are only needed if you:")
    print("  • Want to run Phase 2+ (Compact Recursive ORAM)")
    print("  • Want GPU acceleration for encryption")
    print("  • Want to run neural network models on GPU\n")
    
    print("For now, you can proceed with Phase 1 without them.\n")
    
    print("╔ WHAT YOU CAN DO RIGHT NOW (Without GPU Packages) ════════════════╗\n")
    
    print("With just the essential packages, you can:")
    print("  ✓ Run the existing Agniya application")
    print("  ✓ Use Paillier encryption")
    print("  ✓ Run Flask API server")
    print("  ✓ Process datasets with NumPy/Pandas\n")
    
    print("Test it:")
    if system == "Windows":
        print("  venv\\Scripts\\activate.bat")
    else:
        print("  source venv/bin/activate")
    print("  python examples/complete_workflow.py\n")
    
    print("╔ ADDING GPU PACKAGES LATER ═══════════════════════════════════════╗\n")
    
    print("You can always add GPU packages whenever you're ready:")
    print("  1. Activate your venv")
    print("  2. Run the install command from above")
    print("  3. Takes 10-30 minutes first time")
    print("  4. After that, all GPU features available\n")
    
    print("╔ CURRENT STATUS ═══════════════════════════════════════════════════╗\n")
    
    print("Phase 1 Foundation:")
    print("  ✓ GPU drivers: WORKING (nvidia-smi works)")
    print("  ✓ Essential packages: INSTALLED")
    print("  ✓ GPU acceleration: OPTIONAL (add later)\n")
    
    print("Next step: Use your system as-is, or add GPU packages when ready.\n")


if __name__ == "__main__":
    main()
