from __future__ import annotations

import logging
import random
from collections.abc import Iterable

from wfc.core.constraint import Constraint
from wfc.core.policy import BacktrackPolicy, ResolutionPolicy
from wfc.core.sampler import UniformSampler, ValueSampler
from wfc.core.selector import CellSelector, LowestEntropySelector
from wfc.core.wave import Wave

logger = logging.getLogger(__name__)


def solve(
    wave: Wave,
    constraints: Iterable[Constraint],
    selector: CellSelector | None = None,
    sampler: ValueSampler | None = None,
    policy: ResolutionPolicy | None = None,
    seed: int | None = None,
) -> Wave | None:
    """Solve a wave under a set of constraints.

    Returns a fully-collapsed wave equivalent to a satisfying assignment, or
    None if no assignment exists. Does not mutate the input wave.

    Defaults: lowest-entropy selector, uniform sampler (seeded by `seed` for
    reproducibility), backtracking policy. Override any component to plug a
    different strategy.
    """
    rng = random.Random(seed) if seed is not None else None
    selector = selector or LowestEntropySelector(rng=rng)
    sampler = sampler or UniformSampler(rng=rng)
    policy = policy or BacktrackPolicy()
    logger.info(
        "solve: selector=%s sampler=%s policy=%s seed=%s",
        type(selector).__name__,
        type(sampler).__name__,
        type(policy).__name__,
        seed,
    )
    return policy.solve(wave, constraints, selector, sampler)
