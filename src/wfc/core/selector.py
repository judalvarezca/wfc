from __future__ import annotations

import random
from typing import Protocol, runtime_checkable

from wfc.core.wave import VarId, Wave


@runtime_checkable
class CellSelector(Protocol):
    """Picks the next variable to collapse during search."""

    def select(self, wave: Wave) -> VarId:
        """Return the id of the variable to collapse next.

        Precondition: at least one variable is uncollapsed.
        """
        ...


class LowestEntropySelector:
    """Pick the uncollapsed variable with the smallest domain (MRV).

    This is the canonical WFC "observation" rule — generalized from Maxim
    Gumin's lowest-entropy heuristic. Equivalent to Minimum Remaining Values
    (MRV) in CSP literature when all states are equally likely.

    Ties are broken by the natural order of the var_id (typically a tuple), so
    results are deterministic when var_ids are comparable. Pass an `rng` to
    break ties randomly instead.
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng

    def select(self, wave: Wave) -> VarId:
        best_entropy: int | None = None
        tied: list[VarId] = []
        for var in wave.uncollapsed():
            e = wave.entropy(var)
            if best_entropy is None or e < best_entropy:
                best_entropy = e
                tied = [var]
            elif e == best_entropy:
                tied.append(var)
        if best_entropy is None:
            raise ValueError("no uncollapsed variables to select")
        if self._rng is not None and len(tied) > 1:
            return self._rng.choice(tied)
        return min(tied)
