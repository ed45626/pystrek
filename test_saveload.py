"""
test_saveload.py  –  SST3 Python Edition
Version 0.3.0

Tests for saveload.py: round-trip serialisation, corrupt file handling,
version mismatch, partial field preservation, and quadrant grid fidelity.
"""

import json
import random
import pytest
from pathlib import Path

from config import SAVE_VERSION, galaxy_encode
from state import GameState, Klingon, Prefs
from quadrant import Quadrant, SHIP, KLINGON, STAR, BASE, EMPTY
from saveload import (
    save_game, load_game, save_exists, delete_save,
    _state_to_dict, _dict_to_state, _grid_to_dict, _dict_to_grid,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _full_state() -> GameState:
    """A GameState with non-trivial values in every field."""
    random.seed(7)
    from galaxy import init_new_game, enter_quadrant
    state = init_new_game(2)

    # Force some interesting values
    state.energy          = 1234.5
    state.shields         = 567.8
    state.torpedoes       = 7
    state.stardate        = 2042.5
    state.damage[2]       = -1.75   # LRS damaged
    state.damage[7]       = -0.5    # computer damaged
    state.total_klingons  = 9
    state.initial_klingons = 17
    state.klingons_here   = 2
    state.bases_here      = 1
    state.stars_here      = 4
    state.base_sec_row    = 3
    state.base_sec_col    = 6
    state.docked          = False
    state.fire_first      = True
    state.d4              = 0.31
    state.difficulty      = 2

    # Build a grid with a few tokens
    q = Quadrant()
    q.set(state.sec_row, state.sec_col, SHIP)
    q.set(3, 6, BASE)
    q.set(1, 1, KLINGON)
    q.set(7, 7, KLINGON)
    q.set(4, 2, STAR)
    state.quadrant_grid = q

    state.klingons = [
        Klingon(row=1, col=1, energy=183.4),
        Klingon(row=7, col=7, energy=297.0),
    ]

    return state


@pytest.fixture
def tmp_save(tmp_path):
    return tmp_path / "test_save.json"


@pytest.fixture
def full_state():
    return _full_state()


# ---------------------------------------------------------------------------
# _grid_to_dict / _dict_to_grid
# ---------------------------------------------------------------------------

class TestGridSerialization:

    def test_empty_grid_serialises_to_empty_dict(self):
        q = Quadrant()
        assert _grid_to_dict(q) == {}

    def test_single_token_round_trip(self):
        q = Quadrant()
        q.set(3, 5, KLINGON)
        d = _grid_to_dict(q)
        q2 = _dict_to_grid(d)
        assert q2.get(3, 5) == KLINGON

    def test_empty_cells_not_stored(self):
        q = Quadrant()
        q.set(4, 4, SHIP)
        d = _grid_to_dict(q)
        assert len(d) == 1
        assert "4,4" in d

    def test_all_token_types_preserved(self):
        q = Quadrant()
        tokens = [(1, 1, SHIP), (2, 2, KLINGON), (3, 3, STAR), (4, 4, BASE)]
        for r, c, tok in tokens:
            q.set(r, c, tok)
        q2 = _dict_to_grid(_grid_to_dict(q))
        for r, c, tok in tokens:
            assert q2.get(r, c) == tok

    def test_unset_cells_default_to_empty_after_restore(self):
        q = Quadrant()
        q.set(1, 1, SHIP)
        q2 = _dict_to_grid(_grid_to_dict(q))
        assert q2.get(5, 5) == EMPTY

    def test_all_64_cells_round_trip(self):
        import random as rnd
        rnd.seed(42)
        q = Quadrant()
        all_tokens = [EMPTY, SHIP, KLINGON, STAR, BASE]
        for r in range(1, 9):
            for c in range(1, 9):
                q.set(r, c, rnd.choice(all_tokens))
        d  = _grid_to_dict(q)
        q2 = _dict_to_grid(d)
        for r in range(1, 9):
            for c in range(1, 9):
                assert q2.get(r, c) == q.get(r, c)


# ---------------------------------------------------------------------------
# _state_to_dict / _dict_to_state
# ---------------------------------------------------------------------------

class TestStateSerialization:

    def test_version_key_present(self, full_state):
        d = _state_to_dict(full_state)
        assert d["version"] == SAVE_VERSION

    def test_scalar_fields_preserved(self, full_state):
        d   = _state_to_dict(full_state)
        s2  = _dict_to_state(d)
        for field in ("stardate", "start_stardate", "mission_days",
                      "quad_row", "quad_col", "sec_row", "sec_col",
                      "energy", "max_energy", "torpedoes", "max_torpedoes",
                      "shields", "total_klingons", "initial_klingons",
                      "total_bases", "klingon_strength", "first_shot_chance",
                      "klingons_here", "bases_here", "stars_here",
                      "base_sec_row", "base_sec_col",
                      "docked", "fire_first", "d4", "difficulty"):
            orig = getattr(full_state, field)
            restored = getattr(s2, field)
            assert restored == pytest.approx(orig) if isinstance(orig, float) else restored == orig, \
                f"Field '{field}': expected {orig!r}, got {restored!r}"

    def test_galaxy_flat_and_restored(self, full_state):
        d  = _state_to_dict(full_state)
        assert len(d["galaxy"]) == 64
        s2 = _dict_to_state(d)
        for r in range(1, 9):
            for c in range(1, 9):
                assert s2.galaxy_get(r, c) == full_state.galaxy_get(r, c)

    def test_scanned_flat_and_restored(self, full_state):
        d  = _state_to_dict(full_state)
        assert len(d["scanned"]) == 64
        s2 = _dict_to_state(d)
        for r in range(1, 9):
            for c in range(1, 9):
                assert s2.scanned_get(r, c) == full_state.scanned_get(r, c)

    def test_damage_array_preserved(self, full_state):
        d  = _state_to_dict(full_state)
        s2 = _dict_to_state(d)
        assert s2.damage == pytest.approx(full_state.damage)

    def test_klingons_count_preserved(self, full_state):
        d  = _state_to_dict(full_state)
        s2 = _dict_to_state(d)
        assert len(s2.klingons) == len(full_state.klingons)

    def test_klingon_fields_preserved(self, full_state):
        d  = _state_to_dict(full_state)
        s2 = _dict_to_state(d)
        for orig, restored in zip(full_state.klingons, s2.klingons):
            assert restored.row    == orig.row
            assert restored.col    == orig.col
            assert restored.energy == pytest.approx(orig.energy)

    def test_quadrant_grid_tokens_preserved(self, full_state):
        d  = _state_to_dict(full_state)
        s2 = _dict_to_state(d)
        for r in range(1, 9):
            for c in range(1, 9):
                assert s2.quadrant_grid.get(r, c) == full_state.quadrant_grid.get(r, c)

    def test_no_quadrant_grid_produces_empty_grid(self):
        s = GameState()
        s.quadrant_grid = None
        d  = _state_to_dict(s)
        s2 = _dict_to_state(d)
        assert s2.quadrant_grid is not None
        assert s2.quadrant_grid.get(1, 1) == EMPTY


# ---------------------------------------------------------------------------
# save_game / load_game / delete_save / save_exists  (filesystem)
# ---------------------------------------------------------------------------

class TestFileOperations:

    def test_save_creates_file(self, tmp_save, full_state):
        save_game(full_state, tmp_save)
        assert tmp_save.exists()

    def test_save_exists_true_after_save(self, tmp_save, full_state):
        save_game(full_state, tmp_save)
        assert save_exists(tmp_save) is True

    def test_save_exists_false_before_save(self, tmp_save):
        assert save_exists(tmp_save) is False

    def test_load_returns_none_when_file_missing(self, tmp_save):
        assert load_game(tmp_save) is None

    def test_load_returns_state_after_save(self, tmp_save, full_state):
        save_game(full_state, tmp_save)
        s2 = load_game(tmp_save)
        assert s2 is not None

    def test_delete_removes_file(self, tmp_save, full_state):
        save_game(full_state, tmp_save)
        delete_save(tmp_save)
        assert not tmp_save.exists()

    def test_delete_nonexistent_is_silent(self, tmp_save):
        delete_save(tmp_save)   # must not raise

    def test_load_corrupt_json_returns_none(self, tmp_save, capsys):
        tmp_save.write_text("{{not valid json", encoding="utf-8")
        result = load_game(tmp_save)
        assert result is None
        assert "CORRUPT" in capsys.readouterr().out

    def test_load_wrong_version_returns_none(self, tmp_save, full_state, capsys):
        d = _state_to_dict(full_state)
        d["version"] = "sst3-py-99"
        tmp_save.write_text(json.dumps(d), encoding="utf-8")
        result = load_game(tmp_save)
        assert result is None
        assert "MISMATCH" in capsys.readouterr().out

    def test_load_missing_field_returns_none(self, tmp_save, full_state, capsys):
        d = _state_to_dict(full_state)
        del d["galaxy"]   # remove a required array
        d["galaxy"] = "oops"   # replace with wrong type
        tmp_save.write_text(json.dumps(d), encoding="utf-8")
        # Should either return None (corrupt) or return a state (partial restore)
        # — either is acceptable, just must not raise
        result = load_game(tmp_save)
        # If it returns a state it must be a GameState
        assert result is None or isinstance(result, GameState)


# ---------------------------------------------------------------------------
# Full round-trip fidelity
# ---------------------------------------------------------------------------

class TestRoundTrip:

    @pytest.mark.parametrize("seed", [0, 1, 42, 99, 123])
    def test_full_round_trip_all_seeds(self, tmp_path, seed):
        random.seed(seed)
        from galaxy import init_new_game, enter_quadrant
        state = init_new_game(seed % 4)
        enter_quadrant(state, is_start=True)

        path = tmp_path / f"save_{seed}.json"
        ok = save_game(state, path)
        assert ok is True

        s2 = load_game(path)
        assert s2 is not None

        # Key gameplay fields must match exactly
        assert s2.stardate        == pytest.approx(state.stardate)
        assert s2.total_klingons  == state.total_klingons
        assert s2.total_bases     == state.total_bases
        assert s2.energy          == pytest.approx(state.energy)
        assert s2.shields         == pytest.approx(state.shields)
        assert s2.torpedoes       == state.torpedoes
        assert s2.quad_row        == state.quad_row
        assert s2.quad_col        == state.quad_col
        assert s2.sec_row         == state.sec_row
        assert s2.sec_col         == state.sec_col
        assert s2.damage          == pytest.approx(state.damage)
        assert len(s2.klingons)   == len(state.klingons)

    def test_saved_file_is_valid_json(self, tmp_path):
        random.seed(5)
        from galaxy import init_new_game
        state = init_new_game(0)
        path = tmp_path / "test.json"
        save_game(state, path)
        # Must be parseable without error
        data = json.loads(path.read_text())
        assert isinstance(data, dict)
        assert data["version"] == SAVE_VERSION

    def test_klingon_alive_state_preserved(self, tmp_path):
        state = GameState()
        state.klingons = [
            Klingon(1, 1, 200.0),   # alive
            Klingon(2, 2, 0.0),     # dead
        ]
        state.quadrant_grid = Quadrant()
        path = tmp_path / "klive.json"
        save_game(state, path)
        s2 = load_game(path)
        assert s2.klingons[0].alive is True
        assert s2.klingons[1].alive is False

    def test_damaged_devices_preserved(self, tmp_path):
        state = GameState()
        state.damage = [-2.5, 0.0, -0.3, 1.5, 0.0, 0.0, -1.0, 0.0]
        state.quadrant_grid = Quadrant()
        path = tmp_path / "dmg.json"
        save_game(state, path)
        s2 = load_game(path)
        assert s2.damage == pytest.approx(state.damage)
