"""
quadrant.py  –  SST3 Python Edition
Version 0.1.0

Replaces the BASIC Q$ packed 192-character string.

The BASIC stored the 8×8 sector grid as a flat string:
    index = (col - 1) * 3 + (row - 1) * 24 + 1   (1-indexed)

This class wraps the same logic in a clean interface using a dict keyed
by (row, col) tuples, both 1-indexed to match the BASIC.
"""

import random
from config import SYMBOLS, DISPLOOK_GRID


# Token constants — match the original BASIC strings exactly for STOCK mode.
# Display rendering may substitute mode-specific symbols at render time.
EMPTY   = "   "
STAR    = " * "
KLINGON = "+K+"
SHIP    = "<*>"
BASE    = ">!<"


class Quadrant:
    """
    8×8 grid of sector tokens.

    All row/col coordinates are 1-indexed (1..8) to match the BASIC source.
    """

    def __init__(self):
        # Default every sector to EMPTY
        self._grid: dict = {
            (r, c): EMPTY
            for r in range(1, 9)
            for c in range(1, 9)
        }

    def get(self, row: int, col: int) -> str:
        return self._grid.get((row, col), EMPTY)

    def set(self, row: int, col: int, token: str) -> None:
        assert len(token) == 3, f"Token must be 3 chars, got {token!r}"
        self._grid[(row, col)] = token

    def clear(self, row: int, col: int) -> None:
        self._grid[(row, col)] = EMPTY

    def find(self, token: str) -> list:
        """Return list of (row, col) where token is present."""
        return [(r, c) for (r, c), t in self._grid.items() if t == token]

    def is_empty(self, row: int, col: int) -> bool:
        return self._grid.get((row, col), EMPTY) == EMPTY

    def random_empty(self) -> tuple:
        """
        Return a random empty sector.  Equivalent to BASIC GOSUB 8590.
        Keeps retrying until an empty sector is found.
        """
        while True:
            r = random.randint(1, 8)
            c = random.randint(1, 8)
            if self.is_empty(r, c):
                return r, c

    def populate(self, state) -> None:
        """
        Place the Enterprise, Klingons, starbase(s), and stars into the grid.
        Equivalent to BASIC lines 1680–1910.

        `state` is a GameState; reads quad_row/col, sec_row/col,
        klingons_here, bases_here, stars_here, klingon_strength.
        """
        from state import Klingon

        # Clear the grid first
        for key in self._grid:
            self._grid[key] = EMPTY

        # Place the Enterprise
        self.set(state.sec_row, state.sec_col, SHIP)

        # Place Klingons
        state.klingons = []
        for _ in range(state.klingons_here):
            r, c = self.random_empty()
            self.set(r, c, KLINGON)
            energy = state.klingon_strength * (0.5 + random.random())
            state.klingons.append(Klingon(row=r, col=c, energy=energy))

        # Place starbase
        if state.bases_here >= 1:
            r, c = self.random_empty()
            self.set(r, c, BASE)
            state.base_sec_row = r
            state.base_sec_col = c

        # Place stars
        for _ in range(state.stars_here):
            r, c = self.random_empty()
            self.set(r, c, STAR)

    def display_symbol(self, row: int, col: int, displook: int) -> tuple:
        """
        Return (symbol_str, token_key) for rendering.
        token_key is one of: 'empty', 'star', 'klingon', 'ship', 'base'
        """
        raw = self.get(row, col)
        if raw == STAR:
            key = "star"
        elif raw == KLINGON:
            key = "klingon"
        elif raw == SHIP:
            key = "ship"
        elif raw == BASE:
            key = "base"
        else:
            key = "empty"

        syms = SYMBOLS.get(displook, SYMBOLS[0])
        sym = syms[key]

        # Grid mode: replace spaces with underscores in the symbol
        if displook == DISPLOOK_GRID:
            sym = sym.replace(" ", "_")

        return sym, key
