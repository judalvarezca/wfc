import random

from core.toy import ToyWave
from wfc.core.sampler import UniformSampler


def test_order_is_sorted_without_rng():
    wave = ToyWave([{3, 1, 2}])
    sampler = UniformSampler()
    assert list(sampler.order(wave, 0)) == [1, 2, 3]


def test_yields_every_domain_value():
    wave = ToyWave([{1, 2, 3, 4, 5}])
    sampler = UniformSampler(rng=random.Random(0))
    assert sorted(sampler.order(wave, 0)) == [1, 2, 3, 4, 5]


def test_order_with_rng_is_deterministic_per_seed():
    wave = ToyWave([{1, 2, 3, 4, 5}])
    a = list(UniformSampler(rng=random.Random(42)).order(wave, 0))
    b = list(UniformSampler(rng=random.Random(42)).order(wave, 0))
    assert a == b


def test_order_with_different_seeds_differs():
    wave = ToyWave([{1, 2, 3, 4, 5, 6, 7, 8}])
    a = list(UniformSampler(rng=random.Random(0)).order(wave, 0))
    b = list(UniformSampler(rng=random.Random(1)).order(wave, 0))
    assert a != b  # extremely unlikely they coincide for 8! permutations
