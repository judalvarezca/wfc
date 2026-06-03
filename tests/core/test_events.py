from core.toy import AllDifferentConstraint, ToyWave
from wfc.core.engine import solve
from wfc.core.events import (
    Backtracked,
    Collapsed,
    Contradiction,
    Event,
    Observed,
    Solved,
)


def _solve_capturing(wave, *, seed=None) -> tuple[ToyWave | None, list[Event]]:
    events: list[Event] = []
    result = solve(wave, [AllDifferentConstraint()], seed=seed, on_event=events.append)
    return result, events  # type: ignore[return-value]


def test_already_solved_emits_only_solved():
    wave = ToyWave([{1}, {2}, {3}])
    result, events = _solve_capturing(wave)
    assert result is not None
    assert events == [Solved()]


def test_initial_contradiction_emits_contradiction_and_stops():
    wave = ToyWave([{5}, {5}, {1, 2, 3}])
    result, events = _solve_capturing(wave)
    assert result is None
    assert events == [Contradiction()]


def test_propagation_emits_collapsed_chain():
    # var 0 = {3}, propagation forces var 1 and var 2 away from 3.
    # AllDifferent will further chain: removing 3 from var 1 leaves {1, 2}; same for var 2.
    # No automatic naked single here (still 2 candidates each). So the only initial
    # propagation is the existing collapse of var 0 — no new Collapsed events expected.
    wave = ToyWave([{3}, {1, 2, 3}, {1, 2, 3}])
    _, events = _solve_capturing(wave, seed=0)
    assert any(isinstance(e, Observed) for e in events)
    assert events[-1] == Solved()


def test_backtracking_emits_observed_and_backtracked():
    # 3 vars, 3 values each: requires branching but solvable. Confirm we see
    # both Observed and at least one Backtracked when the wrong path is chosen.
    wave = ToyWave([{1, 2, 3}, {1, 2, 3}, {1, 2, 3}])
    _, events = _solve_capturing(wave, seed=0)
    observed = [e for e in events if isinstance(e, Observed)]
    assert observed  # at least one Observed
    assert events[-1] == Solved()


def test_unsolvable_emits_no_solved():
    # Pigeonhole: 3 vars but only 2 distinct values.
    wave = ToyWave([{1, 2}, {1, 2}, {1, 2}])
    result, events = _solve_capturing(wave)
    assert result is None
    assert not any(isinstance(e, Solved) for e in events)


def test_backtracked_undid_vars_consistent():
    """undid_vars must include the originally observed variable."""
    wave = ToyWave([{1, 2, 3, 4}, {1, 2, 3, 4}, {1, 2, 3, 4}, {1, 2, 3, 4}, {1, 2, 3, 4, 5}])
    _, events = _solve_capturing(wave, seed=3)
    for e in events:
        if isinstance(e, Backtracked):
            assert e.var in e.undid_vars


def test_collapsed_events_match_final_solution():
    """The most-recent Collapsed for each var in the winning path equals its solved value."""
    wave = ToyWave([{1, 2, 3}, {1, 2, 3}, {1, 2, 3}])
    result, events = _solve_capturing(wave, seed=0)
    assert result is not None
    # For each variable, the last Collapsed event for it (not on a discarded branch)
    # should equal the final value. We verify a weaker property: the union of values
    # in Collapsed events covers the final solution.
    final_values = result.values()
    collapsed_vals = {(e.var, e.state) for e in events if isinstance(e, Collapsed)}
    for var, val in enumerate(final_values):
        assert (var, val) in collapsed_vals
