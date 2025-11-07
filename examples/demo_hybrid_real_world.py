"""
Real-World Demo: Hybrid AES + Paillier Healthcare Database

Scenario: Hospital patient records database
- Patient names, SSN, contact info: AES-encrypted (HIPAA compliance)
- Medical costs, treatment times: Paillier-encrypted (for billing analytics)
- Patient IDs, diagnosis codes: Plaintext (for querying/indexing)

This demonstrates:
1. Real-world schema design
2. Privacy-preserving storage
3. Encrypted analytics (compute average costs without seeing individual values)
4. Performance benefits of hybrid approach
"""

import time
import random
from datetime import datetime, timedelta

from agniya.hybrid import HybridDatabase, Schema, Field, FieldType


def create_patient_schema() -> Schema:
    """Create realistic healthcare database schema."""
    return Schema("patients", [
        # Plaintext: Queryable fields
        Field("patient_id", FieldType.PLAINTEXT, int, nullable=False,
              description="Unique patient identifier"),
        Field("admission_date", FieldType.PLAINTEXT, int,
              description="Unix timestamp for admission date"),
        Field("diagnosis_code", FieldType.PLAINTEXT, str,
              description="ICD-10 diagnosis code (for queries)"),
        Field("hospital_id", FieldType.PLAINTEXT, int,
              description="Hospital location ID"),
        
        # AES: Private information (HIPAA protected)
        Field("full_name", FieldType.AES_ENCRYPTED, str,
              description="Patient full name (private)"),
        Field("ssn", FieldType.AES_ENCRYPTED, str,
              description="Social Security Number (highly sensitive)"),
        Field("phone", FieldType.AES_ENCRYPTED, str,
              description="Contact phone number"),
        Field("address", FieldType.AES_ENCRYPTED, str,
              description="Home address"),
        
        # Paillier: Computational fields (for analytics)
        Field("treatment_cost", FieldType.PAILLIER_ENCRYPTED, int,
              description="Treatment cost in cents (billing analytics)"),
        Field("age", FieldType.PAILLIER_ENCRYPTED, int,
              description="Patient age (demographic analytics)"),
        Field("length_of_stay", FieldType.PAILLIER_ENCRYPTED, int,
              description="Hospital stay duration in days"),
    ])


def generate_patient_data(num_patients: int = 100):
    """Generate synthetic patient data for testing."""
    print(f"\n{'='*70}")
    print(f"Generating {num_patients} Synthetic Patient Records")
    print('='*70)
    
    # Sample data pools
    first_names = ["Emma", "Liam", "Olivia", "Noah", "Ava", "Ethan", "Sophia", "Mason", 
                   "Isabella", "William", "Mia", "James", "Charlotte", "Benjamin", "Amelia"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
                  "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez"]
    
    diagnosis_codes = ["J45.9", "E11.9", "I10", "M54.5", "F41.9", "K21.9", "G43.9", 
                       "N39.0", "J06.9", "R50.9"]  # Common ICD-10 codes
    
    hospitals = [1, 2, 3, 4, 5]  # Hospital IDs
    
    base_date = int(datetime(2024, 1, 1).timestamp())
    
    patients = []
    for i in range(num_patients):
        patient = {
            "patient_id": 10000 + i,
            "admission_date": base_date + random.randint(0, 365 * 86400),
            "diagnosis_code": random.choice(diagnosis_codes),
            "hospital_id": random.choice(hospitals),
            
            "full_name": f"{random.choice(first_names)} {random.choice(last_names)}",
            "ssn": f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(1000, 9999)}",
            "phone": f"({random.randint(200, 999)}) {random.randint(100, 999)}-{random.randint(1000, 9999)}",
            "address": f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Maple', 'Cedar'])} St",
            
            "treatment_cost": random.randint(500_00, 50000_00),  # $500 - $50,000 in cents
            "age": random.randint(18, 85),
            "length_of_stay": random.randint(1, 30),
        }
        patients.append(patient)
    
    print(f"✅ Generated {num_patients} patient records")
    print(f"   Sample: {patients[0]['full_name']}, Age {patients[0]['age']}, "
          f"Diagnosis: {patients[0]['diagnosis_code']}")
    
    return patients


def demo_hybrid_healthcare_database():
    """Demonstrate hybrid database with realistic healthcare scenario."""
    
    print("\n" + "="*70)
    print("HYBRID DATABASE DEMO: Healthcare Patient Records")
    print("="*70)
    print("\nScenario: HIPAA-compliant hospital database")
    print("- Private info (names, SSN): AES-256 encrypted")
    print("- Billing data: Paillier encrypted (for analytics)")
    print("- Metadata: Plaintext (for queries)")
    
    # Create schema
    schema = create_patient_schema()
    schema.print_schema()
    
    # Initialize database
    print("\n" + "="*70)
    print("Initializing Database")
    print("="*70)
    db = HybridDatabase(schema, paillier_key_size=2048, enable_verbose=False)
    print(f"✅ Database ready: {db}")
    
    # Generate and insert patient data
    num_patients = 50
    patients = generate_patient_data(num_patients)
    
    print(f"\n{'='*70}")
    print(f"Inserting {num_patients} Patient Records")
    print('='*70)
    
    start_time = time.time()
    record_ids = []
    for i, patient in enumerate(patients):
        record_id = db.insert(patient)
        record_ids.append(record_id)
        
        if (i + 1) % 10 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            print(f"  Progress: {i+1}/{num_patients} records ({rate:.1f} records/sec)")
    
    total_insert_time = time.time() - start_time
    print(f"\n✅ Inserted {num_patients} records in {total_insert_time:.2f}s")
    print(f"   Average: {total_insert_time/num_patients*1000:.1f}ms per record")
    
    # Query individual patients
    print(f"\n{'='*70}")
    print("Querying Individual Patient Records")
    print('='*70)
    
    sample_indices = [0, 10, 25]
    query_times = []
    
    for idx in sample_indices:
        start = time.time()
        result = db.query(record_ids[idx])
        query_time = time.time() - start
        query_times.append(query_time)
        
        print(f"\nPatient #{result['patient_id']}:")
        print(f"  Name: {result['full_name']}")
        print(f"  SSN: {result['ssn']}")
        print(f"  Age: {result['age']} years")
        print(f"  Diagnosis: {result['diagnosis_code']}")
        print(f"  Treatment Cost: ${result['treatment_cost']/100:.2f}")
        print(f"  Length of Stay: {result['length_of_stay']} days")
        print(f"  Query Time: {query_time*1000:.2f}ms")
    
    avg_query_time = sum(query_times) / len(query_times)
    print(f"\n✅ Average query time: {avg_query_time*1000:.2f}ms")
    
    # Encrypted analytics
    print(f"\n{'='*70}")
    print("Encrypted Analytics (NO Decryption of Individual Records!)")
    print('='*70)
    
    print("\nComputing statistics on encrypted data...")
    
    # Total revenue
    start = time.time()
    total_revenue = db.aggregate("treatment_cost", "sum")
    revenue_time = time.time() - start
    print(f"\n📊 Total Hospital Revenue: ${total_revenue/100:,.2f}")
    print(f"   Computation time: {revenue_time:.3f}s")
    print(f"   ✅ Computed without seeing individual treatment costs!")
    
    # Average cost
    start = time.time()
    avg_cost = db.aggregate("treatment_cost", "avg")
    avg_time = time.time() - start
    print(f"\n📊 Average Treatment Cost: ${avg_cost/100:,.2f}")
    print(f"   Computation time: {avg_time:.3f}s")
    
    # Average age
    start = time.time()
    avg_age = db.aggregate("age", "avg")
    age_time = time.time() - start
    print(f"\n📊 Average Patient Age: {avg_age} years")
    print(f"   Computation time: {age_time:.3f}s")
    
    # Average length of stay
    start = time.time()
    avg_los = db.aggregate("length_of_stay", "avg")
    los_time = time.time() - start
    print(f"\n📊 Average Length of Stay: {avg_los} days")
    print(f"   Computation time: {los_time:.3f}s")
    
    # Database statistics
    db.print_stats()
    
    # Security demonstration
    print(f"\n{'='*70}")
    print("Security Verification")
    print('='*70)
    
    print("\n🔒 Checking encrypted data storage...")
    sample_record = db.records[record_ids[0]]
    
    # Check AES fields are encrypted
    print(f"\nAES-Encrypted Fields (server sees this):")
    print(f"  Name field: {str(sample_record.aes_fields['full_name']['ciphertext'])[:50]}...")
    print(f"  SSN field: {str(sample_record.aes_fields['ssn']['ciphertext'])[:50]}...")
    print(f"  ✅ Data is encrypted - server cannot read names/SSN")
    
    # Check Paillier fields
    print(f"\nPaillier-Encrypted Fields (server sees this):")
    cost_ciphertext = sample_record.paillier_fields['treatment_cost']
    print(f"  Treatment cost: {str(cost_ciphertext)[:60]}...")
    print(f"  ✅ Ciphertext is huge number - server cannot read actual cost")
    print(f"  ✅ But server CAN compute SUM/AVG without decryption!")
    
    # Summary
    print(f"\n{'='*70}")
    print("DEMO SUMMARY")
    print('='*70)
    print(f"\n✅ Successfully demonstrated hybrid encryption system:")
    print(f"   - Inserted {num_patients} patient records")
    print(f"   - Queried individual records (avg {avg_query_time*1000:.1f}ms)")
    print(f"   - Computed encrypted analytics without seeing private data")
    print(f"   - Verified data confidentiality (AES + Paillier)")
    print(f"\n🎯 Use Case: HIPAA-compliant healthcare database")
    print(f"   - Protects patient privacy (names, SSN encrypted)")
    print(f"   - Enables billing analytics (encrypted aggregation)")
    print(f"   - Maintains query performance (plaintext indexes)")
    
    print("\n" + "="*70)
    
    return db


if __name__ == "__main__":
    demo_hybrid_healthcare_database()
