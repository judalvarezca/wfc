from pathlib import Path

from wfc.core.events import (
    Backtracked,
    Collapsed,
    Contradiction,
    Observed,
    Solved,
)
from wfc.sudoku.board import Board
from wfc.sudoku.parser import from_file
from wfc.sudoku.solver import solve_with_events

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def test_easy_emits_collapsed_chain_and_solved():
    board = from_file(EXAMPLES / "easy.txt")
    sol, events = solve_with_events(board, seed=0)
    assert sol is not None
    collapsed = [e for e in events if isinstance(e, Collapsed)]
    # 81 - 30 givens = 51 cells to collapse
    assert len(collapsed) == 51
    assert events[-1] == Solved()


def test_hard_emits_observed_and_backtracked():
    board = from_file(EXAMPLES / "hard.txt")
    sol, events = solve_with_events(board, seed=42)
    assert sol is not None
    observed = [e for e in events if isinstance(e, Observed)]
    backtracked = [e for e in events if isinstance(e, Backtracked)]
    assert observed, "hard puzzle should require at least one selector pick"
    assert backtracked, "hard puzzle should backtrack at least once"


def test_unsolvable_emits_only_contradiction():
    board = Board.from_string("55" + "0" * 79)
    sol, events = solve_with_events(board)
    assert sol is None
    assert events == [Contradiction()]


def test_collapsed_events_cover_every_non_given_cell():
    board = from_file(EXAMPLES / "easy.txt")
    sol, events = solve_with_events(board, seed=0)
    assert sol is not None
    # Every cell that ends up with a value but was not a given should appear in
    # at least one Collapsed event.
    given_positions = {
        (r, c) for r in range(9) for c in range(9) if board.cells[r][c].given
    }
    collapsed_positions = {e.var for e in events if isinstance(e, Collapsed)}
    for r in range(9):
        for c in range(9):
            if (r, c) not in given_positions:
                assert (r, c) in collapsed_positions


def test_event_replay_reproduces_solution():
    """Apply Collapsed events on top of the input board → matches solver output."""
    board = from_file(EXAMPLES / "easy.txt")
    sol, events = solve_with_events(board, seed=0)
    assert sol is not None
    replay = board.clone()
    for e in events:
        if isinstance(e, Collapsed):
            r, c = e.var
            replay.cells[r][c].candidates = {e.state}
    assert replay.to_string() == sol.to_string()


def test_no_events_emitted_when_no_callback():
    """Solving without a callback must not regress the no-callback path."""
    board = from_file(EXAMPLES / "easy.txt")
    sol, events = solve_with_events(board, seed=0)
    assert sol is not None
    # solve_with_events always captures, but solve() without on_event should also work.
    from wfc.sudoku.solver import solve as plain_solve

    plain = plain_solve(board, seed=0)
    assert plain is not None
    assert plain.to_string() == sol.to_string()
