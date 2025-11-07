"""
Complete End-to-End Example: Customer Transaction Analysis

This script demonstrates the complete workflow:
1. Load customer transaction data (CSV)
2. Encrypt sensitive fields (names, emails) with AES
3. Encrypt computational fields (amounts) with Paillier
4. Compute analytics WITHOUT decrypting individual transactions
5. Save results to multiple formats (JSON, CSV, HTML report)

Usage:
    python examples/complete_workflow.py
    
Output:
    - output/encrypted_database.pkl
    - output/analytics_results.json
    - output/analytics_results.csv
    - output/analytics_report.html
"""

import os
import sys
import json
import pickle
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agniya.hybrid import HybridDatabase, Schema, Field, FieldType


def create_sample_dataset(num_records=100):
    """Generate sample customer transaction data."""
    import random
    
    print(f"\n{'='*70}")
    print(f"Generating {num_records} Sample Customer Transactions")
    print('='*70)
    
    customers = ["Alice Johnson", "Bob Smith", "Carol Williams", "David Brown", 
                 "Emma Davis", "Frank Miller", "Grace Wilson", "Henry Moore",
                 "Ivy Taylor", "Jack Anderson"]
    
    transactions = []
    for i in range(num_records):
        transaction = {
            "transaction_id": 10000 + i,
            "customer_name": customers[i % len(customers)],
            "customer_email": f"customer{i % len(customers)}@example.com",
            "transaction_amount": random.randint(1000, 50000),  # cents
            "customer_age": random.randint(18, 75),
            "transaction_date": f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
        }
        transactions.append(transaction)
    
    df = pd.DataFrame(transactions)
    print(f"✅ Generated {len(df)} transactions")
    print(f"\nSample records:")
    print(df.head(3).to_string(index=False))
    
    return df


def step1_encrypt_data(df):
    """Step 1: Encrypt the dataset."""
    print(f"\n{'='*70}")
    print("STEP 1: Encrypting Customer Data")
    print('='*70)
    
    # Define schema
    print("\n1.1. Creating encryption schema...")
    schema = Schema("customer_transactions", [
        Field("transaction_id", FieldType.PLAINTEXT, int, nullable=False,
              description="Transaction ID (plaintext for indexing)"),
        Field("customer_name", FieldType.AES_ENCRYPTED, str,
              description="Customer name (AES-encrypted for privacy)"),
        Field("customer_email", FieldType.AES_ENCRYPTED, str,
              description="Email address (AES-encrypted)"),
        Field("transaction_amount", FieldType.PAILLIER_ENCRYPTED, int,
              description="Amount in cents (Paillier for aggregation)"),
        Field("customer_age", FieldType.PAILLIER_ENCRYPTED, int,
              description="Age (Paillier for demographics)"),
        Field("transaction_date", FieldType.PLAINTEXT, str,
              description="Date (plaintext for queries)"),
    ])
    
    schema.print_schema()
    
    # Create encrypted database
    print("\n1.2. Initializing encrypted database...")
    db = HybridDatabase(schema, paillier_key_size=2048, enable_verbose=False)
    print("✅ Database initialized")
    
    # Encrypt and insert records
    print(f"\n1.3. Encrypting {len(df)} transactions...")
    start_time = datetime.now()
    
    for idx, row in df.iterrows():
        db.insert(row.to_dict())
        
        if (idx + 1) % 25 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = (idx + 1) / elapsed
            print(f"   Progress: {idx+1}/{len(df)} ({rate:.1f} records/sec)")
    
    total_time = (datetime.now() - start_time).total_seconds()
    print(f"\n✅ Encryption complete!")
    print(f"   Time: {total_time:.2f}s")
    print(f"   Rate: {len(df)/total_time:.1f} records/sec")
    
    # Save encrypted database
    print("\n1.4. Saving encrypted database...")
    os.makedirs("output", exist_ok=True)
    with open("output/encrypted_database.pkl", "wb") as f:
        pickle.dump(db, f)
    print("✅ Saved to: output/encrypted_database.pkl")
    
    return db


def step2_compute_analytics(db):
    """Step 2: Compute analytics on encrypted data."""
    print(f"\n{'='*70}")
    print("STEP 2: Computing Analytics on Encrypted Data")
    print('='*70)
    print("\n⚠️  NOTE: Analytics computed WITHOUT decrypting individual transactions!")
    
    # Compute aggregations
    print("\n2.1. Computing encrypted aggregations...")
    
    total_revenue = db.aggregate("transaction_amount", "sum")
    avg_transaction = db.aggregate("transaction_amount", "avg")
    avg_age = db.aggregate("customer_age", "avg")
    
    print(f"✅ Aggregations computed:")
    print(f"   Total Revenue: ${total_revenue/100:,.2f}")
    print(f"   Average Transaction: ${avg_transaction/100:,.2f}")
    print(f"   Average Customer Age: {avg_age} years")
    
    # Prepare results
    results = {
        "timestamp": datetime.now().isoformat(),
        "database_info": {
            "total_transactions": len(db.records),
            "encryption_method": "Hybrid AES-256 + Paillier-2048"
        },
        "analytics": {
            "total_revenue_usd": round(total_revenue / 100, 2),
            "average_transaction_usd": round(avg_transaction / 100, 2),
            "average_customer_age": avg_age
        },
        "security_note": "All analytics computed on encrypted data without decryption"
    }
    
    return results


def step3_save_results(results, db):
    """Step 3: Save results to multiple formats."""
    print(f"\n{'='*70}")
    print("STEP 3: Exporting Results")
    print('='*70)
    
    # Save as JSON
    print("\n3.1. Saving JSON format...")
    with open("output/analytics_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("✅ Saved to: output/analytics_results.json")
    
    # Save as CSV
    print("\n3.2. Saving CSV format...")
    csv_data = [
        {"Metric": "Total Transactions", "Value": results["database_info"]["total_transactions"]},
        {"Metric": "Total Revenue (USD)", "Value": f"${results['analytics']['total_revenue_usd']:,.2f}"},
        {"Metric": "Average Transaction (USD)", "Value": f"${results['analytics']['average_transaction_usd']:,.2f}"},
        {"Metric": "Average Customer Age", "Value": f"{results['analytics']['average_customer_age']} years"},
    ]
    pd.DataFrame(csv_data).to_csv("output/analytics_results.csv", index=False)
    print("✅ Saved to: output/analytics_results.csv")
    
    # Save as HTML report
    print("\n3.3. Generating HTML report...")
    html_report = f"""
<!DOCTYPE html>
<html>
<head>
    <title>AGNIYA Analytics Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .metric {{ background: #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #3498db; }}
        .metric-name {{ font-weight: bold; color: #2c3e50; }}
        .metric-value {{ font-size: 24px; color: #27ae60; margin-top: 5px; }}
        .security-note {{ background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 5px; margin-top: 20px; }}
        .timestamp {{ color: #7f8c8d; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 AGNIYA Encrypted Analytics Report</h1>
        <p class="timestamp">Generated: {results['timestamp']}</p>
        
        <h2>Database Information</h2>
        <div class="metric">
            <div class="metric-name">Total Transactions</div>
            <div class="metric-value">{results['database_info']['total_transactions']:,}</div>
        </div>
        <div class="metric">
            <div class="metric-name">Encryption Method</div>
            <div class="metric-value" style="font-size: 16px;">{results['database_info']['encryption_method']}</div>
        </div>
        
        <h2>Analytics Results</h2>
        <div class="metric">
            <div class="metric-name">💰 Total Revenue</div>
            <div class="metric-value">${results['analytics']['total_revenue_usd']:,.2f}</div>
        </div>
        <div class="metric">
            <div class="metric-name">📊 Average Transaction</div>
            <div class="metric-value">${results['analytics']['average_transaction_usd']:,.2f}</div>
        </div>
        <div class="metric">
            <div class="metric-name">👥 Average Customer Age</div>
            <div class="metric-value">{results['analytics']['average_customer_age']} years</div>
        </div>
        
        <div class="security-note">
            <strong>🔐 Security Note:</strong> {results['security_note']}
        </div>
    </div>
</body>
</html>
"""
    
    with open("output/analytics_report.html", "w", encoding="utf-8") as f:
        f.write(html_report)
    print("✅ Saved to: output/analytics_report.html")


def step4_query_samples(db):
    """Step 4: Query individual records (optional demo)."""
    print(f"\n{'='*70}")
    print("STEP 4: Querying Sample Records (Decryption Demo)")
    print('='*70)
    
    record_ids = list(db.records.keys())
    
    print(f"\nQuerying first 3 transactions...")
    for i, record_id in enumerate(record_ids[:3]):
        transaction = db.query(record_id)
        
        print(f"\nTransaction #{i+1}:")
        print(f"  ID: {transaction['transaction_id']}")
        print(f"  Customer: {transaction['customer_name']}")
        print(f"  Email: {transaction['customer_email']}")
        print(f"  Amount: ${transaction['transaction_amount']/100:.2f}")
        print(f"  Age: {transaction['customer_age']} years")
        print(f"  Date: {transaction['transaction_date']}")


def main():
    """Main execution flow."""
    print("\n" + "="*70)
    print("AGNIYA COMPLETE WORKFLOW EXAMPLE")
    print("Customer Transaction Analysis with Encrypted Data")
    print("="*70)
    
    # Generate sample data
    df = create_sample_dataset(num_records=100)
    
    # Step 1: Encrypt data
    db = step1_encrypt_data(df)
    
    # Step 2: Compute analytics
    results = step2_compute_analytics(db)
    
    # Step 3: Save results
    step3_save_results(results, db)
    
    # Step 4: Query samples
    step4_query_samples(db)
    
    # Final summary
    print(f"\n{'='*70}")
    print("✅ WORKFLOW COMPLETE!")
    print('='*70)
    print("\nGenerated Files:")
    print("  📁 output/encrypted_database.pkl      - Encrypted database")
    print("  📄 output/analytics_results.json      - Results in JSON format")
    print("  📊 output/analytics_results.csv       - Results in CSV format")
    print("  📝 output/analytics_report.html       - Visual HTML report")
    
    print("\nNext Steps:")
    print("  1. Open output/analytics_report.html in your browser")
    print("  2. View analytics_results.csv in Excel")
    print("  3. Load encrypted_database.pkl for further analysis")
    
    print("\n" + "="*70)
    print("🎉 Example complete! Check the output/ folder for results.")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
