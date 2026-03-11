"""
Real-World Dataset Benchmarks for AGNIYA Encrypted Database
============================================================

Tests AGNIYA with actual Kaggle datasets representing common encrypted database use cases:
1. Healthcare data (patient records, medical costs)
2. Financial data (salaries, credit card transactions)
3. E-commerce data (sales, revenue)
"""

import os
import sys
import time
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List
from datetime import datetime

# Add agniya to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agniya.core.paillier import generate_keypair, encrypt, decrypt, homomorphic_add
from agniya.core.precomputation import PrecomputationTable


# Recommended Kaggle Datasets for Encrypted Database Testing
DATASETS = {
    'healthcare': {
        'name': 'Healthcare Cost Dataset',
        'url': 'https://www.kaggle.com/datasets/mirichoi0218/insurance',
        'file': 'insurance.csv',
        'numeric_columns': ['age', 'bmi', 'children', 'charges'],
        'description': 'Medical insurance costs - sensitive patient financial data',
        'use_case': 'Hospital billing system with encrypted patient costs'
    },
    'salary': {
        'name': 'Data Science Salaries',
        'url': 'https://www.kaggle.com/datasets/ruchi798/data-science-job-salaries',
        'file': 'ds_salaries.csv',
        'numeric_columns': ['salary', 'salary_in_usd'],
        'description': 'Employee salary data - private HR information',
        'use_case': 'HR system with encrypted employee compensation'
    },
    'credit_card': {
        'name': 'Credit Card Fraud Detection',
        'url': 'https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud',
        'file': 'creditcard.csv',
        'numeric_columns': ['Amount', 'V1', 'V2', 'V3', 'V4', 'V5'],
        'description': 'Credit card transactions - financial data',
        'use_case': 'Banking system with encrypted transaction amounts'
    },
    'ecommerce': {
        'name': 'E-commerce Sales Dataset',
        'url': 'https://www.kaggle.com/datasets/carrie1/ecommerce-data',
        'file': 'data.csv',
        'numeric_columns': ['Quantity', 'UnitPrice'],
        'description': 'Online retail transactions - business revenue data',
        'use_case': 'E-commerce platform with encrypted revenue analytics'
    },
    'employee': {
        'name': 'Employee Dataset',
        'url': 'https://www.kaggle.com/datasets/tawfikelmetwally/employee-dataset',
        'file': 'Employee.csv',
        'numeric_columns': ['Age', 'Salary', 'Years_at_Company'],
        'description': 'Employee records - confidential HR data',
        'use_case': 'Enterprise HR system with encrypted employee records'
    }
}


class RealWorldBenchmark:
    """Benchmark AGNIYA with real-world datasets."""
    
    def __init__(self, data_dir: str = "data/real_world"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir = Path("results/real_world")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def download_instructions(self):
        """Print instructions for downloading datasets."""
        print("="*80)
        print("REAL-WORLD DATASET BENCHMARK - DOWNLOAD INSTRUCTIONS")
        print("="*80)
        print("\nTo test with real-world data, please download these Kaggle datasets:\n")
        
        for key, dataset in DATASETS.items():
            print(f"{key.upper()}: {dataset['name']}")
            print(f"  URL: {dataset['url']}")
            print(f"  Use case: {dataset['use_case']}")
            print(f"  Save to: {self.data_dir / dataset['file']}")
            print()
        
        print("Download Instructions:")
        print("1. Go to each URL above")
        print("2. Click 'Download' button (requires Kaggle account)")
        print(f"3. Extract CSV files to: {self.data_dir}/")
        print("4. Re-run this script")
        print()
        print("="*80)
    
    def load_dataset(self, dataset_key: str) -> pd.DataFrame:
        """Load dataset if available."""
        dataset_info = DATASETS[dataset_key]
        file_path = self.data_dir / dataset_info['file']
        
        if not file_path.exists():
            print(f"❌ Dataset not found: {file_path}")
            return None
        
        print(f"✓ Loading {dataset_info['name']}...")
        
        # Try multiple encodings for CSV files
        for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                print(f"  Rows: {len(df):,} | Columns: {len(df.columns)}")
                return df
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"  Error with {encoding}: {e}")
                continue
        
        print(f"❌ Could not read dataset with any encoding")
        return None
    
    def benchmark_dataset(
        self, 
        dataset_key: str,
        num_rows: int = 1000,
        use_cache: bool = True
    ) -> Dict:
        """Benchmark encryption and queries on real dataset."""
        
        df = self.load_dataset(dataset_key)
        if df is None:
            return None
        
        dataset_info = DATASETS[dataset_key]
        numeric_cols = dataset_info['numeric_columns']
        
        # Sample rows
        if len(df) > num_rows:
            df_sample = df.sample(n=num_rows, random_state=42)
        else:
            df_sample = df
            num_rows = len(df)
        
        print(f"\n  Benchmarking {num_rows} rows from {dataset_key}...")
        
        # Select numeric column for encryption
        test_column = numeric_cols[0]
        values = df_sample[test_column].dropna().astype(int).tolist()[:num_rows]
        
        # Filter out negative values (Paillier requires non-negative integers)
        values = [abs(v) if v < 0 else v for v in values]
        
        print(f"  Testing column: {test_column}")
        print(f"  Value range: [{min(values)}, {max(values)}]")
        
        # Generate keypair
        pub_key, priv_key = generate_keypair(bit_length=2048)
        cache = PrecomputationTable(pub_key) if use_cache else None
        
        # Benchmark encryption
        print(f"  Encrypting {len(values)} values...", end="", flush=True)
        encrypt_start = time.perf_counter()
        if cache:
            ciphertexts = [cache.get_or_encrypt(v) for v in values]
        else:
            ciphertexts = [encrypt(pub_key, v) for v in values]
        encrypt_time = time.perf_counter() - encrypt_start
        print(f" {encrypt_time:.2f}s ({len(values)/encrypt_time:.1f} ops/sec)")
        
        # Benchmark SUM query (sample for large datasets)
        sample_size = min(100, len(values))
        samples = ciphertexts[:sample_size]
        
        print(f"  Computing SUM query ({sample_size} samples)...", end="", flush=True)
        sum_start = time.perf_counter()
        encrypted_sum = samples[0]
        for ct in samples[1:]:
            encrypted_sum = homomorphic_add(pub_key, encrypted_sum, ct)
        sum_time = time.perf_counter() - sum_start
        
        # Decrypt and verify
        decrypted_sum = decrypt(pub_key, priv_key, encrypted_sum)
        actual_sum = sum(values[:sample_size])
        
        sum_time_extrapolated = sum_time * (len(values) / sample_size)
        print(f" {sum_time:.2f}s (extrapolated: {sum_time_extrapolated:.2f}s)")
        print(f"  Verification: Decrypted={decrypted_sum}, Actual={actual_sum}, Match={decrypted_sum==actual_sum}")
        
        return {
            'dataset': dataset_key,
            'dataset_name': dataset_info['name'],
            'use_case': dataset_info['use_case'],
            'num_rows': num_rows,
            'column': test_column,
            'value_min': min(values),
            'value_max': max(values),
            'use_cache': use_cache,
            'encryption_time_sec': encrypt_time,
            'encryption_throughput_ops_sec': len(values) / encrypt_time,
            'sum_query_time_sec': sum_time,
            'sum_query_time_extrapolated_sec': sum_time_extrapolated,
            'sum_sample_size': sample_size,
            'verification_passed': decrypted_sum == actual_sum
        }
    
    def run_all_benchmarks(self):
        """Run benchmarks on all available datasets."""
        print("\n" + "="*80)
        print("AGNIYA - REAL-WORLD DATASET BENCHMARKS")
        print("="*80)
        
        results = []
        available_datasets = []
        
        # Check which datasets are available
        for key in DATASETS.keys():
            file_path = self.data_dir / DATASETS[key]['file']
            if file_path.exists():
                available_datasets.append(key)
        
        if not available_datasets:
            print("\n❌ No datasets found!")
            self.download_instructions()
            return
        
        print(f"\n✓ Found {len(available_datasets)} datasets: {', '.join(available_datasets)}\n")
        
        # Benchmark each dataset with different configurations
        for dataset_key in available_datasets:
            for num_rows in [100, 1000, 10000]:
                for use_cache in [False, True]:
                    result = self.benchmark_dataset(dataset_key, num_rows, use_cache)
                    if result:
                        results.append(result)
        
        # Save results
        if results:
            results_df = pd.DataFrame(results)
            csv_path = self.results_dir / f'real_world_benchmark_{self.timestamp}.csv'
            results_df.to_csv(csv_path, index=False)
            
            print("\n" + "="*80)
            print("BENCHMARK COMPLETE")
            print("="*80)
            print(f"\n✓ Results saved: {csv_path}")
            
            # Print summary
            print("\nSummary by Dataset:")
            print("-" * 80)
            for dataset in results_df['dataset'].unique():
                subset = results_df[results_df['dataset'] == dataset]
                avg_throughput = subset['encryption_throughput_ops_sec'].mean()
                use_case = subset['use_case'].iloc[0]
                print(f"{dataset.upper()}: {avg_throughput:.1f} ops/sec avg")
                print(f"  Use case: {use_case}")
            
            print("\n" + "="*80)
            print("These results demonstrate AGNIYA's performance on real-world")
            print("sensitive data scenarios - perfect for patent technical evidence!")
            print("="*80)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='AGNIYA Real-World Dataset Benchmarks'
    )
    parser.add_argument(
        '--data-dir',
        type=str,
        default='data/real_world',
        help='Directory containing downloaded CSV files'
    )
    
    args = parser.parse_args()
    
    benchmark = RealWorldBenchmark(data_dir=args.data_dir)
    benchmark.run_all_benchmarks()


if __name__ == '__main__':
    main()
