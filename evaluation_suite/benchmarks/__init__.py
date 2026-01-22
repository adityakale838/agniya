"""
Benchmark Module __init__.py

Exports all benchmark running functions.
"""

# Import benchmark modules using file-based imports
try:
    from evaluation_suite.benchmarks import (
        micro_benchmarks,
        end_to_end,
        comparative_seal,
        rns_validation,
        oram_evaluation,
        gpu_acceleration,
        batch_packing,
        real_datasets,
        scalability,
        stress_chaos,
        security_analysis,
        ablation_study
    )
except ImportError:
    # Fallback for different import paths
    import sys
    from pathlib import Path
    
    # Try importing with number prefixes
    try:
        import importlib
        micro_benchmarks = importlib.import_module('evaluation_suite.benchmarks.01_micro_benchmarks')
        end_to_end = importlib.import_module('evaluation_suite.benchmarks.02_end_to_end')
        comparative_seal = importlib.import_module('evaluation_suite.benchmarks.03_comparative_seal')
        rns_validation = importlib.import_module('evaluation_suite.benchmarks.04_rns_validation')
        oram_evaluation = importlib.import_module('evaluation_suite.benchmarks.05_oram_evaluation')
        gpu_acceleration = importlib.import_module('evaluation_suite.benchmarks.06_gpu_acceleration')
        batch_packing = importlib.import_module('evaluation_suite.benchmarks.07_batch_packing')
        real_datasets = importlib.import_module('evaluation_suite.benchmarks.08_real_datasets')
        scalability = importlib.import_module('evaluation_suite.benchmarks.09_scalability')
        stress_chaos = importlib.import_module('evaluation_suite.benchmarks.10_stress_chaos')
        security_analysis = importlib.import_module('evaluation_suite.benchmarks.11_security_analysis')
        ablation_study = importlib.import_module('evaluation_suite.benchmarks.12_ablation_study')
    except Exception as e:
        print(f"Warning: Could not import benchmark modules: {e}")
        raise

__all__ = [
    'micro_benchmarks',
    'end_to_end',
    'comparative_seal',
    'rns_validation',
    'oram_evaluation',
    'gpu_acceleration',
    'batch_packing',
    'real_datasets',
    'scalability',
    'stress_chaos',
    'security_analysis',
    'ablation_study',
]
