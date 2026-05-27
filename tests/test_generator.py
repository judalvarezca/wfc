import pytest

from wfc.generator import generate_puzzle, generate_solved


def test_generated_solved_is_valid():
    board = generate_solved(seed=42)
    assert board.is_solved()


def test_generation_is_deterministic_with_seed():
    a = generate_solved(seed=42)
    b = generate_solved(seed=42)
    assert a.to_string() == b.to_string()


def test_different_seeds_give_different_boards():
    a = generate_solved(seed=1)
    b = generate_solved(seed=2)
    assert a.to_string() != b.to_string()


def test_puzzle_has_correct_number_of_givens():
    board = generate_puzzle(givens=30, seed=42)
    givens = sum(1 for cell in board.iter_cells() if cell.given)
    assert givens == 30


def test_puzzle_givens_match_solved_with_same_seed():
    solved = generate_solved(seed=42)
    puzzle = generate_puzzle(givens=30, seed=42)
    for r in range(9):
        for c in range(9):
            if puzzle.cells[r][c].given:
                assert puzzle.cells[r][c].value == solved.cells[r][c].value


def test_puzzle_empty_cells_have_full_candidates():
    board = generate_puzzle(givens=30, seed=42)
    for cell in board.iter_cells():
        if not cell.given:
            assert cell.candidates == set(range(1, 10))


def test_puzzle_with_81_givens_equals_solved():
    full = generate_puzzle(givens=81, seed=42)
    solved = generate_solved(seed=42)
    assert full.to_string() == solved.to_string()


def test_puzzle_with_zero_givens_is_fully_empty():
    board = generate_puzzle(givens=0, seed=42)
    for cell in board.iter_cells():
        assert not cell.given
        assert not cell.collapsed


def test_invalid_givens_raises():
    with pytest.raises(ValueError, match=r"\[0, 81\]"):
        generate_puzzle(givens=-1, seed=42)
    with pytest.raises(ValueError, match=r"\[0, 81\]"):
        generate_puzzle(givens=82, seed=42)
