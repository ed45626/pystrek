"""
test_shields.py  –  SST3 Python Edition
Version 0.3.0

Tests for the shields command/event architecture.

All tests call execute_shields(state, ShieldsCommand(...)) directly and
assert on the returned list[Event].  No input() mocking needed.
"""

import pytest
from state import GameState
from commands import ShieldsCommand
from shields import execute_shields
from events import (
    ShieldControlInoperable, ShieldsUnchanged, ShieldsSet,
    find_one, find,
)
from config import DEV_SHIELDS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _state(energy=2000.0, shields=500.0):
    s = GameState()
    s.energy  = energy
    s.shields = shields
    return s


def she(state, level):
    return execute_shields(state, ShieldsCommand(level=float(level)))


# ---------------------------------------------------------------------------
# Validation events
# ---------------------------------------------------------------------------

class TestShieldsValidation:

    def test_inoperable_when_damaged(self):
        s = _state(); s.damage[DEV_SHIELDS] = -1.0
        evs = she(s, 500)
        assert find_one(evs, ShieldControlInoperable) is not None
        assert len(evs) == 1

    def test_inoperable_does_not_mutate_state(self):
        s = _state(energy=2000.0, shields=500.0)
        s.damage[DEV_SHIELDS] = -1.0
        she(s, 800)
        assert s.energy  == pytest.approx(2000.0)
        assert s.shields == pytest.approx(500.0)

    def test_negative_request_returns_unchanged(self):
        s = _state()
        evs = she(s, -100)
        ev = find_one(evs, ShieldsUnchanged)
        assert ev is not None
        assert ev.reason == 'negative'

    def test_same_value_returns_unchanged(self):
        s = _state(shields=500.0)
        evs = she(s, 500)
        ev = find_one(evs, ShieldsUnchanged)
        assert ev is not None
        assert ev.reason == 'same'

    def test_overspend_returns_unchanged(self):
        s = _state(energy=1000.0, shields=500.0)   # total = 1500
        evs = she(s, 9999)
        ev = find_one(evs, ShieldsUnchanged)
        assert ev is not None
        assert ev.reason == 'overspend'

    def test_unchanged_event_carries_current_shields(self):
        s = _state(shields=400.0)
        evs = she(s, -50)
        ev = find_one(evs, ShieldsUnchanged)
        assert ev.current_shields == pytest.approx(400.0)

    def test_no_mutation_on_any_rejected_command(self):
        for level in [-1, 500, 9999]:   # negative, same, overspend
            s = _state(energy=2000.0, shields=500.0)
            she(s, level)
            assert s.energy  == pytest.approx(2000.0), f"energy changed for level={level}"
            assert s.shields == pytest.approx(500.0),  f"shields changed for level={level}"


# ---------------------------------------------------------------------------
# State mutation
# ---------------------------------------------------------------------------

class TestShieldsMutation:

    def test_raises_shields(self):
        s = _state(energy=2000.0, shields=0.0)
        she(s, 800)
        assert s.shields == pytest.approx(800.0)
        assert s.energy  == pytest.approx(1200.0)

    def test_lowers_shields(self):
        s = _state(energy=1500.0, shields=800.0)
        she(s, 200)
        assert s.shields == pytest.approx(200.0)
        assert s.energy  == pytest.approx(2100.0)

    def test_set_to_zero(self):
        s = _state(energy=1000.0, shields=500.0)
        she(s, 0)
        assert s.shields == pytest.approx(0.0)
        assert s.energy  == pytest.approx(1500.0)

    def test_set_to_full_available(self):
        s = _state(energy=1000.0, shields=500.0)   # total = 1500
        she(s, 1500)
        assert s.shields == pytest.approx(1500.0)
        assert s.energy  == pytest.approx(0.0)

    def test_total_energy_always_conserved(self):
        for new_level in [0, 100, 500, 1000, 1499]:
            s = _state(energy=1000.0, shields=500.0)
            total_before = s.energy + s.shields
            she(s, new_level)
            assert s.energy + s.shields == pytest.approx(total_before), (
                f"total energy changed at level={new_level}"
            )


# ---------------------------------------------------------------------------
# ShieldsSet event fields
# ---------------------------------------------------------------------------

class TestShieldsSetEvent:

    def test_shields_set_event_emitted(self):
        s = _state(energy=2000.0, shields=0.0)
        evs = she(s, 600)
        assert find_one(evs, ShieldsSet) is not None

    def test_shields_set_only_event_on_success(self):
        s = _state(energy=2000.0, shields=0.0)
        evs = she(s, 600)
        assert len(evs) == 1

    def test_shields_before_field(self):
        s = _state(energy=2000.0, shields=300.0)
        evs = she(s, 700)
        ev = find_one(evs, ShieldsSet)
        assert ev.shields_before == pytest.approx(300.0)

    def test_shields_after_field(self):
        s = _state(energy=2000.0, shields=300.0)
        evs = she(s, 700)
        ev = find_one(evs, ShieldsSet)
        assert ev.shields_after == pytest.approx(700.0)

    def test_energy_before_field(self):
        s = _state(energy=2000.0, shields=300.0)
        evs = she(s, 700)
        ev = find_one(evs, ShieldsSet)
        assert ev.energy_before == pytest.approx(2000.0)

    def test_energy_after_field(self):
        s = _state(energy=2000.0, shields=300.0)
        evs = she(s, 700)
        ev = find_one(evs, ShieldsSet)
        # total = 2300, new shields = 700, new energy = 1600
        assert ev.energy_after == pytest.approx(1600.0)

    def test_event_fields_match_state_after(self):
        s = _state(energy=1800.0, shields=200.0)
        evs = she(s, 1000)
        ev = find_one(evs, ShieldsSet)
        assert ev.shields_after == pytest.approx(s.shields)
        assert ev.energy_after  == pytest.approx(s.energy)


# ---------------------------------------------------------------------------
# Parametric energy conservation sweep
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("energy,shields,new_level", [
    (3000.0,    0.0,  500.0),
    (2500.0,  500.0,    0.0),
    (1000.0,  500.0, 1500.0),   # exactly full available
    (   0.0, 1000.0,  200.0),   # energy is zero, shifting from shields
    (1500.0,  300.0,  300.0),   # no-op (same) — no mutation
])
def test_energy_conservation_parametric(energy, shields, new_level):
    s = _state(energy=energy, shields=shields)
    total = energy + shields
    she(s, new_level)
    assert s.energy + s.shields == pytest.approx(total)
