from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from wfc.core.wave import VarId, Wave


@runtime_checkable
class Constraint(Protocol):
    """Knows how to propagate domain restrictions over a wave.

    A constraint is responsible for ruling out states that violate it. The
    engine calls `propagate` after one or more variables collapse; the
    constraint reduces domains and may collapse additional variables.

    Constraints should propagate to fixed point internally if their rules
    interact (e.g. naked + hidden singles). The engine handles inter-constraint
    fixed point by looping over all constraints until none report changes.
    """

    def propagate(
        self, wave: Wave, seed: Iterable[VarId] | None = None
    ) -> set[VarId]:
        """Apply this constraint to `wave`.

        `seed` is the set of variables recently collapsed (or None for a full
        sweep over all collapsed variables). Returns the set of variables that
        became newly collapsed during this call.

        Raises ContradictionError if propagation reveals unsatisfiability.
        """
        ...
