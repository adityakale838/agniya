import pandas as pd
import numpy as np
import random
import string
import os
from pathlib import Path

class DatasetGenerator:
    def __init__(self, output_dir="data/synthetic"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_medical_dataset(self, num_records=10000):
        """
        Generates a synthetic Medical dataset mimicking 'Heart Disease UCI'.
        Fields: PatientID (str), Age (int), BMI (float), BloodPressure (int), Diagnosis (str)
        """
        print(f"Generating Medical dataset with {num_records} records...")
        
        data = {
            'PatientID': [f"PAT-{i:06d}" for i in range(num_records)],
            'Age': np.random.randint(18, 90, num_records),
            'BMI': np.round(np.random.uniform(18.5, 40.0, num_records), 1),
            'BloodPressure': np.random.randint(90, 180, num_records),
            'Diagnosis': np.random.choice(['Healthy', 'Diabetes', 'Hypertension', 'Heart Disease'], num_records, p=[0.4, 0.2, 0.3, 0.1])
        }
        
        df = pd.DataFrame(data)
        output_path = self.output_dir / "medical_records.csv"
        df.to_csv(output_path, index=False)
        print(f"✅ Saved to {output_path}")
        return str(output_path)

    def generate_financial_dataset(self, num_records=10000):
        """
        Generates a synthetic Financial dataset mimicking 'Credit Card Fraud Detection'.
        Fields: TransID (str), Amount (float), Balance (float), Merchant (str)
        """
        print(f"Generating Financial dataset with {num_records} records...")
        
        merchants = [f"MERCHANT-{i:03d}" for i in range(100)]
        
        data = {
            'TransID': [f"TXN-{i:08d}" for i in range(num_records)],
            'Amount': np.round(np.random.exponential(100, num_records), 2),  # Exponential distribution for amounts
            'Balance': np.round(np.random.uniform(1000, 50000, num_records), 2),
            'Merchant': np.random.choice(merchants, num_records)
        }
        
        df = pd.DataFrame(data)
        output_path = self.output_dir / "financial_transactions.csv"
        df.to_csv(output_path, index=False)
        print(f"✅ Saved to {output_path}")
        return str(output_path)

if __name__ == "__main__":
    gen = DatasetGenerator()
    gen.generate_medical_dataset(10000)
    gen.generate_financial_dataset(10000)
