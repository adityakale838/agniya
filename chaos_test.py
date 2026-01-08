"""
CHAOS TEST SUITE FOR AGNIYA ENCRYPTED DATABASE API
Senior SDET - Aggressive Stress Testing for Race Conditions, Memory Leaks, Logic Errors

Attack Vectors:
1. Entropy Shock - Force rapid strategy switching
2. Concurrency Hammer - Race conditions in cache/storage
3. Mathematical Integrity - Verify encryption correctness
4. Payload Bloat - Test RNS compression limits
"""

import requests
import pandas as pd
import numpy as np
import time
import threading
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from typing import List, Tuple, Dict
import traceback
import random
import tempfile

# API Configuration
API_BASE = "http://localhost:5000"
UPLOAD_ENDPOINT = f"{API_BASE}/api/upload"
ENCRYPT_ENDPOINT = f"{API_BASE}/api/encrypt"
QUERY_ENDPOINT = f"{API_BASE}/api/query"

# Test Configuration
TEMP_DIR = tempfile.gettempdir()
TEST_RESULTS = {
    'entropy_shock': {'passed': False, 'errors': []},
    'concurrency_hammer': {'passed': False, 'errors': []},
    'math_integrity': {'passed': False, 'errors': []},
    'payload_bloat': {'passed': False, 'errors': []}
}

# Logging
class Logger:
    def __init__(self):
        self.lock = threading.Lock()
        
    def log(self, message, level="INFO"):
        with self.lock:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] [{level}] {message}")
            
    def error(self, message):
        self.log(message, "ERROR")
        
    def success(self, message):
        self.log(message, "SUCCESS")
        
    def warning(self, message):
        self.log(message, "WARNING")

logger = Logger()

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def check_api_health():
    """Verify API is running before starting tests"""
    try:
        response = requests.get(f"{API_BASE}/api/health", timeout=5)
        if response.status_code == 200:
            logger.success("API health check passed")
            return True
        else:
            logger.error(f"API health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        logger.error("API is not running! Start server: python api/server_optimized.py")
        return False
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return False

def upload_csv(filename: str, df: pd.DataFrame) -> dict:
    """Upload CSV to API and return schema"""
    csv_path = os.path.join(TEMP_DIR, filename)
    df.to_csv(csv_path, index=False)
    
    with open(csv_path, 'rb') as f:
        files = {'file': (filename, f, 'text/csv')}
        response = requests.post(UPLOAD_ENDPOINT, files=files, timeout=30)
        
    os.remove(csv_path)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Upload failed: {response.status_code} - {response.text}")

def encrypt_dataset(filename: str, schema: list, sample_size: int = None) -> dict:
    """Encrypt dataset with given schema"""
    payload = {
        'filename': filename,
        'schema': schema,
        'sample_size': sample_size,
        'enable_cache': True,
        'enable_batch': True
    }
    
    response = requests.post(ENCRYPT_ENDPOINT, json=payload, timeout=120)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Encryption failed: {response.status_code} - {response.text}")

def query_sum(filename: str, field: str, range_min=None, range_max=None) -> Tuple[float, float, float]:
    """
    Execute SUM query and return (result, latency_ms, ops_per_sec)
    """
    payload = {
        'filename': filename,
        'type': 'SUM',
        'column': field
    }
    
    if range_min is not None:
        payload['range_min'] = range_min
    if range_max is not None:
        payload['range_max'] = range_max
    
    start = time.time()
    response = requests.post(QUERY_ENDPOINT, json=payload, timeout=60)
    latency = (time.time() - start) * 1000
    
    if response.status_code == 200:
        data = response.json()
        return data['result'], latency, data.get('ops_per_sec', 0)
    else:
        raise Exception(f"Query failed: {response.status_code} - {response.text}")

def query_avg(filename: str, field: str) -> Tuple[float, float, float]:
    """Execute AVG query and return (result, latency_ms, ops_per_sec)"""
    payload = {
        'filename': filename,
        'type': 'AVG',
        'column': field
    }
    
    start = time.time()
    response = requests.post(QUERY_ENDPOINT, json=payload, timeout=60)
    latency = (time.time() - start) * 1000
    
    if response.status_code == 200:
        data = response.json()
        return data['result'], latency, data.get('ops_per_sec', 0)
    else:
        raise Exception(f"Query failed: {response.status_code} - {response.text}")

# ============================================================================
# ATTACK VECTOR 1: ENTROPY SHOCK
# ============================================================================

def attack_entropy_shock():
    """
    Test: Force query planner to rapidly switch between cache and parallel modes
    Expected: System correctly identifies entropy and switches strategies
    Failure: Crashes, incorrect results, or strategy selection errors
    """
    logger.log("=" * 80)
    logger.log("ATTACK VECTOR 1: ENTROPY SHOCK")
    logger.log("=" * 80)
    
    try:
        # Generate LOW entropy dataset (only 5 unique values)
        logger.log("Generating LOW entropy dataset (5 unique values)...")
        low_entropy_data = {
            'id': range(100000),
            'value': np.random.choice([1, 2, 3, 4, 5], size=100000)
        }
        low_df = pd.DataFrame(low_entropy_data)
        
        # Generate HIGH entropy dataset (all unique values)
        logger.log("Generating HIGH entropy dataset (10,000 unique values)...")
        high_entropy_data = {
            'id': range(10000),
            'value': np.random.randint(1, 1000000, size=10000)
        }
        high_df = pd.DataFrame(high_entropy_data)
        
        # Upload low entropy
        logger.log("Uploading low_entropy.csv...")
        low_schema_response = upload_csv('low_entropy.csv', low_df)
        low_schema = low_schema_response['schema']
        for field in low_schema:
            if field['name'] == 'value':
                field['encryption'] = 'Paillier-2048'
        
        # Upload high entropy
        logger.log("Uploading high_entropy.csv...")
        high_schema_response = upload_csv('high_entropy.csv', high_df)
        high_schema = high_schema_response['schema']
        for field in high_schema:
            if field['name'] == 'value':
                field['encryption'] = 'Paillier-2048'
        
        # Encrypt both
        logger.log("Encrypting LOW entropy dataset...")
        encrypt_dataset('low_entropy.csv', low_schema)
        
        logger.log("Encrypting HIGH entropy dataset...")
        encrypt_dataset('high_entropy.csv', high_schema)
        
        # Query LOW entropy (should use cache strategy)
        logger.log("\nQuerying LOW entropy dataset (expect CACHE strategy)...")
        low_result, low_latency, low_ops = query_sum('low_entropy.csv', 'value')
        expected_low = low_df['value'].sum()
        
        logger.log(f"  Result: {low_result:.0f}, Expected: {expected_low}")
        logger.log(f"  Latency: {low_latency:.2f}ms, Ops/sec: {low_ops:.0f}")
        
        # Query HIGH entropy (should use parallel strategy)
        logger.log("\nQuerying HIGH entropy dataset (expect PARALLEL strategy)...")
        high_result, high_latency, high_ops = query_sum('high_entropy.csv', 'value')
        expected_high = high_df['value'].sum()
        
        logger.log(f"  Result: {high_result:.0f}, Expected: {expected_high}")
        logger.log(f"  Latency: {high_latency:.2f}ms, Ops/sec: {high_ops:.0f}")
        
        # Rapid switching test
        logger.log("\nRAPID SWITCHING TEST (10 alternating queries)...")
        switch_latencies = []
        for i in range(10):
            dataset = 'low_entropy.csv' if i % 2 == 0 else 'high_entropy.csv'
            _, latency, _ = query_sum(dataset, 'value')
            switch_latencies.append(latency)
            logger.log(f"  Query {i+1} ({dataset}): {latency:.2f}ms")
        
        avg_switch_latency = np.mean(switch_latencies)
        logger.log(f"\nAverage switching latency: {avg_switch_latency:.2f}ms")
        
        # Verify correctness
        low_error = abs(low_result - expected_low) / max(expected_low, 1)
        high_error = abs(high_result - expected_high) / max(expected_high, 1)
        
        if low_error > 0.01:
            raise AssertionError(f"LOW entropy result incorrect: {low_error*100:.2f}% error")
        if high_error > 0.01:
            raise AssertionError(f"HIGH entropy result incorrect: {high_error*100:.2f}% error")
        if avg_switch_latency > 1000:
            raise AssertionError(f"Switching too slow: {avg_switch_latency:.2f}ms")
        
        TEST_RESULTS['entropy_shock']['passed'] = True
        logger.success("✓ ENTROPY SHOCK test PASSED")
        
    except Exception as e:
        TEST_RESULTS['entropy_shock']['errors'].append(str(e))
        logger.error(f"✗ ENTROPY SHOCK test FAILED: {e}")
        traceback.print_exc()

# ============================================================================
# ATTACK VECTOR 2: CONCURRENCY HAMMER
# ============================================================================

def attack_concurrency_hammer():
    """
    Test: Concurrent reads and writes to trigger race conditions
    Expected: System handles concurrent access gracefully
    Failure: Race conditions, cache corruption, deadlocks
    """
    logger.log("=" * 80)
    logger.log("ATTACK VECTOR 2: CONCURRENCY HAMMER")
    logger.log("=" * 80)
    
    try:
        # Prepare base dataset
        logger.log("Preparing base dataset for concurrency test...")
        data = pd.DataFrame({
            'id': range(10000),
            'salary': np.random.randint(30000, 150000, size=10000)
        })
        
        schema_response = upload_csv('concurrent_test.csv', data)
        schema = schema_response['schema']
        for field in schema:
            if field['name'] == 'salary':
                field['encryption'] = 'Paillier-2048'
        
        encrypt_dataset('concurrent_test.csv', schema)
        expected_sum = data['salary'].sum()
        
        logger.log(f"Expected SUM(salary): {expected_sum}")
        
        # Concurrent query threads
        def query_worker(worker_id, iterations=5):
            results = []
            for i in range(iterations):
                try:
                    result, latency, ops = query_sum('concurrent_test.csv', 'salary')
                    results.append({
                        'worker': worker_id,
                        'iteration': i,
                        'result': result,
                        'latency': latency,
                        'ops': ops,
                        'error': None
                    })
                    time.sleep(0.01)  # Small delay
                except Exception as e:
                    results.append({
                        'worker': worker_id,
                        'iteration': i,
                        'result': None,
                        'latency': None,
                        'ops': None,
                        'error': str(e)
                    })
            return results
        
        # Concurrent upload threads (same filename - test file locking)
        def upload_worker(worker_id, iterations=3):
            results = []
            for i in range(iterations):
                try:
                    new_data = pd.DataFrame({
                        'id': range(100),
                        'salary': np.random.randint(50000, 100000, size=100)
                    })
                    filename = f'concurrent_upload_{worker_id}.csv'
                    upload_csv(filename, new_data)
                    results.append({'worker': worker_id, 'iteration': i, 'error': None})
                    time.sleep(0.05)
                except Exception as e:
                    results.append({'worker': worker_id, 'iteration': i, 'error': str(e)})
            return results
        
        logger.log("\nLaunching 50 CONCURRENT THREADS...")
        logger.log("  - 25 threads: Continuous SUM queries")
        logger.log("  - 25 threads: Simultaneous uploads")
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            # Submit query threads (1-25)
            query_futures = [executor.submit(query_worker, i) for i in range(25)]
            
            # Submit upload threads (26-50)
            upload_futures = [executor.submit(upload_worker, i) for i in range(25, 50)]
            
            # Collect results
            all_query_results = []
            all_upload_results = []
            
            for future in as_completed(query_futures):
                all_query_results.extend(future.result())
            
            for future in as_completed(upload_futures):
                all_upload_results.extend(future.result())
        
        elapsed = time.time() - start_time
        
        # Analyze results
        total_queries = len(all_query_results)
        failed_queries = len([r for r in all_query_results if r['error'] is not None])
        successful_queries = total_queries - failed_queries
        
        total_uploads = len(all_upload_results)
        failed_uploads = len([r for r in all_upload_results if r['error'] is not None])
        
        logger.log(f"\nConcurrency test completed in {elapsed:.2f}s")
        logger.log(f"Query Results:")
        logger.log(f"  Total: {total_queries}, Success: {successful_queries}, Failed: {failed_queries}")
        logger.log(f"Upload Results:")
        logger.log(f"  Total: {total_uploads}, Success: {total_uploads - failed_uploads}, Failed: {failed_uploads}")
        
        # Verify correctness of successful queries
        incorrect_results = 0
        latencies = []
        for r in all_query_results:
            if r['error'] is None and r['result'] is not None:
                error_pct = abs(r['result'] - expected_sum) / expected_sum * 100
                if error_pct > 1.0:  # Allow 1% error margin
                    incorrect_results += 1
                latencies.append(r['latency'])
        
        avg_latency = np.mean(latencies) if latencies else 0
        throughput = successful_queries / elapsed
        
        logger.log(f"\nPerformance Metrics:")
        logger.log(f"  Average latency: {avg_latency:.2f}ms")
        logger.log(f"  Throughput: {throughput:.2f} req/sec")
        logger.log(f"  Incorrect results: {incorrect_results}/{successful_queries}")
        
        # Failure conditions
        if failed_queries > total_queries * 0.1:  # More than 10% failures
            raise AssertionError(f"Too many query failures: {failed_queries}/{total_queries}")
        if incorrect_results > 0:
            raise AssertionError(f"Incorrect results detected: {incorrect_results}")
        if avg_latency > 500:
            raise AssertionError(f"Average latency too high: {avg_latency:.2f}ms")
        
        TEST_RESULTS['concurrency_hammer']['passed'] = True
        logger.success("✓ CONCURRENCY HAMMER test PASSED")
        
    except Exception as e:
        TEST_RESULTS['concurrency_hammer']['errors'].append(str(e))
        logger.error(f"✗ CONCURRENCY HAMMER test FAILED: {e}")
        traceback.print_exc()

# ============================================================================
# ATTACK VECTOR 3: MATHEMATICAL INTEGRITY
# ============================================================================

def attack_math_integrity():
    """
    Test: Verify encryption/decryption correctness with edge cases
    Expected: All arithmetic operations are mathematically correct
    Failure: Wrong results, modular arithmetic errors
    """
    logger.log("=" * 80)
    logger.log("ATTACK VECTOR 3: MATHEMATICAL INTEGRITY")
    logger.log("=" * 80)
    
    try:
        # Test Case 1: Simple known values
        logger.log("\nTest Case 1: Simple known values [10, 20, 30]")
        simple_data = pd.DataFrame({'id': [1, 2, 3], 'value': [10, 20, 30]})
        
        schema_response = upload_csv('math_simple.csv', simple_data)
        schema = schema_response['schema']
        for field in schema:
            if field['name'] == 'value':
                field['encryption'] = 'Paillier-2048'
        
        encrypt_dataset('math_simple.csv', schema)
        
        sum_result, _, _ = query_sum('math_simple.csv', 'value')
        avg_result, _, _ = query_avg('math_simple.csv', 'value')
        
        expected_sum = 60
        expected_avg = 20
        
        logger.log(f"  SUM: {sum_result:.0f} (expected: {expected_sum})")
        logger.log(f"  AVG: {avg_result:.2f} (expected: {expected_avg})")
        
        if abs(sum_result - expected_sum) > 0.01:
            raise AssertionError(f"SUM incorrect: {sum_result} != {expected_sum}")
        if abs(avg_result - expected_avg) > 0.01:
            raise AssertionError(f"AVG incorrect: {avg_result} != {expected_avg}")
        
        # Test Case 2: Include zeros
        logger.log("\nTest Case 2: With zeros [0, 5, 0, 10]")
        zero_data = pd.DataFrame({'id': [1, 2, 3, 4], 'value': [0, 5, 0, 10]})
        
        schema_response = upload_csv('math_zeros.csv', zero_data)
        schema = schema_response['schema']
        for field in schema:
            if field['name'] == 'value':
                field['encryption'] = 'Paillier-2048'
        
        encrypt_dataset('math_zeros.csv', schema)
        
        sum_result, _, _ = query_sum('math_zeros.csv', 'value')
        expected_sum = 15
        
        logger.log(f"  SUM: {sum_result:.0f} (expected: {expected_sum})")
        
        if abs(sum_result - expected_sum) > 0.01:
            raise AssertionError(f"Zero handling failed: {sum_result} != {expected_sum}")
        
        # Test Case 3: Large numbers (near 2048-bit limit)
        logger.log("\nTest Case 3: Large numbers (testing Paillier modulus)")
        large_data = pd.DataFrame({
            'id': range(100),
            'value': [999999] * 100
        })
        
        schema_response = upload_csv('math_large.csv', large_data)
        schema = schema_response['schema']
        for field in schema:
            if field['name'] == 'value':
                field['encryption'] = 'Paillier-2048'
        
        encrypt_dataset('math_large.csv', schema)
        
        sum_result, _, _ = query_sum('math_large.csv', 'value')
        expected_sum = 99999900
        
        logger.log(f"  SUM: {sum_result:.0f} (expected: {expected_sum})")
        
        error_pct = abs(sum_result - expected_sum) / expected_sum * 100
        if error_pct > 0.1:
            raise AssertionError(f"Large number handling failed: {error_pct:.4f}% error")
        
        # Test Case 4: Mixed values (positive, zero, large)
        logger.log("\nTest Case 4: Mixed values")
        mixed_data = pd.DataFrame({
            'id': range(10),
            'value': [1, 0, 100, 1000, 10000, 0, 5, 50, 500, 5000]
        })
        
        schema_response = upload_csv('math_mixed.csv', mixed_data)
        schema = schema_response['schema']
        for field in schema:
            if field['name'] == 'value':
                field['encryption'] = 'Paillier-2048'
        
        encrypt_dataset('math_mixed.csv', schema)
        
        sum_result, _, _ = query_sum('math_mixed.csv', 'value')
        avg_result, _, _ = query_avg('math_mixed.csv', 'value')
        
        expected_sum = mixed_data['value'].sum()
        expected_avg = mixed_data['value'].mean()
        
        logger.log(f"  SUM: {sum_result:.0f} (expected: {expected_sum})")
        logger.log(f"  AVG: {avg_result:.2f} (expected: {expected_avg:.2f})")
        
        sum_error = abs(sum_result - expected_sum) / max(expected_sum, 1) * 100
        avg_error = abs(avg_result - expected_avg) / max(expected_avg, 1) * 100
        
        if sum_error > 0.1:
            raise AssertionError(f"Mixed SUM failed: {sum_error:.4f}% error")
        if avg_error > 0.1:
            raise AssertionError(f"Mixed AVG failed: {avg_error:.4f}% error")
        
        TEST_RESULTS['math_integrity']['passed'] = True
        logger.success("✓ MATHEMATICAL INTEGRITY test PASSED")
        
    except Exception as e:
        TEST_RESULTS['math_integrity']['errors'].append(str(e))
        logger.error(f"✗ MATHEMATICAL INTEGRITY test FAILED: {e}")
        traceback.print_exc()

# ============================================================================
# ATTACK VECTOR 4: PAYLOAD BLOAT
# ============================================================================

def attack_payload_bloat():
    """
    Test: Extremely large integers to test RNS compression
    Expected: System handles large values and compression works
    Failure: Overflow, compression errors, reconstruction failures
    """
    logger.log("=" * 80)
    logger.log("ATTACK VECTOR 4: PAYLOAD BLOAT")
    logger.log("=" * 80)
    
    try:
        # Generate dataset with very large integers
        logger.log("Generating dataset with LARGE integers (10^15 range)...")
        
        # Use large but manageable integers
        large_values = np.random.randint(10**12, 10**15, size=1000)
        
        bloat_data = pd.DataFrame({
            'id': range(1000),
            'value': large_values
        })
        
        logger.log(f"  Min value: {large_values.min():,}")
        logger.log(f"  Max value: {large_values.max():,}")
        logger.log(f"  Mean value: {large_values.mean():,.0f}")
        
        # Upload and encrypt
        schema_response = upload_csv('payload_bloat.csv', bloat_data)
        schema = schema_response['schema']
        for field in schema:
            if field['name'] == 'value':
                field['encryption'] = 'Paillier-2048'
        
        logger.log("Encrypting with large values...")
        start_encrypt = time.time()
        encrypt_result = encrypt_dataset('payload_bloat.csv', schema, sample_size=1000)
        encrypt_time = time.time() - start_encrypt
        
        logger.log(f"  Encryption time: {encrypt_time:.2f}s")
        logger.log(f"  Throughput: {1000/encrypt_time:.2f} enc/sec")
        
        # Query the large values
        logger.log("Querying SUM of large values...")
        sum_result, latency, ops = query_sum('payload_bloat.csv', 'value')
        expected_sum = large_values.sum()
        
        logger.log(f"  Result: {sum_result:,.0f}")
        logger.log(f"  Expected: {expected_sum:,.0f}")
        logger.log(f"  Latency: {latency:.2f}ms")
        logger.log(f"  Ops/sec: {ops:.0f}")
        
        # Calculate error (allow larger margin for huge numbers)
        error_pct = abs(sum_result - expected_sum) / expected_sum * 100
        logger.log(f"  Error: {error_pct:.6f}%")
        
        if error_pct > 1.0:  # 1% error margin for large numbers
            raise AssertionError(f"Large value computation failed: {error_pct:.6f}% error")
        
        # Test AVG as well
        avg_result, _, _ = query_avg('payload_bloat.csv', 'value')
        expected_avg = large_values.mean()
        avg_error_pct = abs(avg_result - expected_avg) / expected_avg * 100
        
        logger.log(f"\n  AVG result: {avg_result:,.2f}")
        logger.log(f"  Expected: {expected_avg:,.2f}")
        logger.log(f"  Error: {avg_error_pct:.6f}%")
        
        if avg_error_pct > 1.0:
            raise AssertionError(f"Large value AVG failed: {avg_error_pct:.6f}% error")
        
        TEST_RESULTS['payload_bloat']['passed'] = True
        logger.success("✓ PAYLOAD BLOAT test PASSED")
        
    except Exception as e:
        TEST_RESULTS['payload_bloat']['errors'].append(str(e))
        logger.error(f"✗ PAYLOAD BLOAT test FAILED: {e}")
        traceback.print_exc()

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def print_final_report():
    """Print comprehensive test report"""
    logger.log("\n" + "=" * 80)
    logger.log("CHAOS TEST FINAL REPORT")
    logger.log("=" * 80)
    
    total_tests = len(TEST_RESULTS)
    passed_tests = sum(1 for v in TEST_RESULTS.values() if v['passed'])
    failed_tests = total_tests - passed_tests
    
    for test_name, result in TEST_RESULTS.items():
        status = "✓ PASS" if result['passed'] else "✗ FAIL"
        logger.log(f"\n{test_name.upper().replace('_', ' ')}: {status}")
        if result['errors']:
            for error in result['errors']:
                logger.log(f"  Error: {error}")
    
    logger.log("\n" + "=" * 80)
    logger.log(f"SUMMARY: {passed_tests}/{total_tests} tests passed")
    logger.log("=" * 80)
    
    if failed_tests == 0:
        logger.success("\n🎉 ALL CHAOS TESTS PASSED! System is robust under stress.")
        return 0
    else:
        logger.error(f"\n⚠️  {failed_tests} test(s) FAILED! Review errors above.")
        return 1

def main():
    """Run all chaos tests"""
    print("""
╔═══════════════════════════════════════════════════════════════════════╗
║                  AGNIYA CHAOS TEST SUITE                             ║
║              Senior SDET - Aggressive Stress Testing                 ║
╚═══════════════════════════════════════════════════════════════════════╝
    """)
    
    # Check API health
    if not check_api_health():
        logger.error("Cannot proceed without running API server!")
        return 1
    
    logger.log("\nStarting chaos tests in 3 seconds...")
    time.sleep(3)
    
    # Run all attack vectors
    attack_entropy_shock()
    time.sleep(2)
    
    attack_concurrency_hammer()
    time.sleep(2)
    
    attack_math_integrity()
    time.sleep(2)
    
    attack_payload_bloat()
    
    # Print final report
    return print_final_report()

if __name__ == "__main__":
    sys.exit(main())
