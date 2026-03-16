"""
combat.py  –  SST3 Python Edition
Version 0.3.0

Player offensive weapons: phasers and photon torpedoes.
Pure game logic — zero I/O.

Public API
----------
execute_phasers(state, PhaserCommand)  -> list[Event]
execute_torpedo(state, TorpedoCommand) -> list[Event]

Equivalent BASIC lines: 4260-5490.
"""

import random
from typing import List

from commands import PhaserCommand, TorpedoCommand
from config import (
    DEV_PHASERS, DEV_TORPS, DEV_COMPUTER,
    galaxy_encode, galaxy_decode,
)
from events import (
    Event,
    PhasersInoperative, NoEnemiesInQuadrant, ComputerDamagesAccuracy,
    InsufficientPhaserEnergy, PhaserFired, KlingonHit, KlingonNoDamage,
    KlingonDestroyed, Victory,
    TorpedoesExpended, TubesDamaged, InvalidTorpedoCourse,
    TorpedoFired, TorpedoTracked, TorpedoMissed, TorpedoAbsorbedByStar,
    StarbaseDestroyed,
    KlingonsCounterFire, KlingonFired, EnterpriseDestroyed, StarbaseProtection,
    is_victory,
)
from navigation import _course_vector
from klingons import execute_klingons_fire


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _remove_klingon(state, sector: tuple) -> None:
    """Clear a Klingon from the grid, mark it dead, update galaxy map."""
    r, c = sector
    state.quadrant_grid.clear(r, c)
    for k in state.klingons:
        if k.alive and k.row == r and k.col == c:
            k.energy = 0
            break
    state.klingons_here  -= 1
    state.total_klingons -= 1
    kg, bg, sg = galaxy_decode(state.galaxy_get(state.quad_row, state.quad_col))
    state.galaxy_set(state.quad_row, state.quad_col,
                     galaxy_encode(max(0, kg - 1), bg, sg))
    state.scanned_set(state.quad_row, state.quad_col,
                      state.galaxy_get(state.quad_row, state.quad_col))


def _victory_event(state) -> Victory:
    elapsed = state.stardate - state.start_stardate
    rating  = 1000 * (state.initial_klingons / elapsed) ** 2 if elapsed > 0 else 0
    return Victory(elapsed_stardates=elapsed, efficiency_rating=rating)


def _append_counter_fire(state, events: list) -> None:
    """
    Klingons fire back after a player weapon.
    Prepends KlingonsCounterFire marker then extends events with fire results.
    """
    fire_evts = execute_klingons_fire(state)
    if fire_evts:
        events.append(KlingonsCounterFire())
        events.extend(fire_evts)


# ---------------------------------------------------------------------------
# execute_phasers  (BASIC lines 4260-4680)
# ---------------------------------------------------------------------------

def execute_phasers(state, command: PhaserCommand) -> List[Event]:
    """
    Fire phasers at all Klingons in the quadrant.
    Mutates state in place.  Returns a complete list[Event].
    Never raises, never prints.
    """
    events: List[Event] = []

    if not state.is_device_ok(DEV_PHASERS):
        events.append(PhasersInoperative())
        return events

    if state.klingons_here <= 0:
        events.append(NoEnemiesInQuadrant())
        return events

    computer_ok = state.is_device_ok(DEV_COMPUTER)
    if not computer_ok:
        events.append(ComputerDamagesAccuracy())

    x = command.energy
    if x <= 0 or state.energy - x < 0:
        events.append(InsufficientPhaserEnergy(requested=x, available=state.energy))
        return events

    state.energy -= x
    if not computer_ok:
        x *= random.random()

    events.append(PhaserFired(energy_fired=command.energy,
                               computer_degraded=not computer_ok))

    alive = state.alive_klingons()
    h1    = int(x / len(alive)) if alive else 0

    for k in alive:
        dist   = max(state.distance_to_klingon(k), 0.1)
        h      = int((h1 / dist) * (random.random() + 2))
        sector = (k.row, k.col)

        if h <= 0.15 * k.energy:
            events.append(KlingonNoDamage(sector=sector))
            continue

        k.energy -= h

        if k.energy <= 0:
            _remove_klingon(state, sector)
            events.append(KlingonDestroyed(
                sector=sector,
                total_klingons_remaining=state.total_klingons,
            ))
            if state.total_klingons <= 0:
                events.append(_victory_event(state))
                return events
        else:
            events.append(KlingonHit(
                sector=sector,
                damage=h,
                klingon_energy_after=k.energy,
            ))

    _append_counter_fire(state, events)
    return events


# ---------------------------------------------------------------------------
# execute_torpedo  (BASIC lines 4700-5490)
# ---------------------------------------------------------------------------

def execute_torpedo(state, command: TorpedoCommand) -> List[Event]:
    """
    Fire a photon torpedo on a given course.
    Mutates state in place.  Returns a complete list[Event].
    Never raises, never prints.
    """
    events: List[Event] = []

    if state.torpedoes <= 0:
        events.append(TorpedoesExpended())
        return events

    if not state.is_device_ok(DEV_TORPS):
        events.append(TubesDamaged())
        return events

    c1 = command.course
    if c1 == 9.0:
        c1 = 1.0
    if not (1.0 <= c1 < 9.0):
        events.append(InvalidTorpedoCourse(course=command.course))
        return events

    state.energy    -= 2
    state.torpedoes -= 1
    events.append(TorpedoFired(course=c1))

    x1, x2 = _course_vector(c1)
    pos_r   = float(state.sec_row)
    pos_c   = float(state.sec_col)
    grid    = state.quadrant_grid

    from quadrant import KLINGON, STAR, BASE

    while True:
        pos_r += x1
        pos_c += x2
        r = int(pos_r + 0.5)
        c = int(pos_c + 0.5)

        # Exited quadrant
        if r < 1 or r > 8 or c < 1 or c > 8:
            events.append(TorpedoMissed())
            _append_counter_fire(state, events)
            return events

        events.append(TorpedoTracked(sector=(r, c)))

        token = grid.get(r, c)

        if token == "   ":
            continue

        if token == KLINGON:
            sector = (r, c)
            _remove_klingon(state, sector)
            events.append(KlingonDestroyed(
                sector=sector,
                total_klingons_remaining=state.total_klingons,
            ))
            if state.total_klingons <= 0:
                events.append(_victory_event(state))
                return events
            break

        if token == STAR:
            events.append(TorpedoAbsorbedByStar(sector=(r, c)))
            _append_counter_fire(state, events)
            return events

        if token == BASE:
            grid.clear(r, c)
            state.bases_here  -= 1
            state.total_bases -= 1
            kg, bg, sg = galaxy_decode(state.galaxy_get(state.quad_row, state.quad_col))
            state.galaxy_set(state.quad_row, state.quad_col,
                             galaxy_encode(kg, max(0, bg - 1), sg))
            state.scanned_set(state.quad_row, state.quad_col,
                              state.galaxy_get(state.quad_row, state.quad_col))
            court_martial = (state.total_bases <= 0
                             and state.total_klingons > state.time_remaining())
            events.append(StarbaseDestroyed(
                sector=(r, c),
                bases_remaining=state.total_bases,
                court_martial=court_martial,
            ))
            if court_martial:
                return events
            break

    _append_counter_fire(state, events)
    return events
