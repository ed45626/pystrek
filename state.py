"""
state.py  –  SST3 Python Edition
Version 0.1.0

Central game state and supporting dataclasses.
One GameState instance is created per game and passed through all functions.
"""

import math
from dataclasses import dataclass, field
from config import (
    GALAXY_SIZE, DEFAULT_ENERGY, DEFAULT_TORPEDOES, DEVICE_NAMES, galaxy_decode
)


# ---------------------------------------------------------------------------
# Klingon
# ---------------------------------------------------------------------------
@dataclass
class Klingon:
    """A Klingon ship positioned in the current quadrant."""
    row:    int     # sector row, 1-8
    col:    int     # sector col, 1-8
    energy: float

    @property
    def alive(self) -> bool:
        return self.energy > 0


# ---------------------------------------------------------------------------
# Prefs
# ---------------------------------------------------------------------------
@dataclass
class Prefs:
    """User-configurable display and behaviour preferences."""
    displook:   int  = 1      # display mode  (DISPLOOK_GRID)
    monochrome: bool = False
    mono_color: int  = 0
    mono_bg:    int  = 0
    exit_mode:  int  = 0      # 0=sys.exit, 1=return
    err_trap:   int  = 0

    @classmethod
    def from_dict(cls, d: dict) -> "Prefs":
        valid = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**valid)

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)


# ---------------------------------------------------------------------------
# GameState
# ---------------------------------------------------------------------------
@dataclass
class GameState:
    """
    Complete mutable game state.

    Naming follows the BASIC source where helpful:
      T, T0, T9  →  stardate, start_stardate, mission_days
      Q1, Q2     →  quad_row, quad_col
      S1, S2     →  sec_row, sec_col
      E, E0      →  energy, max_energy
      P, P0      →  torpedoes, max_torpedoes
      S          →  shields
      K9, K7     →  total_klingons, initial_klingons
      B9         →  total_bases
      K3, B3, S3 →  klingons_here, bases_here, stars_here
      D(8)       →  damage[]  (positive=ok, negative=damaged)
      G(8,8)     →  galaxy[][]
      Z(8,8)     →  scanned[][]
      D0         →  docked
      Z8         →  fire_first
    """

    # --- Time ---
    stardate:       float = 0.0
    start_stardate: float = 0.0
    mission_days:   int   = 0

    # --- Enterprise position ---
    quad_row: int = 1   # Q1
    quad_col: int = 1   # Q2
    sec_row:  int = 1   # S1
    sec_col:  int = 1   # S2

    # --- Enterprise resources ---
    energy:        float = DEFAULT_ENERGY
    max_energy:    float = DEFAULT_ENERGY
    torpedoes:     int   = DEFAULT_TORPEDOES
    max_torpedoes: int   = DEFAULT_TORPEDOES
    shields:       float = 0.0

    # --- Damage: index 0-7; >= 0 is operational, < 0 is damaged ---
    damage: list = field(default_factory=lambda: [0.0] * 8)

    # --- Galaxy: [row-1][col-1] = K*100 + B*10 + stars (1-indexed access) ---
    galaxy:  list = field(default_factory=lambda: [[0]*8 for _ in range(8)])
    # scanned: 0 = not yet revealed to player
    scanned: list = field(default_factory=lambda: [[0]*8 for _ in range(8)])

    # --- Klingons in current quadrant (up to 3) ---
    klingons: list = field(default_factory=list)   # list[Klingon]

    # --- Galaxy-wide counts ---
    total_klingons:    int   = 0     # K9
    initial_klingons:  int   = 0     # K7
    total_bases:       int   = 0     # B9
    klingon_strength:  float = 200.0 # S9 — per-ship starting energy
    first_shot_chance: float = 0.0   # R8

    # --- Current quadrant breakdown ---
    klingons_here: int = 0   # K3
    bases_here:    int = 0   # B3
    stars_here:    int = 0   # S3
    base_sec_row:  int = 0   # B4 — sector position of starbase if present
    base_sec_col:  int = 0   # B5

    # --- Flags ---
    docked:      bool  = False  # D0
    fire_first:  bool  = False  # Z8: klingons may fire first this quadrant entry
    d4:          float = 0.0    # random repair time bonus (set per quadrant)
    difficulty:  int   = 0

    # --- Quadrant grid (populated by galaxy.enter_quadrant) ---
    quadrant_grid: object = None    # Quadrant instance

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def galaxy_get(self, r: int, c: int) -> int:
        return self.galaxy[r - 1][c - 1]

    def galaxy_set(self, r: int, c: int, val: int) -> None:
        self.galaxy[r - 1][c - 1] = val

    def scanned_get(self, r: int, c: int) -> int:
        return self.scanned[r - 1][c - 1]

    def scanned_set(self, r: int, c: int, val: int) -> None:
        self.scanned[r - 1][c - 1] = val

    def is_device_ok(self, dev_index: int) -> bool:
        """True if device is operational (damage >= 0)."""
        return self.damage[dev_index] >= 0

    def device_name(self, dev_index: int) -> str:
        return DEVICE_NAMES[dev_index]

    def distance_to_klingon(self, k: Klingon) -> float:
        """FND — Euclidean distance from Enterprise to a Klingon."""
        return math.sqrt((k.row - self.sec_row) ** 2 + (k.col - self.sec_col) ** 2)

    def alive_klingons(self) -> list:
        return [k for k in self.klingons if k.alive]

    def time_remaining(self) -> float:
        return (self.start_stardate + self.mission_days) - self.stardate

    def condition(self) -> str:
        """Returns DOCKED / *RED* / YELLOW / GREEN."""
        if self.docked:
            return "DOCKED"
        if self.klingons_here > 0:
            return "*RED*"
        if (self.energy + self.shields) < self.max_energy * 0.1:
            return "YELLOW"
        return "GREEN"

    def plural(self, count: int, word: str) -> str:
        return word + ("S" if count != 1 else "")
