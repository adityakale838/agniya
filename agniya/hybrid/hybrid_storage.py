"""
Hybrid Database: AES + Paillier Storage Engine

Main database class that routes data to appropriate encryption method
based on schema definitions. Combines fast AES encryption for bulk data
with Paillier homomorphic encryption for computational fields.

Architecture:
┌─────────────────────────────────────────────────────────────┐
│                    HybridDatabase                            │
├─────────────────────────────────────────────────────────────┤
│  Schema: Defines field types (Plaintext/AES/Paillier)      │
├─────────────────────────────────────────────────────────────┤
│  INSERT:                                                     │
│    - Plaintext fields → Store directly                      │
│    - AES fields → Encrypt with AES-256-GCM                  │
│    - Paillier fields → Encrypt with Paillier               │
├─────────────────────────────────────────────────────────────┤
│  QUERY:                                                      │
│    - Plaintext → Return directly                            │
│    - AES → Decrypt with AES key                             │
│    - Paillier → Decrypt with Paillier private key          │
├─────────────────────────────────────────────────────────────┤
│  AGGREGATE (SUM/AVG):                                        │
│    - Only works on Paillier fields                          │
│    - Computes on encrypted data (no decryption!)           │
└─────────────────────────────────────────────────────────────┘

Performance:
- Insert: 50-100x faster than pure Paillier (AES fields)
- Query: 50-100x faster for AES fields
- Storage: 10-20x smaller for AES fields
- Aggregation: Same speed as pure Paillier (still homomorphic)
"""

from typing import Dict, List, Any, Optional
import time
import uuid
from collections import defaultdict

from agniya.core.paillier import (
    PaillierPublicKey,
    PaillierPrivateKey,
    generate_keypair,
    encrypt,
    decrypt_crt
)
from agniya.hybrid.aes_cipher import AESCipher
from agniya.hybrid.key_wrapper import KeyWrapper, HybridKeyManager
from agniya.hybrid.schema import Schema, Field, FieldType


class EncryptedRecord:
    """
    Represents a single encrypted database record.
    
    Contains encrypted data in different formats based on field types.
    """
    
    def __init__(self, record_id: str):
        self.record_id = record_id
        self.plaintext_fields: Dict[str, Any] = {}
        self.aes_fields: Dict[str, Dict[str, str]] = {}  # {field: {ciphertext, nonce, tag}}
        self.paillier_fields: Dict[str, int] = {}  # {field: ciphertext}
    
    def __repr__(self) -> str:
        return (f"EncryptedRecord(id='{self.record_id}', "
                f"plaintext={len(self.plaintext_fields)}, "
                f"aes={len(self.aes_fields)}, "
                f"paillier={len(self.paillier_fields)})")


class HybridDatabase:
    """
    Hybrid encrypted database combining AES and Paillier encryption.
    
    This is the main interface for storing and querying encrypted data
    with automatic encryption method selection based on schema.
    """
    
    def __init__(self, 
                 schema: Schema,
                 paillier_key_size: int = 2048,
                 enable_verbose: bool = True):
        """
        Initialize hybrid database.
        
        Args:
            schema: Database schema defining field encryption types
            paillier_key_size: Size of Paillier keys (default 2048-bit)
            enable_verbose: Print detailed operation logs
        """
        self.schema = schema
        self.verbose = enable_verbose
        
        if self.verbose:
            print("="*70)
            print(f"Initializing Hybrid Database: {schema.table_name}")
            print("="*70)
        
        # Generate Paillier keys for key wrapping and Paillier fields
        if self.verbose:
            print(f"Generating {paillier_key_size}-bit Paillier keys...")
        self.key_manager = HybridKeyManager(paillier_key_size)
        self.paillier_pub = self.key_manager.paillier_pub
        self.paillier_priv = self.key_manager.paillier_priv
        
        # Generate AES key for this database
        if self.verbose:
            print("Generating AES-256 key for bulk encryption...")
        self.aes_key, self.wrapped_aes_key = self.key_manager.create_wrapped_aes_key()
        self.aes_cipher = AESCipher(self.aes_key)
        
        # In-memory storage (in production: use SQLite/PostgreSQL/MongoDB)
        self.records: Dict[str, EncryptedRecord] = {}
        
        # Statistics
        self.insert_count = 0
        self.query_count = 0
        self.aggregate_count = 0
        
        if self.verbose:
            print("\n✅ Database initialized successfully")
            print(f"   - Schema: {len(schema.fields)} fields")
            print(f"   - Plaintext: {len(schema.get_fields_by_type(FieldType.PLAINTEXT))} fields")
            print(f"   - AES: {len(schema.get_fields_by_type(FieldType.AES_ENCRYPTED))} fields")
            print(f"   - Paillier: {len(schema.get_fields_by_type(FieldType.PAILLIER_ENCRYPTED))} fields")
            print("="*70 + "\n")
    
    def insert(self, record: Dict[str, Any]) -> str:
        """
        Insert encrypted record into database.
        
        Automatically encrypts fields based on schema:
        - PLAINTEXT: Store as-is
        - AES_ENCRYPTED: Encrypt with AES-256-GCM
        - PAILLIER_ENCRYPTED: Encrypt with Paillier
        
        Args:
            record: Dictionary of field_name -> value
            
        Returns:
            record_id: Unique identifier for inserted record
            
        Raises:
            ValueError: If record doesn't match schema
        """
        start_time = time.time()
        
        # Validate record against schema
        self.schema.validate_record(record)
        
        # Generate unique record ID
        record_id = str(uuid.uuid4())
        encrypted_record = EncryptedRecord(record_id)
        
        # Encrypt fields based on type
        for field_name, value in record.items():
            field = self.schema.get_field(field_name)
            
            if field.field_type == FieldType.PLAINTEXT:
                # Store plaintext
                encrypted_record.plaintext_fields[field_name] = value
            
            elif field.field_type == FieldType.AES_ENCRYPTED:
                # Encrypt with AES
                if isinstance(value, str):
                    encrypted = self.aes_cipher.encrypt_string(value)
                else:
                    encrypted = self.aes_cipher.encrypt(str(value).encode())
                    encrypted = {
                        'ciphertext': encrypted['ciphertext'].hex(),
                        'nonce': encrypted['nonce'].hex(),
                        'tag': encrypted['tag'].hex()
                    }
                encrypted_record.aes_fields[field_name] = encrypted
            
            elif field.field_type == FieldType.PAILLIER_ENCRYPTED:
                # Encrypt with Paillier
                if not isinstance(value, int):
                    raise ValueError(
                        f"Paillier encryption requires integer values, "
                        f"got {type(value).__name__} for field '{field_name}'"
                    )
                ciphertext = encrypt(self.paillier_pub, value)
                encrypted_record.paillier_fields[field_name] = ciphertext
        
        # Store encrypted record
        self.records[record_id] = encrypted_record
        self.insert_count += 1
        
        insert_time = time.time() - start_time
        
        if self.verbose:
            print(f"✅ Inserted record {record_id[:8]}... in {insert_time*1000:.2f}ms")
        
        return record_id
    
    def query(self, record_id: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Query and decrypt record fields.
        
        Args:
            record_id: Unique record identifier
            fields: List of field names to retrieve (None = all fields)
            
        Returns:
            Dictionary of field_name -> decrypted_value
            
        Raises:
            KeyError: If record_id not found
        """
        start_time = time.time()
        
        if record_id not in self.records:
            raise KeyError(f"Record '{record_id}' not found")
        
        encrypted_record = self.records[record_id]
        result = {}
        
        # Determine which fields to retrieve
        if fields is None:
            fields = list(self.schema.fields.keys())
        
        # Decrypt requested fields
        for field_name in fields:
            field = self.schema.get_field(field_name)
            
            if field.field_type == FieldType.PLAINTEXT:
                result[field_name] = encrypted_record.plaintext_fields.get(field_name)
            
            elif field.field_type == FieldType.AES_ENCRYPTED:
                encrypted = encrypted_record.aes_fields.get(field_name)
                if encrypted:
                    if 'ciphertext' in encrypted and isinstance(encrypted['ciphertext'], str):
                        try:
                            # Try string decryption first
                            result[field_name] = self.aes_cipher.decrypt_string(
                                encrypted['ciphertext'],
                                encrypted['nonce'],
                                encrypted['tag']
                            )
                        except:
                            # Fall back to bytes decryption
                            ciphertext = bytes.fromhex(encrypted['ciphertext'])
                            nonce = bytes.fromhex(encrypted['nonce'])
                            tag = bytes.fromhex(encrypted['tag'])
                            decrypted = self.aes_cipher.decrypt(ciphertext, nonce, tag)
                            result[field_name] = decrypted.decode()
                else:
                    result[field_name] = None
            
            elif field.field_type == FieldType.PAILLIER_ENCRYPTED:
                ciphertext = encrypted_record.paillier_fields.get(field_name)
                if ciphertext:
                    result[field_name] = decrypt_crt(
                        self.paillier_pub,
                        self.paillier_priv,
                        ciphertext
                    )
                else:
                    result[field_name] = None
        
        self.query_count += 1
        query_time = time.time() - start_time
        
        if self.verbose:
            print(f"✅ Queried record {record_id[:8]}... ({len(fields)} fields) in {query_time*1000:.2f}ms")
        
        return result
    
    def aggregate(self, field_name: str, operation: str = "sum") -> int:
        """
        Compute aggregate on encrypted Paillier field WITHOUT decryption.
        
        This is the key homomorphic property: we can compute SUM
        on encrypted values without ever seeing the plaintext!
        
        Args:
            field_name: Field to aggregate (must be PAILLIER_ENCRYPTED)
            operation: Aggregation type ("sum" or "avg")
            
        Returns:
            Aggregation result (plaintext)
            
        Raises:
            ValueError: If field is not Paillier-encrypted
        """
        start_time = time.time()
        
        field = self.schema.get_field(field_name)
        if field.field_type != FieldType.PAILLIER_ENCRYPTED:
            raise ValueError(
                f"Aggregation requires PAILLIER_ENCRYPTED field, "
                f"but '{field_name}' is {field.field_type.value}"
            )
        
        if not self.records:
            return 0
        
        # Homomorphic addition: multiply ciphertexts
        result_ciphertext = None
        count = 0
        
        for encrypted_record in self.records.values():
            if field_name in encrypted_record.paillier_fields:
                ct = encrypted_record.paillier_fields[field_name]
                if result_ciphertext is None:
                    result_ciphertext = ct
                else:
                    # Homomorphic addition
                    result_ciphertext = (result_ciphertext * ct) % self.paillier_pub.n_squared
                count += 1
        
        if result_ciphertext is None:
            return 0
        
        # Decrypt final result
        result = decrypt_crt(self.paillier_pub, self.paillier_priv, result_ciphertext)
        
        # Compute average if requested
        if operation == "avg" and count > 0:
            result = result // count  # Integer division
        
        self.aggregate_count += 1
        aggregate_time = time.time() - start_time
        
        if self.verbose:
            print(f"✅ Computed {operation.upper()}({field_name}) = {result:,} "
                  f"on {count} encrypted values in {aggregate_time:.3f}s")
        
        return result
    
    def print_stats(self):
        """Print database statistics."""
        print("\n" + "="*70)
        print(f"Database Statistics: {self.schema.table_name}")
        print("="*70)
        
        print(f"\nRecords: {len(self.records):,}")
        print(f"Operations:")
        print(f"  - Inserts: {self.insert_count:,}")
        print(f"  - Queries: {self.query_count:,}")
        print(f"  - Aggregations: {self.aggregate_count:,}")
        
        # Storage size estimate
        if self.records:
            sample_record = next(iter(self.records.values()))
            plaintext_size = len(sample_record.plaintext_fields) * 8
            aes_size = len(sample_record.aes_fields) * 50
            paillier_size = len(sample_record.paillier_fields) * 512
            total_size = (plaintext_size + aes_size + paillier_size) * len(self.records)
            
            print(f"\nStorage Estimate:")
            print(f"  - Per record: ~{(plaintext_size + aes_size + paillier_size):,} bytes")
            print(f"  - Total: ~{total_size / (1024*1024):.2f} MB")
        
        print("="*70)
    
    def __repr__(self) -> str:
        return (f"HybridDatabase(table='{self.schema.table_name}', "
                f"records={len(self.records)})")


# Demo
if __name__ == "__main__":
    from agniya.hybrid.schema import create_employee_schema
    
    print("\n" + "="*70)
    print("Hybrid Database Demo: Employee Records")
    print("="*70)
    
    # Create database with employee schema
    schema = create_employee_schema()
    db = HybridDatabase(schema, paillier_key_size=2048, enable_verbose=True)
    
    # Insert employee records
    print("\n" + "="*70)
    print("Inserting Employee Records")
    print("="*70 + "\n")
    
    employees = [
        {
            "emp_id": 1001,
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "salary": 75000,
            "age": 30,
            "hire_date": 1609459200
        },
        {
            "emp_id": 1002,
            "name": "Bob Smith",
            "email": "bob@example.com",
            "salary": 85000,
            "age": 35,
            "hire_date": 1577923200
        },
        {
            "emp_id": 1003,
            "name": "Carol Williams",
            "email": "carol@example.com",
            "salary": 95000,
            "age": 40,
            "hire_date": 1546387200
        }
    ]
    
    record_ids = []
    for emp in employees:
        record_id = db.insert(emp)
        record_ids.append(record_id)
    
    # Query individual records
    print("\n" + "="*70)
    print("Querying Individual Records")
    print("="*70 + "\n")
    
    for i, record_id in enumerate(record_ids):
        result = db.query(record_id)
        print(f"Employee {i+1}:")
        print(f"  Name: {result['name']}")
        print(f"  Email: {result['email']}")
        print(f"  Salary: ${result['salary']:,}")
        print(f"  Age: {result['age']}")
        print()
    
    # Compute aggregations on encrypted data
    print("="*70)
    print("Encrypted Aggregations (No Decryption!)")
    print("="*70 + "\n")
    
    total_salaries = db.aggregate("salary", "sum")
    print(f"Total Payroll: ${total_salaries:,}")
    
    avg_salary = db.aggregate("salary", "avg")
    print(f"Average Salary: ${avg_salary:,}")
    
    avg_age = db.aggregate("age", "avg")
    print(f"Average Age: {avg_age} years")
    
    # Print statistics
    db.print_stats()
    
    print("\n✅ Hybrid Database Demo Complete!")
