from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BoardInput(BaseModel):
    """An 81-character sudoku board (digits 1-9 for givens, '0' or '.' for empty).

    Whitespace and separators ('|', '+', '-') are stripped before parsing.
    """

    board: str = Field(min_length=1, description="Sudoku board as a string")


class GenerateRequest(BaseModel):
    givens: int = Field(default=30, ge=0, le=81)
    seed: int | None = None


class GenerateResponse(BaseModel):
    board: str = Field(description="81-character board string (0 for empty cells)")
    givens: int
    seed: int | None


class ValidateResponse(BaseModel):
    givens: int
    consistent: bool
    solved: bool


class ObservedEvent(BaseModel):
    type: Literal["Observed"] = "Observed"
    var: tuple[int, int]


class CollapsedEvent(BaseModel):
    type: Literal["Collapsed"] = "Collapsed"
    var: tuple[int, int]
    state: int


class BacktrackedEvent(BaseModel):
    type: Literal["Backtracked"] = "Backtracked"
    var: tuple[int, int]
    state: int
    undid_vars: list[tuple[int, int]]


class RestartedEvent(BaseModel):
    type: Literal["Restarted"] = "Restarted"
    attempt: int
    undid_vars: list[tuple[int, int]]


class SolvedEvent(BaseModel):
    type: Literal["Solved"] = "Solved"


class ContradictionEvent(BaseModel):
    type: Literal["Contradiction"] = "Contradiction"


SolveEvent = (
    ObservedEvent
    | CollapsedEvent
    | BacktrackedEvent
    | RestartedEvent
    | SolvedEvent
    | ContradictionEvent
)


class SolveRequest(BaseModel):
    board: str = Field(min_length=1)
    seed: int | None = None


class SolveResponse(BaseModel):
    solution: str | None = Field(
        description="81-char solved board, or null if unsolvable"
    )
    events: list[SolveEvent]
