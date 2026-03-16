"""
test_prefs.py  –  SST3 Python Edition
Version 0.3.0

Tests for prefs.py: load_prefs, save_prefs, delete_prefs, round-trip,
corrupt/version handling, and partial field restoration.
"""

import json
import pytest
from pathlib import Path

from state import Prefs
from prefs import load_prefs, save_prefs, delete_prefs, PREFS_VERSION
from config import DISPLOOK_GRID, DISPLOOK_DOTS, DISPLOOK_STOCK


# ---------------------------------------------------------------------------
# load_prefs
# ---------------------------------------------------------------------------

class TestLoadPrefs:

    def test_returns_defaults_when_no_file(self, tmp_path):
        p = load_prefs(tmp_path / "nonexistent.json")
        assert isinstance(p, Prefs)
        assert p.displook == 1   # default grid

    def test_loads_saved_values(self, tmp_path):
        path = tmp_path / "prefs.json"
        data = {"version": PREFS_VERSION, "displook": DISPLOOK_DOTS,
                "monochrome": True, "exit_mode": 1, "err_trap": 1,
                "mono_color": 10, "mono_bg": 0}
        path.write_text(json.dumps(data), encoding="utf-8")
        p = load_prefs(path)
        assert p.displook   == DISPLOOK_DOTS
        assert p.monochrome is True
        assert p.exit_mode  == 1

    def test_returns_defaults_on_corrupt_json(self, tmp_path, capsys):
        path = tmp_path / "bad.json"
        path.write_text("{not json}", encoding="utf-8")
        p = load_prefs(path)
        assert isinstance(p, Prefs)
        assert "CORRUPT" in capsys.readouterr().out

    def test_returns_defaults_on_version_mismatch(self, tmp_path, capsys):
        path = tmp_path / "old.json"
        path.write_text(json.dumps({"version": "old-1", "displook": 0}), encoding="utf-8")
        p = load_prefs(path)
        assert isinstance(p, Prefs)
        assert "MISMATCH" in capsys.readouterr().out

    def test_unknown_keys_ignored(self, tmp_path):
        path = tmp_path / "extra.json"
        data = {"version": PREFS_VERSION, "displook": DISPLOOK_STOCK,
                "future_setting": 99}
        path.write_text(json.dumps(data), encoding="utf-8")
        p = load_prefs(path)
        assert p.displook == DISPLOOK_STOCK   # known field loaded
        assert not hasattr(p, "future_setting")


# ---------------------------------------------------------------------------
# save_prefs
# ---------------------------------------------------------------------------

class TestSavePrefs:

    def test_creates_file(self, tmp_path):
        path = tmp_path / "prefs.json"
        p = Prefs(displook=2)
        save_prefs(p, path)
        assert path.exists()

    def test_file_contains_version(self, tmp_path):
        path = tmp_path / "prefs.json"
        save_prefs(Prefs(), path)
        data = json.loads(path.read_text())
        assert data["version"] == PREFS_VERSION

    def test_file_is_valid_json(self, tmp_path):
        path = tmp_path / "prefs.json"
        save_prefs(Prefs(displook=3, monochrome=True), path)
        data = json.loads(path.read_text())
        assert isinstance(data, dict)

    def test_returns_true_on_success(self, tmp_path):
        path = tmp_path / "prefs.json"
        result = save_prefs(Prefs(), path)
        assert result is True

    def test_saves_all_fields(self, tmp_path):
        path = tmp_path / "prefs.json"
        p = Prefs(displook=4, monochrome=True, mono_color=7,
                  mono_bg=0, exit_mode=1, err_trap=1)
        save_prefs(p, path)
        data = json.loads(path.read_text())
        assert data["displook"]   == 4
        assert data["monochrome"] is True
        assert data["mono_color"] == 7
        assert data["exit_mode"]  == 1
        assert data["err_trap"]   == 1


# ---------------------------------------------------------------------------
# delete_prefs
# ---------------------------------------------------------------------------

class TestDeletePrefs:

    def test_deletes_existing_file(self, tmp_path):
        path = tmp_path / "prefs.json"
        save_prefs(Prefs(), path)
        delete_prefs(path)
        assert not path.exists()

    def test_silent_when_file_missing(self, tmp_path):
        path = tmp_path / "missing.json"
        delete_prefs(path)   # must not raise


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------

class TestRoundTrip:

    @pytest.mark.parametrize("displook", [0, 1, 2, 3, 4])
    def test_displook_round_trips(self, tmp_path, displook):
        path = tmp_path / "p.json"
        p = Prefs(displook=displook)
        save_prefs(p, path)
        p2 = load_prefs(path)
        assert p2.displook == displook

    def test_monochrome_true_round_trips(self, tmp_path):
        path = tmp_path / "p.json"
        save_prefs(Prefs(monochrome=True, mono_color=10), path)
        p2 = load_prefs(path)
        assert p2.monochrome is True
        assert p2.mono_color == 10

    def test_all_fields_round_trip(self, tmp_path):
        path = tmp_path / "p.json"
        orig = Prefs(displook=3, monochrome=True, mono_color=9,
                     mono_bg=1, exit_mode=1, err_trap=1)
        save_prefs(orig, path)
        restored = load_prefs(path)
        assert restored.displook   == orig.displook
        assert restored.monochrome == orig.monochrome
        assert restored.mono_color == orig.mono_color
        assert restored.mono_bg    == orig.mono_bg
        assert restored.exit_mode  == orig.exit_mode
        assert restored.err_trap   == orig.err_trap

    def test_overwrite_updates_values(self, tmp_path):
        path = tmp_path / "p.json"
        save_prefs(Prefs(displook=0), path)
        save_prefs(Prefs(displook=4), path)
        p = load_prefs(path)
        assert p.displook == 4
