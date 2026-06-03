from __future__ import annotations

import logging

from wfc.core.engine import solve as engine_solve
from wfc.core.events import Event
from wfc.sudoku.adapter import BoardWave, SudokuConstraint
from wfc.sudoku.board import Board

logger = logging.getLogger(__name__)


def solve(board: Board, seed: int | None = None) -> Board | None:
    """Solve a sudoku board using the generic WFC engine.

    Returns a fully-solved Board (independent of the input), or None if the
    puzzle has no solution. The input board is not mutated. `seed` controls
    randomness in tie-breaking and value ordering for reproducible runs.
    """
    logger.info(
        "sudoku.solve: %d givens, seed=%s",
        sum(1 for cell in board.iter_cells() if cell.given),
        seed,
    )
    wave = BoardWave(board.clone())
    result = engine_solve(wave, [SudokuConstraint()], seed=seed)
    if result is None:
        return None
    if not isinstance(result, BoardWave):
        raise TypeError(f"engine returned unexpected wave type {type(result).__name__}")
    return result.board


def solve_with_events(
    board: Board, seed: int | None = None
) -> tuple[Board | None, list[Event]]:
    """Solve a sudoku board and return the full event stream.

    Same semantics as `solve`, but additionally captures every Observed,
    Collapsed, Backtracked, Solved and Contradiction event the engine emits.
    The event list lets UIs replay the solving process at an arbitrary pace.
    """
    events: list[Event] = []
    wave = BoardWave(board.clone())
    result = engine_solve(
        wave, [SudokuConstraint()], seed=seed, on_event=events.append
    )
    if result is None:
        return None, events
    if not isinstance(result, BoardWave):
        raise TypeError(f"engine returned unexpected wave type {type(result).__name__}")
    return result.board, events
