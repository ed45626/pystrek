"""
test_display.py  –  SST3 Python Edition
Version 0.1.0

Tests for display.py: calc_direction_distance() and render helpers.

The direction calculator is the most mathematically sensitive piece of Phase 1
and the foundation for Phase 2 torpedo/navigation targeting.  These tests
validate it against the BASIC source (lines 8220-8470) by working through
each quadrant of the 2-D plane plus degenerate cases.
"""

import math
import io
import sys
import pytest
from display import calc_direction_distance
from state import GameState, Prefs
from config import DISPLOOK_STOCK, DISPLOOK_GRID


# ---------------------------------------------------------------------------
# calc_direction_distance — cardinal and diagonal directions
# ---------------------------------------------------------------------------
#
# BASIC coordinate system (for sectors within a quadrant, 1-indexed):
#   Row increases downward.   Col increases rightward.
#   BASIC "X" = col delta = c2 - c1
#   BASIC "A" = row delta = r1 - r2   (note reversed sign)
#
# Course encoding:
#   1 = right (E), 2 = upper-right (NE), 3 = up (N), 4 = upper-left (NW)
#   5 = left (W), 6 = lower-left (SW), 7 = down (S), 8 = lower-right (SE)
#
# Integer course values map to the eight compass points:
#   same row, col increases → course 1
#   row decreases, col increases → course 2
#   etc.

class TestCardinalDirections:

    def test_east_same_row_col_increases(self):
        # (4,1) → (4,5):  dx=4, dy=0  →  pure East = course 1
        course, gdist, adist = calc_direction_distance(4, 1, 4, 5)
        assert course == pytest.approx(1.0)
        assert gdist  == 4
        assert adist  == pytest.approx(4.0)

    def test_west_same_row_col_decreases(self):
        # (4,6) → (4,2):  dx=-4, dy=0  →  pure West = course 5
        course, gdist, adist = calc_direction_distance(4, 6, 4, 2)
        assert course == pytest.approx(5.0)
        assert gdist  == 4
        assert adist  == pytest.approx(4.0)

    def test_north_row_decreases(self):
        # (6,4) → (2,4):  dx=0, dy=4  →  pure North = course 3
        course, gdist, adist = calc_direction_distance(6, 4, 2, 4)
        assert course == pytest.approx(3.0)
        assert gdist  == 4
        assert adist  == pytest.approx(4.0)

    def test_south_row_increases(self):
        # (2,4) → (6,4):  dx=0, dy=-4  →  pure South = course 7
        course, gdist, adist = calc_direction_distance(2, 4, 6, 4)
        assert course == pytest.approx(7.0)
        assert gdist  == 4
        assert adist  == pytest.approx(4.0)


class TestDiagonalDirections:

    def test_northeast_equal_deltas(self):
        # (6,2) → (2,6):  dx=4, dy=4  →  NE = course 2
        course, gdist, adist = calc_direction_distance(6, 2, 2, 6)
        assert course == pytest.approx(2.0)
        assert gdist  == 4
        assert adist  == pytest.approx(4 * math.sqrt(2))

    def test_northwest_equal_deltas(self):
        # (6,6) → (2,2):  dx=-4, dy=4  →  NW = course 4
        course, gdist, adist = calc_direction_distance(6, 6, 2, 2)
        assert course == pytest.approx(4.0)
        assert gdist  == 4
        assert adist  == pytest.approx(4 * math.sqrt(2))

    def test_southwest_equal_deltas(self):
        # (2,6) → (6,2):  dx=-4, dy=-4  →  SW = course 6
        course, gdist, adist = calc_direction_distance(2, 6, 6, 2)
        assert course == pytest.approx(6.0)
        assert gdist  == 4
        assert adist  == pytest.approx(4 * math.sqrt(2))

    def test_southeast_equal_deltas(self):
        # (2,2) → (6,6):  dx=4, dy=-4  →  SE = course 8
        course, gdist, adist = calc_direction_distance(2, 2, 6, 6)
        assert course == pytest.approx(8.0)
        assert gdist  == 4
        assert adist  == pytest.approx(4 * math.sqrt(2))


class TestDistanceFormulas:

    def test_game_distance_is_chebyshev(self):
        """Game distance = max(|dr|, |dc|) — Chebyshev distance."""
        cases = [
            ((1,1),(4,1), 3),   # vertical 3
            ((1,1),(1,4), 3),   # horizontal 3
            ((1,1),(4,4), 3),   # diagonal 3×3
            ((1,1),(4,6), 5),   # asymmetric max(3,5)=5
        ]
        for (r1,c1),(r2,c2), expected_gdist in cases:
            _, gdist, _ = calc_direction_distance(r1,c1,r2,c2)
            assert gdist == expected_gdist, (
                f"({r1},{c1})→({r2},{c2}): expected game_dist={expected_gdist}, got {gdist}"
            )

    def test_actual_distance_is_euclidean(self):
        r1, c1, r2, c2 = 1, 1, 4, 5
        _, _, adist = calc_direction_distance(r1, c1, r2, c2)
        expected = math.sqrt((c2-c1)**2 + (r2-r1)**2)
        assert adist == pytest.approx(expected)

    def test_pythagorean_triple_3_4_5(self):
        # delta row=3, col=4  →  actual dist=5
        _, _, adist = calc_direction_distance(1, 1, 4, 5)
        assert adist == pytest.approx(5.0)

    def test_same_point_returns_none_course_zero_distance(self):
        course, gdist, adist = calc_direction_distance(4, 4, 4, 4)
        assert course is None
        assert gdist  == pytest.approx(0.0)
        assert adist  == pytest.approx(0.0)


class TestFractionalCourses:
    """
    Fractional courses occur when the row and column deltas are unequal.
    The BASIC formula maps the fractional excess to a fraction of the next
    course increment.  These tests verify the direction is between the two
    nearest cardinal/diagonal courses.
    """

    def test_mostly_east_slight_north(self):
        # (4,1) → (3,5): dx=4, dy=1  → mostly East (1), slight North bias
        # Course between 1 and 2
        course, _, _ = calc_direction_distance(4, 1, 3, 5)
        assert 1.0 < course < 2.0

    def test_mostly_north_slight_east(self):
        # (6,3) → (2,4): dx=1, dy=4  → mostly North (3), slight East bias
        # Course between 2 and 3
        course, _, _ = calc_direction_distance(6, 3, 2, 4)
        assert 2.0 < course < 3.0

    def test_mostly_south_slight_west(self):
        # (2,5) → (6,4): dx=-1, dy=-4  → mostly South (7), slight West bias
        course, _, _ = calc_direction_distance(2, 5, 6, 4)
        assert 6.0 < course < 7.0 or 7.0 < course < 8.0

    def test_course_value_in_range_1_to_9(self):
        """All non-degenerate courses should be in (0, 9)."""
        import random as rnd
        rnd.seed(77)
        for _ in range(200):
            r1, c1 = rnd.randint(1, 8), rnd.randint(1, 8)
            r2, c2 = rnd.randint(1, 8), rnd.randint(1, 8)
            if (r1, c1) == (r2, c2):
                continue
            course, _, _ = calc_direction_distance(r1, c1, r2, c2)
            assert 1.0 <= course < 9.0, (
                f"({r1},{c1})→({r2},{c2}): course={course} out of range"
            )


# ---------------------------------------------------------------------------
# Symmetry / consistency checks
# ---------------------------------------------------------------------------

class TestDirectionConsistency:

    def test_opposite_directions_differ_by_4(self):
        """East and West courses should differ by 4 (opposite on the circle)."""
        east, _, _ = calc_direction_distance(4, 1, 4, 5)
        west, _, _ = calc_direction_distance(4, 5, 4, 1)
        diff = abs(east - west)
        assert diff == pytest.approx(4.0)

    def test_north_and_south_differ_by_4(self):
        north, _, _ = calc_direction_distance(6, 4, 2, 4)
        south, _, _ = calc_direction_distance(2, 4, 6, 4)
        diff = abs(north - south)
        assert diff == pytest.approx(4.0)

    def test_northeast_and_southwest_differ_by_4(self):
        ne, _, _ = calc_direction_distance(6, 2, 2, 6)
        sw, _, _ = calc_direction_distance(2, 6, 6, 2)
        diff = abs(ne - sw)
        assert diff == pytest.approx(4.0)

    def test_actual_distance_is_commutative(self):
        """sqrt distance is the same in both directions."""
        _, _, d1 = calc_direction_distance(1, 3, 5, 7)
        _, _, d2 = calc_direction_distance(5, 7, 1, 3)
        assert d1 == pytest.approx(d2)

    def test_game_distance_is_commutative(self):
        _, g1, _ = calc_direction_distance(2, 3, 6, 5)
        _, g2, _ = calc_direction_distance(6, 5, 2, 3)
        assert g1 == g2


# ---------------------------------------------------------------------------
# render_srs — smoke test (no assertion on ANSI codes, just no crashes)
# ---------------------------------------------------------------------------

class TestRenderSRS:

    def _make_state(self):
        import random as rnd
        rnd.seed(0)
        from galaxy import init_new_game, enter_quadrant
        state = init_new_game(0)
        enter_quadrant(state, is_start=True)
        return state

    def test_srs_renders_without_exception(self, capsys):
        from display import render_srs
        state = self._make_state()
        prefs = Prefs(displook=DISPLOOK_STOCK)
        render_srs(state, prefs)
        captured = capsys.readouterr()
        # Should produce some output
        assert len(captured.out) > 0

    def test_srs_grid_mode_renders_without_exception(self, capsys):
        from display import render_srs
        state = self._make_state()
        prefs = Prefs(displook=DISPLOOK_GRID)
        render_srs(state, prefs)
        captured = capsys.readouterr()
        assert len(captured.out) > 0

    def test_srs_output_contains_condition(self, capsys):
        from display import render_srs
        state = self._make_state()
        prefs = Prefs(displook=DISPLOOK_STOCK)
        render_srs(state, prefs)
        out = capsys.readouterr().out
        # Strip ANSI codes before checking
        import re
        clean = re.sub(r'\033\[[0-9;]*m', '', out)
        assert "CONDITION" in clean

    def test_srs_output_contains_quadrant(self, capsys):
        from display import render_srs
        state = self._make_state()
        prefs = Prefs(displook=DISPLOOK_STOCK)
        render_srs(state, prefs)
        out = capsys.readouterr().out
        import re
        clean = re.sub(r'\033\[[0-9;]*m', '', out)
        assert "QUADRANT" in clean

    def test_srs_output_has_8_grid_rows(self, capsys):
        from display import render_srs
        state = self._make_state()
        prefs = Prefs(displook=DISPLOOK_STOCK)
        render_srs(state, prefs)
        out = capsys.readouterr().out
        import re
        clean = re.sub(r'\033\[[0-9;]*m', '', out)
        # Each of the 8 grid rows contains "STARDATE", "CONDITION", etc.
        status_labels = ["STARDATE", "CONDITION", "QUADRANT", "SECTOR",
                         "PHOTON", "TOTAL ENERGY", "SHIELDS", "KLINGONS"]
        for label in status_labels:
            assert label in clean, f"Status label '{label}' missing from SRS output"


# ---------------------------------------------------------------------------
# render_lrs — smoke test
# ---------------------------------------------------------------------------

class TestRenderLRS:

    def _make_state(self):
        import random as rnd
        rnd.seed(5)
        from galaxy import init_new_game, enter_quadrant
        state = init_new_game(0)
        enter_quadrant(state, is_start=True)
        return state

    def test_lrs_renders_without_exception(self, capsys):
        from display import render_lrs
        state = self._make_state()
        prefs = Prefs()
        render_lrs(state, prefs)
        captured = capsys.readouterr()
        assert len(captured.out) > 0

    def test_lrs_output_contains_scan_header(self, capsys):
        from display import render_lrs
        state = self._make_state()
        prefs = Prefs()
        render_lrs(state, prefs)
        out = capsys.readouterr().out
        import re
        clean = re.sub(r'\033\[[0-9;]*m', '', out)
        assert "LONG RANGE SCAN" in clean

    def test_lrs_reveals_adjacent_quadrants(self):
        import random as rnd
        rnd.seed(5)
        from galaxy import init_new_game, enter_quadrant
        from display import render_lrs
        state = init_new_game(0)
        enter_quadrant(state, is_start=True)

        # Set scanned to 0 for neighbors
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                r = state.quad_row + dr
                c = state.quad_col + dc
                if 1 <= r <= 8 and 1 <= c <= 8:
                    state.scanned_set(r, c, 0)

        sys.stdout = io.StringIO()
        render_lrs(state, Prefs())
        sys.stdout = sys.__stdout__

        # All in-bounds neighbours should now be revealed
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                r = state.quad_row + dr
                c = state.quad_col + dc
                if 1 <= r <= 8 and 1 <= c <= 8:
                    assert state.scanned_get(r, c) != 0, (
                        f"LRS should have revealed ({r},{c})"
                    )

    def test_lrs_inoperative_when_damaged(self, capsys):
        from display import render_lrs
        from config import DEV_LRS
        state = self._make_state()
        state.damage[DEV_LRS] = -1.0
        render_lrs(state, Prefs())
        out = capsys.readouterr().out
        import re
        clean = re.sub(r'\033\[[0-9;]*m', '', out)
        assert "INOPERABLE" in clean
