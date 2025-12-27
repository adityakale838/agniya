"""
Quick test of the updated API server
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_health():
    """Test health endpoint"""
    print("\n" + "="*70)
    print("Testing /api/health endpoint")
    print("="*70)
    
    response = requests.get(f"{BASE_URL}/api/health")
    data = response.json()
    
    print(json.dumps(data, indent=2))
    return data['status'] == 'healthy'

def test_benchmark():
    """Test benchmark endpoint"""
    print("\n" + "="*70)
    print("Testing /api/benchmark endpoint")
    print("="*70)
    
    response = requests.get(f"{BASE_URL}/api/benchmark")
    data = response.json()
    
    print(f"Speedup: {data['speedup']}x")
    print(f"Throughput: {data['throughput_rec_per_sec']:,} ops/sec")
    print(f"GPU Available: {data['gpu']['available']}")
    if data['gpu']['available']:
        print(f"GPU: {data['gpu']['name']}")
    print(f"\nCache hit rate: {data['cache_stats']['hit_rate']}%")
    print(f"Cache speedup: {data['cache_stats']['speedup_with_cache']}x")
    
    return True

def test_stats():
    """Test stats endpoint"""
    print("\n" + "="*70)
    print("Testing /api/stats endpoint")
    print("="*70)
    
    response = requests.get(f"{BASE_URL}/api/stats")
    data = response.json()
    
    print(json.dumps(data, indent=2))
    return data['success']

if __name__ == "__main__":
    print("\n🧪 Testing AGNIYA API Server")
    print("Make sure the server is running on http://localhost:5000")
    
    time.sleep(1)
    
    try:
        if test_health():
            print("\n✓ Health check passed")
        
        if test_benchmark():
            print("\n✓ Benchmark endpoint passed")
        
        if test_stats():
            print("\n✓ Stats endpoint passed")
        
        print("\n" + "="*70)
        print("✅ All tests passed!")
        print("="*70 + "\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server")
        print("Please start the server with: python api/server.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
