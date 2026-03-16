"""
test_state.py  –  SST3 Python Edition
Version 0.1.0

Tests for state.py: Klingon, Prefs, and GameState dataclasses.
"""

import math
import pytest
from state import Klingon, Prefs, GameState
from config import DEFAULT_ENERGY, DEFAULT_TORPEDOES, DEVICE_NAMES


# ---------------------------------------------------------------------------
# Klingon
# ---------------------------------------------------------------------------

class TestKlingon:

    def test_alive_when_positive_energy(self):
        k = Klingon(row=3, col=5, energy=100.0)
        assert k.alive is True

    def test_dead_when_zero_energy(self):
        k = Klingon(row=1, col=1, energy=0.0)
        assert k.alive is False

    def test_dead_when_negative_energy(self):
        k = Klingon(row=1, col=1, energy=-50.0)
        assert k.alive is False

    def test_fields_stored_correctly(self):
        k = Klingon(row=4, col=7, energy=250.5)
        assert k.row    == 4
        assert k.col    == 7
        assert k.energy == 250.5


# ---------------------------------------------------------------------------
# Prefs
# ---------------------------------------------------------------------------

class TestPrefs:

    def test_default_values(self):
        p = Prefs()
        assert p.displook   == 1
        assert p.monochrome is False
        assert p.exit_mode  == 0
        assert p.err_trap   == 0

    def test_from_dict_full(self):
        d = {"displook": 2, "monochrome": True, "mono_color": 7,
             "mono_bg": 0, "exit_mode": 1, "err_trap": 1}
        p = Prefs.from_dict(d)
        assert p.displook   == 2
        assert p.monochrome is True
        assert p.exit_mode  == 1

    def test_from_dict_partial(self):
        """Unspecified fields should use defaults."""
        p = Prefs.from_dict({"displook": 3})
        assert p.displook   == 3
        assert p.monochrome is False  # default

    def test_from_dict_ignores_unknown_keys(self):
        p = Prefs.from_dict({"displook": 0, "nonexistent_key": 99})
        assert p.displook == 0

    def test_to_dict_round_trip(self):
        p = Prefs(displook=2, monochrome=True, exit_mode=1)
        d = p.to_dict()
        p2 = Prefs.from_dict(d)
        assert p2.displook   == p.displook
        assert p2.monochrome == p.monochrome
        assert p2.exit_mode  == p.exit_mode


# ---------------------------------------------------------------------------
# GameState: galaxy helpers
# ---------------------------------------------------------------------------

class TestGameStateGalaxyHelpers:

    @pytest.fixture
    def state(self):
        return GameState()

    def test_galaxy_get_set_round_trip(self, state):
        state.galaxy_set(3, 5, 215)
        assert state.galaxy_get(3, 5) == 215

    def test_galaxy_indices_1_to_8(self, state):
        for r in range(1, 9):
            for c in range(1, 9):
                state.galaxy_set(r, c, r * 100 + c)
        for r in range(1, 9):
            for c in range(1, 9):
                assert state.galaxy_get(r, c) == r * 100 + c

    def test_galaxy_set_does_not_bleed_across_cells(self, state):
        state.galaxy_set(1, 1, 999)
        state.galaxy_set(1, 2, 0)
        assert state.galaxy_get(1, 1) == 999
        assert state.galaxy_get(1, 2) == 0

    def test_scanned_get_set_round_trip(self, state):
        state.scanned_set(7, 2, 312)
        assert state.scanned_get(7, 2) == 312

    def test_default_galaxy_all_zero(self, state):
        for r in range(1, 9):
            for c in range(1, 9):
                assert state.galaxy_get(r, c) == 0

    def test_default_scanned_all_zero(self, state):
        for r in range(1, 9):
            for c in range(1, 9):
                assert state.scanned_get(r, c) == 0


# ---------------------------------------------------------------------------
# GameState: device helpers
# ---------------------------------------------------------------------------

class TestGameStateDeviceHelpers:

    @pytest.fixture
    def state(self):
        return GameState()

    def test_device_ok_when_zero(self, state):
        for i in range(8):
            assert state.is_device_ok(i) is True

    def test_device_damaged_when_negative(self, state):
        state.damage[3] = -2.5
        assert state.is_device_ok(3) is False

    def test_device_ok_when_positive(self, state):
        state.damage[0] = 1.5   # over-repaired
        assert state.is_device_ok(0) is True

    def test_device_name_returns_string(self, state):
        for i in range(8):
            name = state.device_name(i)
            assert isinstance(name, str)
            assert len(name) > 0

    def test_device_names_match_config(self, state):
        for i, expected in enumerate(DEVICE_NAMES):
            assert state.device_name(i) == expected


# ---------------------------------------------------------------------------
# GameState: distance_to_klingon
# ---------------------------------------------------------------------------

class TestDistanceToKlingon:

    @pytest.fixture
    def state(self):
        s = GameState()
        s.sec_row = 4
        s.sec_col = 4
        return s

    def test_distance_to_same_sector_is_zero(self, state):
        k = Klingon(row=4, col=4, energy=100)
        assert state.distance_to_klingon(k) == pytest.approx(0.0)

    def test_horizontal_distance(self, state):
        k = Klingon(row=4, col=7, energy=100)
        assert state.distance_to_klingon(k) == pytest.approx(3.0)

    def test_vertical_distance(self, state):
        k = Klingon(row=1, col=4, energy=100)
        assert state.distance_to_klingon(k) == pytest.approx(3.0)

    def test_diagonal_distance(self, state):
        # 3,4 → 7,8 = (4,4) delta → sqrt(32)
        state.sec_row = 3
        state.sec_col = 4
        k = Klingon(row=7, col=8, energy=100)
        expected = math.sqrt(4**2 + 4**2)
        assert state.distance_to_klingon(k) == pytest.approx(expected)

    def test_known_pythagorean_triple(self, state):
        state.sec_row = 1
        state.sec_col = 1
        k = Klingon(row=4, col=5, energy=100)   # delta (3,4) → dist 5
        assert state.distance_to_klingon(k) == pytest.approx(5.0)

    def test_distance_is_symmetric(self, state):
        k = Klingon(row=2, col=7, energy=100)
        d1 = state.distance_to_klingon(k)
        state.sec_row = k.row
        state.sec_col = k.col
        k2 = Klingon(row=4, col=4, energy=100)
        d2 = state.distance_to_klingon(k2)
        assert d1 == pytest.approx(d2)


# ---------------------------------------------------------------------------
# GameState: condition
# ---------------------------------------------------------------------------

class TestCondition:

    def test_docked_overrides_all(self):
        s = GameState()
        s.docked = True
        s.klingons_here = 3   # would be RED if not docked
        assert s.condition() == "DOCKED"

    def test_red_when_klingons_present(self):
        s = GameState()
        s.docked = False
        s.klingons_here = 1
        assert s.condition() == "*RED*"

    def test_yellow_when_low_energy(self):
        s = GameState()
        s.docked = False
        s.klingons_here = 0
        s.max_energy = 3000.0
        s.energy  = 150.0    # 5% of max
        s.shields = 0.0
        assert s.condition() == "YELLOW"

    def test_green_when_healthy(self):
        s = GameState()
        s.docked = False
        s.klingons_here = 0
        s.max_energy = 3000.0
        s.energy  = 2800.0
        s.shields = 0.0
        assert s.condition() == "GREEN"

    def test_yellow_threshold_boundary_exact(self):
        """
        The BASIC uses E < E0*0.1 (strict less-than), so exactly 10% is GREEN.
        YELLOW requires strictly below 10%.
        """
        s = GameState()
        s.docked = False
        s.klingons_here = 0
        s.max_energy = 1000.0
        s.energy  = 100.0   # exactly 10% → GREEN (strict <)
        s.shields = 0.0
        assert s.condition() == "GREEN"

    def test_yellow_threshold_strictly_below(self):
        """One unit below 10% → YELLOW."""
        s = GameState()
        s.docked = False
        s.klingons_here = 0
        s.max_energy = 1000.0
        s.energy  = 99.9    # < 10%
        s.shields = 0.0
        assert s.condition() == "YELLOW"

    def test_green_just_above_yellow_threshold(self):
        s = GameState()
        s.docked = False
        s.klingons_here = 0
        s.max_energy = 1000.0
        s.energy  = 101.0   # just above 10%
        s.shields = 0.0
        assert s.condition() == "GREEN"

    def test_shields_count_toward_energy_for_condition(self):
        """shields + energy > 10% → GREEN, not YELLOW."""
        s = GameState()
        s.docked = False
        s.klingons_here = 0
        s.max_energy = 1000.0
        s.energy  = 50.0
        s.shields = 100.0   # together = 150 = 15% > 10%
        assert s.condition() == "GREEN"


# ---------------------------------------------------------------------------
# GameState: alive_klingons
# ---------------------------------------------------------------------------

class TestAliveKlingons:

    def test_all_alive(self):
        s = GameState()
        s.klingons = [
            Klingon(1, 1, 100),
            Klingon(2, 2, 200),
            Klingon(3, 3, 50),
        ]
        assert len(s.alive_klingons()) == 3

    def test_some_dead(self):
        s = GameState()
        s.klingons = [
            Klingon(1, 1, 100),
            Klingon(2, 2, 0),    # dead
            Klingon(3, 3, -10),  # dead
        ]
        alive = s.alive_klingons()
        assert len(alive) == 1
        assert alive[0].row == 1

    def test_all_dead(self):
        s = GameState()
        s.klingons = [Klingon(1, 1, 0), Klingon(2, 2, 0)]
        assert s.alive_klingons() == []

    def test_empty_klingon_list(self):
        s = GameState()
        s.klingons = []
        assert s.alive_klingons() == []


# ---------------------------------------------------------------------------
# GameState: time_remaining
# ---------------------------------------------------------------------------

class TestTimeRemaining:

    def test_full_time_at_start(self):
        s = GameState()
        s.start_stardate = 2000.0
        s.mission_days   = 25
        s.stardate       = 2000.0
        assert s.time_remaining() == pytest.approx(25.0)

    def test_decreases_as_stardate_advances(self):
        s = GameState()
        s.start_stardate = 2000.0
        s.mission_days   = 25
        s.stardate       = 2010.0
        assert s.time_remaining() == pytest.approx(15.0)

    def test_zero_when_expired(self):
        s = GameState()
        s.start_stardate = 2000.0
        s.mission_days   = 25
        s.stardate       = 2025.0
        assert s.time_remaining() == pytest.approx(0.0)

    def test_negative_when_overdue(self):
        s = GameState()
        s.start_stardate = 2000.0
        s.mission_days   = 25
        s.stardate       = 2030.0
        assert s.time_remaining() < 0
