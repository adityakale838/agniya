import pandas as pd

df = pd.read_csv('G:\\agniya\\data\\real_datasets\\online_retail_prepared.csv')

print("="*70)
print("CUSTOMER ID ANALYSIS")
print("="*70)
print(f"Total records: {len(df):,}")
print(f"Unique customer IDs: {df['customer_id'].nunique():,}")
print(f"Min customer ID: {df['customer_id'].min()}")
print(f"Max customer ID: {df['customer_id'].max()}")
print(f"\nSample customer IDs:")
print(df['customer_id'].head(20).tolist())

print(f"\nValue distribution:")
print(f"  Mean: {df['customer_id'].mean():.0f}")
print(f"  Median: {df['customer_id'].median():.0f}")
print(f"  Std Dev: {df['customer_id'].std():.0f}")

print(f"\nMost common customer IDs:")
print(df['customer_id'].value_counts().head(10))
