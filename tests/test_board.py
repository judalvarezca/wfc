import pytest

from wfc.board import ALL_VALUES, Board, Cell
from wfc.parser import from_file

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


def test_empty_cell_has_all_candidates():
    cell = Cell()
    assert cell.candidates == ALL_VALUES
    assert cell.entropy == 9
    assert not cell.collapsed
    assert cell.value is None
    assert not cell.given


def test_given_cell_is_collapsed():
    cell = Cell(candidates={5}, given=True)
    assert cell.collapsed
    assert cell.value == 5
    assert cell.given
    assert cell.entropy == 1


def test_default_candidates_are_independent():
    c1 = Cell()
    c2 = Cell()
    c1.candidates.discard(5)
    assert 5 in c2.candidates


def test_board_dimensions():
    board = Board.empty()
    assert len(board.cells) == 9
    assert all(len(row) == 9 for row in board.cells)


def test_from_string_accepts_zeros():
    board = Board.from_string(EASY)
    assert board.cells[0][0].value == 5
    assert board.cells[0][0].given
    assert not board.cells[0][2].collapsed


def test_from_string_accepts_dots():
    s = EASY.replace("0", ".")
    board = Board.from_string(s)
    assert board.cells[0][0].value == 5
    assert not board.cells[0][2].collapsed


def test_from_string_ignores_whitespace():
    formatted = "\n".join(EASY[i : i + 9] for i in range(0, 81, 9))
    board = Board.from_string(formatted)
    assert board.to_string() == EASY


def test_from_string_strips_grid_separators():
    pretty = (
        "5 3 . | . 7 . | . . .\n"
        "6 . . | 1 9 5 | . . .\n"
        ". 9 8 | . . . | . 6 .\n"
        "------+-------+------\n"
        "8 . . | . 6 . | . . 3\n"
        "4 . . | 8 . 3 | . . 1\n"
        "7 . . | . 2 . | . . 6\n"
        "------+-------+------\n"
        ". 6 . | . . . | 2 8 .\n"
        ". . . | 4 1 9 | . . 5\n"
        ". . . | . 8 . | . 7 9\n"
    )
    board = Board.from_string(pretty)
    assert board.to_string() == EASY


def test_str_output_round_trips_back_to_board():
    board = Board.from_string(EASY)
    reparsed = Board.from_string(str(board))
    assert reparsed.to_string() == EASY


def test_from_string_rejects_wrong_length():
    with pytest.raises(ValueError, match="81"):
        Board.from_string("123")


def test_from_string_rejects_invalid_char():
    bad = "X" + "0" * 80
    with pytest.raises(ValueError, match="Invalid character"):
        Board.from_string(bad)


def test_round_trip_string():
    board = Board.from_string(EASY)
    assert board.to_string() == EASY


def test_to_string_has_length_81():
    board = Board.from_string(EASY)
    assert len(board.to_string()) == 81


def test_is_solved_false_when_unsolved():
    board = Board.from_string(EASY)
    assert not board.is_solved()


def test_is_solved_true_when_complete():
    board = Board.from_string(SOLVED)
    assert board.is_solved()


def test_is_solved_false_when_complete_but_duplicate():
    # Change cell (0,0) from 5 to 1 -- creates duplicate '1' in row 0
    bad = "1" + SOLVED[1:]
    board = Board.from_string(bad)
    assert not board.is_solved()


def test_clone_is_independent():
    board = Board.from_string(EASY)
    cloned = board.clone()
    cloned.cells[0][2].candidates.discard(5)
    assert 5 in board.cells[0][2].candidates
    assert 5 not in cloned.cells[0][2].candidates


def test_clone_preserves_given_flag():
    board = Board.from_string(EASY)
    cloned = board.clone()
    assert cloned.cells[0][0].given
    assert not cloned.cells[0][2].given


def test_entropy_reflects_candidate_count():
    board = Board.from_string(EASY)
    assert board.entropy(0, 2) == 9  # empty cell at (0,2)
    assert board.entropy(0, 0) == 1  # given '5' at (0,0)


def test_units_count():
    board = Board.empty()
    units = list(board.iter_units())
    assert len(units) == 27  # 9 rows + 9 cols + 9 boxes


def test_box_cells_returns_correct_cells():
    board = Board.from_string(SOLVED)
    # Box 0 = top-left 3x3
    box0_values = [cell.value for cell in board.box_cells(0)]
    assert box0_values == [5, 3, 4, 6, 7, 2, 1, 9, 8]


def test_str_renders_grid():
    board = Board.from_string(SOLVED)
    output = str(board)
    assert "5 3 4 | 6 7 8 | 9 1 2" in output  # first row
    assert "------+-------+------" in output


def test_from_file_reads_board(tmp_path):
    p = tmp_path / "puzzle.txt"
    p.write_text("\n".join(EASY[i : i + 9] for i in range(0, 81, 9)))
    board = from_file(p)
    assert board.to_string() == EASY
