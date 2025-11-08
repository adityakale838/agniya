#!/usr/bin/env python3
"""
AGNIYA System Verification Script
Verifies all components are working correctly
"""

import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def print_success(text):
    print(f"  ✅ {text}")

def print_error(text):
    print(f"  ❌ {text}")

def verify_python_modules():
    """Verify all Python modules are importable"""
    print_header("Python Modules")
    
    modules = [
        ("agniya.compression.rns_compression", "RNS Compression"),
        ("agniya.storage.deduplication", "Deduplication"),
        ("agniya.core.query_planner", "Query Planning"),
        ("agniya.core.ultimate_system", "Ultimate Database"),
        ("agniya.hybrid.schema", "Schema"),
    ]
    
    all_ok = True
    for module_name, display_name in modules:
        try:
            __import__(module_name)
            print_success(f"{display_name} module")
        except ImportError as e:
            print_error(f"{display_name} module: {e}")
            all_ok = False
    
    return all_ok

def verify_frontend_build():
    """Verify frontend builds"""
    print_header("Frontend Build")
    
    try:
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=os.path.join(os.path.dirname(__file__), "webapp"),
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            print_success("Frontend builds successfully")
            return True
        else:
            print_error(f"Frontend build failed: {result.stderr[:200]}")
            return False
    except Exception as e:
        print_error(f"Could not verify frontend: {e}")
        return False

def verify_files_exist():
    """Verify all essential files exist"""
    print_header("File Structure")
    
    files = [
        ("api/server_advanced.py", "Advanced Backend"),
        ("agniya/compression/rns_compression.py", "RNS Compression Module"),
        ("agniya/storage/deduplication.py", "Deduplication Module"),
        ("agniya/core/query_planner.py", "Query Planner Module"),
        ("webapp/lib/api.ts", "Frontend API Client"),
        ("webapp/app/dashboard/page.tsx", "Dashboard Component"),
        ("start.ps1", "Start Script"),
        ("test_novel_features.py", "Integration Tests"),
    ]
    
    base_path = os.path.dirname(__file__)
    all_ok = True
    
    for file_path, display_name in files:
        full_path = os.path.join(base_path, file_path)
        if os.path.exists(full_path):
            size_kb = os.path.getsize(full_path) / 1024
            print_success(f"{display_name} ({size_kb:.1f} KB)")
        else:
            print_error(f"{display_name} not found at {file_path}")
            all_ok = False
    
    return all_ok

def verify_documentation():
    """Verify documentation files"""
    print_header("Documentation")
    
    docs = [
        "START_HERE.md",
        "NOVEL_FEATURES_SUMMARY.md",
        "COMPETITIVE_ANALYSIS.md",
        "ARCHITECTURE.md",
        "IMPLEMENTATION_CHECKLIST.md",
        "README_QUICK_START.md",
        "ALL_FIXES_COMPLETE.md",
    ]
    
    base_path = os.path.dirname(__file__)
    all_ok = True
    
    for doc in docs:
        full_path = os.path.join(base_path, doc)
        if os.path.exists(full_path):
            size_kb = os.path.getsize(full_path) / 1024
            print_success(f"{doc} ({size_kb:.1f} KB)")
        else:
            print_error(f"{doc} not found")
            all_ok = False
    
    return all_ok

def verify_dependencies():
    """Verify required Python packages"""
    print_header("Python Dependencies")
    
    packages = [
        ("flask", "Flask"),
        ("flask_cors", "Flask CORS"),
        ("pandas", "Pandas"),
        ("numpy", "NumPy"),
        ("gmpy2", "GMPY2"),
    ]
    
    all_ok = True
    for package_name, display_name in packages:
        try:
            __import__(package_name)
            print_success(f"{display_name}")
        except ImportError:
            print_error(f"{display_name} not installed")
            all_ok = False
    
    return all_ok

def main():
    """Run all verification checks"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "AGNIYA System Verification" + " " * 27 + "║")
    print("╚" + "=" * 68 + "╝")
    
    checks = [
        ("Python Modules", verify_python_modules),
        ("Files", verify_files_exist),
        ("Documentation", verify_documentation),
        ("Dependencies", verify_dependencies),
        ("Frontend Build", verify_frontend_build),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"Error in {name}: {e}")
            results.append((name, False))
    
    # Summary
    print_header("Summary")
    
    total = len(results)
    passed = sum(1 for _, result in results if result)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status:8} {name}")
    
    print(f"\n  Total: {passed}/{total} checks passed")
    
    if passed == total:
        print_header("System Status")
        print("  🎉 ALL SYSTEMS GO!")
        print("  ")
        print("  You can now run:")
        print("  ")
        print("    .\\start.ps1")
        print("  ")
        print("  Then open http://localhost:3000 in your browser")
        print("=" * 70 + "\n")
        return 0
    else:
        print_header("System Status")
        print(f"  ⚠️  {total - passed} issue(s) need fixing")
        print("=" * 70 + "\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
