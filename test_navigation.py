"""
test_navigation.py  –  SST3 Python Edition
Version 0.3.0

Tests for the navigation command/event architecture.

All tests call execute_nav(state, NavCommand(...)) directly and assert on
the returned list[Event].  No monkeypatching of input() is needed because
the engine takes no user input — the TUI wrapper in main.py does that.
"""

import random
import math
import pytest

from state import GameState, Klingon
from quadrant import Quadrant, SHIP, KLINGON, STAR, BASE, EMPTY
from commands import NavCommand
from navigation import (
    execute_nav, _course_vector, _maneuver_energy, _damage_tick
)
from events import (
    InvalidCourse, InvalidWarp, WarpEnginesDamaged, InsufficientEnergy,
    ShieldsCrossCircuit, NavigationBlocked, GalacticPerimeterDenied,
    QuadrantEntered, ShipMoved, Docked,
    DeviceRepaired, DeviceDamaged, DeviceImproved,
    KlingonFired, EnterpriseDestroyed, StarbaseProtection,
    is_fatal, find, find_one,
)
from config import DEV_WARP, DEV_SHIELDS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _nav_state(sr=4, sc=4, qr=4, qc=4, energy=3000.0):
    """Minimal GameState positioned at a specific quadrant and sector."""
    s = GameState()
    s.sec_row, s.sec_col   = sr, sc
    s.quad_row, s.quad_col = qr, qc
    s.energy               = energy
    s.max_energy           = energy
    s.shields              = 0.0
    s.stardate             = 2000.0
    s.start_stardate       = 2000.0
    s.mission_days         = 30
    s.klingons_here        = 0
    s.klingons             = []
    q = Quadrant()
    q.set(sr, sc, SHIP)
    s.quadrant_grid = q
    return s


def nav(state, course, warp):
    """Convenience: execute_nav with a simple NavCommand."""
    return execute_nav(state, NavCommand(course=float(course), warp=float(warp)))


# ---------------------------------------------------------------------------
# _course_vector  — cardinal and fractional directions
# ---------------------------------------------------------------------------

class TestCourseVector:

    @pytest.mark.parametrize("course,expected_dr,expected_dc", [
        (1.0,  0.0,  1.0),  (2.0, -1.0,  1.0),  (3.0, -1.0,  0.0),
        (4.0, -1.0, -1.0),  (5.0,  0.0, -1.0),  (6.0,  1.0, -1.0),
        (7.0,  1.0,  0.0),  (8.0,  1.0,  1.0),  (9.0,  0.0,  1.0),
    ])
    def test_cardinal_vectors(self, course, expected_dr, expected_dc):
        dr, dc = _course_vector(course)
        assert dr == pytest.approx(expected_dr)
        assert dc == pytest.approx(expected_dc)

    def test_fractional_1_5_midpoint_east_ne(self):
        dr, dc = _course_vector(1.5)
        assert dr == pytest.approx(-0.5)
        assert dc == pytest.approx(1.0)

    def test_fractional_2_5_midpoint_ne_n(self):
        dr, dc = _course_vector(2.5)
        assert dr == pytest.approx(-1.0)
        assert dc == pytest.approx(0.5)

    def test_fractional_4_5_midpoint_nw_w(self):
        dr, dc = _course_vector(4.5)
        assert dr == pytest.approx(-0.5)
        assert dc == pytest.approx(-1.0)

    def test_fractional_7_5_midpoint_s_se(self):
        dr, dc = _course_vector(7.5)
        assert dr == pytest.approx(1.0)
        assert dc == pytest.approx(0.5)

    def test_opposite_courses_differ_by_4(self):
        for base in [1, 2, 3, 4]:
            dr1, dc1 = _course_vector(float(base))
            dr2, dc2 = _course_vector(float(base + 4))
            assert dr1 == pytest.approx(-dr2)
            assert dc1 == pytest.approx(-dc2)

    def test_all_magnitudes_at_most_sqrt2(self):
        for x10 in range(10, 90):
            dr, dc = _course_vector(x10 / 10.0)
            assert (dr**2 + dc**2)**0.5 <= 2**0.5 + 1e-9


# ---------------------------------------------------------------------------
# _maneuver_energy
# ---------------------------------------------------------------------------

class TestManeuverEnergy:

    def test_deducts_n_plus_10(self):
        s = GameState(); s.energy = 3000.0; s.shields = 0.0
        evs = []
        _maneuver_energy(s, 8, evs)
        assert s.energy == pytest.approx(3000.0 - 18)
        assert evs == []

    def test_draws_from_shields_when_energy_low(self):
        s = GameState(); s.energy = 5.0; s.shields = 500.0
        evs = []
        _maneuver_energy(s, 8, evs)
        assert s.energy == pytest.approx(0.0)
        assert s.shields < 500.0
        assert len(find(evs, ShieldsCrossCircuit)) == 1

    def test_shields_floor_zero(self):
        s = GameState(); s.energy = 0.0; s.shields = 5.0
        evs = []
        _maneuver_energy(s, 100, evs)
        assert s.shields == pytest.approx(0.0)

    def test_no_event_when_energy_sufficient(self):
        s = GameState(); s.energy = 3000.0; s.shields = 0.0
        evs = []
        _maneuver_energy(s, 8, evs)
        assert find(evs, ShieldsCrossCircuit) == []


# ---------------------------------------------------------------------------
# _damage_tick
# ---------------------------------------------------------------------------

class TestDamageTick:

    def test_damaged_device_repairs(self):
        s = GameState(); s.damage[0] = -2.0
        evs = []; _damage_tick(s, 1.0, evs)
        assert s.damage[0] == pytest.approx(-1.0)

    def test_repair_complete_emits_event(self):
        s = GameState(); s.damage[1] = -0.5
        evs = []; _damage_tick(s, 1.0, evs)
        reps = find(evs, DeviceRepaired)
        assert len(reps) == 1
        assert reps[0].device_index == 1

    def test_random_damage_event_emitted(self):
        """Seed so the random event fires and is a damage (not repair)."""
        hits = 0
        for seed in range(200):
            random.seed(seed)
            s = GameState(); evs = []
            _damage_tick(s, 1.0, evs, random_event=True)
            if find(evs, DeviceDamaged) or find(evs, DeviceImproved):
                hits += 1
        assert 10 < hits < 190  # ~20% expected, never 0% or 100%

    def test_no_random_damage_without_flag(self):
        """In-sector navigation should never produce random damage."""
        for seed in range(200):
            random.seed(seed)
            s = GameState(); evs = []
            _damage_tick(s, 1.0, evs)  # random_event defaults to False
            assert not find(evs, DeviceDamaged)
            assert not find(evs, DeviceImproved)

    def test_fractional_warp_repairs_proportionally(self):
        s = GameState(); s.damage[2] = -3.0
        evs = []; _damage_tick(s, 0.5, evs)
        assert s.damage[2] == pytest.approx(-2.5)


# ---------------------------------------------------------------------------
# execute_nav — validation events
# ---------------------------------------------------------------------------

class TestNavValidation:

    def test_invalid_course_low(self):
        s = _nav_state()
        evs = nav(s, 0, 1)
        assert find_one(evs, InvalidCourse) is not None

    def test_invalid_course_high(self):
        s = _nav_state()
        evs = nav(s, 10, 1)
        assert find_one(evs, InvalidCourse) is not None

    def test_course_9_wraps_silently(self):
        """Course 9 is equivalent to course 1; no InvalidCourse emitted."""
        random.seed(0)
        s = _nav_state(sr=4, sc=4)
        evs = nav(s, 9, 0.5)
        assert find_one(evs, InvalidCourse) is None

    def test_warp_zero_returns_empty_events(self):
        s = _nav_state()
        evs = nav(s, 1, 0)
        assert evs == []

    def test_warp_negative_invalid(self):
        s = _nav_state()
        evs = nav(s, 1, -1)
        assert find_one(evs, InvalidWarp) is not None

    def test_warp_above_8_invalid(self):
        s = _nav_state()
        evs = nav(s, 1, 9)
        assert find_one(evs, InvalidWarp) is not None

    def test_damaged_warp_engines_blocks_high_warp(self):
        s = _nav_state()
        s.damage[DEV_WARP] = -1.0
        evs = nav(s, 1, 1.0)
        assert find_one(evs, WarpEnginesDamaged) is not None

    def test_damaged_warp_engines_allows_0_2(self):
        random.seed(0)
        s = _nav_state(sr=4, sc=2)
        s.damage[DEV_WARP] = -1.0
        evs = nav(s, 1, 0.2)
        assert find_one(evs, WarpEnginesDamaged) is None

    def test_insufficient_energy(self):
        s = _nav_state(energy=5.0)
        evs = nav(s, 1, 8)
        ev = find_one(evs, InsufficientEnergy)
        assert ev is not None
        assert ev.available == pytest.approx(5.0)

    def test_insufficient_energy_event_has_correct_fields(self):
        s = _nav_state(energy=10.0)
        s.shields = 200.0
        evs = nav(s, 1, 2.0)  # needs 16+10=26, only 10
        ev = find_one(evs, InsufficientEnergy)
        assert ev.required == 16
        assert ev.shield_energy == pytest.approx(200.0)


# ---------------------------------------------------------------------------
# execute_nav — movement events
# ---------------------------------------------------------------------------

class TestNavMovement:

    def test_ship_moved_event_emitted(self):
        random.seed(0)
        s = _nav_state(sr=4, sc=4)
        evs = nav(s, 7, 0.5)   # south, stays in quadrant
        ev = find_one(evs, ShipMoved)
        assert ev is not None
        assert ev.from_sector == (4, 4)
        # 4 steps south from row 4: 4+4=8
        assert ev.to_sector   == (8, 4)

    def test_ship_moved_energy_used_positive(self):
        random.seed(0)
        s = _nav_state(sr=4, sc=4)
        evs = nav(s, 7, 0.5)
        ev = find_one(evs, ShipMoved)
        assert ev.energy_used > 0

    def test_ship_moved_stardate_advanced(self):
        random.seed(0)
        s = _nav_state(sr=4, sc=4)
        evs = nav(s, 7, 0.5)
        ev = find_one(evs, ShipMoved)
        assert ev.stardate_after == pytest.approx(2000.5)

    def test_move_south_half_warp(self):
        random.seed(0)
        s = _nav_state(sr=2, sc=4)
        nav(s, 7, 0.5)
        assert s.sec_row == 6
        assert s.sec_col == 4

    def test_ship_token_moves_in_grid(self):
        random.seed(0)
        s = _nav_state(sr=4, sc=4)
        nav(s, 7, 0.5)
        assert s.quadrant_grid.get(4, 4) == EMPTY
        assert s.quadrant_grid.get(s.sec_row, s.sec_col) == SHIP

    def test_state_sec_row_col_updated(self):
        # warp 0.5 south: int(0.5*8+0.5) = 4 steps, row 4+4 = row 8
        random.seed(0)
        s = _nav_state(sr=4, sc=4)
        nav(s, 7, 0.5)
        assert s.sec_row == 8
        assert s.sec_col == 4

    def test_energy_deducted_after_warp(self):
        random.seed(0)
        s = _nav_state(energy=3000.0, sr=4, sc=4)
        nav(s, 7, 0.5)
        assert s.energy < 3000.0

    def test_stardate_sub_warp_fractional(self):
        """Warp 0.5 → T8 = 0.1×int(5) = 0.5."""
        random.seed(0)
        s = _nav_state(sr=4, sc=4)
        nav(s, 7, 0.5)
        assert s.stardate == pytest.approx(2000.5)


# ---------------------------------------------------------------------------
# execute_nav — collision
# ---------------------------------------------------------------------------

class TestNavCollision:

    def test_navigation_blocked_event(self):
        random.seed(0)
        s = _nav_state(sr=4, sc=2)
        s.quadrant_grid.set(4, 5, STAR)
        evs = nav(s, 1, 1.0)
        ev = find_one(evs, NavigationBlocked)
        assert ev is not None
        assert ev.stopped_sector[1] < 5

    def test_ship_does_not_land_on_obstacle(self):
        random.seed(5)
        s = _nav_state(sr=4, sc=1)
        s.quadrant_grid.set(4, 4, KLINGON)
        nav(s, 1, 1.0)
        assert s.quadrant_grid.get(4, 4) == KLINGON
        assert not (s.sec_row == 4 and s.sec_col == 4)


# ---------------------------------------------------------------------------
# execute_nav — quadrant boundary crossing
# ---------------------------------------------------------------------------

class TestNavBoundary:

    def test_bug_report_n_warp1_from_sector_row1(self):
        """
        Regression: Q7,2 sec 1,2, course 3 (N), warp 1 → Q6,2 sec 1,2.
        Old buggy formula sent ship to Q5,1 sec 8,2.
        """
        random.seed(0)
        s = _nav_state(sr=1, sc=2, qr=7, qc=2)
        nav(s, 3, 1.0)
        assert s.quad_row == 6
        assert s.quad_col == 2
        assert s.sec_row  == 1
        assert s.sec_col  == 2

    @pytest.mark.parametrize("course,exp_qr,exp_qc", [
        (1, 4, 5),   # East
        (3, 3, 4),   # North
        (5, 4, 3),   # West
        (7, 5, 4),   # South
    ])
    def test_cardinal_warp1_from_centre(self, course, exp_qr, exp_qc):
        random.seed(0)
        s = _nav_state(sr=4, sc=4, qr=4, qc=4)
        nav(s, course, 1.0)
        assert s.quad_row == exp_qr
        assert s.quad_col == exp_qc
        assert s.sec_row  == 4
        assert s.sec_col  == 4

    def test_quadrant_entered_event_on_crossing(self):
        random.seed(0)
        s = _nav_state(sr=4, sc=4, qr=4, qc=4)
        evs = nav(s, 1, 1.0)
        ev = find_one(evs, QuadrantEntered)
        assert ev is not None
        assert ev.quadrant == (4, 5)

    def test_stardate_advances_exactly_1_on_boundary(self):
        random.seed(0)
        s = _nav_state(sr=4, sc=4, qr=4, qc=4)
        nav(s, 1, 1.0)
        assert s.stardate == pytest.approx(2001.0)

    def test_galaxy_edge_emits_denied_event(self):
        random.seed(0)
        s = _nav_state(sr=4, sc=4, qr=1, qc=4)
        evs = nav(s, 3, 2.0)
        ev = find_one(evs, GalacticPerimeterDenied)
        assert ev is not None
        assert ev.clamped_quadrant[0] == 1

    def test_galaxy_edge_does_not_emit_quadrant_entered(self):
        random.seed(0)
        s = _nav_state(sr=4, sc=4, qr=1, qc=4)
        evs = nav(s, 3, 2.0)
        assert find_one(evs, QuadrantEntered) is None

    def test_warp2_crosses_two_quadrants(self):
        random.seed(0)
        s = _nav_state(sr=4, sc=4, qr=4, qc=4)
        nav(s, 1, 2.0)
        assert s.quad_row == 4
        assert s.quad_col == 6

    def test_sector_position_preserved(self):
        """Sector within the new quadrant reflects actual trajectory."""
        random.seed(0)
        s = _nav_state(sr=4, sc=3, qr=4, qc=4)
        nav(s, 1, 1.0)
        assert s.quad_col == 5
        assert s.sec_col  == 3


# ---------------------------------------------------------------------------
# execute_nav — docking
# ---------------------------------------------------------------------------

class TestNavDocking:

    def test_docked_event_when_adjacent_to_base(self):
        random.seed(0)
        s = _nav_state(sr=4, sc=2)
        s.energy = 1000.0; s.max_energy = 3000.0
        s.torpedoes = 3; s.max_torpedoes = 10
        s.bases_here = 1; s.base_sec_row = 4; s.base_sec_col = 5
        s.quadrant_grid.set(4, 5, BASE)
        evs = nav(s, 1, 0.25)   # 2 steps east → (4,4) adjacent to base at (4,5)
        ev = find_one(evs, Docked)
        assert ev is not None

    def test_docking_restores_energy(self):
        random.seed(0)
        s = _nav_state(sr=4, sc=2)
        s.energy = 1000.0; s.max_energy = 3000.0
        s.torpedoes = 3; s.max_torpedoes = 10
        s.bases_here = 1; s.base_sec_row = 4; s.base_sec_col = 5
        s.quadrant_grid.set(4, 5, BASE)
        nav(s, 1, 0.25)
        assert s.energy == s.max_energy

    def test_docking_restores_torpedoes(self):
        random.seed(0)
        s = _nav_state(sr=4, sc=2)
        s.energy = 1000.0; s.max_energy = 3000.0
        s.torpedoes = 3; s.max_torpedoes = 10
        s.bases_here = 1; s.base_sec_row = 4; s.base_sec_col = 5
        s.quadrant_grid.set(4, 5, BASE)
        nav(s, 1, 0.25)
        assert s.torpedoes == s.max_torpedoes


# ---------------------------------------------------------------------------
# execute_nav — klingon fire during warp
# ---------------------------------------------------------------------------

class TestNavKlingonFire:

    def _state_with_klingon(self):
        s = _nav_state(sr=4, sc=4)
        s.shields = 5000.0
        s.klingons_here = 1
        k = Klingon(row=1, col=1, energy=100.0)
        s.klingons = [k]
        s.quadrant_grid.set(1, 1, KLINGON)
        return s

    def test_klingon_fire_event_emitted(self):
        random.seed(1)
        s = self._state_with_klingon()
        evs = nav(s, 7, 0.5)
        fired = find(evs, KlingonFired)
        assert len(fired) >= 1

    def test_enterprise_destroyed_stops_movement(self):
        random.seed(0)
        s = self._state_with_klingon()
        s.shields = 1.0   # will be destroyed on first hit
        k = Klingon(row=4, col=5, energy=5000.0)
        s.klingons = [k]; s.quadrant_grid.set(4, 5, KLINGON)
        evs = nav(s, 7, 0.5)
        assert is_fatal(evs)
        assert find_one(evs, ShipMoved) is None   # no movement after destruction

    def test_starbase_protection_suppresses_fire(self):
        random.seed(0)
        s = self._state_with_klingon()
        s.docked = True
        evs = nav(s, 7, 0.5)
        assert find_one(evs, StarbaseProtection) is not None
        assert find_one(evs, KlingonFired) is None


# ---------------------------------------------------------------------------
# Event helpers
# ---------------------------------------------------------------------------

class TestEventHelpers:

    def test_is_fatal_true_with_destroyed_event(self):
        assert is_fatal([EnterpriseDestroyed()]) is True

    def test_is_fatal_false_without_destroyed(self):
        assert is_fatal([ShipMoved(from_sector=(1,1), to_sector=(2,2),
                                   energy_used=18, stardate_after=2001.0)]) is False

    def test_find_returns_matching_types(self):
        evs = [ShipMoved(from_sector=(1,1), to_sector=(2,2),
                          energy_used=18, stardate_after=2001.0),
               DeviceRepaired(device_index=0, device_name="Warp engines"),
               DeviceRepaired(device_index=1, device_name="Short range sensors")]
        result = find(evs, DeviceRepaired)
        assert len(result) == 2

    def test_find_one_returns_none_when_absent(self):
        evs = [ShipMoved(from_sector=(1,1), to_sector=(2,2),
                          energy_used=18, stardate_after=2001.0)]
        assert find_one(evs, EnterpriseDestroyed) is None

    def test_find_one_returns_first_match(self):
        evs = [DeviceRepaired(device_index=0, device_name="Warp engines"),
               DeviceRepaired(device_index=1, device_name="SRS")]
        ev = find_one(evs, DeviceRepaired)
        assert ev.device_index == 0
