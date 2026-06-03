import random

import pytest

from core.toy import ToyWave
from wfc.core.selector import LowestEntropySelector


def test_picks_lowest_entropy():
    wave = ToyWave([{1, 2, 3}, {1, 2}, {1, 2, 3, 4}])
    selector = LowestEntropySelector()
    assert selector.select(wave) == 1  # entropy 2 is the smallest


def test_tie_break_deterministic_without_rng():
    wave = ToyWave([{1, 2}, {3, 4, 5}, {6, 7}])
    selector = LowestEntropySelector()
    assert selector.select(wave) == 0  # both var 0 and 2 have entropy 2; min(var) = 0
    assert selector.select(wave) == 0  # stable across calls


def test_tie_break_with_rng_can_pick_either():
    wave = ToyWave([{1, 2}, {3, 4, 5}, {6, 7}])
    picks = set()
    for s in range(50):
        sel = LowestEntropySelector(rng=random.Random(s))
        picks.add(sel.select(wave))
    assert picks == {0, 2}  # both tied vars chosen across seeds


def test_skips_collapsed_variables():
    wave = ToyWave([{5}, {1, 2}, {7}])
    selector = LowestEntropySelector()
    assert selector.select(wave) == 1


def test_raises_when_all_collapsed():
    wave = ToyWave([{1}, {2}, {3}])
    selector = LowestEntropySelector()
    with pytest.raises(ValueError, match="no uncollapsed"):
        selector.select(wave)
