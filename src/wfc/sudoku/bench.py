"""Benchmark ResolutionPolicy implementations over a directory of sudoku puzzles.

Used by `wfc bench`. Captures event counts and wall time per (puzzle, policy)
pair and renders a fixed-width table to stdout. Designed for quick comparison,
not rigorous benchmarking — use `--repeat N` for median over N runs if more
stability is needed.
"""
from __future__ import annotations

import logging
import statistics
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from wfc.core.engine import solve as engine_solve
from wfc.core.policy import BacktrackPolicy, ResolutionPolicy, RestartPolicy
from wfc.sudoku.adapter import BoardWave, SudokuConstraint
from wfc.sudoku.parser import from_file

logger = logging.getLogger(__name__)


POLICY_FACTORIES: dict[str, type[ResolutionPolicy]] = {
    "backtrack": BacktrackPolicy,
    "restart": RestartPolicy,
}


@dataclass
class BenchResult:
    puzzle: str
    policy: str
    solved: bool
    time_ms: float
    observed: int
    collapsed: int
    backtracked: int
    restarts: int


def _bench_once(
    board, policy_name: str, policy: ResolutionPolicy, seed: int | None
) -> BenchResult:
    counts: Counter[str] = Counter()

    def sink(e):
        counts[type(e).__name__] += 1

    wave = BoardWave(board.clone())
    t0 = time.perf_counter()
    result = engine_solve(
        wave, [SudokuConstraint()], policy=policy, seed=seed, on_event=sink
    )
    elapsed = (time.perf_counter() - t0) * 1000
    return BenchResult(
        puzzle="",
        policy=policy_name,
        solved=result is not None,
        time_ms=elapsed,
        observed=counts.get("Observed", 0),
        collapsed=counts.get("Collapsed", 0),
        backtracked=counts.get("Backtracked", 0),
        restarts=counts.get("Restarted", 0),
    )


def run(
    directory: Path,
    policy_names: list[str],
    seed: int | None = None,
    repeat: int = 1,
) -> list[BenchResult]:
    """Run every *.txt puzzle in `directory` (non-recursive) against each policy."""
    puzzles = sorted(directory.glob("*.txt"))
    results: list[BenchResult] = []
    for puzzle_path in puzzles:
        board = from_file(puzzle_path)
        for name in policy_names:
            factory = POLICY_FACTORIES[name]
            times: list[float] = []
            last: BenchResult | None = None
            for _ in range(repeat):
                r = _bench_once(board, name, factory(), seed)
                times.append(r.time_ms)
                last = r
            assert last is not None
            last.puzzle = puzzle_path.stem
            last.time_ms = statistics.median(times)
            results.append(last)
    return results


def format_table(results: list[BenchResult]) -> str:
    headers = ["puzzle", "policy", "solved", "time(ms)", "observed", "backtracks", "restarts"]
    rows: list[list[str]] = []
    for r in results:
        rows.append(
            [
                r.puzzle,
                r.policy,
                "yes" if r.solved else "no",
                f"{r.time_ms:.2f}",
                str(r.observed),
                str(r.backtracked) if r.policy == "backtrack" else "-",
                str(r.restarts) if r.policy == "restart" else "-",
            ]
        )
    widths = [
        max(len(h), max((len(row[i]) for row in rows), default=0))
        for i, h in enumerate(headers)
    ]
    sep = "  "
    lines = [sep.join(h.ljust(w) for h, w in zip(headers, widths, strict=False))]
    lines.append(sep.join("-" * w for w in widths))
    for row in rows:
        lines.append(sep.join(c.ljust(w) for c, w in zip(row, widths, strict=False)))
    return "\n".join(lines)
