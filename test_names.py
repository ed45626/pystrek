"""
test_names.py  –  SST3 Python Edition
Version 0.1.0

Tests for names.py: quadrant_name() lookup matching BASIC lines 9010-9260.
"""

import pytest
from names import quadrant_name


# ---------------------------------------------------------------------------
# Known values from BASIC source
# ---------------------------------------------------------------------------

WEST_REGIONS = [
    "ANTARES", "RIGEL", "PROCYON", "VEGA",
    "CANOPUS", "ALTAIR", "SAGITTARIUS", "POLLUX",
]
EAST_REGIONS = [
    "SIRIUS", "DENEB", "CAPELLA", "BETELGEUSE",
    "ALDEBARAN", "REGULUS", "ARCTURUS", "SPICA",
]
SUFFIXES = [" I", " II", " III", " IV"]


class TestKnownValues:
    """
    Spot-check every region/sector combination against the BASIC lookup tables.
    The BASIC uses ON Z4 GOTO to pick the region and ON Z5 GOTO for the suffix,
    with Z5 values 1-4 mapping to I-IV and values 5-8 cycling back to I-IV.
    """

    # West half: columns 1-4
    @pytest.mark.parametrize("row,expected_region", enumerate(WEST_REGIONS, 1))
    def test_west_region_names(self, row, expected_region):
        for col in range(1, 5):
            name = quadrant_name(row, col)
            assert name.startswith(expected_region), (
                f"({row},{col}) expected region {expected_region!r}, got {name!r}"
            )

    # East half: columns 5-8
    @pytest.mark.parametrize("row,expected_region", enumerate(EAST_REGIONS, 1))
    def test_east_region_names(self, row, expected_region):
        for col in range(5, 9):
            name = quadrant_name(row, col)
            assert name.startswith(expected_region), (
                f"({row},{col}) expected region {expected_region!r}, got {name!r}"
            )

    @pytest.mark.parametrize("col,expected_suffix", [
        (1, " I"), (2, " II"), (3, " III"), (4, " IV"),
        (5, " I"), (6, " II"), (7, " III"), (8, " IV"),
    ])
    def test_sector_suffixes(self, col, expected_suffix):
        name = quadrant_name(1, col)   # ANTARES/SIRIUS row
        assert name.endswith(expected_suffix), (
            f"col={col}: expected suffix {expected_suffix!r}, got {name!r}"
        )

    # Specific cells matching BASIC ON Z4/Z5 GOTO cascades
    @pytest.mark.parametrize("row,col,expected", [
        (1, 1, "ANTARES I"),
        (1, 4, "ANTARES IV"),
        (1, 5, "SIRIUS I"),
        (1, 8, "SIRIUS IV"),
        (8, 1, "POLLUX I"),
        (8, 4, "POLLUX IV"),
        (8, 5, "SPICA I"),
        (8, 8, "SPICA IV"),
        (7, 1, "SAGITTARIUS I"),
        (7, 5, "ARCTURUS I"),
        (4, 3, "VEGA III"),
        (5, 6, "ALDEBARAN II"),
        (3, 4, "PROCYON IV"),
        (6, 7, "REGULUS III"),
    ])
    def test_specific_cells(self, row, col, expected):
        assert quadrant_name(row, col) == expected


# ---------------------------------------------------------------------------
# region_only=True
# ---------------------------------------------------------------------------

class TestRegionOnly:

    def test_region_only_returns_bare_name(self):
        assert quadrant_name(1, 1, region_only=True) == "ANTARES"
        assert quadrant_name(1, 5, region_only=True) == "SIRIUS"
        assert quadrant_name(8, 8, region_only=True) == "SPICA"

    def test_region_only_has_no_suffix(self):
        for row in range(1, 9):
            for col in range(1, 9):
                name = quadrant_name(row, col, region_only=True)
                for suffix in [" I", " II", " III", " IV"]:
                    assert not name.endswith(suffix), (
                        f"({row},{col}) region_only name {name!r} has suffix"
                    )

    def test_full_name_is_region_plus_suffix(self):
        for row in range(1, 9):
            for col in range(1, 9):
                region = quadrant_name(row, col, region_only=True)
                full   = quadrant_name(row, col)
                assert full.startswith(region)
                assert len(full) > len(region)


# ---------------------------------------------------------------------------
# Coverage: all 64 quadrants
# ---------------------------------------------------------------------------

class TestFullCoverage:

    def test_all_64_quadrants_return_non_empty_string(self):
        for row in range(1, 9):
            for col in range(1, 9):
                name = quadrant_name(row, col)
                assert isinstance(name, str)
                assert len(name) > 0

    def test_all_64_quadrants_are_unique(self):
        names = [quadrant_name(r, c) for r in range(1, 9) for c in range(1, 9)]
        assert len(set(names)) == 64, (
            f"Expected 64 unique names, got {len(set(names))}"
        )

    def test_all_region_only_names_come_from_known_list(self):
        all_regions = set(WEST_REGIONS) | set(EAST_REGIONS)
        for row in range(1, 9):
            for col in range(1, 9):
                region = quadrant_name(row, col, region_only=True)
                assert region in all_regions, (
                    f"({row},{col}) returned unknown region {region!r}"
                )

    def test_each_region_appears_exactly_four_times(self):
        """Each region spans 4 quadrants (one per sector suffix)."""
        from collections import Counter
        counts = Counter(
            quadrant_name(r, c, region_only=True)
            for r in range(1, 9)
            for c in range(1, 9)
        )
        for region, count in counts.items():
            assert count == 4, f"Region {region!r} appears {count} times, expected 4"

    def test_each_suffix_appears_exactly_16_times(self):
        """4 rows × 4 suffix positions = 16 occurrences of each suffix."""
        from collections import Counter
        counts = Counter()
        for row in range(1, 9):
            for col in range(1, 9):
                name = quadrant_name(row, col)
                for suffix in [" I", " II", " III", " IV"]:
                    if name.endswith(suffix):
                        counts[suffix] += 1
                        break
        for suffix in [" I", " II", " III", " IV"]:
            assert counts[suffix] == 16, (
                f"Suffix {suffix!r} appears {counts[suffix]} times, expected 16"
            )
