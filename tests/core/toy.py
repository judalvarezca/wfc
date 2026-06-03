"""Tiny non-sudoku Wave/Constraint pair used in engine tests.

Proves the core engine works without depending on the sudoku adapter — any
future adapter (tiles, dungeons) is expected to plug in the same way.
"""
from __future__ import annotations

from collections.abc import Iterable, Iterator

from wfc.core.exceptions import ContradictionError
from wfc.core.wave import Wave


class ToyWave:
    """N integer variables with set[int] domains. Identified by their index."""

    def __init__(self, domains: list[set[int]]) -> None:
        self._domains = [set(d) for d in domains]

    def variables(self) -> Iterator[int]:
        yield from range(len(self._domains))

    def uncollapsed(self) -> Iterator[int]:
        for i, d in enumerate(self._domains):
            if len(d) > 1:
                yield i

    def domain(self, var: int) -> set[int]:
        return set(self._domains[var])

    def is_collapsed(self, var: int) -> bool:
        return len(self._domains[var]) == 1

    def value(self, var: int) -> int:
        if not self.is_collapsed(var):
            raise ValueError(f"variable {var} is not collapsed")
        return next(iter(self._domains[var]))

    def entropy(self, var: int) -> int:
        return len(self._domains[var])

    def collapse(self, var: int, state: int) -> None:
        if state not in self._domains[var]:
            raise ContradictionError(f"{state} not in domain of var {var}")
        self._domains[var] = {state}

    def eliminate(self, var: int, state: int) -> bool:
        if state not in self._domains[var]:
            return False
        self._domains[var].discard(state)
        if not self._domains[var]:
            raise ContradictionError(f"var {var} has empty domain")
        return True

    def is_fully_collapsed(self) -> bool:
        return all(len(d) == 1 for d in self._domains)

    def clone(self) -> ToyWave:
        return ToyWave([set(d) for d in self._domains])

    def values(self) -> list[int]:
        """Convenience for assertions: list of single values when fully collapsed."""
        return [next(iter(d)) for d in self._domains]


class AllDifferentConstraint:
    """Every variable in the wave must take a distinct value."""

    def propagate(
        self, wave: Wave, seed: Iterable[int] | None = None
    ) -> set[int]:
        before = {v for v in wave.variables() if wave.is_collapsed(v)}
        changed = True
        while changed:
            changed = False
            for var in list(wave.variables()):
                if not wave.is_collapsed(var):
                    continue
                value = wave.value(var)
                for other in wave.variables():
                    if other == var:
                        continue
                    if wave.eliminate(other, value):
                        changed = True
        after = {v for v in wave.variables() if wave.is_collapsed(v)}
        return after - before
