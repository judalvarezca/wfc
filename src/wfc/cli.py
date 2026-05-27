from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from wfc.board import Board
from wfc.constraints import is_consistent
from wfc.generator import generate_puzzle
from wfc.parser import from_file

logger = logging.getLogger(__name__)

_AUTO_SAVE = "__AUTO__"
_AUTO_SAVE_DIR = Path("examples/generated")


def _configure_logging(verbosity: int) -> None:
    if verbosity == 0:
        level = logging.WARNING
    elif verbosity == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG
    pkg_logger = logging.getLogger("wfc")
    pkg_logger.setLevel(level)
    for h in list(pkg_logger.handlers):
        pkg_logger.removeHandler(h)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    pkg_logger.addHandler(handler)


def _load_board(source: str) -> Board:
    if source == "-":
        return Board.from_string(sys.stdin.read())
    path = Path(source)
    if path.exists() and path.is_file():
        return from_file(path)
    return Board.from_string(source)


def cmd_show(args: argparse.Namespace) -> int:
    try:
        board = _load_board(args.input)
    except (ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    givens = sum(1 for cell in board.iter_cells() if cell.given)
    logger.info("show: loaded board with %d givens", givens)
    print(board)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        board = _load_board(args.input)
    except (ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    givens = sum(1 for cell in board.iter_cells() if cell.given)
    consistent = is_consistent(board)
    solved = board.is_solved()
    logger.info("validate: givens=%d, consistent=%s, solved=%s", givens, consistent, solved)
    print(f"Givens: {givens}/81")
    print(f"Consistent: {consistent}")
    print(f"Solved: {solved}")
    return 0


def _auto_save_path(givens: int, seed: int | None) -> Path:
    if seed is not None:
        name = f"puzzle_givens{givens}_seed{seed}.txt"
    else:
        name = f"puzzle_givens{givens}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    return _AUTO_SAVE_DIR / name


def _board_to_file_text(board: Board) -> str:
    s = board.to_string()
    return "\n".join(s[i : i + 9] for i in range(0, 81, 9)) + "\n"


def cmd_generate(args: argparse.Namespace) -> int:
    try:
        board = generate_puzzle(givens=args.givens, seed=args.seed)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.save is not None:
        path = (
            _auto_save_path(args.givens, args.seed)
            if args.save == _AUTO_SAVE
            else Path(args.save)
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_board_to_file_text(board))
        logger.info("generate: saved to %s", path)
        print(f"Saved to {path}")
        return 0

    if args.raw:
        print(board.to_string())
    else:
        print(board)
    return 0


def cmd_not_implemented(args: argparse.Namespace) -> int:
    print(f"[wfc] command '{args.command}' is not implemented yet.", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wfc",
        description="Wave Function Collapse solver for Sudoku.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity: -v (INFO), -vv (DEBUG step-by-step). Logs to stderr.",
    )
    sub = parser.add_subparsers(dest="command")

    input_help = "Path to a board file, an 81-char string, or '-' for stdin."

    show = sub.add_parser("show", help="Load a board and print it.")
    show.add_argument("input", help=input_help)
    show.set_defaults(func=cmd_show)

    validate = sub.add_parser("validate", help="Load a board and report basic status.")
    validate.add_argument("input", help=input_help)
    validate.set_defaults(func=cmd_validate)

    generate = sub.add_parser("generate", help="Generate a random valid sudoku board.")
    generate.add_argument(
        "--givens",
        type=int,
        default=81,
        help="Number of given cells, 0-81 (default: 81 = full solved board).",
    )
    generate.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility.")
    generate.add_argument(
        "--raw", action="store_true", help="Output as 81-char string instead of formatted grid."
    )
    generate.add_argument(
        "--save",
        nargs="?",
        const=_AUTO_SAVE,
        default=None,
        metavar="PATH",
        help=(
            "Save the board to PATH (9-line format, parent dirs auto-created). "
            "With no PATH, auto-names inside examples/generated/."
        ),
    )
    generate.set_defaults(func=cmd_generate)

    solve = sub.add_parser("solve", help="Solve a sudoku puzzle (not implemented yet).")
    solve.add_argument("input", help=input_help)
    solve.add_argument("--render", metavar="PATH", help="Render the solution to an image file.")
    solve.add_argument("--animate", metavar="PATH", help="Animate the solving process.")
    solve.add_argument("--seed", type=int, default=None, help="Random seed for determinism.")
    solve.set_defaults(func=cmd_not_implemented)

    bench = sub.add_parser("bench", help="Benchmark the solver (not implemented yet).")
    bench.add_argument("dir", help="Directory containing puzzle files.")
    bench.set_defaults(func=cmd_not_implemented)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    if args.command is None:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
