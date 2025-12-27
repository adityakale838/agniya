#!/usr/bin/env python3
"""
COMPLETE SETUP - QUICK REFERENCE
Everything you need for Agniya Phases 1-5
"""

import platform
import sys

system = platform.system()

print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║                    AGNIYA COMPLETE SETUP - QUICK START                   ║
║                         All Phases 1-5 Ready                             ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝

STEP 1: RUN THE COMPLETE SETUP SCRIPT
═══════════════════════════════════════════════════════════════════════════

This is a one-time setup that installs everything needed:

  python complete_setup.py

What it does:
  ✓ Verifies GPU and NVIDIA drivers
  ✓ Creates Python virtual environment
  ✓ Installs ALL required packages
  ✓ Verifies complete installation
  ✓ Shows you what to do next

Time: ~5-10 minutes (depends on internet speed)

═══════════════════════════════════════════════════════════════════════════

STEP 2: ACTIVATE VIRTUAL ENVIRONMENT
═══════════════════════════════════════════════════════════════════════════

""")

if system == "Windows":
    print("On Windows:")
    print("  venv\\Scripts\\activate.bat")
    print("")
    print("Or PowerShell:")
    print("  venv\\Scripts\\Activate.ps1")
else:
    print("On Linux/macOS:")
    print("  source venv/bin/activate")

print("""

After activation, your terminal prompt will show (venv)

═══════════════════════════════════════════════════════════════════════════

STEP 3: VERIFY SETUP WORKED
═══════════════════════════════════════════════════════════════════════════

Run this to confirm everything is installed:

  python -c "import numpy, flask, pycryptodome; print('✓ Setup successful!')"

If you see "✓ Setup successful!" then you're ready to go.

═══════════════════════════════════════════════════════════════════════════

STEP 4: START USING AGNIYA
═══════════════════════════════════════════════════════════════════════════

Run the example workflow:

  python examples/complete_workflow.py

Or start the API server:

  python api/server.py

Or run benchmarks:

  python benchmark_comprehensive.py

═══════════════════════════════════════════════════════════════════════════

WHAT'S INSTALLED
═══════════════════════════════════════════════════════════════════════════

Essential Packages:
  ✓ NumPy           - Numerical computing
  ✓ PyCryptodome    - Encryption (Paillier)
  ✓ SciPy           - Scientific computing
  ✓ Pandas          - Data processing
  ✓ Flask           - Web API framework
  ✓ Requests        - HTTP client
  ✓ Numba           - Python JIT compilation
  ✓ Cython          - C optimizations

GPU Packages (if auto-install succeeded):
  ✓ nvidia-ml-py3   - GPU monitoring
  ✓ gpustat         - GPU stats tool
  ⚠ CuPy            - GPU arrays (optional, may be slow)
  ⚠ PyTorch         - Deep learning (optional, large)
  ⚠ PyCUDA          - CUDA programming (optional, may be slow)

═══════════════════════════════════════════════════════════════════════════

PHASES OVERVIEW
═══════════════════════════════════════════════════════════════════════════

Phase 1: GPU Foundation (DONE after setup.py)
  ✓ Verify GPU and drivers
  ✓ Virtual environment ready
  ✓ All packages installed
  Status: COMPLETE

Phase 2: Compact Recursive ORAM (Coming)
  • Implement 2-level recursive ORAM structure
  • CPU baseline: 0.15-0.2ms per access
  • Estimated: 1-2 weeks

Phase 3: GPU Acceleration (Coming)
  • GPU AES-256-XTS kernel
  • Parallel tree traversal
  • Expected: 5-10× speedup

Phase 4: Hybrid Integration (Coming)
  • Multi-tier caching (3 levels)
  • Adaptive query planning
  • Expected: 1.6× total overhead

Phase 5: Performance Tuning (Coming)
  • NVIDIA Nsight profiling
  • Kernel optimization
  • Target: 15,000 ops/sec

═══════════════════════════════════════════════════════════════════════════

TROUBLESHOOTING
═══════════════════════════════════════════════════════════════════════════

Problem: GPU not detected
  Solution: Install NVIDIA drivers from:
    https://www.nvidia.com/Download/driverDetails.aspx

Problem: Virtual environment not created
  Solution: Check Python version:
    python --version    (should be 3.8+)

Problem: Packages failed to install
  Solution: Run setup script again, or manually:
    pip install -r requirements_complete.txt

Problem: PyTorch/CuPy installation is too slow
  Solution: Skip them for now:
    Ctrl+C to cancel
    They are OPTIONAL

═══════════════════════════════════════════════════════════════════════════

USEFUL COMMANDS
═══════════════════════════════════════════════════════════════════════════

Check GPU status:
  nvidia-smi
  gpustat

Check Python packages:
  pip list

Install specific package:
  pip install package_name

Deactivate virtual environment:
  deactivate

View setup log:
  cat setup_log.txt    (on Linux/Mac)
  type setup_log.txt   (on Windows)

═══════════════════════════════════════════════════════════════════════════

FAQ
═══════════════════════════════════════════════════════════════════════════

Q: Do I need to run complete_setup.py again?
A: No, only once. After that, just activate the venv with:
   source venv/bin/activate  (Linux)
   venv\\Scripts\\activate.bat  (Windows)

Q: Can I install more packages later?
A: Yes, just activate venv and: pip install package_name

Q: What if the script fails?
A: The setup is designed to handle failures gracefully.
   Check setup_log.txt for details.
   Most failures are non-critical.

Q: Can I use this on Windows and Linux?
A: Yes, complete_setup.py works on both.

Q: What about GPU acceleration packages?
A: They are OPTIONAL. The core system works without them.
   Add them later if needed (they take 10-30 min to build).

═══════════════════════════════════════════════════════════════════════════

READY TO START?
═══════════════════════════════════════════════════════════════════════════

Run this now:

  python complete_setup.py

Then follow the instructions above.

═══════════════════════════════════════════════════════════════════════════
""")
