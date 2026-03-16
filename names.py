"""
names.py  –  SST3 Python Edition
Version 0.1.0

Maps (quadrant_row, quadrant_col) to a region + sector name.
Equivalent to BASIC lines 9010–9260.

The galaxy is divided into two 8×4 halves (columns 1-4 = west, 5-8 = east).
Each row within a half has a unique region name.  The column within the half
determines the sector suffix (I, II, III, IV).

Examples:
    (1, 1)  →  "ANTARES I"
    (1, 5)  →  "SIRIUS I"
    (3, 4)  →  "PROCYON IV"
    (8, 8)  →  "SPICA IV"
"""

# Region names for columns 1-4 (west half of galaxy)
_WEST = [
    "ANTARES",
    "RIGEL",
    "PROCYON",
    "VEGA",
    "CANOPUS",
    "ALTAIR",
    "SAGITTARIUS",
    "POLLUX",
]

# Region names for columns 5-8 (east half of galaxy)
_EAST = [
    "SIRIUS",
    "DENEB",
    "CAPELLA",
    "BETELGEUSE",
    "ALDEBARAN",
    "REGULUS",
    "ARCTURUS",
    "SPICA",
]

# Sector suffixes: col mod-4 position (1-indexed) → suffix
_SUFFIX = ["", " I", " II", " III", " IV"]   # index by ((col-1) % 4) + 1


def quadrant_name(row: int, col: int, region_only: bool = False) -> str:
    """
    Return the full name for quadrant (row, col), e.g. "ANTARES I".

    Parameters
    ----------
    row : int
        Galaxy row, 1-8.
    col : int
        Galaxy column, 1-8.
    region_only : bool
        If True, return just the region name without the sector suffix,
        e.g. "ANTARES".  Used by the galaxy region map (COM option 5).
    """
    names = _WEST if col <= 4 else _EAST
    region = names[row - 1]
    if region_only:
        return region
    suffix = _SUFFIX[((col - 1) % 4) + 1]
    return region + suffix
