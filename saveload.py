"""
saveload.py  –  SST3 Python Edition
Version 0.3.0

Save and restore complete game state to/from a JSON file.

Save format version:  "sst3-py-1"

Design decisions
----------------
* All GameState primitive fields are stored by name.
* galaxy and scanned are stored as flat 64-element lists (row-major, 0-indexed
  internally) for compactness.
* klingons is a list of {row, col, energy} dicts.
* quadrant_grid is stored as a dict mapping "row,col" → token string, with
  EMPTY ("   ") cells omitted entirely (implicit on load).
* quadrant_grid is rebuilt on load rather than storing the full 64×3-char grid,
  which matches how the BASIC reconstructed Q$ from the saved variables.
* The file is deleted after a game ends so the next run starts fresh.
  (BASIC lines 12000-13010.)
"""

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from config import SAVE_VERSION, SAVE_FILENAME
from state import GameState, Klingon
from quadrant import Quadrant, EMPTY


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _grid_to_dict(grid: Quadrant) -> dict:
    """Serialise only non-empty cells as {"row,col": token}."""
    return {
        f"{r},{c}": grid.get(r, c)
        for r in range(1, 9)
        for c in range(1, 9)
        if grid.get(r, c) != EMPTY
    }


def _dict_to_grid(data: dict) -> Quadrant:
    """Reconstruct a Quadrant from the compact dict format."""
    q = Quadrant()
    for key, token in data.items():
        r, c = (int(x) for x in key.split(","))
        q.set(r, c, token)
    return q


def _state_to_dict(state: GameState) -> dict:
    """Convert GameState to a plain dict suitable for json.dumps."""
    d: dict = {}
    d["version"] = SAVE_VERSION

    # --- Scalars ---
    for field in (
        "stardate", "start_stardate", "mission_days",
        "quad_row", "quad_col", "sec_row", "sec_col",
        "energy", "max_energy", "torpedoes", "max_torpedoes", "shields",
        "total_klingons", "initial_klingons", "total_bases",
        "klingon_strength", "first_shot_chance",
        "klingons_here", "bases_here", "stars_here",
        "base_sec_row", "base_sec_col",
        "docked", "fire_first", "d4", "difficulty",
    ):
        d[field] = getattr(state, field)

    # --- Arrays ---
    # Flatten galaxy and scanned from list-of-lists to single list (row-major)
    d["galaxy"]  = [state.galaxy[r][c]  for r in range(8) for c in range(8)]
    d["scanned"] = [state.scanned[r][c] for r in range(8) for c in range(8)]
    d["damage"]  = list(state.damage)

    # --- Klingons ---
    d["klingons"] = [{"row": k.row, "col": k.col, "energy": k.energy}
                     for k in state.klingons]

    # --- Quadrant grid ---
    if state.quadrant_grid is not None:
        d["quadrant_grid"] = _grid_to_dict(state.quadrant_grid)
    else:
        d["quadrant_grid"] = {}

    return d


def _dict_to_state(d: dict) -> GameState:
    """Reconstruct a GameState from the dict produced by _state_to_dict."""
    state = GameState()

    # --- Scalars ---
    for field in (
        "stardate", "start_stardate", "mission_days",
        "quad_row", "quad_col", "sec_row", "sec_col",
        "energy", "max_energy", "torpedoes", "max_torpedoes", "shields",
        "total_klingons", "initial_klingons", "total_bases",
        "klingon_strength", "first_shot_chance",
        "klingons_here", "bases_here", "stars_here",
        "base_sec_row", "base_sec_col",
        "docked", "fire_first", "d4", "difficulty",
    ):
        if field in d:
            setattr(state, field, d[field])

    # --- Arrays ---
    flat_galaxy  = d.get("galaxy",  [0] * 64)
    flat_scanned = d.get("scanned", [0] * 64)
    state.galaxy  = [[flat_galaxy [r * 8 + c] for c in range(8)] for r in range(8)]
    state.scanned = [[flat_scanned[r * 8 + c] for c in range(8)] for r in range(8)]
    state.damage  = list(d.get("damage", [0.0] * 8))

    # --- Klingons ---
    state.klingons = [
        Klingon(row=k["row"], col=k["col"], energy=k["energy"])
        for k in d.get("klingons", [])
    ]

    # --- Quadrant grid ---
    state.quadrant_grid = _dict_to_grid(d.get("quadrant_grid", {}))

    return state


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_game(state: GameState, path: Path) -> bool:
    """
    Write game state to *path* as JSON.
    Returns True on success, False on any IO error.
    """
    try:
        data = _state_to_dict(state)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True
    except OSError as exc:
        print(f"COULD NOT SAVE: {exc}")
        return False


def load_game(path: Path) -> Optional[GameState]:
    """
    Read game state from *path*.
    Returns a GameState on success, None if the file is missing,
    corrupt, or the wrong version.
    Prints a message if the file is corrupt.
    """
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("SAVE FILE CORRUPT")
        return None

    if data.get("version") != SAVE_VERSION:
        print(f"SAVE FILE VERSION MISMATCH "
              f"(expected {SAVE_VERSION!r}, got {data.get('version')!r})")
        return None

    try:
        return _dict_to_state(data)
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        print(f"SAVE FILE CORRUPT: {exc}")
        return None


def save_exists(path: Path) -> bool:
    return path.exists()


def delete_save(path: Path) -> None:
    """Delete the save file if it exists.  Silent on failure."""
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass
