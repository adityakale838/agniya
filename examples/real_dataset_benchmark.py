"""
Real-World Dataset Analysis: Medical Insurance Costs

This script uses the Medical Cost Personal Dataset from Kaggle
(publicly available healthcare data)

Dataset: Medical Insurance Costs
Source: https://www.kaggle.com/datasets/mirichoi0218/insurance
Size: ~1,300 records
Fields:
- age: Patient age
- sex: Patient gender
- bmi: Body Mass Index
- children: Number of children
- smoker: Smoking status
- region: Geographic region
- charges: Medical insurance charges (target for aggregation)

We'll demonstrate:
1. Loading real healthcare data
2. Encrypting sensitive fields (PII-like data)
3. Computing analytics on encrypted medical charges
4. Comparing performance with pure Paillier
"""

import os
import sys
import json
import pickle
import time
import pandas as pd
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from agniya.hybrid import HybridDatabase, Schema, Field, FieldType
from agniya.core.paillier import generate_keypair, encrypt, decrypt_crt


def download_dataset():
    """Download the medical insurance dataset."""
    print("\n" + "="*70)
    print("Downloading Real Medical Insurance Dataset")
    print("="*70)
    
    # URL for the dataset
    url = "https://raw.githubusercontent.com/stedy/Machine-Learning-with-R-datasets/master/insurance.csv"
    
    try:
        print(f"\nDownloading from: {url}")
        df = pd.read_csv(url)
        
        # Save locally
        os.makedirs("data", exist_ok=True)
        df.to_csv("data/insurance_real.csv", index=False)
        
        print(f"✅ Downloaded {len(df)} records")
        print(f"✅ Saved to: data/insurance_real.csv")
        
        return df
    except Exception as e:
        print(f"❌ Download failed: {e}")
        print("\nTrying backup dataset...")
        
        # If download fails, try local file
        if os.path.exists("data/insurance_real.csv"):
            print("✅ Using local cached version")
            return pd.read_csv("data/insurance_real.csv")
        else:
            raise Exception("Cannot load dataset")


def explore_dataset(df):
    """Explore the dataset."""
    print("\n" + "="*70)
    print("Dataset Overview")
    print("="*70)
    
    print(f"\n📊 Shape: {df.shape[0]} records × {df.shape[1]} columns")
    print(f"\n📋 Columns:")
    for col in df.columns:
        dtype = df[col].dtype
        unique = df[col].nunique()
        print(f"   - {col}: {dtype} ({unique} unique values)")
    
    print(f"\n📈 Sample Records:")
    print(df.head(5).to_string(index=False))
    
    print(f"\n💰 Medical Charges Statistics:")
    print(f"   Min: ${df['charges'].min():,.2f}")
    print(f"   Max: ${df['charges'].max():,.2f}")
    print(f"   Mean: ${df['charges'].mean():,.2f}")
    print(f"   Median: ${df['charges'].median():,.2f}")
    
    return df


def prepare_data(df):
    """Prepare data for encryption."""
    print("\n" + "="*70)
    print("Preparing Data for Encryption")
    print("="*70)
    
    # Add synthetic PII for demonstration
    df['patient_id'] = range(1000, 1000 + len(df))
    df['patient_name'] = df.apply(lambda x: f"Patient_{x['patient_id']}", axis=1)
    df['charges_cents'] = (df['charges'] * 100).astype(int)  # Convert to cents
    
    print(f"\n✅ Added fields:")
    print(f"   - patient_id (plaintext)")
    print(f"   - patient_name (for AES encryption)")
    print(f"   - charges_cents (for Paillier aggregation)")
    
    return df


def benchmark_hybrid_system(df, sample_size=None):
    """Benchmark hybrid encryption system."""
    if sample_size:
        df_sample = df.head(sample_size)
    else:
        df_sample = df
    
    print("\n" + "="*70)
    print(f"HYBRID SYSTEM: Encrypting {len(df_sample)} Records")
    print("="*70)
    
    # Define schema
    schema = Schema("medical_insurance", [
        Field("patient_id", FieldType.PLAINTEXT, int, nullable=False),
        Field("patient_name", FieldType.AES_ENCRYPTED, str),
        Field("sex", FieldType.AES_ENCRYPTED, str),
        Field("region", FieldType.PLAINTEXT, str),
        Field("smoker", FieldType.PLAINTEXT, str),
        Field("age", FieldType.PAILLIER_ENCRYPTED, int),
        Field("bmi", FieldType.PAILLIER_ENCRYPTED, int),  # Store as int (bmi*10)
        Field("children", FieldType.PAILLIER_ENCRYPTED, int),
        Field("charges_cents", FieldType.PAILLIER_ENCRYPTED, int),
    ])
    
    # Create database
    print("\nInitializing hybrid database...")
    start_init = time.time()
    db = HybridDatabase(schema, paillier_key_size=2048, enable_verbose=False)
    init_time = time.time() - start_init
    print(f"✅ Initialization: {init_time:.2f}s")
    
    # Insert records
    print(f"\nEncrypting {len(df_sample)} records...")
    start_insert = time.time()
    
    for idx, row in df_sample.iterrows():
        db.insert({
            "patient_id": int(row["patient_id"]),
            "patient_name": str(row["patient_name"]),
            "sex": str(row["sex"]),
            "region": str(row["region"]),
            "smoker": str(row["smoker"]),
            "age": int(row["age"]),
            "bmi": int(row["bmi"] * 10),  # Store as integer
            "children": int(row["children"]),
            "charges_cents": int(row["charges_cents"]),
        })
        
        if (idx + 1) % 100 == 0:
            elapsed = time.time() - start_insert
            rate = (idx + 1) / elapsed
            remaining = (len(df_sample) - (idx + 1)) / rate
            print(f"   Progress: {idx+1}/{len(df_sample)} ({rate:.1f} rec/s, ~{remaining:.0f}s remaining)")
    
    insert_time = time.time() - start_insert
    insert_rate = len(df_sample) / insert_time
    
    print(f"\n✅ Insertion complete!")
    print(f"   Total time: {insert_time:.2f}s")
    print(f"   Rate: {insert_rate:.2f} records/sec")
    print(f"   Avg time per record: {insert_time/len(df_sample)*1000:.2f}ms")
    
    # Query benchmark
    print("\nBenchmarking queries...")
    record_ids = list(db.records.keys())
    query_sample = record_ids[:20]  # Query 20 random records
    
    start_query = time.time()
    for record_id in query_sample:
        result = db.query(record_id)
    query_time = time.time() - start_query
    query_avg = query_time / len(query_sample)
    
    print(f"✅ Queried {len(query_sample)} records in {query_time:.3f}s")
    print(f"   Avg query time: {query_avg*1000:.2f}ms")
    
    # Aggregation benchmark
    print("\nComputing analytics on encrypted data...")
    start_agg = time.time()
    
    total_charges = db.aggregate("charges_cents", "sum")
    avg_charges = db.aggregate("charges_cents", "avg")
    avg_age = db.aggregate("age", "avg")
    avg_bmi = db.aggregate("bmi", "avg")
    
    agg_time = time.time() - start_agg
    
    print(f"✅ Aggregations computed in {agg_time:.3f}s")
    print(f"\n📊 Results:")
    print(f"   Total Medical Charges: ${total_charges/100:,.2f}")
    print(f"   Average Charge: ${avg_charges/100:,.2f}")
    print(f"   Average Age: {avg_age} years")
    print(f"   Average BMI: {avg_bmi/10:.1f}")
    
    # Save results
    results = {
        "dataset": "Medical Insurance (Real Data)",
        "records": len(df_sample),
        "system": "Hybrid AES-256 + Paillier-2048",
        "performance": {
            "initialization_time_sec": round(init_time, 2),
            "insertion_total_sec": round(insert_time, 2),
            "insertion_rate_per_sec": round(insert_rate, 2),
            "insertion_avg_ms": round(insert_time/len(df_sample)*1000, 2),
            "query_avg_ms": round(query_avg*1000, 2),
            "aggregation_total_sec": round(agg_time, 3)
        },
        "analytics": {
            "total_charges_usd": round(total_charges/100, 2),
            "average_charge_usd": round(avg_charges/100, 2),
            "average_age": avg_age,
            "average_bmi": round(avg_bmi/10, 1)
        }
    }
    
    return db, results


def benchmark_pure_paillier(df, sample_size=None):
    """Benchmark pure Paillier system for comparison."""
    if sample_size:
        df_sample = df.head(sample_size)
    else:
        df_sample = df
    
    print("\n" + "="*70)
    print(f"PURE PAILLIER: Encrypting {len(df_sample)} Records (Baseline)")
    print("="*70)
    
    # Generate keys
    print("\nGenerating Paillier keys...")
    start_init = time.time()
    pub, priv = generate_keypair(2048)
    init_time = time.time() - start_init
    print(f"✅ Initialization: {init_time:.2f}s")
    
    # Encrypt all fields
    print(f"\nEncrypting {len(df_sample)} records (ALL fields with Paillier)...")
    start_insert = time.time()
    
    encrypted_records = []
    for idx, row in df_sample.iterrows():
        encrypted = {
            "patient_id": encrypt(pub, int(row["patient_id"])),
            "age": encrypt(pub, int(row["age"])),
            "bmi": encrypt(pub, int(row["bmi"] * 10)),
            "children": encrypt(pub, int(row["children"])),
            "charges_cents": encrypt(pub, int(row["charges_cents"])),
        }
        encrypted_records.append(encrypted)
        
        if (idx + 1) % 50 == 0:
            elapsed = time.time() - start_insert
            rate = (idx + 1) / elapsed
            remaining = (len(df_sample) - (idx + 1)) / rate
            print(f"   Progress: {idx+1}/{len(df_sample)} ({rate:.1f} rec/s, ~{remaining:.0f}s remaining)")
    
    insert_time = time.time() - start_insert
    insert_rate = len(df_sample) / insert_time
    
    print(f"\n✅ Insertion complete!")
    print(f"   Total time: {insert_time:.2f}s")
    print(f"   Rate: {insert_rate:.2f} records/sec")
    print(f"   Avg time per record: {insert_time/len(df_sample)*1000:.2f}ms")
    
    # Query benchmark
    print("\nBenchmarking queries...")
    start_query = time.time()
    for i in range(min(20, len(encrypted_records))):
        record = encrypted_records[i]
        # Decrypt all fields
        decrypted = {
            "patient_id": decrypt_crt(pub, priv, record["patient_id"]),
            "age": decrypt_crt(pub, priv, record["age"]),
            "charges": decrypt_crt(pub, priv, record["charges_cents"]),
        }
    query_time = time.time() - start_query
    query_avg = query_time / min(20, len(encrypted_records))
    
    print(f"✅ Queried {min(20, len(encrypted_records))} records in {query_time:.3f}s")
    print(f"   Avg query time: {query_avg*1000:.2f}ms")
    
    # Aggregation
    print("\nComputing aggregations...")
    start_agg = time.time()
    
    result_ct = encrypted_records[0]["charges_cents"]
    for record in encrypted_records[1:]:
        result_ct = (result_ct * record["charges_cents"]) % pub.n_squared
    
    total_charges = decrypt_crt(pub, priv, result_ct)
    agg_time = time.time() - start_agg
    
    print(f"✅ Aggregation computed in {agg_time:.3f}s")
    print(f"   Total Medical Charges: ${total_charges/100:,.2f}")
    
    results = {
        "dataset": "Medical Insurance (Real Data)",
        "records": len(df_sample),
        "system": "Pure Paillier-2048",
        "performance": {
            "initialization_time_sec": round(init_time, 2),
            "insertion_total_sec": round(insert_time, 2),
            "insertion_rate_per_sec": round(insert_rate, 2),
            "insertion_avg_ms": round(insert_time/len(df_sample)*1000, 2),
            "query_avg_ms": round(query_avg*1000, 2),
            "aggregation_total_sec": round(agg_time, 3)
        },
        "analytics": {
            "total_charges_usd": round(total_charges/100, 2)
        }
    }
    
    return results


def generate_comparison_report(hybrid_results, paillier_results):
    """Generate comprehensive comparison report."""
    print("\n" + "="*70)
    print("PERFORMANCE COMPARISON: Real Medical Dataset")
    print("="*70)
    
    hybrid_perf = hybrid_results["performance"]
    paillier_perf = paillier_results["performance"]
    
    # Calculate speedups
    insert_speedup = paillier_perf["insertion_avg_ms"] / hybrid_perf["insertion_avg_ms"]
    query_speedup = paillier_perf["query_avg_ms"] / hybrid_perf["query_avg_ms"]
    agg_speedup = paillier_perf["aggregation_total_sec"] / hybrid_perf["aggregation_total_sec"]
    
    print(f"\n📊 Dataset: {hybrid_results['dataset']}")
    print(f"   Records: {hybrid_results['records']:,}")
    
    print(f"\n⚡ INSERTION PERFORMANCE:")
    print(f"   Pure Paillier:  {paillier_perf['insertion_avg_ms']:.2f}ms per record")
    print(f"   Hybrid System:  {hybrid_perf['insertion_avg_ms']:.2f}ms per record")
    print(f"   ✅ SPEEDUP:     {insert_speedup:.2f}x faster")
    
    print(f"\n⚡ QUERY PERFORMANCE:")
    print(f"   Pure Paillier:  {paillier_perf['query_avg_ms']:.2f}ms per query")
    print(f"   Hybrid System:  {hybrid_perf['query_avg_ms']:.2f}ms per query")
    print(f"   ✅ SPEEDUP:     {query_speedup:.2f}x faster")
    
    print(f"\n⚡ AGGREGATION PERFORMANCE:")
    print(f"   Pure Paillier:  {paillier_perf['aggregation_total_sec']:.3f}s")
    print(f"   Hybrid System:  {hybrid_perf['aggregation_total_sec']:.3f}s")
    print(f"   ✅ SPEEDUP:     {agg_speedup:.2f}x")
    
    print(f"\n💰 ANALYTICS RESULTS:")
    print(f"   Total Medical Charges: ${hybrid_results['analytics']['total_charges_usd']:,.2f}")
    print(f"   Average Charge:        ${hybrid_results['analytics']['average_charge_usd']:,.2f}")
    print(f"   Average Age:           {hybrid_results['analytics']['average_age']} years")
    print(f"   Average BMI:           {hybrid_results['analytics']['average_bmi']}")
    
    # Prepare comparison data
    comparison = {
        "timestamp": datetime.now().isoformat(),
        "dataset": hybrid_results["dataset"],
        "records": hybrid_results["records"],
        "comparison": {
            "insertion_speedup": round(insert_speedup, 2),
            "query_speedup": round(query_speedup, 2),
            "aggregation_speedup": round(agg_speedup, 2)
        },
        "pure_paillier": paillier_results,
        "hybrid_system": hybrid_results
    }
    
    return comparison


def save_results(db, comparison):
    """Save all results to files."""
    print("\n" + "="*70)
    print("Saving Results")
    print("="*70)
    
    os.makedirs("output/real_dataset", exist_ok=True)
    
    # Save encrypted database
    print("\n1. Saving encrypted database...")
    with open("output/real_dataset/encrypted_medical_db.pkl", "wb") as f:
        pickle.dump(db, f)
    print("   ✅ output/real_dataset/encrypted_medical_db.pkl")
    
    # Save comparison JSON
    print("\n2. Saving comparison results...")
    with open("output/real_dataset/performance_comparison.json", "w") as f:
        json.dump(comparison, f, indent=2)
    print("   ✅ output/real_dataset/performance_comparison.json")
    
    # Save CSV report
    print("\n3. Saving CSV report...")
    comparison_df = pd.DataFrame([
        {"Metric": "Insertion Time (ms/record)", 
         "Pure Paillier": comparison["pure_paillier"]["performance"]["insertion_avg_ms"],
         "Hybrid System": comparison["hybrid_system"]["performance"]["insertion_avg_ms"],
         "Speedup": f"{comparison['comparison']['insertion_speedup']}x"},
        {"Metric": "Query Time (ms/query)",
         "Pure Paillier": comparison["pure_paillier"]["performance"]["query_avg_ms"],
         "Hybrid System": comparison["hybrid_system"]["performance"]["query_avg_ms"],
         "Speedup": f"{comparison['comparison']['query_speedup']}x"},
        {"Metric": "Aggregation Time (sec)",
         "Pure Paillier": comparison["pure_paillier"]["performance"]["aggregation_total_sec"],
         "Hybrid System": comparison["hybrid_system"]["performance"]["aggregation_total_sec"],
         "Speedup": f"{comparison['comparison']['aggregation_speedup']}x"},
    ])
    comparison_df.to_csv("output/real_dataset/performance_comparison.csv", index=False)
    print("   ✅ output/real_dataset/performance_comparison.csv")
    
    # Generate HTML report
    print("\n4. Generating HTML report...")
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Real Dataset Performance Analysis</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .metric {{ background: #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .speedup {{ background: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .speedup-value {{ font-size: 32px; color: #28a745; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #3498db; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .highlight {{ background: #fff3cd; padding: 20px; border-radius: 5px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏥 Real Medical Dataset Performance Analysis</h1>
        <p><strong>Dataset:</strong> {comparison['dataset']}</p>
        <p><strong>Records:</strong> {comparison['records']:,}</p>
        <p><strong>Generated:</strong> {comparison['timestamp']}</p>
        
        <div class="highlight">
            <h2>🎯 Key Performance Improvements</h2>
            <div class="speedup">
                <strong>Insertion Speed:</strong>
                <div class="speedup-value">{comparison['comparison']['insertion_speedup']}x FASTER</div>
            </div>
            <div class="speedup">
                <strong>Query Speed:</strong>
                <div class="speedup-value">{comparison['comparison']['query_speedup']}x FASTER</div>
            </div>
            <div class="speedup">
                <strong>Aggregation Speed:</strong>
                <div class="speedup-value">{comparison['comparison']['aggregation_speedup']}x</div>
            </div>
        </div>
        
        <h2>📊 Detailed Performance Comparison</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Pure Paillier</th>
                <th>Hybrid System</th>
                <th>Improvement</th>
            </tr>
            <tr>
                <td>Insertion (ms/record)</td>
                <td>{comparison['pure_paillier']['performance']['insertion_avg_ms']:.2f}</td>
                <td>{comparison['hybrid_system']['performance']['insertion_avg_ms']:.2f}</td>
                <td style="color: #28a745; font-weight: bold;">{comparison['comparison']['insertion_speedup']}x</td>
            </tr>
            <tr>
                <td>Query (ms/query)</td>
                <td>{comparison['pure_paillier']['performance']['query_avg_ms']:.2f}</td>
                <td>{comparison['hybrid_system']['performance']['query_avg_ms']:.2f}</td>
                <td style="color: #28a745; font-weight: bold;">{comparison['comparison']['query_speedup']}x</td>
            </tr>
            <tr>
                <td>Aggregation (seconds)</td>
                <td>{comparison['pure_paillier']['performance']['aggregation_total_sec']:.3f}</td>
                <td>{comparison['hybrid_system']['performance']['aggregation_total_sec']:.3f}</td>
                <td style="color: #28a745; font-weight: bold;">{comparison['comparison']['aggregation_speedup']}x</td>
            </tr>
        </table>
        
        <h2>💰 Medical Analytics Results</h2>
        <div class="metric">
            <strong>Total Medical Charges:</strong> ${comparison['hybrid_system']['analytics']['total_charges_usd']:,.2f}
        </div>
        <div class="metric">
            <strong>Average Charge per Patient:</strong> ${comparison['hybrid_system']['analytics']['average_charge_usd']:,.2f}
        </div>
        <div class="metric">
            <strong>Average Patient Age:</strong> {comparison['hybrid_system']['analytics']['average_age']} years
        </div>
        <div class="metric">
            <strong>Average BMI:</strong> {comparison['hybrid_system']['analytics']['average_bmi']}
        </div>
        
        <div style="background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 5px; margin-top: 20px;">
            <strong>🔐 Security Note:</strong> All analytics computed on encrypted data without decryption. Real medical records remain private throughout the entire process.
        </div>
    </div>
</body>
</html>
"""
    
    with open("output/real_dataset/performance_report.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("   ✅ output/real_dataset/performance_report.html")


def main():
    """Main execution."""
    print("\n" + "="*70)
    print("REAL DATASET BENCHMARK: Medical Insurance Data")
    print("="*70)
    
    # Download dataset
    df = download_dataset()
    
    # Explore dataset
    df = explore_dataset(df)
    
    # Prepare data
    df = prepare_data(df)
    
    # Use smaller sample for demo (or full dataset)
    sample_size = 500  # Change to None for full dataset (~1338 records)
    
    print(f"\n{'='*70}")
    print(f"BENCHMARK CONFIGURATION")
    print(f"{'='*70}")
    print(f"Sample size: {sample_size if sample_size else 'Full dataset'} records")
    print(f"Total available: {len(df)} records")
    
    # Benchmark Pure Paillier
    paillier_results = benchmark_pure_paillier(df, sample_size)
    
    # Benchmark Hybrid System
    db, hybrid_results = benchmark_hybrid_system(df, sample_size)
    
    # Generate comparison
    comparison = generate_comparison_report(hybrid_results, paillier_results)
    
    # Save results
    save_results(db, comparison)
    
    # Final summary
    print("\n" + "="*70)
    print("✅ REAL DATASET ANALYSIS COMPLETE!")
    print("="*70)
    print("\n📁 Generated Files:")
    print("   - output/real_dataset/encrypted_medical_db.pkl")
    print("   - output/real_dataset/performance_comparison.json")
    print("   - output/real_dataset/performance_comparison.csv")
    print("   - output/real_dataset/performance_report.html")
    
    print("\n📊 Key Results:")
    print(f"   ⚡ Insertion: {comparison['comparison']['insertion_speedup']}x faster")
    print(f"   ⚡ Query: {comparison['comparison']['query_speedup']}x faster")
    print(f"   ⚡ Aggregation: {comparison['comparison']['aggregation_speedup']}x")
    
    print("\n🎉 Open performance_report.html to view full results!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
