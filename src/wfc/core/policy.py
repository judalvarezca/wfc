from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from wfc.core.constraint import Constraint
from wfc.core.exceptions import ContradictionError
from wfc.core.sampler import ValueSampler
from wfc.core.selector import CellSelector
from wfc.core.wave import VarId, Wave

logger = logging.getLogger(__name__)


@runtime_checkable
class ResolutionPolicy(Protocol):
    """Drives the search loop. Defines what to do on contradiction."""

    def solve(
        self,
        wave: Wave,
        constraints: Iterable[Constraint],
        selector: CellSelector,
        sampler: ValueSampler,
    ) -> Wave | None:
        """Drive search until `wave` is fully collapsed, or return None.

        Implementations must not mutate the caller's `wave`; clone first.
        """
        ...


def _propagate_to_fixpoint(
    wave: Wave,
    constraints: Iterable[Constraint],
    seed: Iterable[VarId] | None,
) -> None:
    """Apply every constraint in a loop until no constraint reports changes.

    Each constraint handles its own internal fixed point; this driver handles
    the outer fixed point when multiple constraints interact.
    """
    constraints = list(constraints)
    current_seed: Iterable[VarId] | None = seed
    while True:
        any_change = False
        new_collapses: set[VarId] = set()
        for c in constraints:
            collapsed = c.propagate(wave, seed=current_seed)
            if collapsed:
                any_change = True
                new_collapses |= collapsed
        if not any_change:
            return
        current_seed = new_collapses


class BacktrackPolicy:
    """Search by depth-first backtracking on contradiction.

    On each step: pick a variable (selector), iterate its candidates (sampler),
    clone+collapse+propagate; recurse. On ContradictionError, try the next
    candidate. If none works, return None to backtrack.

    The original WFC algorithm uses restart instead — see RestartPolicy in 3c.
    Backtracking is preferred when solutions are sparse (e.g. sudoku); restart
    is preferred when many solutions exist and contradictions are rare but
    expensive to undo (e.g. tile generation).
    """

    def solve(
        self,
        wave: Wave,
        constraints: Iterable[Constraint],
        selector: CellSelector,
        sampler: ValueSampler,
    ) -> Wave | None:
        constraints = list(constraints)
        root = wave.clone()
        try:
            initial_seed = [v for v in root.variables() if root.is_collapsed(v)]
            _propagate_to_fixpoint(root, constraints, seed=initial_seed or None)
        except ContradictionError:
            logger.info("backtrack: initial state is contradictory")
            return None
        return self._search(root, constraints, selector, sampler, depth=0)

    def _search(
        self,
        wave: Wave,
        constraints: list[Constraint],
        selector: CellSelector,
        sampler: ValueSampler,
        depth: int,
    ) -> Wave | None:
        if wave.is_fully_collapsed():
            logger.info("backtrack: solved at depth %d", depth)
            return wave
        var = selector.select(wave)
        logger.debug("backtrack[d=%d]: selected %s (entropy=%d)", depth, var, wave.entropy(var))
        for value in sampler.order(wave, var):
            child = wave.clone()
            try:
                child.collapse(var, value)
                _propagate_to_fixpoint(child, constraints, seed=[var])
            except ContradictionError:
                logger.debug("backtrack[d=%d]: %s=%s → contradiction", depth, var, value)
                continue
            result = self._search(child, constraints, selector, sampler, depth + 1)
            if result is not None:
                return result
            logger.debug("backtrack[d=%d]: %s=%s failed deeper, trying next", depth, var, value)
        return None
