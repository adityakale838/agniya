#!/usr/bin/env python3
"""
Phase 1 Quick Start Guide - Cross-Platform
Windows & Linux compatible
"""

import sys
import platform


def main():
    system = platform.system()
    
    print("\n" + "╔" + "═" * 70 + "╗")
    print("║" + " PHASE 1 QUICK START GUIDE ".center(70) + "║")
    print("║" + f" {system} Environment ".center(70) + "║")
    print("╚" + "═" * 70 + "╝\n")
    
    print("STEP 1: Initial Setup")
    print("─" * 72)
    print("\nRun the setup script (one time only):\n")
    print("  python phase1_setup.py\n")
    print("This will:")
    print("  ✓ Verify GPU and drivers")
    print("  ✓ Create Python virtual environment")
    print("  ✓ Install GPU packages (PyCUDA, CuPy, PyTorch, etc)")
    print("  ✓ Verify all installations\n")
    
    print("STEP 2: Activate Virtual Environment")
    print("─" * 72)
    if system == "Windows":
        print("\nOn Windows, run:\n")
        print("  venv\\Scripts\\activate.bat\n")
        print("Or PowerShell:\n")
        print("  venv\\Scripts\\Activate.ps1\n")
    else:
        print("\nOn Linux/Mac, run:\n")
        print("  source venv/bin/activate\n")
    
    print("STEP 3: Run Tests")
    print("─" * 72)
    print("\nAfter activating venv, run all tests:\n")
    print("  python phase1_test_all.py\n")
    print("Or run individually:\n")
    print("  python phase1_gpu_memory_manager.py")
    print("  python phase1_cpu_gpu_bridge.py")
    print("  python phase1_benchmark_rtx4070.py\n")
    
    print("STEP 4: Verify Output")
    print("─" * 72)
    print("\nExpected results:")
    print("  ✓ GPU Memory Manager: Shows 7.128GB allocated across 6 pools")
    print("  ✓ CPU-GPU Bridge: Shows successful async transfers")
    print("  ✓ GPU Benchmarks: Shows RTX 4070 performance metrics\n")
    print("      Memory bandwidth: 40-50 GB/s")
    print("      Sync latency: 0.2-0.5ms")
    print("      Stream speedup: 3-4×\n")
    
    print("STEP 5: Next Phase")
    print("─" * 72)
    print("\nOnce Phase 1 is complete:")
    print("  1. Phase 1 establishes GPU foundation ✓")
    print("  2. Phase 2 will build Compact Recursive ORAM (CPU baseline)")
    print("  3. Phase 3 will add GPU acceleration")
    print("  4. Phase 4 will integrate hybrid caching")
    print("  5. Phase 5 will tune for final performance\n")
    print("Target: 15,000 ops/sec with 1.6× overhead\n")
    
    print("TROUBLESHOOTING")
    print("─" * 72)
    print("\nIf GPU not detected:")
    print("  → Install NVIDIA drivers from:")
    print("    https://www.nvidia.com/Download/driverDetails.aspx\n")
    
    print("If PyCUDA fails:")
    print("  → Ensure CUDA Toolkit is installed")
    print("  → On Linux: sudo apt-get install cuda-toolkit-12-4")
    print("  → On Windows: Download from https://developer.nvidia.com/cuda-downloads\n")
    
    print("If PyTorch/CuPy fail:")
    print("  → They are optional for Phase 1")
    print("  → GPU memory manager and bridge work without them\n")
    
    print("SYSTEM REQUIREMENTS")
    print("─" * 72)
    print("\n✓ OS: Windows 10+ or Linux (Ubuntu 18.04+)")
    print("✓ GPU: NVIDIA RTX 4070 or compatible (8GB+ VRAM)")
    print("✓ Python: 3.8 or higher")
    print("✓ Internet: Required for first setup (package downloads)")
    print("✓ Disk space: ~3GB for CUDA packages\n")
    
    print("FILES CREATED BY SETUP")
    print("─" * 72)
    print("\n├─ venv/                          Virtual environment")
    print("├─ phase1_setup.py                Setup script (this creates venv)")
    print("├─ phase1_gpu_memory_manager.py   GPU memory manager")
    print("├─ phase1_cpu_gpu_bridge.py       CPU-GPU transfer bridge")
    print("├─ phase1_benchmark_rtx4070.py    GPU benchmarking suite")
    print("├─ phase1_test_all.py             Test runner script")
    print("├─ requirements_gpu_phase1.txt    Package requirements")
    print("└─ phase1_quick_start.py          This guide\n")
    
    print("READY TO START?")
    print("─" * 72)
    print("\nRun this to begin:\n")
    print("  python phase1_setup.py\n")


if __name__ == "__main__":
    main()
