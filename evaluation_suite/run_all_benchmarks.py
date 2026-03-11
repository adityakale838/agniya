"""
AGNIYA Comprehensive Evaluation Suite - Main Orchestrator

This script coordinates the execution of all benchmark categories,
collects results, and generates publication-ready outputs.

Usage:
    python run_all_benchmarks.py --full
    python run_all_benchmarks.py --quick
    python run_all_benchmarks.py --category micro
    python run_all_benchmarks.py --config custom_config.yaml
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import yaml

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import benchmark modules
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
    ablation_study,
)
from evaluation_suite.benchmarks.utils import (
    setup_logging,
    save_results,
    get_hardware_info,
    get_software_versions,
)


class BenchmarkOrchestrator:
    """Coordinates execution of all benchmark categories."""
    
    def __init__(self, config_path: str = "evaluation_suite/config.yaml"):
        """
        Initialize the benchmark orchestrator.
        
        Args:
            config_path: Path to configuration YAML file
        """
        self.config = self._load_config(config_path)
        self.results = {}
        self.start_time = None
        self.end_time = None
        
        # Setup logging
        setup_logging(
            level=self.config['logging']['level'],
            console=self.config['logging']['console'],
            file=self.config['logging']['file'],
            file_path=self.config['logging']['file_path']
        )
        self.logger = logging.getLogger(__name__)
        
        # Create output directories
        self._create_output_dirs()
        
        # Record environment
        if self.config['reproducibility']['record_environment']:
            self._record_environment()
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _create_output_dirs(self):
        """Create output directories if they don't exist."""
        for key, path in self.config['output'].items():
            Path(path).mkdir(parents=True, exist_ok=True)
    
    def _record_environment(self):
        """Record hardware and software environment for reproducibility."""
        environment = {
            'timestamp': datetime.now().isoformat(),
            'hardware': get_hardware_info(),
            'software': get_software_versions(),
            'config': self.config
        }
        
        env_path = Path(self.config['output']['raw_data']) / 'environment.json'
        with open(env_path, 'w') as f:
            json.dump(environment, f, indent=2)
        
        self.logger.info(f"Environment recorded to {env_path}")
    
    def run_all_benchmarks(self) -> Dict[str, Any]:
        """
        Execute all enabled benchmark categories.
        
        Returns:
            Dictionary containing all benchmark results
        """
        self.start_time = time.time()
        self.logger.info("="*80)
        self.logger.info("STARTING AGNIYA COMPREHENSIVE EVALUATION SUITE")
        self.logger.info("="*80)
        
        # Define benchmark execution order and functions
        benchmarks = [
            ('micro_benchmarks', micro_benchmarks.run, 
             "Part 1: Micro-Benchmarks (Component Performance)"),
            
            ('end_to_end', end_to_end.run,
             "Part 1: End-to-End System Benchmarks"),
            
            ('comparative_seal', comparative_seal.run,
             "Part 2: Comparative Evaluation vs SEAL"),
            
            ('rns_validation', rns_validation.run,
             "Part 3: RNS Compression Validation (Patent Claim 1)"),
            
            ('oram_evaluation', oram_evaluation.run,
             "Part 3: Hybrid ORAM Evaluation (Patent Claim 2)"),
            
            ('gpu_acceleration', gpu_acceleration.run,
             "Part 3: GPU Acceleration Deep Dive"),
            
            ('batch_packing', batch_packing.run,
             "Part 3: Batch Packing Analysis"),
            
            ('real_datasets', real_datasets.run,
             "Part 4: Real-World Dataset Evaluation"),
            
            ('scalability', scalability.run,
             "Part 5: Scalability Tests"),
            
            ('stress_chaos', stress_chaos.run,
             "Part 5: Stress & Chaos Testing"),
            
            ('security_analysis', security_analysis.run,
             "Part 6: Security Analysis"),
            
            ('ablation_study', ablation_study.run,
             "Part 9: Ablation Studies"),
        ]
        
        # Execute enabled benchmarks
        for category, run_func, description in benchmarks:
            if self.config['benchmarks'].get(category, False):
                self.logger.info("\n" + "="*80)
                self.logger.info(description)
                self.logger.info("="*80)
                
                try:
                    category_start = time.time()
                    results = run_func(self.config)
                    category_duration = time.time() - category_start
                    
                    self.results[category] = {
                        'results': results,
                        'duration_seconds': category_duration,
                        'status': 'SUCCESS'
                    }
                    
                    self.logger.info(f"[OK] {description} completed in {category_duration:.1f}s")
                    
                    # Save intermediate results
                    self._save_intermediate_results(category)
                    
                except Exception as e:
                    self.logger.error(f"[FAILED] {description}: {str(e)}", exc_info=True)
                    self.results[category] = {
                        'error': str(e),
                        'status': 'FAILED'
                    }
            else:
                self.logger.info(f"[SKIP] {description} (disabled in config)")
        
        self.end_time = time.time()
        total_duration = self.end_time - self.start_time
        
        # Generate summary
        self._generate_summary(total_duration)
        
        # Save final results
        self._save_final_results()
        
        self.logger.info("\n" + "="*80)
        self.logger.info(f"EVALUATION SUITE COMPLETED in {total_duration/3600:.2f} hours")
        self.logger.info("="*80)
        
        return self.results
    
    def _save_intermediate_results(self, category: str):
        """Save results for a single category."""
        output_path = Path(self.config['output']['raw_data']) / f"{category}_results.json"
        
        with open(output_path, 'w') as f:
            json.dump(self.results[category], f, indent=2)
        
        self.logger.debug(f"Intermediate results saved to {output_path}")
    
    def _save_final_results(self):
        """Save complete results from all benchmarks."""
        output_path = Path(self.config['output']['raw_data']) / "complete_results.json"
        
        final_results = {
            'timestamp': datetime.now().isoformat(),
            'total_duration_hours': (self.end_time - self.start_time) / 3600,
            'config': self.config,
            'results': self.results
        }
        
        with open(output_path, 'w') as f:
            json.dump(final_results, f, indent=2)
        
        self.logger.info(f"Complete results saved to {output_path}")
    
    def _generate_summary(self, total_duration: float):
        """Generate human-readable summary report."""
        summary_path = Path(self.config['output']['summary'])
        
        # Ensure parent directory exists
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write("# AGNIYA Evaluation Suite - Summary Report\n\n")
                f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"**Total Duration:** {total_duration/3600:.2f} hours\n\n")
                f.write("---\n\n")
                
                # Summary table
                f.write("## Benchmark Execution Summary\n\n")
                f.write("| Category | Status | Duration |\n")
                f.write("|----------|--------|----------|\n")
                
                for category, data in self.results.items():
                    status = data.get('status', 'UNKNOWN')
                    duration = data.get('duration_seconds', 0)
                    icon = '[OK]' if status == 'SUCCESS' else '[FAIL]'
                    f.write(f"| {category} | {icon} {status} | {duration:.1f}s |\n")
                
                f.write("\n---\n\n")
                
                # Key metrics (if available)
                f.write("## Critical Success Metrics\n\n")
                
                # Extract key metrics from results
                if 'micro_benchmarks' in self.results:
                    mb_results = self.results['micro_benchmarks'].get('results', {})
                    f.write("### Performance Achievements\n\n")
                    
                    if 'cache_performance' in mb_results:
                        cache_ops = mb_results['cache_performance'].get('ops_per_sec', 'N/A')
                        f.write(f"- **Cache Lookups:** {cache_ops:,} ops/sec\n")
                    
                    if 'speedup_multiplier' in mb_results:
                        speedup = mb_results['speedup_multiplier']
                        f.write(f"- **Overall Speedup:** {speedup}x vs baseline\n")
                
                if 'rns_validation' in self.results:
                    rns_results = self.results['rns_validation'].get('results', {})
                    f.write("\n### RNS Compression (Patent Claim 1)\n\n")
                    
                    if 'compression_ratio' in rns_results:
                        ratio = rns_results['compression_ratio']
                        f.write(f"- **Compression Ratio:** {ratio}% size reduction\n")
                    
                    if 'compress_ops_sec' in rns_results:
                        compress = rns_results['compress_ops_sec']
                        f.write(f"- **Compression Speed:** {compress:,} ops/sec\n")
                
                if 'oram_evaluation' in self.results:
                    oram_results = self.results['oram_evaluation'].get('results', {})
                    f.write("\n### Hybrid ORAM (Patent Claim 2)\n\n")
                    
                    if 'overhead_multiplier' in oram_results:
                        overhead = oram_results['overhead_multiplier']
                        f.write(f"- **ORAM Overhead:** {overhead}x (vs 100-1000x traditional)\n")
                
                f.write("\n---\n\n")
                
                # Next steps
                f.write("## Next Steps\n\n")
                f.write("1. Run visualization suite: `python evaluation_suite/visualization/generate_all_graphs.py`\n")
                f.write("2. Generate LaTeX tables: `python evaluation_suite/visualization/paper_ready.py`\n")
                f.write("3. Review raw data in: `evaluation_suite/results/raw_data/`\n")
                f.write("4. Check logs for details: `evaluation_suite/results/logs/benchmark.log`\n")
            
                self.logger.info(f"Summary report generated: {summary_path}")
        except PermissionError:
            self.logger.warning(f"Could not write summary to {summary_path} (file may be open)")
        except Exception as e:
            self.logger.error(f"Failed to generate summary: {str(e)}")


def main():
    """Main entry point for benchmark orchestrator."""
    parser = argparse.ArgumentParser(
        description="AGNIYA Comprehensive Evaluation Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run full evaluation suite (4-6 hours)
    python run_all_benchmarks.py --full
    
    # Quick validation run (30 minutes)
    python run_all_benchmarks.py --quick
    
    # Run specific category
    python run_all_benchmarks.py --category micro
    
    # Custom configuration
    python run_all_benchmarks.py --config my_config.yaml
        """
    )
    
    parser.add_argument(
        '--full',
        action='store_true',
        help='Run full evaluation suite with all tests'
    )
    
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick validation run with reduced iterations'
    )
    
    parser.add_argument(
        '--category',
        type=str,
        choices=['micro', 'end_to_end', 'comparative', 'rns', 'oram', 
                 'gpu', 'batch', 'datasets', 'scalability', 'stress', 
                 'security', 'ablation'],
        help='Run specific benchmark category only'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='evaluation_suite/config.yaml',
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Override output directory'
    )
    
    args = parser.parse_args()
    
    # Load config
    config_path = args.config
    
    # Modify config based on arguments
    if args.quick:
        # Create temporary quick config
        import tempfile
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        config['mode'] = 'quick'
        config['statistics'] = config['quick_mode']
        
        # Save temporary config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name
    
    elif args.category:
        # Enable only specified category
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Disable all categories
        for key in config['benchmarks']:
            config['benchmarks'][key] = False
        
        # Enable specified category
        category_map = {
            'micro': 'micro_benchmarks',
            'end_to_end': 'end_to_end',
            'comparative': 'comparative_seal',
            'rns': 'rns_validation',
            'oram': 'oram_evaluation',
            'gpu': 'gpu_acceleration',
            'batch': 'batch_packing',
            'datasets': 'real_datasets',
            'scalability': 'scalability',
            'stress': 'stress_chaos',
            'security': 'security_analysis',
            'ablation': 'ablation_study'
        }
        
        if args.category in category_map:
            config['benchmarks'][category_map[args.category]] = True
        
        # Save temporary config
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name
    
    # Create orchestrator and run
    orchestrator = BenchmarkOrchestrator(config_path)
    
    try:
        results = orchestrator.run_all_benchmarks()
        
        # Print quick summary
        print("\n" + "="*80)
        print("EVALUATION COMPLETE")
        print("="*80)
        
        success_count = sum(1 for r in results.values() if r.get('status') == 'SUCCESS')
        total_count = len(results)
        
        print(f"[OK] {success_count}/{total_count} benchmark categories completed successfully")
        print(f"\nResults: {orchestrator.config['output']['raw_data']}/")
        print(f"Summary: {orchestrator.config['output']['summary']}")
        print(f"Logs: {orchestrator.config['output']['logs']}/benchmark.log")
        
        return 0 if success_count == total_count else 1
        
    except KeyboardInterrupt:
        print("\n\n[WARNING] Benchmark interrupted by user")
        return 130
    
    except Exception as e:
        print(f"\n\n[FAILED] Fatal error: {str(e)}")
        logging.exception("Fatal error in benchmark orchestrator")
        return 1


if __name__ == "__main__":
    sys.exit(main())
