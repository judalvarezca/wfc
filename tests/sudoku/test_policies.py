"""Verify both ResolutionPolicy implementations solve real sudoku puzzles."""
from pathlib import Path

import pytest

from wfc.core.engine import solve as engine_solve
from wfc.core.events import Collapsed, Restarted, Solved
from wfc.core.policy import BacktrackPolicy, RestartPolicy
from wfc.sudoku.adapter import BoardWave, SudokuConstraint
from wfc.sudoku.parser import from_file

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def _solve(name, policy, seed=42):
    board = from_file(EXAMPLES / f"{name}.txt")
    wave = BoardWave(board.clone())
    events = []
    result = engine_solve(
        wave,
        [SudokuConstraint()],
        policy=policy,
        seed=seed,
        on_event=events.append,
    )
    return result, events


@pytest.mark.parametrize("name", ["easy", "medium"])
def test_both_policies_solve_easy_medium(name):
    for policy in (BacktrackPolicy(), RestartPolicy()):
        result, events = _solve(name, policy)
        assert result is not None, f"{name} unsolved by {type(policy).__name__}"
        assert result.board.is_solved()
        assert events[-1] == Solved()


def test_restart_emits_restarted_on_hard():
    result, events = _solve("hard", RestartPolicy(), seed=42)
    assert result is not None
    assert result.board.is_solved()
    restarts = [e for e in events if isinstance(e, Restarted)]
    # hard requires at least some restarts with seed 42 (empirically ~100+).
    assert len(restarts) >= 1


def test_backtrack_does_not_emit_restarted_on_hard():
    _, events = _solve("hard", BacktrackPolicy(), seed=42)
    assert not any(isinstance(e, Restarted) for e in events)


def test_restart_undid_vars_covers_attempt_collapses():
    """For each Restarted, every Collapsed within that attempt appears in undid_vars.

    Initial-propagation Collapsed events (which fire before any Observed) are not
    part of an attempt and so must be skipped — those cells stay collapsed across
    restarts in `root`.
    """
    from wfc.core.events import Observed

    _, events = _solve("hard", RestartPolicy(), seed=42)
    collapsed_since: list[tuple[int, int]] = []
    in_attempt = False
    for e in events:
        if isinstance(e, Observed):
            in_attempt = True
        elif isinstance(e, Collapsed) and in_attempt:
            collapsed_since.append(e.var)
        elif isinstance(e, Restarted):
            assert set(collapsed_since) <= set(e.undid_vars), (
                f"missing collapses in undid_vars: "
                f"{set(collapsed_since) - set(e.undid_vars)}"
            )
            collapsed_since = []
            in_attempt = False
