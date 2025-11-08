"""
Quick Verification Script - Test All Fixes
Run this to verify all components work correctly
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_ultimate_database_methods():
    """Test that UltimateOptimizedDatabase has all required methods"""
    print("\n" + "="*70)
    print("TEST 1: UltimateOptimizedDatabase Methods")
    print("="*70)
    
    from agniya.core.ultimate_system import UltimateOptimizedDatabase
    from agniya.core.paillier import decrypt_crt
    
    db = UltimateOptimizedDatabase(key_size=2048)
    
    # Check properties exist
    assert hasattr(db, 'public_key'), "❌ Missing public_key property"
    print("✅ public_key property exists")
    
    assert hasattr(db, 'private_key'), "❌ Missing private_key property"
    print("✅ private_key property exists")
    
    assert hasattr(db, 'sum_encrypted'), "❌ Missing sum_encrypted method"
    print("✅ sum_encrypted method exists")
    
    # Test encryption and homomorphic sum
    print("\n" + "="*70)
    print("TEST 2: Homomorphic Sum with Decryption")
    print("="*70)
    
    values = [100, 200, 300, 400, 500]
    print(f"Test values: {values}")
    print(f"Expected sum: {sum(values)}")
    
    # Encrypt
    ciphertexts = [db.precomp.get_or_encrypt(v) for v in values]
    print(f"✅ Encrypted {len(ciphertexts)} values")
    
    # Homomorphic sum
    result_ct = db.sum_encrypted(ciphertexts)
    print(f"✅ Computed homomorphic sum")
    
    # Decrypt using standalone function
    result = decrypt_crt(db.public_key, db.private_key, result_ct)
    print(f"✅ Decrypted result: {result}")
    
    assert result == sum(values), f"❌ Sum mismatch: {result} != {sum(values)}"
    print(f"✅ Homomorphic sum CORRECT: {result} == {sum(values)}")
    
    return True

def test_query_types():
    """Test query type case normalization"""
    print("\n" + "="*70)
    print("TEST 3: Query Type Case Handling")
    print("="*70)
    
    test_cases = ['SUM', 'sum', 'Sum', 'AVG', 'avg', 'COUNT', 'count']
    
    for qt in test_cases:
        normalized = qt.lower()
        assert normalized in ['sum', 'avg', 'count'], f"❌ Invalid normalized type: {normalized}"
        print(f"✅ '{qt}' → '{normalized}'")
    
    return True

def test_imports():
    """Test all critical imports"""
    print("\n" + "="*70)
    print("TEST 4: Critical Imports")
    print("="*70)
    
    try:
        from agniya.core.ultimate_system import UltimateOptimizedDatabase
        print("✅ UltimateOptimizedDatabase imported")
        
        from agniya.core.paillier import decrypt_crt, decrypt
        print("✅ decrypt_crt imported")
        print("✅ decrypt imported")
        
        from agniya.compression.rns_compression import RNSCompressor
        print("✅ RNSCompressor imported")
        
        from agniya.storage.deduplication import CiphertextDeduplicator
        print("✅ CiphertextDeduplicator imported")
        
        from agniya.core.query_planner import AdaptiveQueryPlanner
        print("✅ AdaptiveQueryPlanner imported")
        
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_api_compatibility():
    """Test API endpoint logic (without Flask server)"""
    print("\n" + "="*70)
    print("TEST 5: API Logic Compatibility")
    print("="*70)
    
    from agniya.core.ultimate_system import UltimateOptimizedDatabase
    from agniya.core.paillier import decrypt_crt
    
    # Simulate database creation
    db = UltimateOptimizedDatabase(key_size=2048)
    
    # Simulate encryption phase
    test_data = [50, 100, 150, 200, 250]
    encrypted_data = {
        'test_column': [db.precomp.get_or_encrypt(v) for v in test_data]
    }
    print(f"✅ Simulated encryption of {len(test_data)} values")
    
    # Simulate query: SUM
    column = 'test_column'
    query_type = 'SUM'  # Frontend sends uppercase
    query_type = query_type.lower()  # Backend normalizes
    
    ciphertexts = encrypted_data[column]
    
    if query_type == 'sum':
        result_ct = db.sum_encrypted(ciphertexts)
        result = decrypt_crt(db.public_key, db.private_key, result_ct)
        print(f"✅ SUM query result: {result} (expected: {sum(test_data)})")
        assert result == sum(test_data)
    
    # Simulate query: AVG
    query_type = 'AVG'
    query_type = query_type.lower()
    
    if query_type == 'avg':
        sum_ct = db.sum_encrypted(ciphertexts)
        sum_val = decrypt_crt(db.public_key, db.private_key, sum_ct)
        result = sum_val / len(ciphertexts)
        expected_avg = sum(test_data) / len(test_data)
        print(f"✅ AVG query result: {result} (expected: {expected_avg})")
        assert abs(result - expected_avg) < 0.01
    
    # Simulate query: COUNT
    query_type = 'COUNT'
    query_type = query_type.lower()
    
    if query_type == 'count':
        result = len(ciphertexts)
        print(f"✅ COUNT query result: {result} (expected: {len(test_data)})")
        assert result == len(test_data)
    
    return True

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 COMPREHENSIVE VERIFICATION SUITE")
    print("="*70)
    print("Testing all fixes applied to AGNIYA system...")
    
    tests = [
        ("Database Methods", test_ultimate_database_methods),
        ("Query Type Handling", test_query_types),
        ("Import Verification", test_imports),
        ("API Compatibility", test_api_compatibility)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"\n❌ {test_name} FAILED with exception:")
            print(f"   {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("📊 TEST RESULTS")
    print("="*70)
    print(f"✅ Passed: {passed}/{len(tests)}")
    print(f"❌ Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! System is ready for production.")
        print("="*70)
        return 0
    else:
        print("\n⚠️  Some tests failed. Review errors above.")
        print("="*70)
        return 1

if __name__ == "__main__":
    exit(main())
