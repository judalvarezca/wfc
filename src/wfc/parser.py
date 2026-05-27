from __future__ import annotations

from pathlib import Path

from wfc.board import Board


def from_file(path: str | Path) -> Board:
    return Board.from_string(Path(path).read_text())
