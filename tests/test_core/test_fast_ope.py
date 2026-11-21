"""FastOPE must produce exactly pyope's tags (same scheme, same key), only faster."""
import random
import secrets

from pyope.ope import OPE, ValueRange

from agniya.hybrid.fast_ope import FastOPE


def test_tags_identical_to_pyope():
    rng = random.Random(3)
    for top in (1, 46, 10**5, 630_000_000):
        key = secrets.token_bytes(32)
        ranges = dict(in_range=ValueRange(0, top), out_range=ValueRange(0, 2**64 - 1))
        vals = [rng.randint(0, top) for _ in range(60)] + [0, top]
        ref = [OPE(key, **ranges).encrypt(v) for v in vals]
        fast = FastOPE(key, **ranges)
        assert fast.encrypt_list(vals) == ref
        assert [fast.encrypt(v) for v in vals[:10]] == ref[:10]
        assert fast.decrypt(ref[0]) == vals[0]


def test_order_preserved_and_ties_equal():
    f = FastOPE(secrets.token_bytes(32), in_range=ValueRange(0, 1000), out_range=ValueRange(0, 2**64 - 1))
    vals = [5, 5, 999, 0, 500, 501]
    tags = f.encrypt_list(vals)
    assert tags[0] == tags[1]
    assert sorted(range(6), key=tags.__getitem__) == sorted(range(6), key=vals.__getitem__)
