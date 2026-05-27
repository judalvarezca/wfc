from wfc.cli import main

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


def test_no_args_prints_help(capsys):
    exit_code = main([])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Wave Function Collapse" in captured.out


def test_show_from_string(capsys):
    exit_code = main(["show", EASY])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "5 3 . | . 7 ." in captured.out
    assert "------+-------+------" in captured.out


def test_show_from_file(tmp_path, capsys):
    p = tmp_path / "puzzle.txt"
    p.write_text(EASY)
    exit_code = main(["show", str(p)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "5 3 . | . 7 ." in captured.out


def test_show_from_stdin(monkeypatch, capsys):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(EASY))
    exit_code = main(["show", "-"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "5 3 . | . 7 ." in captured.out


def test_pipeline_show_output_into_validate(monkeypatch, capsys):
    """The formatted output of `show` should be re-parsable by `validate` via stdin."""
    import io

    main(["show", EASY])
    formatted = capsys.readouterr().out
    monkeypatch.setattr("sys.stdin", io.StringIO(formatted))
    exit_code = main(["validate", "-"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Givens: 30/81" in captured.out


def test_show_invalid_input_returns_error(capsys):
    exit_code = main(["show", "garbage"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "error" in captured.err.lower()


def test_validate_reports_givens(tmp_path, capsys):
    p = tmp_path / "puzzle.txt"
    p.write_text(EASY)
    exit_code = main(["validate", str(p)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Givens: 30/81" in captured.out
    assert "Consistent: True" in captured.out
    assert "Solved: False" in captured.out


def test_solve_is_stubbed(capsys):
    exit_code = main(["solve", EASY])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "not implemented" in captured.err.lower()


def test_generate_full_board_formatted(capsys):
    exit_code = main(["generate", "--seed", "42"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "------+-------+------" in captured.out


def test_generate_raw_is_81_chars(capsys):
    exit_code = main(["generate", "--seed", "42", "--raw"])
    captured = capsys.readouterr()
    assert exit_code == 0
    output = captured.out.strip()
    assert len(output) == 81
    assert all(c in "123456789" for c in output)


def test_generate_puzzle_has_correct_givens(capsys):
    exit_code = main(["generate", "--givens", "30", "--seed", "42", "--raw"])
    captured = capsys.readouterr()
    assert exit_code == 0
    output = captured.out.strip()
    assert len(output) == 81
    givens = sum(1 for c in output if c in "123456789")
    assert givens == 30


def test_generate_invalid_givens(capsys):
    exit_code = main(["generate", "--givens", "100"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "error" in captured.err.lower()


def test_generate_save_explicit_path(tmp_path, capsys):
    out = tmp_path / "sub" / "puzzle.txt"
    exit_code = main(["generate", "--seed", "42", "--save", str(out)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert out.exists()
    assert f"Saved to {out}" in captured.out


def test_generate_save_creates_parent_dirs(tmp_path):
    out = tmp_path / "a" / "b" / "c" / "p.txt"
    exit_code = main(["generate", "--seed", "42", "--save", str(out)])
    assert exit_code == 0
    assert out.exists()


def test_generate_save_file_is_9_lines(tmp_path):
    out = tmp_path / "p.txt"
    main(["generate", "--seed", "42", "--save", str(out)])
    lines = [ln for ln in out.read_text().split("\n") if ln]
    assert len(lines) == 9
    assert all(len(ln) == 9 for ln in lines)


def test_generate_saved_file_roundtrips(tmp_path):
    from wfc.generator import generate_puzzle
    from wfc.parser import from_file

    out = tmp_path / "p.txt"
    main(["generate", "--seed", "42", "--givens", "30", "--save", str(out)])
    loaded = from_file(out)
    expected = generate_puzzle(givens=30, seed=42)
    assert loaded.to_string() == expected.to_string()


def test_generate_save_auto_path(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    exit_code = main(["generate", "--givens", "30", "--seed", "42", "--save"])
    captured = capsys.readouterr()
    assert exit_code == 0
    expected = tmp_path / "examples" / "generated" / "puzzle_givens30_seed42.txt"
    assert expected.exists()
    assert "Saved to" in captured.out


def test_default_no_logs_to_stderr(capsys):
    main(["generate", "--seed", "42", "--raw"])
    captured = capsys.readouterr()
    assert "[INFO]" not in captured.err
    assert "[DEBUG]" not in captured.err


def test_verbose_emits_info_logs(capsys):
    main(["-v", "generate", "--seed", "42", "--raw"])
    captured = capsys.readouterr()
    assert "[INFO]" in captured.err
    assert "generate_solved" in captured.err
    assert "[DEBUG]" not in captured.err


def test_very_verbose_emits_debug_logs(capsys):
    main(["-vv", "generate", "--seed", "42", "--raw"])
    captured = capsys.readouterr()
    assert "[INFO]" in captured.err
    assert "[DEBUG]" in captured.err


def test_verbose_validate_logs_propagation(monkeypatch, capsys):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(EASY))
    main(["-v", "validate", "-"])
    captured = capsys.readouterr()
    assert "[INFO]" in captured.err
    assert "validate" in captured.err
