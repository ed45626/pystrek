"""
events.py  –  SST3 Python Edition
Version 0.3.0

Structured event objects returned by the game engine.

Every event is an immutable dataclass.  The UI layer (TUI, GUI, or test
harness) receives a list[Event] after each command and decides how to
present each one — coloured text, a dialog box, an animation, a log entry,
or just an assertion in a test.

No I/O, no state mutation, no imports from other game modules.
Safe to import anywhere.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Event:
    """All events inherit from this so isinstance checks are simple."""


# ---------------------------------------------------------------------------
# Input validation — returned when the player's command was rejected
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InvalidCourse(Event):
    """Course number was outside 1–9."""
    course: float


@dataclass(frozen=True)
class InvalidWarp(Event):
    """Warp factor was outside the legal range."""
    warp: float
    max_warp: float          # 8.0 normally, 0.2 when engines are damaged


@dataclass(frozen=True)
class WarpEnginesDamaged(Event):
    """Player requested warp > 0.2 but warp engines are damaged."""
    requested_warp: float


@dataclass(frozen=True)
class InsufficientEnergy(Event):
    """Not enough energy to execute the warp."""
    required: int            # n steps needed
    available: float         # main energy available
    shield_energy: float     # shields available (may cover the gap)
    shields_damaged: bool    # if True, shields cannot cross-circuit


# ---------------------------------------------------------------------------
# Movement events — what happened during the warp
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ShieldsCrossCircuit(Event):
    """Shield energy was tapped to complete the maneuver."""
    shields_before: float
    shields_after: float


@dataclass(frozen=True)
class NavigationBlocked(Event):
    """Ship stopped early due to an obstacle in its path."""
    obstacle_sector: tuple       # (row, col) of the blocking object
    stopped_sector: tuple        # (row, col) where the ship ended up


@dataclass(frozen=True)
class GalacticPerimeterDenied(Event):
    """Attempted to cross the galaxy edge; Starfleet refused."""
    clamped_quadrant: tuple      # (quad_row, quad_col) after clamping
    clamped_sector: tuple        # (sec_row, sec_col) after clamping


@dataclass(frozen=True)
class QuadrantEntered(Event):
    """Ship crossed into a new quadrant."""
    quadrant: tuple              # (quad_row, quad_col)
    quadrant_name: str
    klingons: int
    bases: int
    stars: int


@dataclass(frozen=True)
class ShipMoved(Event):
    """Ship completed movement and is now in a new sector."""
    from_sector: tuple           # (row, col)
    to_sector: tuple             # (row, col)
    energy_used: float
    stardate_after: float


@dataclass(frozen=True)
class Docked(Event):
    """Ship docked at a starbase: fully refuelled."""
    sector: tuple                # (row, col) of the starbase
    energy_restored: float
    torpedoes_restored: int


# ---------------------------------------------------------------------------
# Damage / repair events — during warp ticks
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DeviceRepaired(Event):
    """A device completed repair during this warp."""
    device_index: int
    device_name: str


@dataclass(frozen=True)
class DeviceDamaged(Event):
    """A device was damaged (random event during warp)."""
    device_index: int
    device_name: str
    new_level: float             # new damage value (negative)


@dataclass(frozen=True)
class DeviceImproved(Event):
    """A device's repair state improved (random event during warp)."""
    device_index: int
    device_name: str
    new_level: float


# ---------------------------------------------------------------------------
# Klingon fire events — Klingons fire when the ship begins to warp
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StarbaseProtection(Event):
    """Docked at a starbase; Klingon fire was suppressed."""


@dataclass(frozen=True)
class KlingonFired(Event):
    """A single Klingon fired on the Enterprise."""
    from_sector: tuple           # (row, col) of the Klingon
    damage: int                  # hit points absorbed by shields
    shields_after: float         # shields remaining after hit
    device_damaged: Optional[int] = None    # device index if a device was hit
    device_name: Optional[str]   = None


@dataclass(frozen=True)
class EnterpriseDestroyed(Event):
    """Shields dropped to zero; the Enterprise is destroyed."""




# ---------------------------------------------------------------------------
# Shield events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ShieldControlInoperable(Event):
    """Shield control device is damaged; shields cannot be adjusted."""


@dataclass(frozen=True)
class ShieldsUnchanged(Event):
    """
    Shield level was not changed.

    reason : str — one of:
        'same'      : requested level equals current shields
        'negative'  : requested level was < 0
        'overspend' : requested level exceeds available energy
        'cancelled' : player cancelled input (empty / non-numeric)
    """
    reason: str
    current_shields: float


@dataclass(frozen=True)
class ShieldsSet(Event):
    """Shield level was successfully changed."""
    shields_before: float
    shields_after:  float
    energy_before:  float
    energy_after:   float


# ---------------------------------------------------------------------------
# Phaser events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PhasersInoperative(Event):
    """Phaser control device is damaged."""


@dataclass(frozen=True)
class NoEnemiesInQuadrant(Event):
    """Player fired phasers but no Klingons are present."""


@dataclass(frozen=True)
class ComputerDamagesAccuracy(Event):
    """Library-computer is damaged; phaser accuracy is degraded."""


@dataclass(frozen=True)
class InsufficientPhaserEnergy(Event):
    """Player requested more energy than available."""
    requested: float
    available: float


@dataclass(frozen=True)
class PhaserFired(Event):
    """Phasers were discharged at a specific Klingon."""
    energy_fired: float          # total energy committed by player
    computer_degraded: bool      # True if computer was damaged


@dataclass(frozen=True)
class KlingonHit(Event):
    """Phasers struck a Klingon."""
    sector: tuple                # (row, col) of the Klingon
    damage: int                  # energy subtracted from Klingon
    klingon_energy_after: float  # remaining energy (0 if destroyed)


@dataclass(frozen=True)
class KlingonNoDamage(Event):
    """Hit was too weak to register (< 15% of Klingon energy)."""
    sector: tuple


@dataclass(frozen=True)
class KlingonDestroyed(Event):
    """A Klingon was destroyed (by phasers or torpedo)."""
    sector: tuple                # (row, col) where it was
    total_klingons_remaining: int


@dataclass(frozen=True)
class Victory(Event):
    """Last Klingon destroyed — mission complete."""
    elapsed_stardates: float
    efficiency_rating: float


# ---------------------------------------------------------------------------
# Torpedo events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TorpedoesExpended(Event):
    """No torpedoes left."""


@dataclass(frozen=True)
class TubesDamaged(Event):
    """Photon tubes device is damaged."""


@dataclass(frozen=True)
class InvalidTorpedoCourse(Event):
    """Torpedo course was outside 1–9."""
    course: float


@dataclass(frozen=True)
class TorpedoFired(Event):
    """A torpedo was launched."""
    course: float


@dataclass(frozen=True)
class TorpedoTracked(Event):
    """Torpedo passed through a sector (one per step)."""
    sector: tuple                # (row, col)


@dataclass(frozen=True)
class TorpedoMissed(Event):
    """Torpedo exited the quadrant without hitting anything."""


@dataclass(frozen=True)
class TorpedoAbsorbedByStar(Event):
    """Torpedo hit a star and was absorbed."""
    sector: tuple


@dataclass(frozen=True)
class StarbaseDestroyed(Event):
    """A torpedo struck a Federation starbase."""
    sector: tuple
    bases_remaining: int
    court_martial: bool          # True if mission is now unwinnable


# ---------------------------------------------------------------------------
# Klingon counter-fire events  (after player fires)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KlingonsAmbush(Event):
    """Marker: Klingons fired first on quadrant entry (fire_first flag)."""


@dataclass(frozen=True)
class KlingonsCounterFire(Event):
    """Marker: the following KlingonFired events are counter-fire after a player weapon."""


# ---------------------------------------------------------------------------
# is_victory helper
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def is_fatal(events: list) -> bool:
    """True if any event in the list signals ship destruction."""
    return any(isinstance(e, EnterpriseDestroyed) for e in events)


def is_victory(events: list) -> bool:
    """True if any event in the list signals mission success."""
    return any(isinstance(e, Victory) for e in events)


def find(events: list, event_type: type) -> list:
    """Return all events of a given type from a list."""
    return [e for e in events if isinstance(e, event_type)]


def find_one(events: list, event_type: type):
    """Return the first event of a given type, or None."""
    for e in events:
        if isinstance(e, event_type):
            return e
    return None
