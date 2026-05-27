from __future__ import annotations

import logging
import random

from wfc.board import ALL_VALUES, SIZE, Board, Cell

logger = logging.getLogger(__name__)


def _canonical_grid() -> list[list[int]]:
    return [[((r % 3) * 3 + r // 3 + c) % SIZE + 1 for c in range(SIZE)] for r in range(SIZE)]


def _relabel_digits(grid: list[list[int]], rng: random.Random) -> None:
    perm = list(range(1, SIZE + 1))
    rng.shuffle(perm)
    for r in range(SIZE):
        for c in range(SIZE):
            grid[r][c] = perm[grid[r][c] - 1]


def _shuffle_rows_in_bands(grid: list[list[int]], rng: random.Random) -> None:
    for band in range(3):
        rows = grid[band * 3 : band * 3 + 3]
        rng.shuffle(rows)
        grid[band * 3 : band * 3 + 3] = rows


def _shuffle_cols_in_stacks(grid: list[list[int]], rng: random.Random) -> None:
    for stack in range(3):
        order = [stack * 3, stack * 3 + 1, stack * 3 + 2]
        rng.shuffle(order)
        for r in range(SIZE):
            slice_ = [grid[r][i] for i in order]
            grid[r][stack * 3 : stack * 3 + 3] = slice_


def _shuffle_bands(grid: list[list[int]], rng: random.Random) -> None:
    bands = [grid[b * 3 : b * 3 + 3] for b in range(3)]
    rng.shuffle(bands)
    new_grid: list[list[int]] = []
    for band in bands:
        new_grid.extend(band)
    grid[:] = new_grid


def _shuffle_stacks(grid: list[list[int]], rng: random.Random) -> None:
    order = [0, 1, 2]
    rng.shuffle(order)
    for r in range(SIZE):
        new_row: list[int] = []
        for s in order:
            new_row.extend(grid[r][s * 3 : s * 3 + 3])
        grid[r] = new_row


def _maybe_transpose(grid: list[list[int]], rng: random.Random) -> bool:
    if rng.random() < 0.5:
        grid[:] = [[grid[c][r] for c in range(SIZE)] for r in range(SIZE)]
        return True
    return False


def _grid_to_board(grid: list[list[int]]) -> Board:
    cells = [[Cell(candidates={v}, given=True) for v in row] for row in grid]
    return Board(cells=cells)


def generate_solved(seed: int | None = None) -> Board:
    logger.info("generate_solved: seed=%s", seed)
    rng = random.Random(seed)
    grid = _canonical_grid()
    logger.debug("canonical grid built")
    _relabel_digits(grid, rng)
    logger.debug("applied relabel_digits")
    _shuffle_rows_in_bands(grid, rng)
    logger.debug("applied shuffle_rows_in_bands")
    _shuffle_cols_in_stacks(grid, rng)
    logger.debug("applied shuffle_cols_in_stacks")
    _shuffle_bands(grid, rng)
    logger.debug("applied shuffle_bands")
    _shuffle_stacks(grid, rng)
    logger.debug("applied shuffle_stacks")
    transposed = _maybe_transpose(grid, rng)
    logger.debug("transpose=%s", transposed)
    return _grid_to_board(grid)


def generate_puzzle(givens: int = 30, seed: int | None = None) -> Board:
    if not 0 <= givens <= 81:
        raise ValueError(f"givens must be in [0, 81], got {givens}")
    logger.info("generate_puzzle: givens=%d, seed=%s", givens, seed)
    board = generate_solved(seed=seed)
    if givens == 81:
        return board
    rng = random.Random(seed)
    positions = [(r, c) for r in range(SIZE) for c in range(SIZE)]
    rng.shuffle(positions)
    holes = 81 - givens
    logger.debug("digging %d holes", holes)
    for r, c in positions[:holes]:
        board.cells[r][c].candidates = set(ALL_VALUES)
        board.cells[r][c].given = False
        logger.debug("hole at (%d,%d)", r, c)
    return board
