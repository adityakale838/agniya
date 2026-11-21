"""Fixed-base short-exponent r^n (DJN) and the randomness pool."""
import secrets

import gmpy2
import pytest

from agniya.core.paillier import generate_keypair, encrypt_with_rn, decrypt_crt
from agniya.core.djn import FixedBaseRN
from agniya.core.precomputation import RandomnessPool


@pytest.fixture(scope="module")
def keys():
    return generate_keypair(2048)


@pytest.fixture(scope="module")
def gen(keys):
    return FixedBaseRN(keys[0])


def test_comb_matches_powmod(keys, gen):
    for _ in range(10):
        a = secrets.randbits(gen.exponent_bits)
        assert gen.rn_for(a) == int(gmpy2.powmod(gen.hs, a, keys[0].n_squared))
    assert gen.rn_for(0) == 1


def test_exponent_is_half_modulus(keys, gen):
    assert gen.exponent_bits == keys[0].n.bit_length() // 2


def test_hs_is_nth_residue_and_decrypts(keys, gen):
    pub, priv = keys
    cts = [encrypt_with_rn(pub, 31337, gen()) for _ in range(30)]
    assert len(set(cts)) == 30
    assert all(decrypt_crt(pub, priv, c) == 31337 for c in cts)


@pytest.mark.parametrize("method", ["standard", "djn"])
def test_pool_methods(keys, method):
    pub, priv = keys
    pool = RandomnessPool(pub, method=method, workers=1)
    cts = pool.encrypt_batch([5, 5, 5, 7])
    assert len(set(cts)) == 4
    assert [decrypt_crt(pub, priv, c) for c in cts] == [5, 5, 5, 7]
    assert pool.get_stats()["used"] == 4


def test_pool_rejects_unknown_method(keys):
    with pytest.raises(ValueError):
        RandomnessPool(keys[0], method="cache")


def test_generated_keys_are_djn_admissible(keys):
    from agniya.core.paillier import is_djn_admissible
    pub, priv = keys
    assert is_djn_admissible(priv)
    assert priv.p % 4 == 3 and priv.q % 4 == 3
    assert gmpy2.gcd(priv.p - 1, priv.q - 1) == 2


def test_non_admissible_keys_detected():
    from agniya.core.number_theory import generate_prime
    from agniya.core.paillier import is_djn_admissible, keypair_from_primes
    while True:  # ordinary random primes are almost never safe primes
        p, q = generate_prime(1024), generate_prime(1024)
        if not (gmpy2.is_prime((p - 1) // 2) or gmpy2.is_prime((q - 1) // 2)):
            break
    assert not is_djn_admissible(keypair_from_primes(p, q)[1])
