"""
commands.py  –  SST3 Python Edition
Version 0.3.0

Structured command objects sent to the game engine by the UI layer.

The UI (TUI, GUI, or test) collects player intent through whatever input
mechanism it uses, packages it as a Command, and calls engine.execute().
The engine never calls input() and never knows what kind of UI it is
talking to.

No I/O, no state mutation, no imports from other game modules.
Safe to import anywhere.
"""

from __future__ import annotations
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Command:
    """All commands inherit from this."""


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NavCommand(Command):
    """
    Warp the Enterprise on a given course at a given warp factor.

    course : float  — 1.0–8.9  (9.0 is treated as 1.0 by the engine)
    warp   : float  — 0.0–8.0  (0.0 = no-op / cancel)
    """
    course: float
    warp: float


# ---------------------------------------------------------------------------
# Combat
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PhaserCommand(Command):
    """
    Fire phasers at all Klingons in the current quadrant.

    energy : float  — units to discharge (must be > 0 and <= state.energy)
    """
    energy: float


@dataclass(frozen=True)
class TorpedoCommand(Command):
    """
    Fire a photon torpedo on a given course.

    course : float  — 1.0–8.9  (9.0 is treated as 1.0 by the engine)
    """
    course: float


# ---------------------------------------------------------------------------
# Shields
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ShieldsCommand(Command):
    """
    Set shields to a specific energy level.

    level : float  — desired shield energy (0 to state.energy + state.shields)
    """
    level: float
