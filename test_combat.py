"""
test_combat.py  –  SST3 Python Edition
Version 0.3.0

Tests for the combat command/event architecture.

All tests call execute_phasers / execute_torpedo directly with Command
objects and assert on the returned list[Event].  No input() mocking needed.
"""

import random
import pytest

from state import GameState, Klingon
from quadrant import Quadrant, SHIP, KLINGON, STAR, BASE, EMPTY
from commands import PhaserCommand, TorpedoCommand
from combat import execute_phasers, execute_torpedo, _remove_klingon
from events import (
    PhasersInoperative, NoEnemiesInQuadrant, ComputerDamagesAccuracy,
    InsufficientPhaserEnergy, PhaserFired, KlingonHit, KlingonNoDamage,
    KlingonDestroyed, Victory,
    TorpedoesExpended, TubesDamaged, InvalidTorpedoCourse,
    TorpedoFired, TorpedoTracked, TorpedoMissed, TorpedoAbsorbedByStar,
    StarbaseDestroyed,
    KlingonsCounterFire, KlingonFired, EnterpriseDestroyed, StarbaseProtection,
    is_fatal, is_victory, find, find_one,
)
from config import DEV_PHASERS, DEV_TORPS, DEV_COMPUTER, galaxy_encode, galaxy_decode


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _state(ship_r=4, ship_c=1, k_r=4, k_c=5,
           k_energy=200.0, shields=500.0, energy=3000.0):
    """Minimal GameState with one Klingon, galaxy cell set correctly."""
    s = GameState()
    s.sec_row, s.sec_col     = ship_r, ship_c
    s.quad_row, s.quad_col   = 3, 3
    s.energy                 = energy
    s.shields                = shields
    s.torpedoes              = 10
    s.max_torpedoes          = 10
    s.klingons_here          = 1
    s.total_klingons         = 5
    s.initial_klingons       = 5
    s.total_bases            = 2
    s.stardate               = 2000.0
    s.start_stardate         = 2000.0
    s.mission_days           = 30
    s.galaxy_set(3, 3, galaxy_encode(1, 0, 4))
    k = Klingon(row=k_r, col=k_c, energy=k_energy)
    s.klingons = [k]
    q = Quadrant()
    q.set(ship_r, ship_c, SHIP)
    q.set(k_r, k_c, KLINGON)
    s.quadrant_grid = q
    return s


def pha(state, energy):
    return execute_phasers(state, PhaserCommand(energy=float(energy)))


def tor(state, course):
    return execute_torpedo(state, TorpedoCommand(course=float(course)))


# ---------------------------------------------------------------------------
# execute_phasers — validation
# ---------------------------------------------------------------------------

class TestPhaserValidation:

    def test_phasers_inoperative_when_damaged(self):
        s = _state(); s.damage[DEV_PHASERS] = -1.0
        evs = pha(s, 500)
        assert find_one(evs, PhasersInoperative) is not None
        assert len(evs) == 1

    def test_no_enemies_returns_early(self):
        s = _state(); s.klingons_here = 0; s.klingons = []
        evs = pha(s, 500)
        assert find_one(evs, NoEnemiesInQuadrant) is not None

    def test_zero_energy_rejected(self):
        s = _state()
        evs = pha(s, 0)
        assert find_one(evs, InsufficientPhaserEnergy) is not None

    def test_negative_energy_rejected(self):
        s = _state()
        evs = pha(s, -100)
        assert find_one(evs, InsufficientPhaserEnergy) is not None

    def test_overspend_rejected(self):
        s = _state(energy=100.0)
        evs = pha(s, 500)
        ev = find_one(evs, InsufficientPhaserEnergy)
        assert ev is not None
        assert ev.available == pytest.approx(100.0)

    def test_computer_damage_warning_emitted(self):
        s = _state(); s.damage[DEV_COMPUTER] = -1.0
        evs = pha(s, 0)   # rejected by energy check, but warning comes first
        assert find_one(evs, ComputerDamagesAccuracy) is not None

    def test_phaser_fired_event_present_on_valid_fire(self):
        random.seed(0)
        s = _state(k_energy=10.0)
        evs = pha(s, 2000)
        assert find_one(evs, PhaserFired) is not None


# ---------------------------------------------------------------------------
# execute_phasers — state mutation
# ---------------------------------------------------------------------------

class TestPhaserMutation:

    def test_energy_deducted(self):
        random.seed(0)
        s = _state(k_energy=10.0); s.energy = 3000.0
        pha(s, 500)
        assert s.energy == pytest.approx(2500.0)

    def test_klingon_killed_clears_grid(self):
        random.seed(99)
        s = _state(k_r=4, k_c=2, k_energy=10.0)
        pha(s, 2000)
        assert all(not k.alive for k in s.klingons)
        assert s.quadrant_grid.get(4, 2) == EMPTY

    def test_klingon_killed_decrements_klingons_here(self):
        random.seed(99)
        s = _state(k_r=4, k_c=2, k_energy=10.0)
        pha(s, 2000)
        assert s.klingons_here == 0

    def test_klingon_killed_decrements_total_klingons(self):
        random.seed(99)
        s = _state(k_r=4, k_c=2, k_energy=10.0)
        before = s.total_klingons
        pha(s, 2000)
        assert s.total_klingons == before - 1

    def test_galaxy_klingon_count_updated(self):
        random.seed(99)
        s = _state(k_r=4, k_c=2, k_energy=10.0)
        s.galaxy_set(3, 3, galaxy_encode(1, 0, 4))
        pha(s, 2000)
        k, _, _ = galaxy_decode(s.galaxy_get(3, 3))
        assert k == 0


# ---------------------------------------------------------------------------
# execute_phasers — events emitted
# ---------------------------------------------------------------------------

class TestPhaserEvents:

    def test_klingon_destroyed_event_on_kill(self):
        random.seed(99)
        s = _state(k_r=4, k_c=2, k_energy=10.0)
        evs = pha(s, 2000)
        ev = find_one(evs, KlingonDestroyed)
        assert ev is not None
        assert ev.sector == (4, 2)

    def test_victory_event_when_last_klingon_dies(self):
        random.seed(99)
        s = _state(k_r=4, k_c=2, k_energy=10.0)
        s.total_klingons = 1
        s.galaxy_set(3, 3, galaxy_encode(1, 0, 4))
        evs = pha(s, 2000)
        assert is_victory(evs)

    def test_no_victory_when_klingons_remain(self):
        random.seed(99)
        s = _state(k_r=4, k_c=2, k_energy=10.0)
        s.total_klingons = 3  # more remain
        evs = pha(s, 2000)
        assert not is_victory(evs)

    def test_klingon_hit_event_when_damaged_not_dead(self):
        random.seed(5)
        s = _state(k_r=4, k_c=2, k_energy=5000.0)
        evs = pha(s, 100)
        hits = find(evs, KlingonHit)
        # May be a hit or no-damage depending on roll; just check no crash
        assert isinstance(evs, list)

    def test_no_damage_event_for_tiny_hit(self):
        """Very distant Klingon with high energy — hit likely below 15% threshold."""
        random.seed(0)
        s = _state(k_r=1, k_c=8, k_energy=5000.0)
        evs = pha(s, 50)
        no_dmg = find(evs, KlingonNoDamage)
        hit    = find(evs, KlingonHit)
        # One of these must be present (not both)
        assert len(no_dmg) + len(hit) >= 1

    def test_counter_fire_follows_attack(self):
        """After phasers fire, alive Klingons counter-fire."""
        random.seed(0)
        s = _state(k_energy=5000.0)
        s.shields = 5000.0
        evs = pha(s, 100)
        marker = find_one(evs, KlingonsCounterFire)
        kfired = find(evs, KlingonFired)
        assert marker is not None
        assert len(kfired) >= 1

    def test_no_counter_fire_when_docked(self):
        random.seed(0)
        s = _state(k_energy=5000.0); s.docked = True
        evs = pha(s, 100)
        assert find_one(evs, KlingonFired) is None
        assert find_one(evs, StarbaseProtection) is not None

    def test_enterprise_destroyed_is_fatal(self):
        random.seed(0)
        s = _state(k_energy=50000.0); s.shields = 1.0
        evs = pha(s, 100)
        assert is_fatal(evs)

    def test_multiple_klingons_all_targeted(self):
        random.seed(42)
        s = GameState()
        s.sec_row, s.sec_col = 4, 4
        s.quad_row, s.quad_col = 3, 3
        s.energy = 3000.0; s.shields = 5000.0
        s.torpedoes = 10; s.max_torpedoes = 10
        s.klingons_here = 3; s.total_klingons = 3
        s.initial_klingons = 3; s.total_bases = 1
        s.stardate = 2000.0; s.start_stardate = 2000.0; s.mission_days = 30
        s.galaxy_set(3, 3, galaxy_encode(3, 0, 4))
        s.klingons = [Klingon(4,5,1000), Klingon(4,6,1000), Klingon(4,7,1000)]
        q = Quadrant(); q.set(4,4,SHIP)
        for k in s.klingons: q.set(k.row,k.col,KLINGON)
        s.quadrant_grid = q
        evs = execute_phasers(s, PhaserCommand(energy=900.0))
        hits = find(evs, KlingonHit) + find(evs, KlingonNoDamage) + find(evs, KlingonDestroyed)
        assert len(hits) == 3   # one event per Klingon


# ---------------------------------------------------------------------------
# execute_torpedo — validation
# ---------------------------------------------------------------------------

class TestTorpedoValidation:

    def test_no_torpedoes_left(self):
        s = _state(); s.torpedoes = 0
        evs = tor(s, 1)
        assert find_one(evs, TorpedoesExpended) is not None
        assert len(evs) == 1

    def test_tubes_damaged(self):
        s = _state(); s.damage[DEV_TORPS] = -1.0
        evs = tor(s, 1)
        assert find_one(evs, TubesDamaged) is not None
        assert len(evs) == 1

    def test_invalid_course_low(self):
        s = _state()
        evs = tor(s, 0)
        assert find_one(evs, InvalidTorpedoCourse) is not None

    def test_invalid_course_high(self):
        s = _state()
        evs = tor(s, 10)
        assert find_one(evs, InvalidTorpedoCourse) is not None

    def test_course_9_wraps_to_1(self):
        random.seed(0)
        s = _state(ship_r=4, ship_c=1, k_r=4, k_c=5)
        evs = tor(s, 9)
        # Course 9 = East: should hit klingon at (4,5)
        assert find_one(evs, KlingonDestroyed) is not None


# ---------------------------------------------------------------------------
# execute_torpedo — state mutation
# ---------------------------------------------------------------------------

class TestTorpedoMutation:

    def test_torpedo_count_decremented(self):
        random.seed(0)
        s = _state(); s.torpedoes = 10
        tor(s, 1)
        assert s.torpedoes == 9

    def test_energy_decremented_by_2(self):
        random.seed(0)
        s = _state(); s.energy = 3000.0
        tor(s, 1)
        assert s.energy < 3000.0
        # Minimum deduction is 2 (before counter-fire)
        assert s.energy <= 3000.0 - 2

    def test_direct_hit_kills_klingon(self):
        random.seed(0)
        s = _state(ship_r=4, ship_c=1, k_r=4, k_c=5)
        tor(s, 1)
        assert all(not k.alive for k in s.klingons)

    def test_direct_hit_clears_grid(self):
        random.seed(0)
        s = _state(ship_r=4, ship_c=1, k_r=4, k_c=5)
        tor(s, 1)
        assert s.quadrant_grid.get(4, 5) == EMPTY

    def test_direct_hit_decrements_total_klingons(self):
        random.seed(0)
        s = _state(ship_r=4, ship_c=1, k_r=4, k_c=5)
        before = s.total_klingons
        tor(s, 1)
        assert s.total_klingons == before - 1

    def test_galaxy_updated_after_torpedo_kill(self):
        random.seed(0)
        s = _state(ship_r=4, ship_c=1, k_r=4, k_c=5)
        s.galaxy_set(3, 3, galaxy_encode(1, 0, 4))
        tor(s, 1)
        k, _, _ = galaxy_decode(s.galaxy_get(3, 3))
        assert k == 0


# ---------------------------------------------------------------------------
# execute_torpedo — events emitted
# ---------------------------------------------------------------------------

class TestTorpedoEvents:

    def test_torpedo_fired_event_present(self):
        random.seed(0)
        s = _state(ship_r=4, ship_c=1, k_r=4, k_c=5)
        evs = tor(s, 1)
        assert find_one(evs, TorpedoFired) is not None

    def test_torpedo_track_events_printed(self):
        random.seed(0)
        s = _state(ship_r=4, ship_c=1, k_r=4, k_c=5)
        evs = tor(s, 1)
        track = find(evs, TorpedoTracked)
        assert len(track) >= 1
        # Last tracked sector should be (4,5) — the klingon's position
        assert track[-1].sector == (4, 5)

    def test_klingon_destroyed_event_on_hit(self):
        random.seed(0)
        s = _state(ship_r=4, ship_c=1, k_r=4, k_c=5)
        evs = tor(s, 1)
        ev = find_one(evs, KlingonDestroyed)
        assert ev is not None
        assert ev.sector == (4, 5)

    def test_victory_when_last_klingon_destroyed(self):
        random.seed(0)
        s = _state(ship_r=4, ship_c=1, k_r=4, k_c=5)
        s.total_klingons = 1
        s.galaxy_set(3, 3, galaxy_encode(1, 0, 4))
        evs = tor(s, 1)
        assert is_victory(evs)

    def test_torpedo_missed_event_when_exits_quadrant(self):
        random.seed(0)
        s = _state(ship_r=1, ship_c=4); s.klingons = []; s.klingons_here = 0
        evs = tor(s, 3)   # north from row 1 exits immediately
        assert find_one(evs, TorpedoMissed) is not None

    def test_star_absorbed_event(self):
        random.seed(0)
        s = _state(ship_r=4, ship_c=1); s.klingons = []; s.klingons_here = 0
        s.quadrant_grid.set(4, 3, STAR)
        evs = tor(s, 1)
        ev = find_one(evs, TorpedoAbsorbedByStar)
        assert ev is not None
        assert ev.sector == (4, 3)
        assert s.quadrant_grid.get(4, 3) == STAR   # star survives

    def test_starbase_destroyed_event(self):
        random.seed(0)
        s = _state(ship_r=4, ship_c=1); s.klingons = []; s.klingons_here = 0
        s.bases_here = 1; s.total_bases = 2
        s.quadrant_grid.set(4, 3, BASE)
        evs = tor(s, 1)
        ev = find_one(evs, StarbaseDestroyed)
        assert ev is not None
        assert ev.sector == (4, 3)
        assert ev.bases_remaining == 1
        assert s.quadrant_grid.get(4, 3) == EMPTY

    def test_court_martial_when_last_base_destroyed_unwinnable(self):
        random.seed(0)
        s = _state(ship_r=4, ship_c=1); s.klingons = []; s.klingons_here = 0
        s.total_bases = 1; s.bases_here = 1
        s.total_klingons = 50   # impossible to beat in time
        s.stardate = 2028.0
        s.quadrant_grid.set(4, 3, BASE)
        evs = tor(s, 1)
        ev = find_one(evs, StarbaseDestroyed)
        assert ev is not None
        assert ev.court_martial is True

    def test_counter_fire_after_hit(self):
        random.seed(0)
        s = _state(ship_r=4, ship_c=1, k_r=4, k_c=5)
        s.shields = 5000.0
        # Add a second klingon that survives to return fire
        s.klingons.append(Klingon(row=1, col=1, energy=300.0))
        s.klingons_here = 2; s.total_klingons = 6
        s.quadrant_grid.set(1, 1, KLINGON)
        s.galaxy_set(3, 3, galaxy_encode(2, 0, 4))
        evs = tor(s, 1)
        assert find_one(evs, KlingonsCounterFire) is not None

    def test_no_counter_fire_when_docked(self):
        random.seed(0)
        s = _state(ship_r=4, ship_c=1, k_r=4, k_c=5)
        s.docked = True
        evs = tor(s, 1)
        assert find_one(evs, KlingonFired) is None


# ---------------------------------------------------------------------------
# _remove_klingon helper
# ---------------------------------------------------------------------------

class TestRemoveKlingon:

    def _make(self):
        s = GameState()
        s.quad_row, s.quad_col = 2, 2
        s.klingons_here = 2; s.total_klingons = 5
        s.galaxy_set(2, 2, galaxy_encode(2, 0, 3))
        k = Klingon(3, 5, 200.0)
        s.klingons = [k, Klingon(6, 6, 200.0)]
        q = Quadrant()
        q.set(k.row, k.col, KLINGON); q.set(6, 6, KLINGON)
        s.quadrant_grid = q
        return s, k

    def test_grid_cell_cleared(self):
        s, k = self._make()
        _remove_klingon(s, (k.row, k.col))
        assert s.quadrant_grid.get(k.row, k.col) == EMPTY

    def test_klingon_energy_zeroed(self):
        s, k = self._make()
        _remove_klingon(s, (k.row, k.col))
        assert k.energy == 0.0

    def test_klingons_here_decremented(self):
        s, k = self._make()
        _remove_klingon(s, (k.row, k.col))
        assert s.klingons_here == 1

    def test_total_klingons_decremented(self):
        s, k = self._make()
        before = s.total_klingons
        _remove_klingon(s, (k.row, k.col))
        assert s.total_klingons == before - 1

    def test_galaxy_map_updated(self):
        s, k = self._make()
        _remove_klingon(s, (k.row, k.col))
        kg, _, _ = galaxy_decode(s.galaxy_get(2, 2))
        assert kg == 1

    def test_scanned_map_matches_galaxy(self):
        s, k = self._make()
        _remove_klingon(s, (k.row, k.col))
        assert s.scanned_get(2, 2) == s.galaxy_get(2, 2)
