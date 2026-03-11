"""
Shared utilities for AGNIYA evaluation suite.

Provides common functions for logging, data collection, hardware detection,
statistical analysis, and result serialization.
"""

import json
import logging
import os
import platform
import psutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
import numpy as np
from dataclasses import dataclass, asdict


@dataclass
class BenchmarkResult:
    """Standard container for benchmark results."""
    name: str
    category: str
    timestamp: str
    measurements: List[float]
    mean: float
    median: float
    std_dev: float
    min_val: float
    max_val: float
    p95: float
    p99: float
    unit: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


def setup_logging(level: str = "INFO", console: bool = True, 
                  file: bool = True, file_path: str = None):
    """
    Configure logging for benchmark suite.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        console: Enable console logging
        file: Enable file logging
        file_path: Path to log file
    """
    handlers = []
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, level))
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        handlers.append(console_handler)
    
    # File handler
    if file and file_path:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(getattr(logging, level))
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level),
        handlers=handlers
    )


def get_hardware_info() -> Dict[str, Any]:
    """
    Collect detailed hardware information for reproducibility.
    
    Returns:
        Dictionary containing CPU, RAM, GPU, and system information
    """
    info = {
        'timestamp': datetime.now().isoformat(),
        'platform': {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
        },
        'cpu': {
            'physical_cores': psutil.cpu_count(logical=False),
            'logical_cores': psutil.cpu_count(logical=True),
            'max_frequency_mhz': psutil.cpu_freq().max if psutil.cpu_freq() else None,
            'current_frequency_mhz': psutil.cpu_freq().current if psutil.cpu_freq() else None,
        },
        'memory': {
            'total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
            'available_gb': round(psutil.virtual_memory().available / (1024**3), 2),
        },
        'disk': {
            'total_gb': round(psutil.disk_usage('/').total / (1024**3), 2),
            'free_gb': round(psutil.disk_usage('/').free / (1024**3), 2),
        }
    }
    
    # Try to detect GPU
    try:
        import cupy as cp
        gpu_count = cp.cuda.runtime.getDeviceCount()
        info['gpu'] = {
            'available': True,
            'count': gpu_count,
            'devices': []
        }
        
        for i in range(gpu_count):
            with cp.cuda.Device(i):
                props = cp.cuda.runtime.getDeviceProperties(i)
                info['gpu']['devices'].append({
                    'id': i,
                    'name': props['name'].decode('utf-8'),
                    'compute_capability': f"{props['major']}.{props['minor']}",
                    'total_memory_gb': round(props['totalGlobalMem'] / (1024**3), 2),
                })
    except (ImportError, Exception):
        info['gpu'] = {'available': False}
    
    return info


def get_software_versions() -> Dict[str, str]:
    """
    Record software versions for reproducibility.
    
    Returns:
        Dictionary of package names and versions
    """
    versions = {
        'python': platform.python_version(),
    }
    
    # Try to import and get versions
    packages = [
        'numpy', 'pandas', 'gmpy2', 'scipy', 'matplotlib', 
        'seaborn', 'cupy', 'numba', 'cryptography'
    ]
    
    for package in packages:
        try:
            mod = __import__(package)
            versions[package] = getattr(mod, '__version__', 'unknown')
        except ImportError:
            versions[package] = 'not installed'
    
    return versions


def run_benchmark(func, args=(), kwargs=None, repetitions=10, 
                  warmup=5, unit='ops/sec') -> BenchmarkResult:
    """
    Run a benchmark function with statistical rigor.
    
    Args:
        func: Function to benchmark
        args: Positional arguments for func
        kwargs: Keyword arguments for func
        repetitions: Number of times to run
        warmup: Number of warmup iterations to discard
        unit: Unit of measurement
        
    Returns:
        BenchmarkResult with statistical measures
    """
    if kwargs is None:
        kwargs = {}
    
    logger = logging.getLogger(__name__)
    logger.debug(f"Running benchmark: {func.__name__} ({repetitions} reps, {warmup} warmup)")
    
    measurements = []
    
    # Warmup phase
    for i in range(warmup):
        try:
            func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Warmup iteration {i} failed: {str(e)}")
    
    # Measurement phase
    for i in range(repetitions):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            
            duration = end_time - start_time
            
            # Convert to ops/sec if measuring operations
            if unit == 'ops/sec' and hasattr(result, '__len__'):
                ops_per_sec = len(result) / duration
                measurements.append(ops_per_sec)
            elif unit == 'ops/sec':
                ops_per_sec = 1.0 / duration
                measurements.append(ops_per_sec)
            else:
                measurements.append(duration)
                
        except Exception as e:
            logger.error(f"Measurement iteration {i} failed: {str(e)}")
            raise
    
    # Remove outliers (>3 std dev)
    measurements_array = np.array(measurements)
    mean = np.mean(measurements_array)
    std = np.std(measurements_array)
    
    filtered = measurements_array[np.abs(measurements_array - mean) <= 3 * std]
    
    if len(filtered) < len(measurements):
        logger.debug(f"Removed {len(measurements) - len(filtered)} outliers")
        measurements_array = filtered
    
    # Calculate statistics
    return BenchmarkResult(
        name=func.__name__,
        category='benchmark',
        timestamp=datetime.now().isoformat(),
        measurements=measurements_array.tolist(),
        mean=float(np.mean(measurements_array)),
        median=float(np.median(measurements_array)),
        std_dev=float(np.std(measurements_array)),
        min_val=float(np.min(measurements_array)),
        max_val=float(np.max(measurements_array)),
        p95=float(np.percentile(measurements_array, 95)),
        p99=float(np.percentile(measurements_array, 99)),
        unit=unit,
        metadata={}
    )


def save_results(results: Dict[str, Any], output_path: str):
    """
    Save benchmark results to JSON file.
    
    Args:
        results: Dictionary of results
        output_path: Path to output file
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logging.getLogger(__name__).info(f"Results saved to {output_path}")


def load_results(input_path: str) -> Dict[str, Any]:
    """
    Load benchmark results from JSON file.
    
    Args:
        input_path: Path to results file
        
    Returns:
        Dictionary of results
    """
    with open(input_path, 'r') as f:
        return json.load(f)


def calculate_speedup(baseline: float, optimized: float) -> float:
    """
    Calculate speedup multiplier.
    
    Args:
        baseline: Baseline performance
        optimized: Optimized performance
        
    Returns:
        Speedup multiplier (e.g., 255.0 for 255× faster)
    """
    if baseline == 0:
        return float('inf')
    return optimized / baseline


def format_number(num: float, precision: int = 2) -> str:
    """
    Format large numbers with appropriate suffixes.
    
    Args:
        num: Number to format
        precision: Decimal places
        
    Returns:
        Formatted string (e.g., "6.7M", "2.5K")
    """
    if num >= 1_000_000:
        return f"{num/1_000_000:.{precision}f}M"
    elif num >= 1_000:
        return f"{num/1_000:.{precision}f}K"
    else:
        return f"{num:.{precision}f}"


def create_latex_table(data: List[List[Any]], headers: List[str], 
                       caption: str, label: str) -> str:
    """
    Generate LaTeX table from data.
    
    Args:
        data: 2D list of table data
        headers: Column headers
        caption: Table caption
        label: LaTeX label for referencing
        
    Returns:
        LaTeX table code
    """
    num_cols = len(headers)
    col_spec = 'l' + 'r' * (num_cols - 1)
    
    latex = f"\\begin{{table}}[htbp]\n"
    latex += f"\\centering\n"
    latex += f"\\caption{{{caption}}}\n"
    latex += f"\\label{{{label}}}\n"
    latex += f"\\begin{{tabular}}{{{col_spec}}}\n"
    latex += f"\\toprule\n"
    latex += " & ".join(headers) + " \\\\\n"
    latex += f"\\midrule\n"
    
    for row in data:
        latex += " & ".join(str(cell) for cell in row) + " \\\\\n"
    
    latex += f"\\bottomrule\n"
    latex += f"\\end{{tabular}}\n"
    latex += f"\\end{{table}}\n"
    
    return latex


def measure_memory_usage(func, *args, **kwargs) -> Tuple[Any, Dict[str, float]]:
    """
    Measure memory usage of a function.
    
    Args:
        func: Function to measure
        args: Positional arguments
        kwargs: Keyword arguments
        
    Returns:
        Tuple of (function result, memory stats dict)
    """
    import tracemalloc
    
    tracemalloc.start()
    initial_memory = psutil.Process().memory_info().rss / (1024**2)  # MB
    
    result = func(*args, **kwargs)
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    final_memory = psutil.Process().memory_info().rss / (1024**2)  # MB
    
    memory_stats = {
        'initial_mb': initial_memory,
        'final_mb': final_memory,
        'delta_mb': final_memory - initial_memory,
        'peak_tracemalloc_mb': peak / (1024**2),
        'current_tracemalloc_mb': current / (1024**2)
    }
    
    return result, memory_stats


class ProgressTracker:
    """Track and display progress of long-running benchmarks."""
    
    def __init__(self, total_steps: int, description: str = "Progress"):
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.start_time = time.time()
        self.logger = logging.getLogger(__name__)
    
    def update(self, step: int = None, description: str = None):
        """Update progress."""
        if step is not None:
            self.current_step = step
        else:
            self.current_step += 1
        
        if description:
            self.description = description
        
        percentage = (self.current_step / self.total_steps) * 100
        elapsed = time.time() - self.start_time
        
        if self.current_step > 0:
            eta = (elapsed / self.current_step) * (self.total_steps - self.current_step)
            self.logger.info(
                f"{self.description}: {self.current_step}/{self.total_steps} "
                f"({percentage:.1f}%) - ETA: {eta:.0f}s"
            )
        else:
            self.logger.info(f"{self.description}: Starting...")
    
    def complete(self):
        """Mark as complete."""
        elapsed = time.time() - self.start_time
        self.logger.info(
            f"{self.description}: Complete! "
            f"({self.total_steps} steps in {elapsed:.1f}s)"
        )
