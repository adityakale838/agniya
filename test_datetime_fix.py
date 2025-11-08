"""
Quick test to verify datetime handling
"""
import pandas as pd

# Create test CSV with datetime column
test_data = {
    'age': [25, 30, 35, 40],
    'salary': [50000, 60000, 70000, 80000],
    'timestamp': ['2025-07-22 09:22:54', '2025-07-22 09:23:10', '2025-07-22 09:24:00', '2025-07-22 09:25:30']
}

df = pd.DataFrame(test_data)
print("Test DataFrame:")
print(df)
print("\nData types:")
print(df.dtypes)

# Test numeric detection
print("\nNumeric column detection:")
for col in df.columns:
    is_numeric = pd.api.types.is_numeric_dtype(df[col])
    is_datetime = pd.api.types.is_datetime64_any_dtype(df[col])
    print(f"  {col}: numeric={is_numeric}, datetime={is_datetime}")

# Test conversion
print("\nTesting conversion:")
for col in df.columns:
    if pd.api.types.is_numeric_dtype(df[col]):
        try:
            values = df[col].fillna(0).astype(int).tolist()
            print(f"  ✅ {col}: {values}")
        except Exception as e:
            print(f"  ❌ {col}: {e}")
    else:
        print(f"  ⏭️  {col}: Skipping (non-numeric)")
