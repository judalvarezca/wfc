from __future__ import annotations

import random
from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from wfc.core.wave import State, VarId, Wave


@runtime_checkable
class ValueSampler(Protocol):
    """Yields the states to try for a variable, in order."""

    def order(self, wave: Wave, var: VarId) -> Iterator[State]:
        """Yield states from `var`'s current domain in the order to try them."""
        ...


class UniformSampler:
    """Uniform sampling over the current domain.

    Without an rng: yields states in their natural sorted order (deterministic).
    With an rng: yields a random permutation (uniformly sampled).

    Future extensions: WeightedSampler (states with non-uniform priors, useful
    for tile generation), LCV (least-constraining-value, sudoku-specific).
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng

    def order(self, wave: Wave, var: VarId) -> Iterator[State]:
        states = list(wave.domain(var))
        if self._rng is None:
            states.sort()
        else:
            self._rng.shuffle(states)
        yield from states
