"""
navigation.py  –  SST3 Python Edition
Version 0.3.0

Warp drive engine: pure game logic, zero I/O.

Public API
----------
execute_nav(state, command) -> list[Event]
    Validate the NavCommand, move the ship, return a complete list of
    Event objects describing everything that happened.  The caller
    (TUI, GUI, or test) reads the event list and decides how to present it.

Internal helpers remain private (_course_vector, _maneuver_energy, etc.)
and are unchanged in logic from v0.2.0.

Equivalent BASIC lines: 2300-3980.
"""

import random
from typing import List

from commands import NavCommand
from config import GALAXY_SIZE, DEV_WARP, DEV_SHIELDS, DEVICE_NAMES
from events import (
    Event,
    InvalidCourse, InvalidWarp, WarpEnginesDamaged, InsufficientEnergy,
    ShieldsCrossCircuit, NavigationBlocked, GalacticPerimeterDenied,
    QuadrantEntered, ShipMoved, Docked,
    DeviceRepaired, DeviceDamaged, DeviceImproved,
    StarbaseProtection, KlingonFired, EnterpriseDestroyed,
)
from klingons import execute_klingons_fire


# ---------------------------------------------------------------------------
# Course direction vectors  (BASIC lines 530-600)
# ---------------------------------------------------------------------------
_COURSE_VECTORS = {
    1: ( 0.0,  1.0),  2: (-1.0,  1.0),  3: (-1.0,  0.0),  4: (-1.0, -1.0),
    5: ( 0.0, -1.0),  6: ( 1.0, -1.0),  7: ( 1.0,  0.0),  8: ( 1.0,  1.0),
    9: ( 0.0,  1.0),
}


def _course_vector(c1: float) -> tuple:
    """Fractional course interpolation. BASIC lines 3110-3140."""
    base  = int(c1)
    frac  = c1 - base
    next_ = base + 1 if base < 9 else 1
    dr1, dc1 = _COURSE_VECTORS.get(base,  (0.0, 0.0))
    dr2, dc2 = _COURSE_VECTORS.get(next_, (0.0, 0.0))
    return dr1 + (dr2 - dr1) * frac, dc1 + (dc2 - dc1) * frac


def _maneuver_energy(state, n: int, events: list) -> None:
    """Deduct N+10 energy, draw from shields if needed. BASIC lines 3910-3980."""
    state.energy -= n + 10
    if state.energy >= 0:
        return
    shields_before = state.shields
    state.shields  += state.energy
    state.energy    = 0.0
    if state.shields < 0:
        state.shields = 0.0
    events.append(ShieldsCrossCircuit(
        shields_before=shields_before,
        shields_after=state.shields,
    ))


def _damage_tick(state, d6: float, events: list) -> None:
    """Repair tick + 20% random event. BASIC lines 2770-3060."""
    for i in range(8):
        if state.damage[i] < 0:
            state.damage[i] += d6
            if -0.1 < state.damage[i] < 0:
                state.damage[i] = -0.1
                continue
            if state.damage[i] >= 0:
                events.append(DeviceRepaired(device_index=i, device_name=DEVICE_NAMES[i]))

    if random.random() > 0.2:
        return
    dev = random.randint(0, 7)
    if random.random() < 0.6:
        state.damage[dev] -= random.random() * 5 + 1
        events.append(DeviceDamaged(
            device_index=dev, device_name=DEVICE_NAMES[dev], new_level=state.damage[dev]))
    else:
        state.damage[dev] += random.random() * 3 + 1
        events.append(DeviceImproved(
            device_index=dev, device_name=DEVICE_NAMES[dev], new_level=state.damage[dev]))



def _cross_quadrant_boundary(state, x, y, n, x1, x2, events: list) -> bool:
    """
    Compute new quadrant/sector position after crossing a boundary.
    BASIC lines 3500-3590.  Returns True if clamped at galaxy edge.
    """
    abs_row = 8 * state.quad_row + x + n * x1
    abs_col = 8 * state.quad_col + y + n * x2

    new_qr = int(abs_row / 8)
    new_qc = int(abs_col / 8)
    new_sr = int(abs_row - new_qr * 8)
    new_sc = int(abs_col - new_qc * 8)

    if new_sr == 0: new_qr -= 1; new_sr = 8
    if new_sc == 0: new_qc -= 1; new_sc = 8

    hit_edge = False
    if new_qr < 1:           hit_edge = True; new_qr = 1;           new_sr = 1
    if new_qr > GALAXY_SIZE: hit_edge = True; new_qr = GALAXY_SIZE; new_sr = GALAXY_SIZE
    if new_qc < 1:           hit_edge = True; new_qc = 1;           new_sc = 1
    if new_qc > GALAXY_SIZE: hit_edge = True; new_qc = GALAXY_SIZE; new_sc = GALAXY_SIZE

    state.quad_row = new_qr;  state.quad_col = new_qc
    state.sec_row  = new_sr;  state.sec_col  = new_sc

    if hit_edge:
        events.append(GalacticPerimeterDenied(
            clamped_quadrant=(new_qr, new_qc),
            clamped_sector=(new_sr, new_sc),
        ))
    return hit_edge


def _advance_stardate(state, w1: float) -> None:
    state.stardate += 1.0 if w1 >= 1.0 else 0.1 * int(10 * w1)


def _place_ship(state) -> None:
    from quadrant import SHIP
    grid = state.quadrant_grid
    if grid is None:
        return
    r = max(1, min(8, state.sec_row))
    c = max(1, min(8, state.sec_col))
    state.sec_row = r;  state.sec_col = c
    if grid.is_empty(r, c):
        grid.set(r, c, SHIP)


def _check_docking(state, events: list) -> None:
    """Scan adjacent sectors for a starbase; dock if found."""
    from quadrant import BASE
    grid = state.quadrant_grid
    if grid is None:
        return
    found = any(
        1 <= state.sec_row + dr <= 8
        and 1 <= state.sec_col + dc <= 8
        and grid.get(state.sec_row + dr, state.sec_col + dc) == BASE
        for dr in range(-1, 2)
        for dc in range(-1, 2)
        if not (dr == 0 and dc == 0)
    )
    if found and not state.docked:
        e_before = state.energy
        t_before = state.torpedoes
        state.shields   = 0.0
        state.energy    = state.max_energy
        state.torpedoes = state.max_torpedoes
        events.append(Docked(
            sector=(state.base_sec_row, state.base_sec_col),
            energy_restored=state.energy - e_before,
            torpedoes_restored=state.max_torpedoes - t_before,
        ))
    state.docked = found


def _setup_new_quadrant(state, events: list) -> None:
    """
    Set up state for a freshly entered quadrant and append QuadrantEntered.
    Mirrors galaxy.enter_quadrant() logic without any printing.
    """
    import random as _r
    from config import galaxy_decode
    from quadrant import Quadrant
    from names import quadrant_name

    state.d4 = 0.5 * _r.random()
    state.quad_row = max(1, min(GALAXY_SIZE, state.quad_row))
    state.quad_col = max(1, min(GALAXY_SIZE, state.quad_col))

    gval = state.galaxy_get(state.quad_row, state.quad_col)
    state.scanned_set(state.quad_row, state.quad_col, gval)
    state.klingons_here, state.bases_here, state.stars_here = galaxy_decode(gval)

    state.quadrant_grid = Quadrant()
    state.quadrant_grid.populate(state)

    events.append(QuadrantEntered(
        quadrant=(state.quad_row, state.quad_col),
        quadrant_name=quadrant_name(state.quad_row, state.quad_col),
        klingons=state.klingons_here,
        bases=state.bases_here,
        stars=state.stars_here,
    ))
    state.fire_first = True
    _check_docking(state, events)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def execute_nav(state, command: NavCommand) -> List[Event]:
    """
    Execute a NavCommand.  Mutates state in place.
    Returns a complete list[Event].  Never raises, never prints.
    """
    events: List[Event] = []

    # Validate course
    c1 = command.course
    if c1 == 9.0:
        c1 = 1.0
    if not (1.0 <= c1 < 9.0):
        events.append(InvalidCourse(course=command.course))
        return events

    # Validate warp
    w1       = command.warp
    warp_ok  = state.is_device_ok(DEV_WARP)
    max_warp = 8.0 if warp_ok else 0.2

    if w1 == 0.0:
        return events

    if not warp_ok and w1 > 0.2:
        events.append(WarpEnginesDamaged(requested_warp=w1))
        return events

    if not (0 < w1 <= 8.0):
        events.append(InvalidWarp(warp=w1, max_warp=max_warp))
        return events

    # Energy check
    n = int(w1 * 8 + 0.5)
    if state.energy - n < 0:
        events.append(InsufficientEnergy(
            required=n,
            available=state.energy,
            shield_energy=state.shields,
            shields_damaged=not state.is_device_ok(DEV_SHIELDS),
        ))
        return events

    # Klingons reposition and fire before we move
    from klingons import klingons_reposition
    klingons_reposition(state)
    _fire_evts = execute_klingons_fire(state)
    events.extend(_fire_evts)
    if any(isinstance(e, EnterpriseDestroyed) for e in _fire_evts):
        return events

    # Set up movement
    d6     = w1 if w1 < 1.0 else 1.0
    x1, x2 = _course_vector(c1)

    from quadrant import SHIP
    grid = state.quadrant_grid
    grid.clear(state.sec_row, state.sec_col)

    pos_r  = float(state.sec_row)
    pos_c  = float(state.sec_col)
    orig_r = pos_r
    orig_c = pos_c
    from_sector  = (state.sec_row, state.sec_col)
    steps_taken  = n

    # Step loop
    for step in range(n):
        pos_r += x1
        pos_c += x2

        if pos_r < 1 or pos_r >= 9 or pos_c < 1 or pos_c >= 9:
            hit_edge = _cross_quadrant_boundary(
                state, orig_r, orig_c, n, x1, x2, events)
            _damage_tick(state, d6, events)
            _maneuver_energy(state, n, events)
            state.stardate += 1
            if not hit_edge:
                _setup_new_quadrant(state, events)
            else:
                _place_ship(state)
                _check_docking(state, events)
            return events

        sr, sc = int(pos_r), int(pos_c)
        if not grid.is_empty(sr, sc):
            pos_r -= x1;  pos_c -= x2
            sr, sc = int(pos_r), int(pos_c)
            events.append(NavigationBlocked(
                obstacle_sector=(int(pos_r + x1), int(pos_c + x2)),
                stopped_sector=(sr, sc),
            ))
            steps_taken = step
            break

        _damage_tick(state, d6, events)

    # Place ship at final position
    final_r = max(1, min(8, int(pos_r)))
    final_c = max(1, min(8, int(pos_c)))
    state.sec_row = final_r;  state.sec_col = final_c
    grid.set(final_r, final_c, SHIP)

    energy_before = state.energy
    _maneuver_energy(state, steps_taken, events)
    _advance_stardate(state, w1)

    events.append(ShipMoved(
        from_sector=from_sector,
        to_sector=(final_r, final_c),
        energy_used=energy_before - state.energy,
        stardate_after=state.stardate,
    ))

    _check_docking(state, events)
    return events
