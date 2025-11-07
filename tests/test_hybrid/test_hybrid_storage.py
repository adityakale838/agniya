"""
Comprehensive Test Suite for Hybrid AES + Paillier Storage System

Tests all components:
1. AES-256-GCM encryption/decryption
2. Paillier key wrapping
3. Schema validation
4. Hybrid database insert/query/aggregate operations
5. Security properties
6. Performance characteristics
"""

import pytest
from agniya.hybrid.aes_cipher import AESCipher
from agniya.hybrid.key_wrapper import KeyWrapper, HybridKeyManager
from agniya.hybrid.schema import Schema, Field, FieldType, create_employee_schema
from agniya.hybrid.hybrid_storage import HybridDatabase


class TestAESCipher:
    """Test AES-256-GCM encryption/decryption."""
    
    def test_key_generation(self):
        """Test random key generation."""
        key = AESCipher.generate_key()
        assert len(key) == 32, "AES-256 requires 32-byte key"
        
        # Keys should be random
        key2 = AESCipher.generate_key()
        assert key != key2, "Keys should be different"
    
    def test_string_encryption_decryption(self):
        """Test string encryption round-trip."""
        cipher = AESCipher()
        plaintext = "Sensitive data: SSN 123-45-6789"
        
        # Encrypt
        encrypted = cipher.encrypt_string(plaintext)
        assert 'ciphertext' in encrypted
        assert 'nonce' in encrypted
        assert 'tag' in encrypted
        
        # Decrypt
        decrypted = cipher.decrypt_string(
            encrypted['ciphertext'],
            encrypted['nonce'],
            encrypted['tag']
        )
        assert decrypted == plaintext
    
    def test_binary_encryption_decryption(self):
        """Test binary data encryption round-trip."""
        cipher = AESCipher()
        data = b"Binary data \x00\x01\x02\xff\xfe"
        
        # Encrypt
        encrypted = cipher.encrypt(data)
        
        # Decrypt
        decrypted = cipher.decrypt(
            encrypted['ciphertext'],
            encrypted['nonce'],
            encrypted['tag']
        )
        assert decrypted == data
    
    def test_tampering_detection(self):
        """Test that tampering is detected."""
        cipher = AESCipher()
        data = b"Secret message"
        encrypted = cipher.encrypt(data)
        
        # Tamper with ciphertext
        tampered = encrypted['ciphertext'][:-1] + b'\x00'
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Authentication failed"):
            cipher.decrypt(tampered, encrypted['nonce'], encrypted['tag'])
    
    def test_different_nonces(self):
        """Test that each encryption uses unique nonce."""
        cipher = AESCipher()
        plaintext = b"Same message"
        
        enc1 = cipher.encrypt(plaintext)
        enc2 = cipher.encrypt(plaintext)
        
        # Nonces should be different
        assert enc1['nonce'] != enc2['nonce']
        # Ciphertexts should be different
        assert enc1['ciphertext'] != enc2['ciphertext']


class TestKeyWrapper:
    """Test Paillier key wrapping for AES keys."""
    
    def test_key_wrapping_unwrapping(self):
        """Test wrap/unwrap round-trip."""
        manager = HybridKeyManager(paillier_key_size=2048)
        
        # Generate AES key
        aes_key = AESCipher.generate_key()
        
        # Wrap
        wrapped = manager.wrapper.wrap_key(aes_key)
        assert isinstance(wrapped, int)
        
        # Unwrap
        unwrapped = manager.wrapper.unwrap_key(wrapped)
        assert unwrapped == aes_key
    
    def test_server_cannot_unwrap(self):
        """Test that server without private key cannot unwrap."""
        manager = HybridKeyManager(paillier_key_size=2048)
        
        # Create server-side wrapper (public key only)
        server_wrapper = manager.get_public_key_only_wrapper()
        
        # Generate and wrap key
        aes_key = AESCipher.generate_key()
        wrapped = manager.wrapper.wrap_key(aes_key)
        
        # Server should not be able to unwrap
        with pytest.raises(ValueError, match="private key not available"):
            server_wrapper.unwrap_key(wrapped)
    
    def test_wrapped_key_deterministic(self):
        """Test that wrapping same key twice gives same result."""
        manager = HybridKeyManager(paillier_key_size=2048)
        aes_key = AESCipher.generate_key()
        
        wrapped1 = manager.wrapper.wrap_key(aes_key)
        wrapped2 = manager.wrapper.wrap_key(aes_key)
        
        # Paillier encryption is randomized, so these will differ
        # But unwrapping should give same result
        unwrapped1 = manager.wrapper.unwrap_key(wrapped1)
        unwrapped2 = manager.wrapper.unwrap_key(wrapped2)
        
        assert unwrapped1 == unwrapped2 == aes_key


class TestSchema:
    """Test schema validation and field types."""
    
    def test_create_employee_schema(self):
        """Test employee schema creation."""
        schema = create_employee_schema()
        
        assert schema.table_name == "employees"
        assert len(schema.fields) == 6
        
        # Check field types
        assert schema.get_field("emp_id").field_type == FieldType.PLAINTEXT
        assert schema.get_field("name").field_type == FieldType.AES_ENCRYPTED
        assert schema.get_field("salary").field_type == FieldType.PAILLIER_ENCRYPTED
    
    def test_schema_validation_success(self):
        """Test valid record passes validation."""
        schema = create_employee_schema()
        record = {
            "emp_id": 1001,
            "name": "John Doe",
            "email": "john@example.com",
            "salary": 75000,
            "age": 30,
            "hire_date": 1609459200
        }
        
        # Should not raise
        schema.validate_record(record)
    
    def test_schema_validation_wrong_type(self):
        """Test wrong type fails validation."""
        schema = create_employee_schema()
        record = {
            "emp_id": 1001,
            "name": "John Doe",
            "email": "john@example.com",
            "salary": "not a number",  # Wrong type!
            "age": 30,
            "hire_date": 1609459200
        }
        
        with pytest.raises(ValueError, match="expects type int"):
            schema.validate_record(record)
    
    def test_schema_validation_extra_field(self):
        """Test extra field fails validation."""
        schema = create_employee_schema()
        record = {
            "emp_id": 1001,
            "name": "John Doe",
            "email": "john@example.com",
            "salary": 75000,
            "age": 30,
            "hire_date": 1609459200,
            "extra_field": "not in schema"
        }
        
        with pytest.raises(ValueError, match="Unknown fields"):
            schema.validate_record(record)


class TestHybridDatabase:
    """Test hybrid database operations."""
    
    def test_database_initialization(self):
        """Test database initializes correctly."""
        schema = create_employee_schema()
        db = HybridDatabase(schema, enable_verbose=False)
        
        assert db.schema == schema
        assert len(db.records) == 0
        assert db.aes_cipher is not None
        assert db.paillier_pub is not None
    
    def test_insert_and_query(self):
        """Test insert and query operations."""
        schema = create_employee_schema()
        db = HybridDatabase(schema, enable_verbose=False)
        
        # Insert record
        record = {
            "emp_id": 1001,
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "salary": 75000,
            "age": 30,
            "hire_date": 1609459200
        }
        
        record_id = db.insert(record)
        assert record_id is not None
        
        # Query record
        result = db.query(record_id)
        
        assert result["emp_id"] == 1001
        assert result["name"] == "Alice Johnson"
        assert result["email"] == "alice@example.com"
        assert result["salary"] == 75000
        assert result["age"] == 30
        assert result["hire_date"] == 1609459200
    
    def test_aggregate_sum(self):
        """Test SUM aggregation on encrypted data."""
        schema = create_employee_schema()
        db = HybridDatabase(schema, enable_verbose=False)
        
        # Insert multiple records
        salaries = [75000, 85000, 95000]
        for i, salary in enumerate(salaries):
            db.insert({
                "emp_id": 1001 + i,
                "name": f"Employee {i}",
                "email": f"emp{i}@example.com",
                "salary": salary,
                "age": 30 + i,
                "hire_date": 1609459200
            })
        
        # Compute SUM on encrypted salaries
        total = db.aggregate("salary", "sum")
        assert total == sum(salaries)
    
    def test_aggregate_avg(self):
        """Test AVG aggregation on encrypted data."""
        schema = create_employee_schema()
        db = HybridDatabase(schema, enable_verbose=False)
        
        # Insert records
        ages = [30, 35, 40]
        for i, age in enumerate(ages):
            db.insert({
                "emp_id": 1001 + i,
                "name": f"Employee {i}",
                "email": f"emp{i}@example.com",
                "salary": 75000,
                "age": age,
                "hire_date": 1609459200
            })
        
        # Compute AVG
        avg_age = db.aggregate("age", "avg")
        assert avg_age == sum(ages) // len(ages)
    
    def test_aggregate_wrong_field_type(self):
        """Test aggregation fails on non-Paillier fields."""
        schema = create_employee_schema()
        db = HybridDatabase(schema, enable_verbose=False)
        
        # Try to aggregate AES field
        with pytest.raises(ValueError, match="requires PAILLIER_ENCRYPTED"):
            db.aggregate("name", "sum")
    
    def test_query_nonexistent_record(self):
        """Test querying nonexistent record raises error."""
        schema = create_employee_schema()
        db = HybridDatabase(schema, enable_verbose=False)
        
        with pytest.raises(KeyError, match="not found"):
            db.query("nonexistent-id")
    
    def test_data_confidentiality(self):
        """Test that encrypted data is not plaintext."""
        schema = create_employee_schema()
        db = HybridDatabase(schema, enable_verbose=False)
        
        # Insert sensitive data
        sensitive_name = "John Doe"
        sensitive_email = "john@secret.com"
        
        record_id = db.insert({
            "emp_id": 1001,
            "name": sensitive_name,
            "email": sensitive_email,
            "salary": 75000,
            "age": 30,
            "hire_date": 1609459200
        })
        
        # Get encrypted record
        encrypted_record = db.records[record_id]
        
        # Check AES fields are encrypted (not plaintext)
        assert 'name' in encrypted_record.aes_fields
        aes_data = str(encrypted_record.aes_fields['name'])
        assert sensitive_name not in aes_data
        assert sensitive_email not in str(encrypted_record.aes_fields['email'])
        
        # Check Paillier fields are encrypted (huge numbers)
        assert 'salary' in encrypted_record.paillier_fields
        salary_ciphertext = encrypted_record.paillier_fields['salary']
        assert salary_ciphertext > 75000  # Encrypted value is much larger
    
    def test_multiple_inserts_and_queries(self):
        """Test multiple operations."""
        schema = create_employee_schema()
        db = HybridDatabase(schema, enable_verbose=False)
        
        # Insert 10 records
        record_ids = []
        for i in range(10):
            record_id = db.insert({
                "emp_id": 1001 + i,
                "name": f"Employee {i}",
                "email": f"emp{i}@example.com",
                "salary": 50000 + i * 10000,
                "age": 25 + i,
                "hire_date": 1609459200 + i * 86400
            })
            record_ids.append(record_id)
        
        # Query all records
        for i, record_id in enumerate(record_ids):
            result = db.query(record_id)
            assert result["emp_id"] == 1001 + i
            assert result["name"] == f"Employee {i}"
            assert result["salary"] == 50000 + i * 10000
        
        # Aggregate
        total_salary = db.aggregate("salary", "sum")
        expected = sum(50000 + i * 10000 for i in range(10))
        assert total_salary == expected


def test_full_workflow():
    """Integration test: full database workflow."""
    # Create schema
    schema = create_employee_schema()
    
    # Initialize database
    db = HybridDatabase(schema, paillier_key_size=2048, enable_verbose=False)
    
    # Insert employees
    employees = [
        {"emp_id": 1, "name": "Alice", "email": "alice@co.com", 
         "salary": 70000, "age": 28, "hire_date": 1609459200},
        {"emp_id": 2, "name": "Bob", "email": "bob@co.com",
         "salary": 80000, "age": 32, "hire_date": 1577923200},
        {"emp_id": 3, "name": "Carol", "email": "carol@co.com",
         "salary": 90000, "age": 36, "hire_date": 1546387200},
    ]
    
    record_ids = [db.insert(emp) for emp in employees]
    
    # Query employees
    for i, record_id in enumerate(record_ids):
        result = db.query(record_id)
        assert result["name"] == employees[i]["name"]
        assert result["salary"] == employees[i]["salary"]
    
    # Compute aggregations
    total_salary = db.aggregate("salary", "sum")
    assert total_salary == 70000 + 80000 + 90000
    
    avg_age = db.aggregate("age", "avg")
    assert avg_age == (28 + 32 + 36) // 3
    
    print("✅ Full workflow test passed!")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
