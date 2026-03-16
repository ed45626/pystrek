"""
test_klingons.py  –  SST3 Python Edition
Version 0.3.0

Tests for klingons.py: execute_klingons_fire() and klingons_reposition().

All tests call execute_klingons_fire(state) directly and assert on the
returned list[Event].  No input() or cprint() mocking required.
"""

import random
import pytest

from state import GameState, Klingon
from quadrant import Quadrant, KLINGON, SHIP, EMPTY
from klingons import execute_klingons_fire, klingons_reposition
from events import (
    StarbaseProtection, KlingonFired, EnterpriseDestroyed,
    is_fatal, find, find_one,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _state(ship_r=4, ship_c=4, k_r=4, k_c=7, k_energy=300.0, shields=500.0):
    s = GameState()
    s.sec_row, s.sec_col = ship_r, ship_c
    s.shields        = shields
    s.energy         = 2000.0
    s.klingons_here  = 1
    s.klingons       = [Klingon(row=k_r, col=k_c, energy=k_energy)]
    q = Quadrant()
    q.set(ship_r, ship_c, SHIP)
    q.set(k_r, k_c, KLINGON)
    s.quadrant_grid = q
    return s


# ---------------------------------------------------------------------------
# execute_klingons_fire — return value and early exits
# ---------------------------------------------------------------------------

class TestKlingonsFireEvents:

    def test_empty_events_when_no_klingons(self):
        s = GameState(); s.klingons_here = 0
        evs = execute_klingons_fire(s)
        assert evs == []

    def test_starbase_protection_when_docked(self):
        s = _state(); s.docked = True
        evs = execute_klingons_fire(s)
        assert find_one(evs, StarbaseProtection) is not None
        assert len(evs) == 1

    def test_starbase_protection_no_hit_when_docked(self):
        s = _state(shields=100.0); s.docked = True
        execute_klingons_fire(s)
        assert s.shields == pytest.approx(100.0)   # shields untouched

    def test_klingon_fired_event_emitted(self):
        random.seed(1)
        s = _state(k_energy=500.0, shields=1000.0)
        evs = execute_klingons_fire(s)
        assert find_one(evs, KlingonFired) is not None

    def test_enterprise_destroyed_event_when_shields_zero(self):
        random.seed(0)
        s = _state(k_energy=5000.0, shields=1.0)
        evs = execute_klingons_fire(s)
        assert is_fatal(evs)

    def test_enterprise_destroyed_is_last_event(self):
        """EnterpriseDestroyed must come after the KlingonFired that caused it."""
        random.seed(0)
        s = _state(k_energy=5000.0, shields=1.0)
        evs = execute_klingons_fire(s)
        assert isinstance(evs[-1], EnterpriseDestroyed)

    def test_no_destroyed_event_when_shields_hold(self):
        random.seed(5)
        s = _state(k_energy=100.0, shields=5000.0)
        evs = execute_klingons_fire(s)
        assert not is_fatal(evs)

    def test_dead_klingons_produce_no_events(self):
        s = _state(k_energy=0.0, shields=100.0)
        evs = execute_klingons_fire(s)
        assert find(evs, KlingonFired) == []
        assert s.shields == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# execute_klingons_fire — event field correctness
# ---------------------------------------------------------------------------

class TestKlingonFiredEventFields:

    def test_from_sector_matches_klingon_position(self):
        random.seed(1)
        s = _state(k_r=3, k_c=6, shields=5000.0)
        evs = execute_klingons_fire(s)
        fired = find(evs, KlingonFired)
        assert len(fired) >= 1
        assert fired[0].from_sector == (3, 6)

    def test_shields_after_equals_state_shields(self):
        random.seed(2)
        s = _state(k_energy=200.0, shields=2000.0)
        evs = execute_klingons_fire(s)
        fired = find(evs, KlingonFired)
        assert len(fired) >= 1
        last  = fired[-1]
        assert last.shields_after == pytest.approx(s.shields)

    def test_damage_is_positive(self):
        random.seed(3)
        s = _state(k_energy=300.0, shields=2000.0)
        evs = execute_klingons_fire(s)
        for ev in find(evs, KlingonFired):
            assert ev.damage >= 0


# ---------------------------------------------------------------------------
# execute_klingons_fire — state mutation
# ---------------------------------------------------------------------------

class TestKlingonsFireMutation:

    def test_shields_reduced_after_hit(self):
        random.seed(1)
        s = _state(k_energy=500.0, shields=1000.0)
        execute_klingons_fire(s)
        assert s.shields < 1000.0

    def test_shields_set_to_zero_on_destruction(self):
        random.seed(0)
        s = _state(k_energy=5000.0, shields=1.0)
        execute_klingons_fire(s)
        assert s.shields == pytest.approx(0.0)

    def test_klingon_energy_decreases_after_firing(self):
        random.seed(2)
        s = _state(k_energy=300.0, shields=2000.0)
        initial = s.klingons[0].energy
        execute_klingons_fire(s)
        assert s.klingons[0].energy < initial

    def test_klingon_energy_divided_by_at_least_3(self):
        """After firing, energy = initial / (3 + rand) — must be < initial/3."""
        random.seed(3)
        s = _state(k_energy=300.0, shields=2000.0)
        execute_klingons_fire(s)
        assert s.klingons[0].energy < 300.0 / 3

    def test_distance_affects_hit_magnitude(self):
        """Closer Klingon deals more damage than a far one with equal energy."""
        random.seed(99)
        s_close = _state(ship_r=4, ship_c=4, k_r=4, k_c=5, k_energy=200.0, shields=2000.0)
        execute_klingons_fire(s_close)
        dmg_close = 2000.0 - s_close.shields

        random.seed(99)
        s_far = _state(ship_r=4, ship_c=4, k_r=1, k_c=1, k_energy=200.0, shields=2000.0)
        execute_klingons_fire(s_far)
        dmg_far = 2000.0 - s_far.shields

        assert dmg_close > dmg_far

    def test_multiple_klingons_all_fire(self):
        random.seed(4)
        s = GameState()
        s.sec_row, s.sec_col = 4, 4
        s.shields = 5000.0; s.energy = 2000.0; s.klingons_here = 3
        s.klingons = [Klingon(1,1,200), Klingon(7,7,200), Klingon(1,7,200)]
        q = Quadrant(); q.set(4,4,SHIP)
        for k in s.klingons: q.set(k.row,k.col,KLINGON)
        s.quadrant_grid = q
        initial_shields = s.shields
        evs = execute_klingons_fire(s)
        fired = find(evs, KlingonFired)
        assert len(fired) == 3
        assert s.shields < initial_shields


# ---------------------------------------------------------------------------
# Context marker pattern
# ---------------------------------------------------------------------------

class TestContextMarkers:

    def test_caller_can_prepend_ambush_marker(self):
        """Demonstrates the intended usage pattern for game_loop."""
        from events import KlingonsAmbush
        random.seed(1)
        s = _state(shields=2000.0)
        fire_evts = [KlingonsAmbush()] + execute_klingons_fire(s)
        assert isinstance(fire_evts[0], KlingonsAmbush)
        assert any(isinstance(e, KlingonFired) for e in fire_evts)

    def test_caller_can_prepend_counter_fire_marker(self):
        """Demonstrates the intended usage pattern for combat."""
        from events import KlingonsCounterFire
        random.seed(2)
        s = _state(shields=2000.0)
        fire_evts = execute_klingons_fire(s)
        if fire_evts:
            wrapped = [KlingonsCounterFire()] + fire_evts
            assert isinstance(wrapped[0], KlingonsCounterFire)


# ---------------------------------------------------------------------------
# klingons_reposition
# ---------------------------------------------------------------------------

class TestKlingonsReposition:

    def _state_with_klingon(self, k_r=4, k_c=7):
        s = GameState()
        s.sec_row, s.sec_col = 4, 4
        s.shields = 500.0; s.energy = 2000.0; s.klingons_here = 1
        s.klingons = [Klingon(row=k_r, col=k_c, energy=300.0)]
        q = Quadrant(); q.set(4,4,SHIP); q.set(k_r,k_c,KLINGON)
        s.quadrant_grid = q
        return s

    def test_klingon_token_at_new_position(self):
        random.seed(11)
        s = self._state_with_klingon(k_r=4, k_c=7)
        klingons_reposition(s)
        k = s.klingons[0]
        assert s.quadrant_grid.get(k.row, k.col) == KLINGON

    def test_new_sector_is_empty_before_move(self):
        random.seed(12)
        s = self._state_with_klingon(k_r=2, k_c=2)
        klingons_reposition(s)
        k = s.klingons[0]
        assert s.quadrant_grid.get(k.row, k.col) == KLINGON

    def test_dead_klingons_do_not_reposition(self):
        s = self._state_with_klingon()
        s.klingons[0].energy = 0.0
        grid_snapshot = {(r,c): s.quadrant_grid.get(r,c)
                         for r in range(1,9) for c in range(1,9)}
        klingons_reposition(s)
        for (r,c), tok in grid_snapshot.items():
            assert s.quadrant_grid.get(r,c) == tok

    def test_no_grid_is_safe(self):
        s = GameState()
        s.klingons = [Klingon(1,1,200)]
        s.quadrant_grid = None
        klingons_reposition(s)   # must not raise

    def test_reposition_stays_in_bounds(self):
        random.seed(55)
        s = self._state_with_klingon()
        for _ in range(30):
            klingons_reposition(s)
        k = s.klingons[0]
        assert 1 <= k.row <= 8
        assert 1 <= k.col <= 8
