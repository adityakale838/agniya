import pytest
from agniya.math_utils import modular_inverse

def test_modular_inverse_success():
    # 3 * 7 = 21 ≡ 1 mod 10, so inverse of 3 mod 10 is 7
    assert modular_inverse(3, 10) == 7

def test_modular_inverse_large_numbers():
    # 17 * 2753 = 46801 ≡ 1 mod 3120, so inverse of 17 mod 3120 is 2753
    assert modular_inverse(17, 3120) == 2753

def test_modular_inverse_failure():
    # 4 and 18 are not coprime, so inverse does not exist
    with pytest.raises(ValueError):
        modular_inverse(4, 18)
