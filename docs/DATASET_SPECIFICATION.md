# Dataset Specification for Agniya Benchmarking

## Overview
This document specifies the datasets used for benchmarking the Agniya hybrid encryption system.

## Dataset Categories

### 1. Healthcare Dataset (Small Values, High Security)
**Purpose:** Test performance on sensitive, small-range integer data
- **Rows:** 100K, 500K, 1M, 5M
- **Columns:**
  - `patient_id` (integer, 1-1,000,000)
  - `age` (integer, 0-120)
  - `heart_rate` (integer, 40-200)
  - `blood_pressure_systolic` (integer, 70-200)
  - `blood_pressure_diastolic` (integer, 40-130)
  - `glucose_level` (integer, 50-400)
  - `cholesterol` (integer, 100-400)
  - `temperature` (integer, 95-105, stored as tenths: 950-1050)
- **Value Ranges:** Small (0-1,000) - Perfect for adaptive bit-length optimization
- **Query Types:** AVG, SUM, COUNT with filters

### 2. Financial Dataset (Large Values, High Precision)
**Purpose:** Test performance on large monetary values
- **Rows:** 100K, 500K, 1M, 5M
- **Columns:**
  - `transaction_id` (integer, 1-10,000,000)
  - `account_balance` (integer, cents: 0-10,000,000,000) # $0 - $100M
  - `transaction_amount` (integer, cents: -1,000,000 to 1,000,000) # ±$10K
  - `salary` (integer, cents: 2,000,000-50,000,000) # $20K - $500K
  - `loan_amount` (integer, cents: 0-100,000,000) # $0 - $1M
  - `credit_score` (integer, 300-850)
- **Value Ranges:** Large (10^6 - 10^10) - Tests CRT optimization
- **Query Types:** SUM, AVG, range queries

### 3. IoT Sensor Dataset (High Volume, Mixed Ranges)
**Purpose:** Test throughput and pipeline efficiency
- **Rows:** 1M, 5M, 10M
- **Columns:**
  - `sensor_id` (integer, 1-10,000)
  - `timestamp` (integer, Unix epoch)
  - `temperature` (integer, -40 to 125, tenths: -400 to 1250)
  - `humidity` (integer, 0-100)
  - `pressure` (integer, 870-1085)
  - `light_level` (integer, 0-10000)
  - `battery_level` (integer, 0-100)
- **Value Ranges:** Mixed (0-10,000) - Tests adaptive selection
- **Query Types:** Aggregations over time windows, grouped by sensor

### 4. E-commerce Dataset (Sparse Data, Frequent Queries)
**Purpose:** Test caching and precomputation effectiveness
- **Rows:** 500K, 2M, 5M
- **Columns:**
  - `order_id` (integer, 1-10,000,000)
  - `product_price` (integer, cents: 100-1,000,000) # $1 - $10K
  - `quantity` (integer, 1-1000)
  - `discount_percent` (integer, 0-75)
  - `shipping_cost` (integer, cents: 0-10,000) # $0 - $100
  - `customer_id` (integer, 1-100,000)
- **Value Ranges:** Medium (10^2 - 10^6) - Tests all optimizations
- **Query Types:** Repeated aggregations (total revenue, avg order value)

## Synthetic Data Generation Parameters

### Distribution Types
1. **Uniform Distribution** - Baseline
2. **Normal Distribution** - Real-world simulation
3. **Zipf Distribution** - Skewed data (common in real systems)
4. **Bimodal Distribution** - Mixed populations

### Key Characteristics
- **Cardinality:** Low (age), Medium (salary), High (transaction_id)
- **Null Values:** 0%, 5%, 15% (to test real-world scenarios)
- **Outliers:** 1-5% extreme values
- **Correlation:** Some columns correlated (e.g., age vs. salary)

## Benchmark Query Suite

### Query Categories

#### 1. Simple Aggregations
```sql
-- Q1: Total sum
SELECT SUM(salary) FROM employees;

-- Q2: Average value
SELECT AVG(age) FROM patients;

-- Q3: Count with filter
SELECT COUNT(*) FROM transactions WHERE amount > 1000;
```

#### 2. Filtered Aggregations
```sql
-- Q4: Conditional sum
SELECT SUM(salary) FROM employees WHERE department = 5;

-- Q5: Range query
SELECT AVG(heart_rate) FROM patients WHERE age BETWEEN 30 AND 60;
```

#### 3. Grouped Aggregations
```sql
-- Q6: Group by aggregation
SELECT department, SUM(salary) FROM employees GROUP BY department;

-- Q7: Time-series aggregation
SELECT DATE(timestamp), AVG(temperature) FROM sensors GROUP BY DATE(timestamp);
```

#### 4. Complex Multi-Column Operations
```sql
-- Q8: Multi-column computation
SELECT SUM(price * quantity) FROM orders;

-- Q9: Composite aggregation
SELECT AVG(systolic - diastolic) FROM blood_pressure;
```

#### 5. Repeated Queries (Cache Testing)
```sql
-- Q10: Same query repeated 100 times
SELECT SUM(revenue) FROM sales WHERE month = 10;
```

## Performance Metrics to Collect

### Primary Metrics
1. **Query Latency** (milliseconds)
   - Total end-to-end time
   - AES decryption time
   - Paillier encryption time
   - Homomorphic computation time
   - Result decryption time

2. **Throughput** (operations/second)
   - Records processed per second
   - Queries per second

3. **Storage Overhead**
   - Plaintext size (bytes)
   - AES ciphertext size (bytes)
   - Paillier ciphertext size (bytes)
   - Compression ratio

### Secondary Metrics
4. **Memory Usage** (MB)
   - Peak memory consumption
   - Cache hit rate (for intelligent caching)

5. **CPU Utilization** (%)
   - Per-core usage (for pipeline analysis)

6. **Network Overhead** (KB)
   - Data transferred between components

## Baseline Comparisons

### Comparison Groups
1. **Pure Plaintext** - Theoretical best performance
2. **Pure AES** - Cannot compute on encrypted data
3. **Pure Paillier** - No optimization, standard implementation
4. **Paillier + CRT** - Standard optimization
5. **Agniya Hybrid (No optimizations)** - Basic hybrid
6. **Agniya Hybrid (Phase 1)** - With all Phase 1 optimizations

### Expected Improvements
- **Storage:** 50-70% reduction vs. pure Paillier
- **Query Latency:** 40-60% reduction with optimizations
- **Throughput:** 2-5x improvement with pipeline
- **Cache Hit Rate:** 60-80% for repeated queries

## Dataset Storage Locations

```
data/
├── sample_datasets/
│   ├── healthcare/
│   │   ├── patients_100k.csv
│   │   ├── patients_500k.csv
│   │   ├── patients_1m.csv
│   │   └── patients_5m.csv
│   ├── financial/
│   │   ├── transactions_100k.csv
│   │   ├── transactions_500k.csv
│   │   └── ...
│   ├── iot/
│   │   └── sensor_readings_1m.csv
│   └── ecommerce/
│       └── orders_500k.csv
└── benchmark_results/
    ├── baseline/
    ├── phase1_optimized/
    └── comparative_analysis/
```

## Data Generation Scripts

All synthetic data will be generated using reproducible seeds for consistency:
- Random seed: 42
- NumPy version: 2.2.6
- Generation timestamp recorded

## Privacy & Ethics
- All datasets are **synthetic** - no real PII/PHI
- Generated data follows realistic distributions
- Can be shared publicly with research paper
