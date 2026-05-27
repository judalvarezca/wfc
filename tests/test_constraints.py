import pytest

from wfc.board import Board
from wfc.constraints import ContradictionError, is_consistent, peers, propagate

EASY = (
    "530070000"
    "600195000"
    "098000060"
    "800060003"
    "400803001"
    "700020006"
    "060000280"
    "000419005"
    "000080079"
)

SOLVED = (
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


# ----- peers -----

def test_peers_returns_exactly_20_cells():
    assert len(peers(0, 0)) == 20
    assert len(peers(4, 4)) == 20
    assert len(peers(8, 8)) == 20


def test_peers_excludes_self():
    assert (0, 0) not in peers(0, 0)
    assert (4, 4) not in peers(4, 4)


def test_peers_covers_row_col_box():
    p = peers(4, 4)
    # row 4
    for c in range(9):
        if c != 4:
            assert (4, c) in p
    # col 4
    for r in range(9):
        if r != 4:
            assert (r, 4) in p
    # box (rows 3-5, cols 3-5)
    for r in range(3, 6):
        for c in range(3, 6):
            if (r, c) != (4, 4):
                assert (r, c) in p


def test_peers_excludes_unrelated_cells():
    p = peers(0, 0)
    assert (3, 3) not in p
    assert (8, 8) not in p
    assert (4, 5) not in p


# ----- naked singles propagation -----

def test_propagate_eliminates_value_from_peers():
    board = Board.empty()
    board.cells[0][0].candidates = {5}
    propagate(board)
    assert 5 not in board.cells[0][1].candidates  # row peer
    assert 5 not in board.cells[1][0].candidates  # col peer
    assert 5 not in board.cells[2][2].candidates  # box peer
    assert 5 in board.cells[8][8].candidates       # not a peer


def test_propagate_chains_naked_singles():
    board = Board.empty()
    board.cells[0][0].candidates = {5}
    board.cells[0][1].candidates = {5, 7}
    propagate(board)
    assert board.cells[0][1].candidates == {7}


def test_propagate_reduces_easy_puzzle():
    board = Board.from_string(EASY)
    initial_total = sum(cell.entropy for cell in board.iter_cells())
    propagate(board)
    final_total = sum(cell.entropy for cell in board.iter_cells())
    assert final_total < initial_total
    assert is_consistent(board)


def test_propagate_is_noop_on_solved_board():
    board = Board.from_string(SOLVED)
    propagate(board)
    assert board.is_solved()


def test_propagate_is_noop_on_empty_board():
    board = Board.empty()
    propagate(board)
    for cell in board.iter_cells():
        assert cell.entropy == 9


# ----- contradiction detection -----

def test_propagate_detects_duplicate_in_row():
    board = Board.empty()
    board.cells[0][0].candidates = {5}
    board.cells[0][1].candidates = {5}
    with pytest.raises(ContradictionError):
        propagate(board)


def test_propagate_detects_duplicate_in_col():
    board = Board.empty()
    board.cells[0][0].candidates = {3}
    board.cells[1][0].candidates = {3}
    with pytest.raises(ContradictionError):
        propagate(board)


def test_propagate_detects_duplicate_in_box():
    board = Board.empty()
    board.cells[0][0].candidates = {7}
    board.cells[1][1].candidates = {7}
    with pytest.raises(ContradictionError):
        propagate(board)


# ----- hidden singles -----

def test_hidden_single_in_row():
    board = Board.empty()
    for c in range(9):
        if c != 5:
            board.cells[0][c].candidates.discard(7)
    propagate(board)
    assert board.cells[0][5].value == 7


def test_hidden_single_in_col():
    board = Board.empty()
    for r in range(9):
        if r != 3:
            board.cells[r][2].candidates.discard(4)
    propagate(board)
    assert board.cells[3][2].value == 4


def test_hidden_single_in_box():
    board = Board.empty()
    for r in range(3):
        for c in range(3):
            if (r, c) != (1, 1):
                board.cells[r][c].candidates.discard(9)
    propagate(board)
    assert board.cells[1][1].value == 9


def test_hidden_single_with_no_candidate_is_contradiction():
    board = Board.empty()
    for c in range(9):
        board.cells[0][c].candidates.discard(7)
    with pytest.raises(ContradictionError):
        propagate(board)


# ----- is_consistent -----

def test_is_consistent_on_empty_board():
    assert is_consistent(Board.empty())


def test_is_consistent_on_solved_board():
    assert is_consistent(Board.from_string(SOLVED))


def test_is_consistent_on_easy_puzzle():
    assert is_consistent(Board.from_string(EASY))


def test_is_consistent_detects_duplicate_in_row():
    board = Board.empty()
    board.cells[0][0].candidates = {5}
    board.cells[0][1].candidates = {5}
    assert not is_consistent(board)


def test_is_consistent_detects_duplicate_in_box():
    board = Board.empty()
    board.cells[0][0].candidates = {2}
    board.cells[2][2].candidates = {2}
    assert not is_consistent(board)
