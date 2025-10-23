# Real-World Public Datasets for Agniya Benchmarking

## Overview
This document lists publicly available datasets suitable for benchmarking the Agniya hybrid encryption system. These datasets provide realistic data characteristics and are commonly used in academic research.

## Recommended Real-World Datasets

### 1. Healthcare/Medical Data

#### MIMIC-III Clinical Database (Recommended)
- **Source:** MIT Lab for Computational Physiology
- **URL:** https://physionet.org/content/mimiciii/1.4/
- **Description:** De-identified health records from ICU patients
- **Size:** 58,000+ hospital admissions, 2M+ ICU stays
- **Data Types:**
  - Patient demographics (age, gender)
  - Vital signs (heart rate, blood pressure, temperature)
  - Lab results (glucose, electrolytes, blood counts)
  - Medications and procedures
- **Access:** Free after completing training (CITI certification)
- **License:** Open-source (PhysioNet Credentialed Health Data License)
- **Columns we can use:**
  - Age, heart rate, respiratory rate, temperature
  - Systolic/diastolic blood pressure
  - Glucose levels, lab values
  - All are integers or convertible to integers

#### Alternative: CDC NHANES Dataset
- **Source:** Centers for Disease Control and Prevention
- **URL:** https://www.cdc.gov/nchs/nhanes/index.htm
- **Description:** National Health and Nutrition Examination Survey
- **Size:** 10,000+ participants per cycle (2017-2020)
- **Data Types:** Physical exams, lab tests, questionnaires
- **Access:** Publicly available, no registration
- **Format:** CSV/XPT files

### 2. Financial Data

#### UCI Bank Marketing Dataset (Recommended)
- **Source:** UCI Machine Learning Repository
- **URL:** https://archive.ics.uci.edu/dataset/222/bank+marketing
- **Description:** Direct marketing campaigns of Portuguese banking institution
- **Size:** 45,211 records with 17 attributes
- **Data Types:**
  - Age, balance, duration
  - Campaign interactions
  - Previous contacts
- **Access:** Free download
- **License:** Creative Commons (CC BY 4.0)

#### Alternative: Lending Club Loan Data
- **Source:** Lending Club (via Kaggle)
- **URL:** https://www.kaggle.com/datasets/wordsforthewise/lending-club
- **Description:** Loan data from 2007-2018
- **Size:** 2.9M+ loan records
- **Data Types:**
  - Loan amounts (in cents when converted)
  - Interest rates
  - Annual income
  - Credit scores
  - Payment history
- **Access:** Free with Kaggle account
- **License:** CC0 (Public Domain)

#### Stock Market Data
- **Source:** Yahoo Finance / Alpha Vantage
- **URL:** https://www.alphavantage.co/
- **Description:** Historical stock prices, volumes
- **Size:** Decades of trading data
- **Data Types:** Prices (in cents), volumes, market cap
- **Access:** Free API with registration
- **Good for:** Time-series aggregations, large integer arithmetic

### 3. IoT/Sensor Data

#### Intel Lab Sensor Data (Recommended)
- **Source:** Intel Berkeley Research Lab
- **URL:** http://db.csail.mit.edu/labdata/labdata.html
- **Description:** Sensor network deployment with 54 sensors
- **Size:** 2.3M readings over 1 month
- **Data Types:**
  - Temperature, humidity, light, voltage
  - Timestamps, sensor IDs
- **Access:** Direct download
- **License:** Public domain
- **Perfect for:** Testing IoT scenarios, time-series queries

#### Alternative: Smart Home Dataset (REFIT)
- **Source:** REFIT Electrical Load Measurements
- **URL:** https://pureportal.strath.ac.uk/en/datasets/refit-electrical-load-measurements
- **Description:** Electricity consumption from 20 households
- **Size:** 2+ years of measurements at 8-second intervals
- **Data Types:** Power consumption (watts), timestamps, appliances
- **Access:** Free download after registration
- **License:** Creative Commons

#### NOAA Weather Data
- **Source:** National Oceanic and Atmospheric Administration
- **URL:** https://www.ncdc.noaa.gov/cdo-web/datasets
- **Description:** Historical weather observations
- **Size:** Millions of records from thousands of stations
- **Data Types:** Temperature, precipitation, wind, pressure
- **Access:** Free API and bulk downloads
- **License:** Public domain (US government data)

### 4. E-commerce/Retail Data

#### Instacart Market Basket Analysis (Recommended)
- **Source:** Instacart (via Kaggle)
- **URL:** https://www.kaggle.com/c/instacart-market-basket-analysis/data
- **Description:** 3M+ grocery orders from 200K+ users
- **Size:** Orders: 3.4M, Products: 50K, Order-Product pairs: 32M
- **Data Types:**
  - Product prices (when available)
  - Order IDs, product IDs, user IDs
  - Reorder flags, order times
- **Access:** Free with Kaggle account
- **License:** Custom (academic use allowed)

#### Alternative: Brazilian E-Commerce (Olist)
- **Source:** Olist Store (via Kaggle)
- **URL:** https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
- **Description:** Brazilian e-commerce transactions 2016-2018
- **Size:** 100K orders with product, customer, review data
- **Data Types:**
  - Order values (prices in BRL cents)
  - Payment values, freight values
  - Product dimensions and weights
  - Customer locations
- **Access:** Free with Kaggle account
- **License:** CC BY-NC-SA 4.0

#### Online Retail Dataset (UCI)
- **Source:** UCI Machine Learning Repository
- **URL:** https://archive.ics.uci.edu/dataset/352/online+retail
- **Description:** UK online retail transactions
- **Size:** 541,909 transactions
- **Data Types:**
  - Invoice numbers, quantities, unit prices
  - Customer IDs, countries
- **Access:** Free download
- **License:** CC BY 4.0

### 5. Mixed/General Purpose

#### Taxi Trip Data (NYC TLC)
- **Source:** NYC Taxi & Limousine Commission
- **URL:** https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
- **Description:** Yellow and green taxi trip records
- **Size:** Millions of trips per month
- **Data Types:**
  - Fare amounts (cents), tip amounts, tolls
  - Trip distances, durations
  - Passenger counts
  - Pickup/dropoff locations
- **Access:** Direct download (monthly parquet files)
- **License:** Public domain
- **Good for:** Large-scale aggregations, geographic queries

## Dataset Selection Strategy

### For Your Project, I Recommend:

#### Primary Real-World Datasets:
1. **Healthcare:** MIMIC-III or CDC NHANES
   - Strong for showing privacy-preserving queries
   - Highly sensitive data = strong encryption justification
   - Good integer ranges for testing adaptive bit-length

2. **Financial:** Lending Club Loan Data
   - Large dataset (2.9M records)
   - Mix of small and large values
   - Real-world financial scenario

3. **IoT:** Intel Lab Sensor Data
   - Time-series data
   - High volume (2.3M readings)
   - Multiple sensors for testing parallelization

4. **E-commerce:** Instacart or Olist Dataset
   - Large transaction volume
   - Good for cache testing (repeated queries)
   - Realistic query patterns

#### Keep Synthetic Data For:
- Controlled experiments (varying data distributions)
- Stress testing (extreme values, edge cases)
- Reproducibility across all research environments
- Testing specific algorithmic properties

## Data Preparation Pipeline

```
Real Dataset → Cleaning → Integer Conversion → AES Encryption → Storage
                    ↓
            Metadata Extraction (min/max, distribution)
                    ↓
        Used for Adaptive Bit-Length Selection
```

## Implementation Plan

1. **Download & Preparation Script**
   - Automated download from sources
   - Data cleaning (remove nulls, outliers)
   - Convert floats to integers (e.g., dollars → cents)
   - Save in consistent format

2. **Dataset Loader Module**
   - Load both real and synthetic datasets
   - Unified interface for benchmarking
   - Automatic metadata extraction

3. **Benchmark Both Types**
   - Real datasets: Show practical applicability
   - Synthetic datasets: Show controlled performance gains

## Licensing & Ethics

All recommended datasets:
- ✅ Publicly available
- ✅ Permissive licenses (academic use)
- ✅ De-identified/anonymized
- ✅ Can be cited in academic papers
- ✅ Can be used for patent applications

## Citations for Paper

When using real datasets, cite:
- Original data source
- Access method (UCI Repository, Kaggle, etc.)
- Date accessed
- Any preprocessing applied

Example:
```
Johnson, A., Pollard, T., & Mark, R. (2016). MIMIC-III Clinical Database 
(version 1.4). PhysioNet. https://doi.org/10.13026/C2XW26
```

## Next Steps

Would you like me to:
1. Create download scripts for specific datasets?
2. Build a data loader module that handles both real and synthetic data?
3. Create preprocessing pipelines for integer conversion?
4. Generate the comparative benchmark suite?

For your thesis/paper, using **2-3 real datasets + synthetic data** provides:
- ✅ Real-world validation
- ✅ Controlled experiments
- ✅ Broader applicability claims
- ✅ Stronger patent position
