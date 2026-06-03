from __future__ import annotations

from collections.abc import Hashable, Iterator
from typing import Protocol, runtime_checkable

VarId = Hashable
State = Hashable


@runtime_checkable
class Wave(Protocol):
    """A collection of variables in superposition over finite domains.

    The fundamental abstraction of WFC. Each variable has a finite domain (set
    of possible states); a variable is "collapsed" when its domain has exactly
    one state. The wave is "fully collapsed" when every variable is collapsed.

    Concrete adapters (sudoku, tiles, dungeons) implement this Protocol with
    domain-specific var_id and state types.
    """

    def variables(self) -> Iterator[VarId]:
        """Yield every variable id in this wave."""
        ...

    def uncollapsed(self) -> Iterator[VarId]:
        """Yield variables that are not yet collapsed."""
        ...

    def domain(self, var: VarId) -> set[State]:
        """The current set of possible states for `var`. Empty = contradiction."""
        ...

    def is_collapsed(self, var: VarId) -> bool:
        """True iff `var`'s domain has exactly one state."""
        ...

    def value(self, var: VarId) -> State:
        """The unique state of `var`. Only valid when `is_collapsed(var)`."""
        ...

    def entropy(self, var: VarId) -> int:
        """Number of remaining candidates for `var` (i.e. `len(domain(var))`)."""
        ...

    def collapse(self, var: VarId, state: State) -> None:
        """Restrict `var`'s domain to `{state}`.

        Raises ContradictionError if `state` is not currently in the domain.
        """
        ...

    def eliminate(self, var: VarId, state: State) -> bool:
        """Remove `state` from `var`'s domain.

        Returns True if `state` was present (and is now gone). Raises
        ContradictionError if eliminating leaves the domain empty.
        """
        ...

    def is_fully_collapsed(self) -> bool:
        """True iff every variable is collapsed."""
        ...

    def clone(self) -> Wave:
        """Deep copy of the wave state. Independent of the original."""
        ...
