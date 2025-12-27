#!/usr/bin/env python3
"""
Phase 1 Test Runner - Cross-Platform (Windows & Linux)
Tests GPU memory manager, CPU-GPU bridge, and benchmarks
"""

import sys
import os
import subprocess
from pathlib import Path


def run_script(script_name, description):
    """Run a Python script and return success status"""
    print(f"\n{'─' * 72}")
    print(f"Running: {description}")
    print(f"Script: {script_name}")
    print(f"{'─' * 72}\n")
    
    try:
        result = subprocess.run([sys.executable, script_name], check=False)
        if result.returncode == 0:
            print(f"\n✓ {description} completed successfully")
            return True
        else:
            print(f"\n⚠ {description} had exit code {result.returncode}")
            return False
    except Exception as e:
        print(f"\n✗ Failed to run {description}: {e}")
        return False


def main():
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    
    print("╔" + "═" * 70 + "╗")
    print("║" + " PHASE 1 TEST SUITE ".center(70) + "║")
    print("║" + " Cross-Platform GPU Verification ".center(70) + "║")
    print("╚" + "═" * 70 + "╝")
    
    tests = [
        ("phase1_gpu_memory_manager.py", "GPU Memory Manager Test"),
        ("phase1_cpu_gpu_bridge.py", "CPU-GPU Bridge Test"),
        ("phase1_benchmark_rtx4070.py", "RTX 4070 Benchmarks"),
    ]
    
    results = {}
    for script, description in tests:
        if (script_dir / script).exists():
            results[description] = run_script(script, description)
        else:
            print(f"\n⚠ Script not found: {script}")
            results[description] = False
    
    # Summary
    print("\n" + "╔" + "═" * 70 + "╗")
    print("║" + " TEST SUMMARY ".center(70) + "║")
    print("╚" + "═" * 70 + "╝\n")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test, success in results.items():
        status = "✓" if success else "⚠"
        print(f"{status} {test}")
    
    print(f"\nTotal: {passed}/{total} tests passed\n")
    
    if passed == total:
        print("✓ All tests completed successfully!")
        print("\nPhase 1 GPU foundation is ready.")
        print("Next: Proceed to Phase 2 (Compact Recursive ORAM)\n")
        return 0
    else:
        print("⚠ Some tests had issues. Review output above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
