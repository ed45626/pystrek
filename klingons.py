"""
klingons.py  –  SST3 Python Edition
Version 0.3.0

Enemy AI: Klingon firing and repositioning — pure game logic, zero I/O.

Public API
----------
execute_klingons_fire(state) -> list[Event]
    All alive Klingons fire on the Enterprise.  Returns a complete list of
    Event objects.  The caller prepends a context marker if needed:
        KlingonsAmbush()      — game_loop, fire_first on quadrant entry
        KlingonsCounterFire() — combat.py, after a player weapon fires

klingons_reposition(state) -> None
    Each alive Klingon moves to a random empty sector.  Called at the
    start of a warp before the ship moves.  No I/O, no events.

Equivalent BASIC lines: 6000-6200 and 2580-2700.
"""

import random
from typing import List

from config import DEVICE_NAMES
from events import (
    Event,
    StarbaseProtection,
    KlingonFired,
    EnterpriseDestroyed,
)


# ---------------------------------------------------------------------------
# execute_klingons_fire  (BASIC lines 6000-6200)
# ---------------------------------------------------------------------------

def execute_klingons_fire(state) -> List[Event]:
    """
    All alive Klingons fire on the Enterprise.
    Mutates state.shields, state.klingons[*].energy, state.damage[].
    Returns a list[Event] — never raises, never prints.

    The caller is responsible for prepending a context marker event
    (KlingonsAmbush or KlingonsCounterFire) before this list if the
    distinction matters for the UI.

    BASIC formulas:
        H = INT( (K(I,3) / FND(1)) * (2 + RND(1)) )
        S = S - H
        K(I,3) = K(I,3) / (3 + RND(0))
    """
    events: List[Event] = []

    if state.klingons_here <= 0:
        return events

    if state.docked:
        events.append(StarbaseProtection())
        return events

    for k in state.klingons:
        if not k.alive:
            continue

        dist  = max(state.distance_to_klingon(k), 0.1)
        h     = int((k.energy / dist) * (2 + random.random()))
        state.shields -= h
        k.energy = k.energy / (3 + random.random())

        dev_hit = dev_name = None
        if h >= 20 and random.random() > 0.6 and (h / max(state.shields, 1)) > 0.02:
            dev_hit  = random.randint(0, 7)
            dev_name = DEVICE_NAMES[dev_hit]
            state.damage[dev_hit] -= h / max(state.shields, 1) + 0.5 * random.random()

        if state.shields <= 0:
            state.shields = 0.0
            events.append(KlingonFired(
                from_sector=(k.row, k.col), damage=h, shields_after=0.0,
                device_damaged=dev_hit, device_name=dev_name))
            events.append(EnterpriseDestroyed())
            return events

        events.append(KlingonFired(
            from_sector=(k.row, k.col), damage=h, shields_after=state.shields,
            device_damaged=dev_hit, device_name=dev_name))

    return events


# ---------------------------------------------------------------------------
# klingons_reposition  (BASIC lines 2580-2700)
# ---------------------------------------------------------------------------

def klingons_reposition(state) -> None:
    """
    Each alive Klingon moves to a random empty sector.
    Called once per warp command before the ship moves.
    Pure logic — no I/O, no events (repositioning is invisible to the player).
    """
    from quadrant import KLINGON
    grid = state.quadrant_grid
    if grid is None:
        return
    for k in state.klingons:
        if not k.alive:
            continue
        grid.clear(k.row, k.col)
        r, c  = grid.random_empty()
        k.row = r
        k.col = c
        grid.set(r, c, KLINGON)
