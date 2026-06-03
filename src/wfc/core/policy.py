from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from wfc.core.constraint import Constraint
from wfc.core.events import (
    Backtracked,
    Collapsed,
    Contradiction,
    EventSink,
    Observed,
    Solved,
)
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
        on_event: EventSink | None = None,
    ) -> Wave | None:
        """Drive search until `wave` is fully collapsed, or return None.

        Implementations must not mutate the caller's `wave`; clone first.
        """
        ...


def _propagate_to_fixpoint(
    wave: Wave,
    constraints: Iterable[Constraint],
    seed: Iterable[VarId] | None,
    on_event: EventSink | None = None,
) -> set[VarId]:
    """Apply every constraint in a loop until no constraint reports changes.

    Returns the union of all vars collapsed during propagation (across the
    full fixed-point loop, all constraints).
    """
    constraints = list(constraints)
    current_seed: Iterable[VarId] | None = seed
    all_collapses: set[VarId] = set()
    while True:
        any_change = False
        new_collapses: set[VarId] = set()
        for c in constraints:
            collapsed = c.propagate(wave, seed=current_seed, on_event=on_event)
            if collapsed:
                any_change = True
                new_collapses |= collapsed
        if not any_change:
            return all_collapses
        all_collapses |= new_collapses
        current_seed = new_collapses


class BacktrackPolicy:
    """Search by depth-first backtracking on contradiction.

    On each step: pick a variable (selector), iterate its candidates (sampler),
    clone+collapse+propagate; recurse. On ContradictionError, try the next
    candidate. If none works, return None to backtrack.

    Event semantics: emits `Observed` on each variable selection; `Collapsed`
    for both the direct collapse and every propagation-induced collapse under
    it; `Backtracked` (with the full list of `undid_vars` for that branch)
    when the branch fails or the deeper search returns no solution.
    """

    def solve(
        self,
        wave: Wave,
        constraints: Iterable[Constraint],
        selector: CellSelector,
        sampler: ValueSampler,
        on_event: EventSink | None = None,
    ) -> Wave | None:
        constraints = list(constraints)
        root = wave.clone()
        try:
            initial_seed = [v for v in root.variables() if root.is_collapsed(v)]
            _propagate_to_fixpoint(
                root, constraints, seed=initial_seed or None, on_event=on_event
            )
        except ContradictionError:
            logger.info("backtrack: initial state is contradictory")
            if on_event is not None:
                on_event(Contradiction())
            return None
        result = self._search(root, constraints, selector, sampler, on_event, depth=0)
        if result is not None and on_event is not None:
            on_event(Solved())
        return result

    def _search(
        self,
        wave: Wave,
        constraints: list[Constraint],
        selector: CellSelector,
        sampler: ValueSampler,
        on_event: EventSink | None,
        depth: int,
    ) -> Wave | None:
        if wave.is_fully_collapsed():
            logger.info("backtrack: solved at depth %d", depth)
            return wave
        var = selector.select(wave)
        logger.debug("backtrack[d=%d]: selected %s (entropy=%d)", depth, var, wave.entropy(var))
        if on_event is not None:
            on_event(Observed(var))
        for value in sampler.order(wave, var):
            child = wave.clone()
            branch_collapses: list[VarId] = [var]
            try:
                child.collapse(var, value)
                if on_event is not None:
                    on_event(Collapsed(var, value))
                propagated = _propagate_to_fixpoint(
                    child, constraints, seed=[var], on_event=on_event
                )
                branch_collapses.extend(propagated)
            except ContradictionError:
                logger.debug("backtrack[d=%d]: %s=%s → contradiction", depth, var, value)
                if on_event is not None:
                    on_event(
                        Backtracked(var=var, state=value, undid_vars=tuple(branch_collapses))
                    )
                continue
            result = self._search(child, constraints, selector, sampler, on_event, depth + 1)
            if result is not None:
                return result
            logger.debug("backtrack[d=%d]: %s=%s failed deeper, trying next", depth, var, value)
            if on_event is not None:
                on_event(
                    Backtracked(var=var, state=value, undid_vars=tuple(branch_collapses))
                )
        return None
