from __future__ import annotations

import logging
from functools import cache

from wfc.board import BOX, SIZE, Board

logger = logging.getLogger(__name__)


class ContradictionError(Exception):
    """Raised when constraint propagation detects an unsolvable state."""


@cache
def peers(r: int, c: int) -> frozenset[tuple[int, int]]:
    result: set[tuple[int, int]] = set()
    for cc in range(SIZE):
        if cc != c:
            result.add((r, cc))
    for rr in range(SIZE):
        if rr != r:
            result.add((rr, c))
    br, bc = (r // BOX) * BOX, (c // BOX) * BOX
    for rr in range(br, br + BOX):
        for cc in range(bc, bc + BOX):
            if (rr, cc) != (r, c):
                result.add((rr, cc))
    return frozenset(result)


def _build_units() -> list[list[tuple[int, int]]]:
    units: list[list[tuple[int, int]]] = []
    for r in range(SIZE):
        units.append([(r, c) for c in range(SIZE)])
    for c in range(SIZE):
        units.append([(r, c) for r in range(SIZE)])
    for b in range(SIZE):
        br, bc = divmod(b, BOX)
        units.append(
            [(br * BOX + dr, bc * BOX + dc) for dr in range(BOX) for dc in range(BOX)]
        )
    return units


UNITS: list[list[tuple[int, int]]] = _build_units()


def is_consistent(board: Board) -> bool:
    for unit in UNITS:
        values = [board.cells[r][c].value for r, c in unit if board.cells[r][c].collapsed]
        if len(values) != len(set(values)):
            return False
    return True


def _apply_hidden_singles(board: Board) -> list[tuple[int, int]]:
    new_collapses: list[tuple[int, int]] = []
    for unit in UNITS:
        for v in range(1, SIZE + 1):
            possible = [(r, c) for r, c in unit if v in board.cells[r][c].candidates]
            if not possible:
                raise ContradictionError(f"value {v} has no place in a unit")
            if len(possible) == 1:
                r, c = possible[0]
                if not board.cells[r][c].collapsed:
                    board.cells[r][c].candidates = {v}
                    logger.debug("hidden single: (%d,%d) = %d", r, c, v)
                    new_collapses.append((r, c))
    return new_collapses


def propagate(board: Board, seed: tuple[int, int] | None = None) -> None:
    """Apply naked + hidden single rules to fixed point. Mutates board.

    With `seed=(r, c)`, treats that as the only newly collapsed cell (incremental).
    Without `seed`, propagates from every currently-collapsed cell (full sweep).
    Raises Contradiction if any cell ends up with zero candidates or if some value
    has no place in a unit.
    """
    if seed is not None:
        queue: list[tuple[int, int]] = [seed]
    else:
        queue = [
            (r, c)
            for r in range(SIZE)
            for c in range(SIZE)
            if board.cells[r][c].collapsed
        ]

    initial = sum(1 for cell in board.iter_cells() if cell.collapsed)
    logger.info("propagate: starting with %d collapsed cells", initial)

    iteration = 0
    eliminations_total = 0
    naked_total = 0
    hidden_total = 0

    while True:
        iteration += 1
        iter_eliminations = 0
        iter_naked = 0
        while queue:
            r, c = queue.pop()
            cell = board.cells[r][c]
            if not cell.collapsed:
                continue
            v = cell.value
            for pr, pc in peers(r, c):
                peer = board.cells[pr][pc]
                if v in peer.candidates:
                    peer.candidates.discard(v)
                    iter_eliminations += 1
                    logger.debug("naked: removed %d from (%d,%d)", v, pr, pc)
                    if not peer.candidates:
                        raise ContradictionError(f"cell ({pr},{pc}) has no candidates left")
                    if peer.collapsed:
                        iter_naked += 1
                        logger.debug(
                            "naked single: (%d,%d) = %d", pr, pc, next(iter(peer.candidates))
                        )
                        queue.append((pr, pc))

        new_collapses = _apply_hidden_singles(board)
        eliminations_total += iter_eliminations
        naked_total += iter_naked
        hidden_total += len(new_collapses)
        logger.debug(
            "iter %d: %d eliminations, %d naked, %d hidden",
            iteration,
            iter_eliminations,
            iter_naked,
            len(new_collapses),
        )
        if not new_collapses:
            final = sum(1 for cell in board.iter_cells() if cell.collapsed)
            logger.info(
                "propagate: done in %d iterations — %d eliminations, "
                "%d naked + %d hidden collapses → %d/81 cells",
                iteration,
                eliminations_total,
                naked_total,
                hidden_total,
                final,
            )
            return
        queue.extend(new_collapses)
