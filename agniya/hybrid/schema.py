"""
Schema System for Hybrid Database

Defines field types and schema annotations for determining which
encryption method to use for each field.

Field Types:
1. PLAINTEXT: No encryption (IDs, timestamps, public metadata)
2. AES_ENCRYPTED: AES-256 symmetric encryption (names, emails, addresses)
3. PAILLIER_ENCRYPTED: Homomorphic encryption (salaries, ages, amounts)

Design Principles:
- Declarative: Define schema once, enforcement is automatic
- Type-safe: Field type validation at insertion time
- Extensible: Easy to add new field types (e.g., searchable encryption)
"""

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass


class FieldType(Enum):
    """
    Encryption type for database fields.
    
    Determines how data is stored and what operations are available.
    """
    
    PLAINTEXT = "plaintext"
    """
    No encryption. Use for:
    - Primary keys (need to reference records)
    - Timestamps (need to query by date range)
    - Public metadata (user role, status)
    
    Operations: Full SQL (WHERE, ORDER BY, GROUP BY)
    Security: ⚠️ Data visible to server
    Performance: Fastest (no encryption overhead)
    """
    
    AES_ENCRYPTED = "aes"
    """
    AES-256-GCM symmetric encryption. Use for:
    - Personal identifiable information (names, emails, SSN)
    - Addresses and contact information
    - Any data that doesn't need computation
    
    Operations: Exact match only (with encrypted index)
    Security: ✅ Confidential, authenticated, tamper-proof
    Performance: Fast (100 MB/s encryption, ~50 bytes storage)
    """
    
    PAILLIER_ENCRYPTED = "paillier"
    """
    Paillier homomorphic encryption. Use for:
    - Financial data (salaries, transaction amounts)
    - Numeric data requiring aggregation (ages, counts, scores)
    - Data for encrypted machine learning
    
    Operations: SUM, AVG, weighted averages (without decryption!)
    Security: ✅ Fully homomorphic for addition
    Performance: Slow (150ms/value, ~512 bytes storage)
    """


@dataclass
class Field:
    """
    Field definition in database schema.
    
    Specifies field name, type, encryption method, and constraints.
    """
    
    name: str
    """Field name (e.g., 'employee_id', 'salary')"""
    
    field_type: FieldType
    """Encryption method for this field"""
    
    data_type: type
    """Python data type (int, str, float, bytes)"""
    
    nullable: bool = True
    """Whether field can be NULL/None"""
    
    indexed: bool = False
    """Whether to create encrypted index (for AES fields only)"""
    
    description: str = ""
    """Human-readable description"""
    
    def __repr__(self) -> str:
        return (f"Field(name='{self.name}', type={self.field_type.value}, "
                f"data_type={self.data_type.__name__}, nullable={self.nullable})")


class Schema:
    """
    Database schema defining fields and their encryption types.
    
    Example:
        >>> schema = Schema("employees", [
        ...     Field("emp_id", FieldType.PLAINTEXT, int, nullable=False),
        ...     Field("name", FieldType.AES_ENCRYPTED, str),
        ...     Field("email", FieldType.AES_ENCRYPTED, str),
        ...     Field("salary", FieldType.PAILLIER_ENCRYPTED, int),
        ...     Field("age", FieldType.PAILLIER_ENCRYPTED, int),
        ... ])
    """
    
    def __init__(self, table_name: str, fields: list[Field]):
        """
        Initialize schema.
        
        Args:
            table_name: Name of the table/collection
            fields: List of Field definitions
        """
        self.table_name = table_name
        self.fields = {field.name: field for field in fields}
        
        # Validate schema
        self._validate()
    
    def _validate(self):
        """Validate schema constraints."""
        if not self.fields:
            raise ValueError("Schema must have at least one field")
        
        # Check for duplicate field names
        if len(self.fields) != len(set(self.fields.keys())):
            raise ValueError("Duplicate field names in schema")
        
        # Check for at least one plaintext field (for record ID)
        has_plaintext = any(
            f.field_type == FieldType.PLAINTEXT 
            for f in self.fields.values()
        )
        if not has_plaintext:
            raise ValueError(
                "Schema must have at least one PLAINTEXT field for record identification"
            )
    
    def get_field(self, field_name: str) -> Field:
        """
        Get field definition by name.
        
        Args:
            field_name: Name of field
            
        Returns:
            Field definition
            
        Raises:
            KeyError: If field doesn't exist in schema
        """
        if field_name not in self.fields:
            raise KeyError(f"Field '{field_name}' not in schema. "
                          f"Available fields: {list(self.fields.keys())}")
        return self.fields[field_name]
    
    def get_fields_by_type(self, field_type: FieldType) -> list[Field]:
        """
        Get all fields of a specific encryption type.
        
        Args:
            field_type: Encryption type to filter by
            
        Returns:
            List of fields with matching type
        """
        return [
            field for field in self.fields.values()
            if field.field_type == field_type
        ]
    
    def validate_record(self, record: Dict[str, Any]) -> None:
        """
        Validate record against schema.
        
        Checks:
        - All non-nullable fields are present
        - Field data types match schema
        - No extra fields
        
        Args:
            record: Dictionary of field_name -> value
            
        Raises:
            ValueError: If validation fails
        """
        # Check for missing required fields
        for field_name, field in self.fields.items():
            if not field.nullable and field_name not in record:
                raise ValueError(f"Required field '{field_name}' missing from record")
        
        # Check for extra fields
        extra_fields = set(record.keys()) - set(self.fields.keys())
        if extra_fields:
            raise ValueError(f"Unknown fields in record: {extra_fields}")
        
        # Check data types
        for field_name, value in record.items():
            if value is None:
                continue  # None is valid if nullable
            
            field = self.fields[field_name]
            
            # Type checking
            if not isinstance(value, field.data_type):
                raise ValueError(
                    f"Field '{field_name}' expects type {field.data_type.__name__}, "
                    f"got {type(value).__name__}"
                )
    
    def get_storage_estimate(self, num_records: int) -> Dict[str, int]:
        """
        Estimate storage size for given number of records.
        
        Args:
            num_records: Number of records to estimate
            
        Returns:
            Dictionary with size breakdown by field type
        """
        plaintext_size = 0
        aes_size = 0
        paillier_size = 0
        
        for field in self.fields.values():
            if field.field_type == FieldType.PLAINTEXT:
                # Rough estimate: 8 bytes per field
                plaintext_size += 8 * num_records
            elif field.field_type == FieldType.AES_ENCRYPTED:
                # AES: ~50 bytes per field (data + nonce + tag)
                aes_size += 50 * num_records
            elif field.field_type == FieldType.PAILLIER_ENCRYPTED:
                # Paillier-2048: 512 bytes per field
                paillier_size += 512 * num_records
        
        total = plaintext_size + aes_size + paillier_size
        
        return {
            'plaintext_bytes': plaintext_size,
            'aes_bytes': aes_size,
            'paillier_bytes': paillier_size,
            'total_bytes': total,
            'total_mb': total / (1024 * 1024)
        }
    
    def print_schema(self):
        """Print human-readable schema representation."""
        print("="*70)
        print(f"Schema: {self.table_name}")
        print("="*70)
        
        # Group by field type
        for field_type in FieldType:
            fields = self.get_fields_by_type(field_type)
            if not fields:
                continue
            
            print(f"\n{field_type.value.upper()} Fields:")
            for field in fields:
                nullable_str = "NULL" if field.nullable else "NOT NULL"
                indexed_str = " [INDEXED]" if field.indexed else ""
                print(f"  - {field.name}: {field.data_type.__name__} "
                      f"({nullable_str}){indexed_str}")
                if field.description:
                    print(f"      {field.description}")
        
        print("\n" + "="*70)
    
    def __repr__(self) -> str:
        return (f"Schema(table='{self.table_name}', "
                f"fields={len(self.fields)})")


# Example schemas for common use cases
def create_employee_schema() -> Schema:
    """Example: Employee database schema."""
    return Schema("employees", [
        Field("emp_id", FieldType.PLAINTEXT, int, nullable=False,
              description="Unique employee identifier"),
        Field("name", FieldType.AES_ENCRYPTED, str,
              description="Full name (private)"),
        Field("email", FieldType.AES_ENCRYPTED, str,
              description="Email address (private)"),
        Field("salary", FieldType.PAILLIER_ENCRYPTED, int,
              description="Annual salary (supports encrypted aggregation)"),
        Field("age", FieldType.PAILLIER_ENCRYPTED, int,
              description="Age in years (supports encrypted statistics)"),
        Field("hire_date", FieldType.PLAINTEXT, int,
              description="Hire date as Unix timestamp (queryable)"),
    ])


def create_patient_schema() -> Schema:
    """Example: Healthcare patient database schema."""
    return Schema("patients", [
        Field("patient_id", FieldType.PLAINTEXT, int, nullable=False,
              description="Unique patient identifier"),
        Field("name", FieldType.AES_ENCRYPTED, str,
              description="Patient name (HIPAA protected)"),
        Field("ssn", FieldType.AES_ENCRYPTED, str,
              description="Social Security Number (HIPAA protected)"),
        Field("diagnosis_code", FieldType.PLAINTEXT, str,
              description="ICD-10 diagnosis code (queryable)"),
        Field("treatment_cost", FieldType.PAILLIER_ENCRYPTED, int,
              description="Treatment cost in cents (encrypted billing)"),
        Field("age", FieldType.PAILLIER_ENCRYPTED, int,
              description="Age (encrypted demographics)"),
    ])


def create_transaction_schema() -> Schema:
    """Example: Financial transaction database schema."""
    return Schema("transactions", [
        Field("txn_id", FieldType.PLAINTEXT, int, nullable=False,
              description="Unique transaction ID"),
        Field("user_id", FieldType.PLAINTEXT, int,
              description="User identifier (indexed)"),
        Field("card_number", FieldType.AES_ENCRYPTED, str,
              description="Encrypted credit card number"),
        Field("amount", FieldType.PAILLIER_ENCRYPTED, int,
              description="Transaction amount in cents (fraud detection)"),
        Field("merchant_category", FieldType.PLAINTEXT, str,
              description="Merchant category code (queryable)"),
        Field("timestamp", FieldType.PLAINTEXT, int,
              description="Unix timestamp (queryable)"),
    ])


# Demo
if __name__ == "__main__":
    print("\n" + "="*70)
    print("Schema System Demo")
    print("="*70)
    
    # Create employee schema
    schema = create_employee_schema()
    schema.print_schema()
    
    # Storage estimate
    print("\nStorage Estimate (1000 records):")
    estimate = schema.get_storage_estimate(1000)
    print(f"  Plaintext: {estimate['plaintext_bytes']:,} bytes")
    print(f"  AES: {estimate['aes_bytes']:,} bytes")
    print(f"  Paillier: {estimate['paillier_bytes']:,} bytes")
    print(f"  Total: {estimate['total_mb']:.2f} MB")
    
    # Validate record
    print("\n" + "="*70)
    print("Record Validation")
    print("="*70)
    
    valid_record = {
        "emp_id": 1001,
        "name": "John Doe",
        "email": "john@example.com",
        "salary": 75000,
        "age": 30,
        "hire_date": 1609459200
    }
    
    try:
        schema.validate_record(valid_record)
        print("✅ Valid record passed validation")
    except ValueError as e:
        print(f"❌ Validation failed: {e}")
    
    # Test invalid record
    invalid_record = {
        "emp_id": 1002,
        "name": "Jane Doe",
        "salary": "not a number",  # Wrong type!
    }
    
    try:
        schema.validate_record(invalid_record)
        print("❌ Invalid record incorrectly passed validation")
    except ValueError as e:
        print(f"✅ Invalid record correctly rejected: {e}")
    
    print("\n" + "="*70)
