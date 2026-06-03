from __future__ import annotations

from collections.abc import Iterable, Iterator

from wfc.core.events import EventSink
from wfc.core.exceptions import ContradictionError
from wfc.core.wave import VarId, Wave
from wfc.sudoku.board import SIZE, Board
from wfc.sudoku.constraints import propagate as sudoku_propagate

SudokuVar = tuple[int, int]
SudokuState = int


class BoardWave:
    """Wave Protocol over a sudoku Board.

    Variable ids are (row, col) tuples; states are ints in 1..9. Operations
    delegate to the wrapped Board so existing sudoku code (renderer, parser)
    can still operate on board directly via the `board` property.
    """

    def __init__(self, board: Board) -> None:
        self._board = board

    @property
    def board(self) -> Board:
        return self._board

    def variables(self) -> Iterator[SudokuVar]:
        for r in range(SIZE):
            for c in range(SIZE):
                yield (r, c)

    def uncollapsed(self) -> Iterator[SudokuVar]:
        for r in range(SIZE):
            for c in range(SIZE):
                if not self._board.cells[r][c].collapsed:
                    yield (r, c)

    def domain(self, var: SudokuVar) -> set[SudokuState]:
        r, c = var
        return set(self._board.cells[r][c].candidates)

    def is_collapsed(self, var: SudokuVar) -> bool:
        r, c = var
        return self._board.cells[r][c].collapsed

    def value(self, var: SudokuVar) -> SudokuState:
        r, c = var
        v = self._board.cells[r][c].value
        if v is None:
            raise ValueError(f"variable {var} is not collapsed")
        return v

    def entropy(self, var: SudokuVar) -> int:
        r, c = var
        return self._board.cells[r][c].entropy

    def collapse(self, var: SudokuVar, state: SudokuState) -> None:
        r, c = var
        cell = self._board.cells[r][c]
        if state not in cell.candidates:
            raise ContradictionError(
                f"cannot collapse ({r},{c}) to {state}: not in domain {cell.candidates}"
            )
        cell.candidates = {state}

    def eliminate(self, var: SudokuVar, state: SudokuState) -> bool:
        r, c = var
        cell = self._board.cells[r][c]
        if state not in cell.candidates:
            return False
        cell.candidates.discard(state)
        if not cell.candidates:
            raise ContradictionError(f"cell ({r},{c}) has no candidates left")
        return True

    def is_fully_collapsed(self) -> bool:
        return all(cell.collapsed for cell in self._board.iter_cells())

    def clone(self) -> BoardWave:
        return BoardWave(self._board.clone())


class SudokuConstraint:
    """All-different on rows, columns and 3×3 boxes, with naked + hidden singles.

    Wraps the existing `wfc.sudoku.constraints.propagate` (which already runs
    both rules to internal fixed point). The engine still drives an outer
    fixed-point loop, but for sudoku that loop converges in one iteration since
    there is a single combined constraint.
    """

    def propagate(
        self,
        wave: Wave,
        seed: Iterable[VarId] | None = None,
        on_event: EventSink | None = None,
    ) -> set[SudokuVar]:
        if not isinstance(wave, BoardWave):
            raise TypeError(
                f"SudokuConstraint requires a BoardWave, got {type(wave).__name__}"
            )
        board = wave.board
        before = _collapsed_set(board)
        sudoku_propagate(board, seed=None, on_event=on_event)
        after = _collapsed_set(board)
        return after - before


def _collapsed_set(board: Board) -> set[SudokuVar]:
    return {
        (r, c)
        for r in range(SIZE)
        for c in range(SIZE)
        if board.cells[r][c].collapsed
    }
