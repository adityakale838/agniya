#!/usr/bin/env bash
# AGNIYA Patent-Grade Benchmark - Complete Reproducibility Script
# ================================================================
#
# This script runs all experiments end-to-end for Indian patent filing.
#
# Usage:
#   bash run.sh                    # Run all benchmarks
#   bash run.sh --quick            # Run quick test (reduced iterations)
#   bash run.sh --output results2  # Custom output directory
#
# Requirements:
#   - Python 3.10+
#   - Virtual environment at ./envb/ (or modify VENV_PATH)
#   - All dependencies installed (see requirements.txt)

set -e  # Exit on error
set -u  # Exit on undefined variable

# Configuration
VENV_PATH="./envb"
SCRIPT_PATH="scripts/patent_grade_benchmark.py"
OUTPUT_DIR="${1:-results}"

echo "================================================================"
echo "AGNIYA - Patent-Grade Benchmark Suite"
echo "================================================================"
echo ""
echo "Output directory: ${OUTPUT_DIR}"
echo ""

# Check if virtual environment exists
if [ ! -d "${VENV_PATH}" ]; then
    echo "Error: Virtual environment not found at ${VENV_PATH}"
    echo "Please run: python -m venv ${VENV_PATH}"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
if [ -f "${VENV_PATH}/Scripts/activate" ]; then
    # Windows
    source "${VENV_PATH}/Scripts/activate"
elif [ -f "${VENV_PATH}/bin/activate" ]; then
    # Linux/Mac
    source "${VENV_PATH}/bin/activate"
else
    echo "Error: Cannot find activation script"
    exit 1
fi

# Verify Python
echo "Checking Python version..."
python --version

# Verify dependencies
echo "Verifying dependencies..."
python -c "import numpy, pandas; print('✓ numpy, pandas')" || exit 1
python -c "import gmpy2; print('✓ gmpy2')" || echo "Warning: gmpy2 not installed (optional)"

# Set UTF-8 encoding
export PYTHONIOENCODING=utf-8

# Run benchmark
echo ""
echo "Starting benchmark suite..."
echo "This may take 10-30 minutes depending on hardware."
echo ""

python "${SCRIPT_PATH}" --output-dir "${OUTPUT_DIR}"

# Check if results were generated
if [ -f "${OUTPUT_DIR}/summary.md" ]; then
    echo ""
    echo "================================================================"
    echo "SUCCESS!"
    echo "================================================================"
    echo ""
    echo "Results saved in: ${OUTPUT_DIR}/"
    echo ""
    echo "Key files:"
    echo "  - summary.md            # Executive summary"
    echo "  - methods.md            # Methodology"
    echo "  - env/environment.txt   # Environment specs"
    echo "  - csv/*.csv             # Raw data"
    echo ""
    echo "Ready for patent filing!"
else
    echo ""
    echo "Error: Benchmark completed but summary.md not found"
    exit 1
fi
