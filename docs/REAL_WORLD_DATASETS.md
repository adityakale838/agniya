# Real-World Dataset Benchmarks for AGNIYA

## Overview

This benchmark tests AGNIYA with actual sensitive data from Kaggle, demonstrating real-world encrypted database use cases for patent evidence.

---

## 📊 Recommended Datasets

### 1. Healthcare Insurance Costs
- **Dataset**: Medical Insurance Cost Dataset
- **URL**: https://www.kaggle.com/datasets/mirichoi0218/insurance
- **Size**: ~1,300 rows
- **Columns**: age, bmi, children, charges (medical costs)
- **Use Case**: Hospital billing system with encrypted patient financial records
- **Why Important**: HIPAA compliance requires encryption of medical billing data

### 2. Employee Salaries
- **Dataset**: Data Science Job Salaries
- **URL**: https://www.kaggle.com/datasets/ruchi798/data-science-job-salaries
- **Size**: ~600 rows
- **Columns**: salary, salary_in_usd, experience_level
- **Use Case**: HR system with encrypted employee compensation
- **Why Important**: Salary data is highly confidential and requires encryption

### 3. Credit Card Transactions
- **Dataset**: Credit Card Fraud Detection
- **URL**: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
- **Size**: ~280,000 rows
- **Columns**: Amount, Time, V1-V28 (PCA features)
- **Use Case**: Banking system with encrypted transaction amounts
- **Why Important**: PCI-DSS compliance requires credit card data encryption

### 4. E-Commerce Sales
- **Dataset**: E-Commerce Data
- **URL**: https://www.kaggle.com/datasets/carrie1/ecommerce-data
- **Size**: ~500,000 rows
- **Columns**: Quantity, UnitPrice, CustomerID
- **Use Case**: Retail analytics with encrypted revenue data
- **Why Important**: Business intelligence on sensitive sales data

### 5. Employee Records
- **Dataset**: Employee Dataset
- **URL**: https://www.kaggle.com/datasets/tawfikelmetwally/employee-dataset
- **Size**: ~1,000 rows
- **Columns**: Age, Salary, Years_at_Company
- **Use Case**: Enterprise HR management with encrypted employee data
- **Why Important**: Employee records require protection under GDPR/privacy laws

---

## 🚀 Quick Start

### Step 1: Download Datasets

1. **Create Kaggle account** (if you don't have one):
   - Go to https://www.kaggle.com/
   - Sign up with email or Google account

2. **Download datasets**:
   ```powershell
   # Create directory
   mkdir g:\agniya\data\real_world
   
   # Visit each URL above and click "Download"
   # Extract CSV files to: g:\agniya\data\real_world\
   ```

3. **Expected files**:
   ```
   data/real_world/
   ├── insurance.csv
   ├── ds_salaries.csv
   ├── creditcard.csv
   ├── data.csv
   └── Employee.csv
   ```

### Step 2: Run Benchmark

```powershell
cd g:\agniya
.\envb\Scripts\activate
python scripts\real_world_benchmark.py
```

**Expected time**: 5-10 minutes  
**Output**: `results/real_world/real_world_benchmark_*.csv`

---

## 📈 What Gets Tested

For each dataset, the benchmark measures:

1. **Encryption Performance**
   - 100, 1K, 10K rows
   - With and without caching
   - Throughput (operations/second)

2. **Query Performance**
   - Homomorphic SUM queries
   - End-to-end latency
   - Verification (encrypted result = plaintext result)

3. **Real-World Scenarios**
   - Hospital billing totals
   - Employee salary analytics
   - Credit card transaction sums
   - E-commerce revenue calculations

---

## 🎯 Patent Use Cases

### Use Case 1: Healthcare Compliance (HIPAA)
**Dataset**: insurance.csv  
**Scenario**: Hospital needs to compute total medical costs across patients without decrypting individual records.

**Evidence**:
- Encrypted patient charges: X ops/sec
- SUM query on 10K patients: Y seconds
- Result verified: ✓ Matches plaintext computation

### Use Case 2: Financial Services (PCI-DSS)
**Dataset**: creditcard.csv  
**Scenario**: Bank analyzes transaction patterns while keeping amounts encrypted.

**Evidence**:
- Encrypted transactions: X ops/sec
- SUM query on 100K transactions: Y seconds
- Fraud detection possible on encrypted data

### Use Case 3: HR Privacy (GDPR)
**Dataset**: ds_salaries.csv, Employee.csv  
**Scenario**: Company computes average/total salaries without exposing individual compensation.

**Evidence**:
- Encrypted salaries: X ops/sec
- Analytics on 1K employees: Y seconds
- Zero plaintext exposure

### Use Case 4: E-Commerce Analytics
**Dataset**: data.csv  
**Scenario**: Retailer performs sales analytics while protecting customer purchase data.

**Evidence**:
- Encrypted revenue: X ops/sec
- SUM query on 10K orders: Y seconds
- Business intelligence without data breach risk

---

## 📊 Expected Results

### Typical Performance
- **Small datasets (100-1K rows)**: 1-2 seconds encryption
- **Medium datasets (10K rows)**: 10-20 seconds encryption
- **Large datasets (100K+ rows)**: 2-5 minutes encryption (first time)
- **Cached encryption**: 100-1000× faster for repeated values

### Query Performance
- **SUM query (100 samples)**: 2-5 seconds
- **SUM query (1K samples)**: 30-50 seconds
- **Extrapolated for 1M rows**: Proportional scaling

### Use Cache?
- **First encryption**: Cache slower (precomputation overhead)
- **Repeated values**: Cache 100-1000× faster
- **Recommendation**: Use cache for production systems with value reuse

---

## 🔬 For Patent Filing

### Why Real-World Data Matters

Patent examiners want to see:
1. ✅ **Practical applicability**: Not just synthetic data
2. ✅ **Industry relevance**: Healthcare, finance, HR use cases
3. ✅ **Performance on real workloads**: Actual data distributions
4. ✅ **Compliance scenarios**: HIPAA, PCI-DSS, GDPR examples

### Evidence to Include

From `results/real_world/real_world_benchmark_*.csv`:

**For Form 2, Section 4 (Technical Effect)**:
- Healthcare: "System encrypts 1,300 patient records at X ops/sec"
- Finance: "System processes 280,000 credit card transactions with encryption"
- HR: "System performs salary analytics on encrypted employee data"

**For Form 2, Section 6 (Industrial Applicability)**:
- "Tested with real healthcare data (HIPAA scenario)"
- "Validated with actual credit card transactions (PCI-DSS compliance)"
- "Demonstrated on employee records (GDPR privacy protection)"

---

## 📁 Output Files

After running the benchmark:

```
results/real_world/
└── real_world_benchmark_YYYYMMDD_HHMMSS.csv
```

**CSV Columns**:
- `dataset`: Dataset name (healthcare, salary, credit_card, etc.)
- `dataset_name`: Full dataset name
- `use_case`: Real-world application scenario
- `num_rows`: Number of rows tested
- `column`: Column used for encryption
- `value_min`, `value_max`: Value range
- `use_cache`: Whether cache was used
- `encryption_time_sec`: Time to encrypt dataset
- `encryption_throughput_ops_sec`: Operations per second
- `sum_query_time_sec`: Time for SUM query
- `verification_passed`: ✓ If result matches plaintext

---

## 🆘 Troubleshooting

### Issue: "No datasets found"
**Solution**: Download CSV files from Kaggle URLs and place in `data/real_world/`

### Issue: "ModuleNotFoundError"
**Solution**: Activate virtual environment:
```powershell
.\envb\Scripts\activate
```

### Issue: Dataset too large (e.g., creditcard.csv = 150MB)
**Solution**: The script automatically samples rows. For very large datasets:
```python
# Edit real_world_benchmark.py
# Change: num_rows in [100, 1000, 10000]
# To: num_rows in [100, 1000]  # Skip 10K for huge datasets
```

---

## ✅ Checklist

Before running:
- [ ] Kaggle account created
- [ ] Datasets downloaded (at least 2-3)
- [ ] CSV files placed in `data/real_world/`
- [ ] Virtual environment activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)

After running:
- [ ] Results CSV generated
- [ ] All verifications passed (✓)
- [ ] Performance metrics documented
- [ ] Ready to include in patent filing

---

**Status**: Ready for real-world validation testing!  
**Impact**: Demonstrates AGNIYA works with actual sensitive data, not just synthetic benchmarks.  
**Patent Value**: Shows practical applicability across healthcare, finance, and HR industries.
