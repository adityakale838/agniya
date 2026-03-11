"""
Synthetic Dataset Generator for Agniya Benchmarking

This module generates realistic synthetic datasets for testing the hybrid
encryption system. All data is completely synthetic and safe for public sharing.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Tuple, Dict
import json
from datetime import datetime, timedelta


class DatasetGenerator:
    """Generate synthetic datasets with controlled characteristics."""
    
    def __init__(self, seed: int = 42):
        """
        Initialize the dataset generator.
        
        Args:
            seed: Random seed for reproducibility
        """
        self.seed = seed
        np.random.seed(seed)
        self.metadata = {
            "generation_timestamp": datetime.now().isoformat(),
            "numpy_version": np.__version__,
            "random_seed": seed
        }
    
    def generate_healthcare_dataset(self, n_rows: int) -> pd.DataFrame:
        """
        Generate synthetic healthcare dataset.
        
        Args:
            n_rows: Number of patient records to generate
            
        Returns:
            DataFrame with healthcare data
        """
        print(f"Generating healthcare dataset with {n_rows:,} rows...")
        
        # Generate patient IDs
        patient_ids = np.arange(1, n_rows + 1)
        
        # Age: Normal distribution centered at 45, std=18
        ages = np.clip(np.random.normal(45, 18, n_rows).astype(int), 0, 120)
        
        # Heart rate: Normal around 75, std=12
        heart_rates = np.clip(np.random.normal(75, 12, n_rows).astype(int), 40, 200)
        
        # Blood pressure: Age-correlated
        bp_systolic = np.clip((100 + ages * 0.5 + np.random.normal(0, 15, n_rows)).astype(int), 70, 200)
        bp_diastolic = np.clip((bp_systolic * 0.6 + np.random.normal(0, 10, n_rows)).astype(int), 40, 130)
        
        # Glucose: Normal around 100, std=20
        glucose = np.clip(np.random.normal(100, 20, n_rows).astype(int), 50, 400)
        
        # Cholesterol: Age-correlated
        cholesterol = np.clip((150 + ages * 0.8 + np.random.normal(0, 30, n_rows)).astype(int), 100, 400)
        
        # Temperature: Normal around 98.6F (986 in tenths)
        temperature = np.clip(np.random.normal(986, 10, n_rows).astype(int), 950, 1050)
        
        df = pd.DataFrame({
            'patient_id': patient_ids,
            'age': ages,
            'heart_rate': heart_rates,
            'blood_pressure_systolic': bp_systolic,
            'blood_pressure_diastolic': bp_diastolic,
            'glucose_level': glucose,
            'cholesterol': cholesterol,
            'temperature': temperature
        })
        
        # Add 5% null values randomly
        for col in df.columns[1:]:  # Skip patient_id
            null_mask = np.random.random(n_rows) < 0.05
            df.loc[null_mask, col] = np.nan
        
        self.metadata['healthcare'] = {
            'rows': n_rows,
            'columns': list(df.columns),
            'null_percentage': 5.0,
            'value_ranges': {col: f"{df[col].min():.0f}-{df[col].max():.0f}" 
                            for col in df.columns if col != 'patient_id'}
        }
        
        return df
    
    def generate_financial_dataset(self, n_rows: int) -> pd.DataFrame:
        """
        Generate synthetic financial dataset.
        
        Args:
            n_rows: Number of transaction records to generate
            
        Returns:
            DataFrame with financial data
        """
        print(f"Generating financial dataset with {n_rows:,} rows...")
        
        transaction_ids = np.arange(1, n_rows + 1)
        
        # Account balances: Log-normal distribution (realistic wealth distribution)
        # Most accounts have moderate balances, few have very high
        account_balance = np.clip(
            np.random.lognormal(13, 2, n_rows).astype(int),  # Mean ~$4M, wide spread
            0, 
            10_000_000_000  # $100M max
        )
        
        # Transaction amounts: Normal around $500, with some large outliers
        base_amounts = np.random.normal(50000, 30000, n_rows).astype(int)  # In cents
        # Add 2% large transactions
        large_tx_mask = np.random.random(n_rows) < 0.02
        base_amounts[large_tx_mask] = np.random.uniform(500000, 1000000, large_tx_mask.sum()).astype(int)
        transaction_amount = np.clip(base_amounts, -1_000_000, 1_000_000)
        
        # Salaries: Normal distribution by quartiles
        salary = np.clip(np.random.normal(6_000_000, 2_000_000, n_rows).astype(int), 2_000_000, 50_000_000)
        
        # Loan amounts: Mix of zero (no loan) and various loan sizes
        has_loan = np.random.random(n_rows) < 0.3  # 30% have loans
        loan_amount = np.zeros(n_rows, dtype=int)
        loan_amount[has_loan] = np.random.lognormal(11, 1.5, has_loan.sum()).astype(int)
        loan_amount = np.clip(loan_amount, 0, 100_000_000)
        
        # Credit scores: Approximately normal around 700
        credit_score = np.clip(np.random.normal(700, 80, n_rows).astype(int), 300, 850)
        
        df = pd.DataFrame({
            'transaction_id': transaction_ids,
            'account_balance': account_balance,
            'transaction_amount': transaction_amount,
            'salary': salary,
            'loan_amount': loan_amount,
            'credit_score': credit_score
        })
        
        self.metadata['financial'] = {
            'rows': n_rows,
            'columns': list(df.columns),
            'value_ranges': {col: f"{df[col].min():,}-{df[col].max():,}" 
                            for col in df.columns if col != 'transaction_id'}
        }
        
        return df
    
    def generate_iot_dataset(self, n_rows: int, n_sensors: int = 1000) -> pd.DataFrame:
        """
        Generate synthetic IoT sensor dataset.
        
        Args:
            n_rows: Number of sensor readings to generate
            n_sensors: Number of unique sensors
            
        Returns:
            DataFrame with IoT sensor data
        """
        print(f"Generating IoT dataset with {n_rows:,} rows from {n_sensors} sensors...")
        
        # Sensor IDs: Repeated for multiple readings
        sensor_ids = np.random.randint(1, n_sensors + 1, n_rows)
        
        # Timestamps: Last 30 days of readings
        start_time = int((datetime.now() - timedelta(days=30)).timestamp())
        timestamps = np.sort(np.random.randint(start_time, start_time + 30*24*3600, n_rows))
        
        # Temperature: Normal around 20C (200 in tenths), with daily cycles
        hour_of_day = (timestamps % 86400) / 3600
        daily_variation = 50 * np.sin((hour_of_day - 6) * np.pi / 12)  # Peak at 2 PM
        temperature = np.clip(
            (200 + daily_variation + np.random.normal(0, 30, n_rows)).astype(int),
            -400, 1250
        )
        
        # Humidity: Anti-correlated with temperature
        humidity = np.clip((70 - daily_variation/3 + np.random.normal(0, 15, n_rows)).astype(int), 0, 100)
        
        # Pressure: Slowly varying
        pressure = np.clip(np.random.normal(1013, 15, n_rows).astype(int), 870, 1085)
        
        # Light level: Strong daily cycle
        light_level = np.clip(
            (5000 * np.maximum(0, np.sin((hour_of_day - 6) * np.pi / 12)) + 
             np.random.normal(0, 500, n_rows)).astype(int),
            0, 10000
        )
        
        # Battery level: Slowly decreasing, recharged periodically
        battery_level = np.random.randint(20, 100, n_rows)
        
        df = pd.DataFrame({
            'sensor_id': sensor_ids,
            'timestamp': timestamps,
            'temperature': temperature,
            'humidity': humidity,
            'pressure': pressure,
            'light_level': light_level,
            'battery_level': battery_level
        })
        
        # Sort by timestamp
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        self.metadata['iot'] = {
            'rows': n_rows,
            'sensors': n_sensors,
            'columns': list(df.columns),
            'time_range_days': 30
        }
        
        return df
    
    def generate_ecommerce_dataset(self, n_rows: int) -> pd.DataFrame:
        """
        Generate synthetic e-commerce dataset.
        
        Args:
            n_rows: Number of orders to generate
            
        Returns:
            DataFrame with e-commerce data
        """
        print(f"Generating e-commerce dataset with {n_rows:,} rows...")
        
        order_ids = np.arange(1, n_rows + 1)
        
        # Product prices: Log-normal (most products cheap, few expensive)
        product_price = np.clip(
            np.random.lognormal(6, 1.5, n_rows).astype(int),  # Mean ~$10
            100, 1_000_000  # $1 to $10,000
        )
        
        # Quantity: Most orders are 1-3 items, few bulk orders
        quantity = np.random.choice([1, 2, 3], n_rows, p=[0.6, 0.3, 0.1])
        bulk_mask = np.random.random(n_rows) < 0.02
        quantity[bulk_mask] = np.random.randint(10, 1000, bulk_mask.sum())
        
        # Discount: Zipf distribution (most no discount, few large discounts)
        discount_percent = np.zeros(n_rows, dtype=int)
        has_discount = np.random.random(n_rows) < 0.4
        discount_percent[has_discount] = np.clip(
            np.random.exponential(10, has_discount.sum()).astype(int),
            5, 75
        )
        
        # Shipping cost: Depends on quantity and price
        base_shipping = 500 + (quantity * 50) + (product_price * 0.01).astype(int)
        shipping_cost = np.clip(base_shipping.astype(int), 0, 10000)
        
        # Customer IDs: Zipf distribution (some customers order frequently)
        customer_id = np.random.zipf(1.5, n_rows)
        customer_id = np.clip(customer_id, 1, 100000)
        
        df = pd.DataFrame({
            'order_id': order_ids,
            'product_price': product_price,
            'quantity': quantity,
            'discount_percent': discount_percent,
            'shipping_cost': shipping_cost,
            'customer_id': customer_id
        })
        
        self.metadata['ecommerce'] = {
            'rows': n_rows,
            'columns': list(df.columns),
            'unique_customers': df['customer_id'].nunique()
        }
        
        return df
    
    def save_dataset(self, df: pd.DataFrame, filepath: Path):
        """Save dataset and metadata to disk."""
        # Create directory if needed
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Save CSV
        df.to_csv(filepath, index=False)
        print(f"Saved dataset to {filepath}")
        
        # Save metadata
        metadata_file = filepath.with_suffix('.json')
        with open(metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
        print(f"Saved metadata to {metadata_file}")
        
        # Print statistics
        print(f"\nDataset Statistics:")
        print(f"  Shape: {df.shape}")
        print(f"  Memory: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
        print(f"  Null values: {df.isnull().sum().sum()}")
        print()


def generate_adaptive_test_datasets():
    """
    Generate datasets specifically designed to test all key sizes.
    
    This demonstrates the adaptive bit-length optimization across
    the full spectrum from 512-bit to 4096-bit keys.
    """
    generator = DatasetGenerator(seed=42)
    base_path = Path("data/sample_datasets/adaptive_tests")
    
    print("\n" + "=" * 70)
    print("Generating Adaptive Bit-Length Test Datasets")
    print("=" * 70)
    
    # Test 1: Tiny values (should select 512-bit)
    print("\n1. Tiny Values Dataset (512-bit target)")
    tiny_values = pd.DataFrame({
        'id': range(10000),
        'age': np.random.randint(0, 120, 10000),  # 0-120
        'score': np.random.randint(0, 100, 10000),  # 0-100
        'rating': np.random.randint(1, 5, 10000),  # 1-5 stars
        'count': np.random.randint(0, 1000, 10000)  # 0-1000
    })
    generator.save_dataset(tiny_values, base_path / "tiny_values_512bit.csv")
    print(f"   Max value: {tiny_values[['age', 'score', 'rating', 'count']].max().max()}")
    print(f"   Expected key: 512-bit")
    
    # Test 2: Small values (should select 1024-bit)
    print("\n2. Small Values Dataset (1024-bit target)")
    small_values = pd.DataFrame({
        'id': range(10000),
        'temperature': np.random.randint(-400, 1250, 10000),  # -40°C to 125°C (tenths)
        'humidity': np.random.randint(0, 100, 10000),  # 0-100%
        'heart_rate': np.random.randint(40, 200, 10000),  # 40-200 bpm
        'blood_pressure': np.random.randint(70, 200, 10000),  # 70-200 mmHg
        'inventory_count': np.random.randint(0, 100000, 10000)  # 0-100K
    })
    generator.save_dataset(small_values, base_path / "small_values_1024bit.csv")
    print(f"   Max value: {small_values[['temperature', 'humidity', 'heart_rate', 'blood_pressure', 'inventory_count']].max().max()}")
    print(f"   Expected key: 1024-bit")
    
    # Test 3: Medium values (should select 2048-bit)
    print("\n3. Medium Values Dataset (2048-bit target)")
    medium_values = pd.DataFrame({
        'id': range(10000),
        'salary_cents': np.random.randint(2000000, 50000000, 10000),  # $20K-$500K
        'transaction_amount': np.random.randint(100, 100000000, 10000),  # $1-$1M
        'account_balance': np.random.randint(0, 1000000000, 10000),  # $0-$10M
        'product_id': np.random.randint(0, 10000000, 10000)  # 0-10M
    })
    generator.save_dataset(medium_values, base_path / "medium_values_2048bit.csv")
    print(f"   Max value: {medium_values[['salary_cents', 'transaction_amount', 'account_balance', 'product_id']].max().max()}")
    print(f"   Expected key: 2048-bit")
    
    # Test 4: Large values (should select 3072-bit)
    print("\n4. Large Values Dataset (3072-bit target)")
    # Use lognormal distribution for very large values
    large_values = pd.DataFrame({
        'id': range(10000),
        'large_account': (np.random.lognormal(28, 2, 10000)).astype(np.int64),  # Very large balances
        'big_transaction': (np.random.lognormal(29, 2, 10000)).astype(np.int64),  # Huge transactions
        'enterprise_revenue': (np.random.lognormal(30, 2, 10000)).astype(np.int64)  # Enterprise scale
    })
    generator.save_dataset(large_values, base_path / "large_values_3072bit.csv")
    print(f"   Max value: {large_values[['large_account', 'big_transaction', 'enterprise_revenue']].max().max()}")
    print(f"   Expected key: 3072-bit")
    
    # Test 5: Huge values (should select 4096-bit)
    print("\n5. Huge Values Dataset (4096-bit target)")
    # Use even larger lognormal distribution
    huge_values = pd.DataFrame({
        'id': range(10000),
        'cryptographic_nonce': (np.random.lognormal(40, 3, 10000)).astype(np.int64),  # Very large numbers
        'global_identifier': (np.random.lognormal(42, 3, 10000)).astype(np.int64),  # Global scale IDs
    })
    generator.save_dataset(huge_values, base_path / "huge_values_4096bit.csv")
    print(f"   Max value: {huge_values[['cryptographic_nonce', 'global_identifier']].max().max()}")
    print(f"   Expected key: 4096-bit")
    
    # Test 6: Mixed range dataset (tests adaptive selection intelligence)
    print("\n6. Mixed Range Dataset (tests smart column-by-column selection)")
    mixed_values = pd.DataFrame({
        'id': range(10000),
        'small_col': np.random.randint(0, 100, 10000),  # 512-bit if separate
        'medium_col': np.random.randint(0, 1000000, 10000),  # 1024-bit if separate
        'large_col': (np.random.uniform(0, 10**10, 10000)).astype(np.int64),  # 2048-bit if separate
        'category': np.random.randint(1, 20, 10000),  # 512-bit if separate
    })
    generator.save_dataset(mixed_values, base_path / "mixed_range_values.csv")
    print(f"   Column max values:")
    for col in ['small_col', 'medium_col', 'large_col', 'category']:
        print(f"     {col}: {mixed_values[col].max()}")
    print(f"   Use case: Test column-wise adaptive optimization")
    
    print("\n" + "=" * 70)
    print("Adaptive test datasets generated successfully!")
    print("=" * 70)


def generate_all_datasets():
    """Generate all benchmark datasets."""
    generator = DatasetGenerator(seed=42)
    base_path = Path("data/sample_datasets")
    
    # Healthcare datasets
    for size in [100_000, 500_000, 1_000_000]:
        df = generator.generate_healthcare_dataset(size)
        generator.save_dataset(
            df, 
            base_path / f"healthcare/patients_{size//1000}k.csv"
        )
    
    # Financial datasets
    for size in [100_000, 500_000, 1_000_000]:
        df = generator.generate_financial_dataset(size)
        generator.save_dataset(
            df,
            base_path / f"financial/transactions_{size//1000}k.csv"
        )
    
    # IoT dataset
    df = generator.generate_iot_dataset(1_000_000, n_sensors=1000)
    generator.save_dataset(
        df,
        base_path / "iot/sensor_readings_1m.csv"
    )
    
    # E-commerce datasets
    for size in [500_000, 2_000_000]:
        df = generator.generate_ecommerce_dataset(size)
        generator.save_dataset(
            df,
            base_path / f"ecommerce/orders_{size//1000}k.csv"
        )
    
    # Generate adaptive test datasets
    generate_adaptive_test_datasets()
    
    print("=" * 60)
    print("All datasets generated successfully!")
    print("=" * 60)


if __name__ == "__main__":
    generate_all_datasets()
