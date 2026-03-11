import numpy as np
np.random.seed(42)
data = np.random.randint(1, 1000, size=1000).tolist()
print(f"Sum: {sum(data)}")
print(f"First 10: {data[:10]}")
