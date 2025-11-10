"""
Quick test to verify upload fix works with diabetic_data.csv
"""

import requests
import os

print("="*70)
print("TESTING UPLOAD FIX")
print("="*70)

# Check if server is running
try:
    response = requests.get('http://localhost:5000/api/health', timeout=2)
    print(f"✅ Server is running")
    print(f"   Status: {response.json()['status']}")
    print(f"   Max file size: {response.json().get('max_size', '100 MB')}")
except requests.exceptions.ConnectionError:
    print("❌ Server is not running!")
    print("   Start server with: .\\start.ps1")
    exit(1)

# Check if file exists
file_path = r"c:\Users\kaled\Downloads\Compressed\archive_3\diabetic_data.csv"
if not os.path.exists(file_path):
    print(f"\n❌ File not found: {file_path}")
    print("   Please update the path in this script")
    exit(1)

file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
print(f"\n📁 File: diabetic_data.csv")
print(f"   Size: {file_size_mb:.2f} MB")

# Test upload
print(f"\n📤 Uploading to server...")
try:
    with open(file_path, 'rb') as f:
        files = {'file': ('diabetic_data.csv', f, 'text/csv')}
        response = requests.post('http://localhost:5000/api/upload', files=files, timeout=60)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Upload successful!")
        print(f"   Filename: {data['filename']}")
        print(f"   File size: {data.get('file_size_mb', 'N/A')} MB")
        print(f"   Records: {data['records']:,}")
        print(f"   Columns: {data['columns']}")
        print(f"\n📊 Schema (first 5 columns):")
        for col in data['schema'][:5]:
            print(f"   - {col['name']}: {col['type']} → {col['encryption']}")
    else:
        print(f"\n❌ Upload failed!")
        print(f"   Status: {response.status_code}")
        print(f"   Error: {response.json()}")
        
except requests.exceptions.Timeout:
    print(f"\n⏱️  Upload timed out (file too large or server busy)")
except Exception as e:
    print(f"\n❌ Error: {str(e)}")

print("\n" + "="*70)
