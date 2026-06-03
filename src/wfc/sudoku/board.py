from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

SIZE = 9
BOX = 3
ALL_VALUES: frozenset[int] = frozenset(range(1, 10))
_IGNORED_CHARS: frozenset[str] = frozenset(" \n\r\t|+-")


@dataclass
class Cell:
    candidates: set[int] = field(default_factory=lambda: set(ALL_VALUES))
    given: bool = False

    @property
    def collapsed(self) -> bool:
        return len(self.candidates) == 1

    @property
    def value(self) -> int | None:
        if self.collapsed:
            return next(iter(self.candidates))
        return None

    @property
    def entropy(self) -> int:
        return len(self.candidates)


@dataclass
class Board:
    cells: list[list[Cell]]

    @classmethod
    def empty(cls) -> Board:
        return cls(cells=[[Cell() for _ in range(SIZE)] for _ in range(SIZE)])

    @classmethod
    def from_string(cls, s: str) -> Board:
        normalized = "".join(ch for ch in s if ch not in _IGNORED_CHARS)
        if len(normalized) != SIZE * SIZE:
            raise ValueError(
                f"Board string must have 81 cell characters, got {len(normalized)}"
            )
        cells: list[list[Cell]] = []
        for r in range(SIZE):
            row: list[Cell] = []
            for c in range(SIZE):
                ch = normalized[r * SIZE + c]
                if ch in "0.":
                    row.append(Cell())
                elif ch in "123456789":
                    row.append(Cell(candidates={int(ch)}, given=True))
                else:
                    raise ValueError(f"Invalid character {ch!r} at row {r}, col {c}")
            cells.append(row)
        return cls(cells=cells)

    def to_string(self) -> str:
        chars: list[str] = []
        for row in self.cells:
            for cell in row:
                chars.append(str(cell.value) if cell.collapsed else "0")
        return "".join(chars)

    def clone(self) -> Board:
        return Board(
            cells=[
                [Cell(set(cell.candidates), cell.given) for cell in row] for row in self.cells
            ]
        )

    def entropy(self, r: int, c: int) -> int:
        return self.cells[r][c].entropy

    def iter_cells(self) -> Iterator[Cell]:
        for row in self.cells:
            yield from row

    def row_cells(self, r: int) -> list[Cell]:
        return list(self.cells[r])

    def col_cells(self, c: int) -> list[Cell]:
        return [self.cells[r][c] for r in range(SIZE)]

    def box_cells(self, b: int) -> list[Cell]:
        br, bc = divmod(b, BOX)
        return [
            self.cells[br * BOX + dr][bc * BOX + dc] for dr in range(BOX) for dc in range(BOX)
        ]

    def iter_units(self) -> Iterator[list[Cell]]:
        for r in range(SIZE):
            yield self.row_cells(r)
        for c in range(SIZE):
            yield self.col_cells(c)
        for b in range(SIZE):
            yield self.box_cells(b)

    def is_solved(self) -> bool:
        return all(
            {cell.value for cell in unit} == ALL_VALUES for unit in self.iter_units()
        )

    def __str__(self) -> str:
        sep = "------+-------+------"
        lines: list[str] = []
        for r in range(SIZE):
            chars = [str(cell.value) if cell.collapsed else "." for cell in self.cells[r]]
            line = (
                " ".join(chars[0:3])
                + " | "
                + " ".join(chars[3:6])
                + " | "
                + " ".join(chars[6:9])
            )
            lines.append(line)
            if r in (2, 5):
                lines.append(sep)
        return "\n".join(lines)
