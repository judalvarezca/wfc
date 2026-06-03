"""Tests that exercise RestartPolicy against the toy AllDifferent constraint.

The Backtrack policy is already covered by tests/core/test_engine.py (which
uses the engine's default policy). These tests focus on the restart-specific
semantics: same input is solved, Restarted events fire when a path fails,
and the max_attempts bound prevents infinite loops on unsolvable inputs.
"""
import pytest

from core.toy import AllDifferentConstraint, ToyWave
from wfc.core.engine import solve
from wfc.core.events import (
    Collapsed,
    Contradiction,
    Restarted,
    Solved,
)
from wfc.core.policy import RestartPolicy


def _solve_with_restart(wave, *, seed=None, max_attempts=200):
    events = []
    result = solve(
        wave,
        [AllDifferentConstraint()],
        policy=RestartPolicy(max_attempts=max_attempts),
        seed=seed,
        on_event=events.append,
    )
    return result, events


def test_restart_solves_trivial():
    wave = ToyWave([{1}, {2}, {3}])
    result, events = _solve_with_restart(wave)
    assert result is not None
    assert result.values() == [1, 2, 3]
    assert events == [Solved()]


def test_restart_solves_branching():
    wave = ToyWave([{1, 2, 3}, {1, 2, 3}, {1, 2, 3}])
    result, events = _solve_with_restart(wave, seed=0)
    assert result is not None
    assert sorted(result.values()) == [1, 2, 3]
    assert events[-1] == Solved()
    # At least one Collapsed event must have fired in the successful path.
    assert any(isinstance(e, Collapsed) for e in events)


def test_restart_returns_none_on_initial_contradiction():
    # Two collapsed vars with same value — caught before any attempt.
    wave = ToyWave([{5}, {5}, {1, 2, 3}])
    result, events = _solve_with_restart(wave)
    assert result is None
    assert events == [Contradiction()]


def test_restart_gives_up_after_max_attempts_on_unsolvable():
    # Pigeonhole: 3 vars, only 2 values. Every attempt is a dead end, so the
    # policy bails out after max_attempts and emits one Restarted per attempt.
    wave = ToyWave([{1, 2}, {1, 2}, {1, 2}])
    result, events = _solve_with_restart(wave, seed=0, max_attempts=5)
    assert result is None
    restarts = [e for e in events if isinstance(e, Restarted)]
    assert len(restarts) == 5
    assert restarts[0].attempt == 1
    assert restarts[-1].attempt == 5


def test_restarted_event_undid_vars_match_collapsed_in_attempt():
    wave = ToyWave([{1, 2}, {1, 2}, {1, 2}])
    _, events = _solve_with_restart(wave, seed=0, max_attempts=3)
    # Walk the event stream; between two Restarted events (or from start to
    # first Restarted), every Collapsed var should be in the next Restarted's
    # undid_vars.
    collapsed_since_start: list[int] = []
    for e in events:
        if isinstance(e, Collapsed):
            collapsed_since_start.append(e.var)
        elif isinstance(e, Restarted):
            assert set(collapsed_since_start) <= set(e.undid_vars)
            collapsed_since_start = []


@pytest.mark.parametrize("seed", [0, 1, 7, 42, 99])
def test_restart_finds_valid_solution(seed):
    wave = ToyWave([{1, 2, 3, 4}, {1, 2, 3, 4}, {1, 2, 3, 4}, {1, 2, 3, 4}])
    result, _ = _solve_with_restart(wave, seed=seed)
    assert result is not None
    assert sorted(result.values()) == [1, 2, 3, 4]


def test_restart_does_not_mutate_input():
    wave = ToyWave([{1, 2, 3}, {1, 2, 3}, {1, 2, 3}])
    snapshot = [wave.domain(v) for v in wave.variables()]
    _solve_with_restart(wave, seed=0)
    assert [wave.domain(v) for v in wave.variables()] == snapshot
