def _extended_gcd(a: int, b: int) -> tuple[int, int, int]:
    """
    Extended Euclidean Algorithm.
    Returns a tuple of (gcd, x, y) such that ax + by = gcd(a, b)
    """
    if b == 0:
        return (a, 1, 0)
    else:
        gcd, x1, y1 = _extended_gcd(b, a % b)
        x = y1
        y = x1 - (a // b) * y1
        return (gcd, x, y)

def modular_inverse(a: int, m: int) -> int:
    """
    Computes the modular multiplicative inverse of a modulo m.
    Raises ValueError if the inverse does not exist.
    """
    gcd, x, _ = _extended_gcd(a, m)
    if gcd != 1:
        raise ValueError(f"No modular inverse exists for {a} modulo {m}.")
    return x % m
