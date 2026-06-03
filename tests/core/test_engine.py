import pytest

from core.toy import AllDifferentConstraint, ToyWave
from wfc.core.engine import solve


def test_already_solved_returns_unchanged():
    wave = ToyWave([{1}, {2}, {3}])
    result = solve(wave, [AllDifferentConstraint()])
    assert result is not None
    assert result.values() == [1, 2, 3]


def test_does_not_mutate_input():
    wave = ToyWave([{1, 2, 3}, {1, 2, 3}, {1, 2, 3}])
    snapshot = [wave.domain(v) for v in wave.variables()]
    solve(wave, [AllDifferentConstraint()])
    assert [wave.domain(v) for v in wave.variables()] == snapshot


def test_propagation_alone_solves_partial():
    # var 2 is fixed to 3; propagation should leave var 0, 1 with {1, 2}
    # but those still need a branch decision. We just check it solves.
    wave = ToyWave([{1, 2, 3}, {1, 2, 3}, {3}])
    result = solve(wave, [AllDifferentConstraint()], seed=0)
    assert result is not None
    vals = result.values()
    assert sorted(vals) == [1, 2, 3]
    assert vals[2] == 3


def test_requires_backtracking():
    # 3 vars all in {1, 2, 3}: no immediate inference; backtracking needed.
    wave = ToyWave([{1, 2, 3}, {1, 2, 3}, {1, 2, 3}])
    result = solve(wave, [AllDifferentConstraint()], seed=7)
    assert result is not None
    assert sorted(result.values()) == [1, 2, 3]


def test_unsolvable_returns_none():
    # 3 variables but only 2 values available: pigeonhole → no solution.
    wave = ToyWave([{1, 2}, {1, 2}, {1, 2}])
    result = solve(wave, [AllDifferentConstraint()])
    assert result is None


def test_initial_contradiction_returns_none():
    # Two collapsed variables with the same value: initial propagation contradicts.
    wave = ToyWave([{5}, {5}, {1, 2, 3, 4, 6, 7, 8, 9}])
    result = solve(wave, [AllDifferentConstraint()])
    assert result is None


def test_seed_determinism():
    wave_a = ToyWave([{1, 2, 3, 4}, {1, 2, 3, 4}, {1, 2, 3, 4}, {1, 2, 3, 4}])
    wave_b = wave_a.clone()
    result_a = solve(wave_a, [AllDifferentConstraint()], seed=123)
    result_b = solve(wave_b, [AllDifferentConstraint()], seed=123)
    assert result_a is not None and result_b is not None
    assert result_a.values() == result_b.values()


@pytest.mark.parametrize("seed", [0, 1, 7, 42, 99])
def test_any_seed_finds_valid_solution(seed):
    wave = ToyWave([{1, 2, 3, 4}, {1, 2, 3, 4}, {1, 2, 3, 4}, {1, 2, 3, 4}])
    result = solve(wave, [AllDifferentConstraint()], seed=seed)
    assert result is not None
    assert sorted(result.values()) == [1, 2, 3, 4]
