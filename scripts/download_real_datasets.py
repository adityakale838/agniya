"""
Dataset Downloader and Preprocessor for Real-World Data

This module downloads and prepares publicly available datasets for benchmarking.
Handles conversion to integer format suitable for Paillier encryption.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Tuple
import requests
from urllib.parse import urlparse
import zipfile
import gzip
import shutil


class RealDatasetDownloader:
    """Download and preprocess real-world public datasets."""
    
    def __init__(self, data_dir: Path = Path("data/real_datasets")):
        """
        Initialize dataset downloader.
        
        Args:
            data_dir: Directory to store downloaded datasets
        """
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def download_file(self, url: str, filename: str) -> Path:
        """
        Download a file from URL.
        
        Args:
            url: URL to download from
            filename: Local filename to save as
            
        Returns:
            Path to downloaded file
        """
        filepath = self.data_dir / filename
        
        if filepath.exists():
            print(f"File {filename} already exists, skipping download")
            return filepath
        
        print(f"Downloading {filename}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Downloaded to {filepath}")
        return filepath
    
    def extract_zip(self, zip_path: Path, extract_to: Optional[Path] = None) -> Path:
        """Extract ZIP file."""
        if extract_to is None:
            extract_to = zip_path.parent
        
        print(f"Extracting {zip_path.name}...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        
        print(f"Extracted to {extract_to}")
        return extract_to
    
    def download_uci_bank_marketing(self) -> pd.DataFrame:
        """
        Download and prepare UCI Bank Marketing dataset.
        
        Returns:
            Prepared DataFrame with integer columns
        """
        print("\n" + "="*60)
        print("Downloading UCI Bank Marketing Dataset")
        print("="*60)
        
        url = "https://archive.ics.uci.edu/ml/machine-learning-databases/00222/bank-additional.zip"
        
        # Download
        zip_path = self.download_file(url, "bank-additional.zip")
        
        # Extract
        extract_dir = self.extract_zip(zip_path)
        
        # Load the full dataset
        csv_path = extract_dir / "bank-additional" / "bank-additional-full.csv"
        df = pd.read_csv(csv_path, sep=';')
        
        print(f"Loaded {len(df)} records with {len(df.columns)} columns")
        
        # Select and prepare integer columns
        prepared_df = pd.DataFrame({
            'age': df['age'],
            'balance': df['balance'],  # Already in euros
            'duration': df['duration'],  # Call duration in seconds
            'campaign': df['campaign'],  # Number of contacts
            'pdays': df['pdays'].replace(999, -1),  # Days since last contact
            'previous': df['previous'],  # Previous contacts
        })
        
        # Save prepared dataset
        output_path = self.data_dir / "bank_marketing_prepared.csv"
        prepared_df.to_csv(output_path, index=False)
        print(f"Saved prepared dataset to {output_path}")
        
        return prepared_df
    
    def download_intel_sensor_data(self) -> pd.DataFrame:
        """
        Download and prepare Intel Lab Sensor dataset.
        
        Returns:
            Prepared DataFrame with sensor readings
        """
        print("\n" + "="*60)
        print("Downloading Intel Lab Sensor Dataset")
        print("="*60)
        
        url = "http://db.csail.mit.edu/labdata/data.txt.gz"
        
        # Download
        gz_path = self.download_file(url, "intel_sensors.txt.gz")
        
        # Extract
        txt_path = self.data_dir / "intel_sensors.txt"
        if not txt_path.exists():
            print(f"Extracting {gz_path.name}...")
            with gzip.open(gz_path, 'rb') as f_in:
                with open(txt_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            print(f"Extracted to {txt_path}")
        
        # Load data
        print("Loading sensor data...")
        df = pd.read_csv(txt_path, sep=' ', header=None, 
                        names=['date', 'time', 'epoch', 'sensor_id', 'temperature', 
                               'humidity', 'light', 'voltage'])
        
        print(f"Loaded {len(df)} sensor readings")
        
        # Prepare integer columns
        # Convert temperature to tenths of degrees (multiply by 10)
        # Keep humidity as percentage (0-100)
        # Light is already integer
        # Voltage in millivolts (multiply by 1000)
        
        prepared_df = pd.DataFrame({
            'sensor_id': df['sensor_id'],
            'timestamp': pd.to_datetime(df['date'] + ' ' + df['time']).astype(int) // 10**9,
            'temperature': (df['temperature'] * 10).astype(int),  # Tenths of Celsius
            'humidity': df['humidity'].astype(int),
            'light': df['light'].astype(int),
            'voltage': (df['voltage'] * 1000).astype(int)  # Millivolts
        })
        
        # Remove any rows with NaN
        prepared_df = prepared_df.dropna()
        
        # Save prepared dataset
        output_path = self.data_dir / "intel_sensors_prepared.csv"
        prepared_df.to_csv(output_path, index=False)
        print(f"Saved prepared dataset to {output_path}")
        
        return prepared_df
    
    def download_online_retail_uci(self) -> pd.DataFrame:
        """
        Download and prepare UCI Online Retail dataset.
        
        Returns:
            Prepared DataFrame with transaction data
        """
        print("\n" + "="*60)
        print("Downloading UCI Online Retail Dataset")
        print("="*60)
        
        url = "https://archive.ics.uci.edu/ml/machine-learning-databases/00352/Online%20Retail.xlsx"
        
        # Download
        xlsx_path = self.download_file(url, "online_retail.xlsx")
        
        # Load Excel file
        print("Loading retail data...")
        df = pd.read_excel(xlsx_path)
        
        print(f"Loaded {len(df)} transactions")
        
        # Prepare integer columns
        # Convert prices to pence (multiply by 100)
        prepared_df = pd.DataFrame({
            'invoice_no': df['InvoiceNo'].astype(str),
            'stock_code': df['StockCode'].astype(str),
            'quantity': df['Quantity'],
            'unit_price_pence': (df['UnitPrice'] * 100).astype(int),  # Convert to pence
            'customer_id': df['CustomerID']
        })
        
        # Remove cancelled orders (negative quantities) and nulls
        prepared_df = prepared_df[prepared_df['quantity'] > 0]
        prepared_df = prepared_df.dropna()
        
        # Calculate total price
        prepared_df['total_price_pence'] = prepared_df['quantity'] * prepared_df['unit_price_pence']
        
        print(f"After cleaning: {len(prepared_df)} valid transactions")
        
        # Save prepared dataset
        output_path = self.data_dir / "online_retail_prepared.csv"
        prepared_df.to_csv(output_path, index=False)
        print(f"Saved prepared dataset to {output_path}")
        
        return prepared_df
    
    def download_all(self):
        """Download all available datasets."""
        try:
            self.download_uci_bank_marketing()
        except Exception as e:
            print(f"Error downloading Bank Marketing: {e}")
        
        try:
            self.download_intel_sensor_data()
        except Exception as e:
            print(f"Error downloading Intel Sensors: {e}")
        
        try:
            self.download_online_retail_uci()
        except Exception as e:
            print(f"Error downloading Online Retail: {e}")
        
        print("\n" + "="*60)
        print("Dataset download complete!")
        print("="*60)


class DatasetLoader:
    """Unified loader for both real and synthetic datasets."""
    
    def __init__(self, real_data_dir: Path = Path("data/real_datasets"),
                 synthetic_data_dir: Path = Path("data/sample_datasets")):
        """
        Initialize dataset loader.
        
        Args:
            real_data_dir: Directory with real-world datasets
            synthetic_data_dir: Directory with synthetic datasets
        """
        self.real_data_dir = real_data_dir
        self.synthetic_data_dir = synthetic_data_dir
    
    def load_dataset(self, name: str, dataset_type: str = 'real') -> Tuple[pd.DataFrame, Dict]:
        """
        Load a dataset by name.
        
        Args:
            name: Dataset name
            dataset_type: 'real' or 'synthetic'
            
        Returns:
            Tuple of (DataFrame, metadata_dict)
        """
        if dataset_type == 'real':
            base_dir = self.real_data_dir
        else:
            base_dir = self.synthetic_data_dir
        
        # Find the dataset file
        csv_files = list(base_dir.rglob(f"*{name}*.csv"))
        
        if not csv_files:
            raise FileNotFoundError(f"Dataset '{name}' not found in {base_dir}")
        
        filepath = csv_files[0]
        print(f"Loading {filepath}...")
        
        df = pd.read_csv(filepath)
        
        # Generate metadata
        metadata = {
            'name': name,
            'type': dataset_type,
            'rows': len(df),
            'columns': list(df.columns),
            'file_size_mb': filepath.stat().st_size / (1024 * 1024),
            'value_ranges': {}
        }
        
        # Calculate value ranges for numeric columns
        for col in df.select_dtypes(include=[np.number]).columns:
            metadata['value_ranges'][col] = {
                'min': int(df[col].min()),
                'max': int(df[col].max()),
                'mean': float(df[col].mean()),
                'std': float(df[col].std())
            }
        
        print(f"Loaded {metadata['rows']} rows, {len(metadata['columns'])} columns")
        
        return df, metadata
    
    def list_available_datasets(self, dataset_type: str = 'real') -> list:
        """List all available datasets."""
        if dataset_type == 'real':
            base_dir = self.real_data_dir
        else:
            base_dir = self.synthetic_data_dir
        
        if not base_dir.exists():
            return []
        
        csv_files = list(base_dir.rglob("*.csv"))
        return [f.stem for f in csv_files]


def main():
    """Main function to download datasets."""
    print("Agniya Dataset Downloader")
    print("="*60)
    print("This will download publicly available datasets for benchmarking.")
    print("Please ensure you have sufficient disk space (~500 MB).")
    print("="*60)
    
    downloader = RealDatasetDownloader()
    downloader.download_all()
    
    # Show what's available
    loader = DatasetLoader()
    real_datasets = loader.list_available_datasets('real')
    
    print(f"\nAvailable real datasets: {real_datasets}")


if __name__ == "__main__":
    main()
