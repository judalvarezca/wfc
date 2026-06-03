from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from wfc.core.events import (
    Backtracked,
    Collapsed,
    Contradiction,
    Event,
    Observed,
    Solved,
)
from wfc.sudoku.board import Board
from wfc.sudoku.constraints import is_consistent
from wfc.sudoku.generator import generate_puzzle
from wfc.sudoku.solver import solve_with_events
from wfc.web.models import (
    BacktrackedEvent,
    CollapsedEvent,
    ContradictionEvent,
    GenerateRequest,
    GenerateResponse,
    ObservedEvent,
    SolvedEvent,
    SolveEvent,
    SolveRequest,
    SolveResponse,
    ValidateResponse,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="WFC Sudoku",
    description="Wave Function Collapse engine, sudoku adapter, web UI.",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/generate", response_model=GenerateResponse)
def api_generate(req: GenerateRequest) -> GenerateResponse:
    board = generate_puzzle(givens=req.givens, seed=req.seed)
    return GenerateResponse(board=board.to_string(), givens=req.givens, seed=req.seed)


@app.post("/api/validate", response_model=ValidateResponse)
def api_validate(req: SolveRequest) -> ValidateResponse:
    try:
        board = Board.from_string(req.board)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    givens = sum(1 for cell in board.iter_cells() if cell.given)
    return ValidateResponse(
        givens=givens,
        consistent=is_consistent(board),
        solved=board.is_solved(),
    )


@app.post("/api/solve", response_model=SolveResponse)
def api_solve(req: SolveRequest) -> SolveResponse:
    try:
        board = Board.from_string(req.board)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    solution, events = solve_with_events(board, seed=req.seed)
    return SolveResponse(
        solution=solution.to_string() if solution is not None else None,
        events=[_serialize_event(e) for e in events],
    )


def _serialize_event(e: Event) -> SolveEvent:
    if isinstance(e, Observed):
        return ObservedEvent(var=e.var)
    if isinstance(e, Collapsed):
        return CollapsedEvent(var=e.var, state=e.state)
    if isinstance(e, Backtracked):
        return BacktrackedEvent(var=e.var, state=e.state, undid_vars=list(e.undid_vars))
    if isinstance(e, Solved):
        return SolvedEvent()
    if isinstance(e, Contradiction):
        return ContradictionEvent()
    raise TypeError(f"unknown event type: {type(e).__name__}")
