from pathlib import Path

import pytest

from wfc.cli import main
from wfc.sudoku.bench import format_table, run

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def test_run_solves_easy_with_both_policies():
    results = run(EXAMPLES, ["backtrack", "restart"], seed=0, repeat=1)
    # 3 puzzles × 2 policies = 6 results
    assert len(results) == 6
    by_puzzle = {(r.puzzle, r.policy): r for r in results}
    for name in ("easy", "medium", "hard"):
        assert by_puzzle[(name, "backtrack")].solved
        assert by_puzzle[(name, "restart")].solved


def test_run_only_backtrack():
    results = run(EXAMPLES, ["backtrack"], seed=0, repeat=1)
    assert len(results) == 3  # one per puzzle, only backtrack
    assert all(r.policy == "backtrack" for r in results)


def test_run_empty_directory(tmp_path):
    results = run(tmp_path, ["backtrack"], seed=0, repeat=1)
    assert results == []


def test_format_table_headers_and_separators():
    results = run(EXAMPLES, ["backtrack"], seed=0, repeat=1)
    table = format_table(results)
    lines = table.splitlines()
    assert "puzzle" in lines[0]
    assert "policy" in lines[0]
    assert "time(ms)" in lines[0]
    assert "backtracks" in lines[0]
    assert "restarts" in lines[0]
    # Separator row of dashes
    assert all(ch in "- " for ch in lines[1])
    # One row per puzzle
    assert len(lines) == 2 + len(results)


def test_bench_event_counts_match_policy():
    """Backtrack policy never emits Restarted; restart never emits Backtracked."""
    results = run(EXAMPLES, ["backtrack", "restart"], seed=42, repeat=1)
    for r in results:
        if r.policy == "backtrack":
            assert r.restarts == 0
        elif r.policy == "restart":
            assert r.backtracked == 0


def test_cli_bench_smoke(capsys):
    exit_code = main(["bench", str(EXAMPLES), "--seed", "0", "--repeat", "1"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "puzzle" in out
    assert "backtrack" in out
    assert "restart" in out


def test_cli_bench_policy_filter(capsys):
    exit_code = main([
        "bench", str(EXAMPLES), "--seed", "0", "--repeat", "1", "--policy", "backtrack",
    ])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "backtrack" in out
    # No 'restart' row should appear (only the word inside the column header
    # 'restarts' would match — but we filter by checking individual lines).
    rows = [line for line in out.splitlines() if line and not line.startswith(("puzzle", "-"))]
    assert all("restart " not in row for row in rows)


def test_cli_bench_invalid_directory(tmp_path, capsys):
    nonexistent = tmp_path / "does_not_exist"
    exit_code = main(["bench", str(nonexistent)])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "not a directory" in captured.err


@pytest.mark.parametrize("policy", ["backtrack", "restart"])
def test_bench_collapsed_count_matches_givens(policy):
    """For a fully-solved puzzle the number of Collapsed events should equal
    the number of non-given cells (81 - givens). Sanity check that our event
    stream is complete."""
    from wfc.sudoku.parser import from_file

    board = from_file(EXAMPLES / "easy.txt")
    givens = sum(1 for cell in board.iter_cells() if cell.given)
    results = run(EXAMPLES, [policy], seed=0, repeat=1)
    easy = next(r for r in results if r.puzzle == "easy")
    # restart may collapse more (failed-and-retried cells emit Collapsed each
    # time before being undone), so just sanity-check minimum.
    assert easy.collapsed >= 81 - givens
