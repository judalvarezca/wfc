from pathlib import Path

import pytest

from wfc.sudoku.board import ALL_VALUES, Board
from wfc.sudoku.constraints import is_consistent
from wfc.sudoku.generator import generate_puzzle, generate_solved
from wfc.sudoku.parser import from_file
from wfc.sudoku.solver import solve

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"

EASY_SOLUTION = (
    "534678912"
    "672195348"
    "198342567"
    "859761423"
    "426853791"
    "713924856"
    "961537284"
    "287419635"
    "345286179"
)

UNSOLVABLE = (
    "550000000"
    "000000000"
    "000000000"
    "000000000"
    "000000000"
    "000000000"
    "000000000"
    "000000000"
    "000000000"
)


def _is_valid_sudoku_solution(board: Board) -> bool:
    if not board.is_solved():
        return False
    return all({cell.value for cell in unit} == ALL_VALUES for unit in board.iter_units())


def test_solves_easy():
    board = from_file(EXAMPLES / "easy.txt")
    result = solve(board)
    assert result is not None
    assert _is_valid_sudoku_solution(result)


def test_easy_solution_matches_expected():
    board = from_file(EXAMPLES / "easy.txt")
    result = solve(board, seed=0)
    assert result is not None
    assert result.to_string() == EASY_SOLUTION


def test_solves_medium():
    board = from_file(EXAMPLES / "medium.txt")
    result = solve(board)
    assert result is not None
    assert _is_valid_sudoku_solution(result)


@pytest.mark.slow
def test_solves_hard():
    board = from_file(EXAMPLES / "hard.txt")
    result = solve(board, seed=0)
    assert result is not None
    assert _is_valid_sudoku_solution(result)


def test_preserves_givens():
    board = from_file(EXAMPLES / "easy.txt")
    given_positions = [
        (r, c)
        for r in range(9)
        for c in range(9)
        if board.cells[r][c].given
    ]
    result = solve(board)
    assert result is not None
    for r, c in given_positions:
        assert result.cells[r][c].value == board.cells[r][c].value


def test_does_not_mutate_input():
    board = from_file(EXAMPLES / "easy.txt")
    snapshot = board.to_string()
    solve(board)
    assert board.to_string() == snapshot


def test_already_solved_returns_equivalent():
    board = Board.from_string(EASY_SOLUTION)
    result = solve(board)
    assert result is not None
    assert result.to_string() == EASY_SOLUTION


def test_unsolvable_returns_none():
    board = Board.from_string(UNSOLVABLE)
    result = solve(board)
    assert result is None


def test_solution_consistent():
    board = from_file(EXAMPLES / "medium.txt")
    result = solve(board)
    assert result is not None
    assert is_consistent(result)


def test_seed_determinism():
    board = from_file(EXAMPLES / "easy.txt")
    a = solve(board, seed=42)
    b = solve(board, seed=42)
    assert a is not None and b is not None
    assert a.to_string() == b.to_string()


@pytest.mark.parametrize("seed", [0, 1, 7, 42, 99])
def test_solves_generated_puzzles(seed):
    puzzle = generate_puzzle(givens=30, seed=seed)
    result = solve(puzzle, seed=seed)
    assert result is not None
    assert _is_valid_sudoku_solution(result)


def test_solves_fully_collapsed_generated():
    solved = generate_solved(seed=1)
    result = solve(solved)
    assert result is not None
    assert result.to_string() == solved.to_string()
