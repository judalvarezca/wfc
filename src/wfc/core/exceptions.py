class ContradictionError(Exception):
    """Raised when constraint propagation reaches an unsatisfiable state.

    Shared by every WFC application: any adapter (sudoku, tiles, dungeons)
    signals an empty domain or unsatisfiable unit by raising this.
    """
