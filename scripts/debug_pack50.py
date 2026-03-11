import numpy as np

np.random.seed(42)
dataset = np.random.randint(0, 1000, 1000)
test_values = dataset[:100].tolist()

print(f"Test values (first 10): {test_values[:10]}")
print(f"Expected sum: {sum(test_values)}")
print(f"Max value: {max(test_values)}")

# Simulate packing with base=1024
base = 1024
pack_size = 50

# Pack 1: values 0-49
pack1_values = test_values[:50]
# Pack 2: values 50-99
pack2_values = test_values[50:100]

print(f"\nPack 1 sum: {sum(pack1_values)}")
print(f"Pack 2 sum: {sum(pack2_values)}")
print(f"Total: {sum(pack1_values) + sum(pack2_values)}")

# Check if any sum exceeds base
max_per_position = max(pack1_values[i] + pack2_values[i] for i in range(50))
print(f"\nMax sum at any position: {max_per_position}")
print(f"Base: {base}")
print(f"Overflow? {max_per_position >= base}")
