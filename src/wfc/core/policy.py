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
    Restarted,
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


def _make_tracker(
    on_event: EventSink | None, collected: list[VarId]
) -> EventSink:
    """Wrap `on_event` so every `Collapsed` event also appends to `collected`.

    Necessary because propagation can emit `Collapsed` events and then raise
    `ContradictionError`. Without this, the cells collapsed mid-propagation
    wouldn't make it into the failing branch's undid_vars, leaving stale cells
    in the UI after backtrack/restart.
    """

    def track(e):
        if isinstance(e, Collapsed):
            collected.append(e.var)
        if on_event is not None:
            on_event(e)

    return track


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
            branch_collapses: list[VarId] = []
            tracker = _make_tracker(on_event, branch_collapses)
            try:
                child.collapse(var, value)
                tracker(Collapsed(var, value))
                _propagate_to_fixpoint(child, constraints, seed=[var], on_event=tracker)
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


class RestartPolicy:
    """Search by greedy collapse + restart on contradiction.

    This is the classical WFC algorithm (Maxim Gumin, 2016): on each step,
    observe the lowest-entropy variable, sample a value, propagate; if
    propagation ever contradicts, *throw away the whole attempt* and start
    over from the post-initial-propagation root. The selector/sampler's
    shared rng advances between attempts so different paths are explored.

    Restart is preferred over backtracking when solutions are abundant and
    rejections are "deep" — typical for tile/dungeon generation. For sudoku
    (sparse solutions) backtracking usually wins; this policy is included
    primarily so `wfc bench` can compare them.

    `max_attempts` bounds the loop so unsolvable puzzles don't hang. The
    initial propagation still detects obvious contradictions in 0 attempts.
    """

    def __init__(self, max_attempts: int = 200) -> None:
        self.max_attempts = max_attempts

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
            logger.info("restart: initial state is contradictory")
            if on_event is not None:
                on_event(Contradiction())
            return None

        for attempt in range(1, self.max_attempts + 1):
            logger.debug("restart: attempt %d/%d", attempt, self.max_attempts)
            wave_attempt = root.clone()
            collapsed_this_attempt: list[VarId] = []
            result = self._greedy_fill(
                wave_attempt,
                constraints,
                selector,
                sampler,
                on_event,
                collapsed_this_attempt,
            )
            if result is not None:
                logger.info("restart: solved on attempt %d", attempt)
                if on_event is not None:
                    on_event(Solved())
                return result
            if on_event is not None:
                on_event(
                    Restarted(attempt=attempt, undid_vars=tuple(collapsed_this_attempt))
                )
        logger.info("restart: gave up after %d attempts", self.max_attempts)
        return None

    def _greedy_fill(
        self,
        wave: Wave,
        constraints: list[Constraint],
        selector: CellSelector,
        sampler: ValueSampler,
        on_event: EventSink | None,
        collapsed_out: list[VarId],
    ) -> Wave | None:
        tracker = _make_tracker(on_event, collapsed_out)
        try:
            while not wave.is_fully_collapsed():
                var = selector.select(wave)
                if on_event is not None:
                    on_event(Observed(var))
                # Take the first state the sampler suggests. The sampler's
                # rng advances across attempts so different paths are tried.
                try:
                    value = next(iter(sampler.order(wave, var)))
                except StopIteration:
                    return None
                wave.collapse(var, value)
                tracker(Collapsed(var, value))
                _propagate_to_fixpoint(wave, constraints, seed=[var], on_event=tracker)
        except ContradictionError:
            return None
        return wave
