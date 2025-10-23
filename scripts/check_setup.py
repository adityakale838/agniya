"""
Quick demonstration of the dataset infrastructure.
Run this to verify everything is set up correctly.
"""

from pathlib import Path
import sys

def check_structure():
    """Check if all directories and files are in place."""
    print("=" * 70)
    print("Agniya Dataset Infrastructure Check")
    print("=" * 70)
    
    base = Path(".")
    
    checks = [
        ("Documentation", [
            "docs/DATASET_SPECIFICATION.md",
            "docs/REAL_WORLD_DATASETS.md",
            "docs/PHASE1_IMPLEMENTATION_PLAN.md"
        ]),
        ("Scripts", [
            "scripts/generate_datasets.py",
            "scripts/download_real_datasets.py"
        ]),
        ("Benchmarking", [
            "agniya/benchmarks/benchmark_suite.py"
        ]),
        ("Data Directories", [
            "data/sample_datasets",
            "data/real_datasets",
            "data/benchmark_results"
        ])
    ]
    
    all_good = True
    
    for category, paths in checks:
        print(f"\n{category}:")
        for path_str in paths:
            path = base / path_str
            exists = path.exists()
            status = "✓" if exists else "✗"
            print(f"  {status} {path_str}")
            if not exists:
                all_good = False
    
    print("\n" + "=" * 70)
    
    if all_good:
        print("✓ All infrastructure files are in place!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install requests openpyxl matplotlib seaborn psutil")
        print("2. Download real datasets: python scripts/download_real_datasets.py")
        print("3. Generate synthetic data: python scripts/generate_datasets.py")
    else:
        print("✗ Some files are missing. Please check the setup.")
    
    print("=" * 70)
    
    return all_good

if __name__ == "__main__":
    check_structure()
