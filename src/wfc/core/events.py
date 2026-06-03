from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from wfc.core.wave import State, VarId


@dataclass(frozen=True)
class Observed:
    """The selector picked this variable as the next collapse target."""

    var: VarId


@dataclass(frozen=True)
class Collapsed:
    """A variable was collapsed to a single state.

    Emitted both for direct collapses (policy chose a value) and for
    propagation-induced collapses (naked/hidden singles, etc.). Listeners can
    distinguish by checking whether the most recent Observed event references
    the same var — if so, this is a direct collapse; otherwise it's propagated.
    """

    var: VarId
    state: State


@dataclass(frozen=True)
class Backtracked:
    """A search branch failed; these variables are being un-collapsed.

    `undid_vars` is the ordered list of variables to revert (the originally
    observed variable plus every variable that propagation collapsed under it).
    Listeners should restore each var's prior domain — for simple replay UIs,
    that means clearing the displayed value.

    `value` is the value the originally observed variable tried that failed.
    """

    var: VarId
    state: State
    undid_vars: tuple[VarId, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Solved:
    """The wave is fully collapsed and the solution stands."""


@dataclass(frozen=True)
class Contradiction:
    """The initial state already violates the constraints; no solution possible."""


Event = Observed | Collapsed | Backtracked | Solved | Contradiction
EventSink = Callable[[Event], None]
