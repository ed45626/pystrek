"""
test_config.py  –  SST3 Python Edition
Version 0.1.0

Tests for config.py: constants, galaxy encode/decode, symbol tables.
"""

import pytest
from config import (
    VERSION,
    DISPLOOK_STOCK, DISPLOOK_GRID, DISPLOOK_DOTS, DISPLOOK_DIV1, DISPLOOK_DIV2,
    SYMBOLS,
    DEV_WARP, DEV_SRS, DEV_LRS, DEV_PHASERS, DEV_TORPS,
    DEV_DAMAGE, DEV_SHIELDS, DEV_COMPUTER,
    DEVICE_NAMES,
    galaxy_encode, galaxy_decode,
    DEFAULT_ENERGY, DEFAULT_TORPEDOES,
    DIFFICULTY,
    SAVE_FILENAME, PREFS_FILENAME,
)


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

def test_version_is_string():
    assert isinstance(VERSION, str)
    assert len(VERSION) > 0


def test_version_semver_format():
    parts = VERSION.split(".")
    assert len(parts) == 3
    for part in parts:
        assert part.isdigit()


# ---------------------------------------------------------------------------
# Display mode constants
# ---------------------------------------------------------------------------

def test_display_mode_values_are_distinct():
    modes = [DISPLOOK_STOCK, DISPLOOK_GRID, DISPLOOK_DOTS, DISPLOOK_DIV1, DISPLOOK_DIV2]
    assert len(set(modes)) == 5


def test_display_modes_are_non_negative_ints():
    for mode in [DISPLOOK_STOCK, DISPLOOK_GRID, DISPLOOK_DOTS, DISPLOOK_DIV1, DISPLOOK_DIV2]:
        assert isinstance(mode, int)
        assert mode >= 0


# ---------------------------------------------------------------------------
# Symbol tables
# ---------------------------------------------------------------------------

REQUIRED_TOKEN_KEYS = {"empty", "star", "klingon", "ship", "base"}


def test_symbols_have_all_modes():
    for mode in [DISPLOOK_STOCK, DISPLOOK_GRID, DISPLOOK_DOTS, DISPLOOK_DIV1, DISPLOOK_DIV2]:
        assert mode in SYMBOLS, f"Mode {mode} missing from SYMBOLS"


def test_symbols_have_all_token_keys():
    for mode, table in SYMBOLS.items():
        missing = REQUIRED_TOKEN_KEYS - set(table.keys())
        assert not missing, f"Mode {mode} missing token keys: {missing}"


def test_all_symbols_are_exactly_3_chars():
    for mode, table in SYMBOLS.items():
        for key, sym in table.items():
            assert len(sym) == 3, (
                f"Mode {mode} key '{key}' symbol {sym!r} is {len(sym)} chars, expected 3"
            )


def test_stock_symbols_match_basic_originals():
    s = SYMBOLS[DISPLOOK_STOCK]
    assert s["star"]    == " * "
    assert s["klingon"] == "+K+"
    assert s["ship"]    == "<*>"
    assert s["base"]    == ">!<"
    assert s["empty"]   == "   "


def test_grid_symbols_differ_from_stock():
    """DISPLOOK_GRID uses letter symbols for better readability."""
    stock = SYMBOLS[DISPLOOK_STOCK]
    grid  = SYMBOLS[DISPLOOK_GRID]
    # At least klingon, ship, and base should differ
    assert grid["klingon"] != stock["klingon"]
    assert grid["ship"]    != stock["ship"]
    assert grid["base"]    != stock["base"]


def test_dots_mode_empty_is_dot():
    assert SYMBOLS[DISPLOOK_DOTS]["empty"] == " . "


# ---------------------------------------------------------------------------
# Device index constants
# ---------------------------------------------------------------------------

def test_device_indices_are_0_to_7():
    indices = [DEV_WARP, DEV_SRS, DEV_LRS, DEV_PHASERS,
               DEV_TORPS, DEV_DAMAGE, DEV_SHIELDS, DEV_COMPUTER]
    assert sorted(indices) == list(range(8))


def test_device_names_count():
    assert len(DEVICE_NAMES) == 8


def test_device_names_are_non_empty_strings():
    for name in DEVICE_NAMES:
        assert isinstance(name, str)
        assert len(name) > 0


# ---------------------------------------------------------------------------
# galaxy_encode / galaxy_decode  — round-trip
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("k,b,s", [
    (0, 0, 1),
    (0, 0, 8),
    (1, 0, 3),
    (2, 0, 5),
    (3, 0, 7),
    (0, 1, 1),
    (1, 1, 4),
    (3, 1, 8),
])
def test_galaxy_encode_decode_round_trip(k, b, s):
    encoded = galaxy_encode(k, b, s)
    k2, b2, s2 = galaxy_decode(encoded)
    assert k2 == k, f"klingons mismatch for ({k},{b},{s})"
    assert b2 == b, f"bases mismatch for ({k},{b},{s})"
    assert s2 == s, f"stars mismatch for ({k},{b},{s})"


def test_galaxy_encode_formula():
    assert galaxy_encode(3, 1, 5) == 315
    assert galaxy_encode(0, 0, 1) == 1
    assert galaxy_encode(0, 1, 0) == 10


def test_galaxy_decode_known_values():
    assert galaxy_decode(315) == (3, 1, 5)
    assert galaxy_decode(200) == (2, 0, 0)
    assert galaxy_decode(10)  == (0, 1, 0)
    assert galaxy_decode(1)   == (0, 0, 1)
    assert galaxy_decode(0)   == (0, 0, 0)


def test_galaxy_decode_max_value():
    """Max realistic galaxy cell: 3 klingons, 1 base, 8 stars = 318."""
    k, b, s = galaxy_decode(318)
    assert k == 3
    assert b == 1
    assert s == 8


def test_galaxy_encode_stars_range():
    """Stars per quadrant should be 1-8."""
    for stars in range(1, 9):
        val = galaxy_encode(0, 0, stars)
        _, _, s = galaxy_decode(val)
        assert s == stars


# ---------------------------------------------------------------------------
# Default game settings
# ---------------------------------------------------------------------------

def test_default_energy_positive():
    assert DEFAULT_ENERGY > 0


def test_default_torpedoes_positive():
    assert DEFAULT_TORPEDOES > 0


def test_difficulty_has_four_levels():
    assert set(DIFFICULTY.keys()) == {0, 1, 2, 3}


def test_difficulty_tuples_are_valid():
    for level, (energy, strength, r8) in DIFFICULTY.items():
        assert energy > 0,    f"Level {level}: energy must be positive"
        assert strength > 0,  f"Level {level}: klingon_strength must be positive"
        assert 0.0 <= r8 <= 1.0, f"Level {level}: first_shot_chance must be 0-1"


def test_difficulty_increases_with_level():
    """Higher difficulty → more klingon strength, higher first-shot chance."""
    prev_e, prev_s, prev_r8 = DIFFICULTY[0]
    for level in [1, 2, 3]:
        e, s, r8 = DIFFICULTY[level]
        assert s >= prev_s,   f"Level {level}: klingon_strength should not decrease"
        assert r8 >= prev_r8, f"Level {level}: first_shot_chance should not decrease"
        prev_s, prev_r8 = s, r8


# ---------------------------------------------------------------------------
# Filenames
# ---------------------------------------------------------------------------

def test_save_filename_has_json_extension():
    assert SAVE_FILENAME.endswith(".json")


def test_prefs_filename_has_json_extension():
    assert PREFS_FILENAME.endswith(".json")


def test_filenames_are_distinct():
    assert SAVE_FILENAME != PREFS_FILENAME
