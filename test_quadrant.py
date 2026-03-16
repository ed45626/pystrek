"""
test_quadrant.py  –  SST3 Python Edition
Version 0.1.0

Tests for quadrant.py: Quadrant grid class, token management, populate().
"""

import random
import pytest
from quadrant import Quadrant, EMPTY, STAR, KLINGON, SHIP, BASE
from config import DISPLOOK_STOCK, DISPLOOK_GRID, DISPLOOK_DOTS


# ---------------------------------------------------------------------------
# Token constants
# ---------------------------------------------------------------------------

class TestTokenConstants:

    def test_all_tokens_are_3_chars(self):
        for token in [EMPTY, STAR, KLINGON, SHIP, BASE]:
            assert len(token) == 3, f"Token {token!r} must be 3 chars"

    def test_tokens_are_distinct(self):
        tokens = [EMPTY, STAR, KLINGON, SHIP, BASE]
        assert len(set(tokens)) == 5


# ---------------------------------------------------------------------------
# Quadrant grid basics
# ---------------------------------------------------------------------------

class TestQuadrantBasics:

    @pytest.fixture
    def q(self):
        return Quadrant()

    def test_default_grid_all_empty(self, q):
        for r in range(1, 9):
            for c in range(1, 9):
                assert q.get(r, c) == EMPTY

    def test_set_and_get_round_trip(self, q):
        q.set(3, 5, KLINGON)
        assert q.get(3, 5) == KLINGON

    def test_set_does_not_bleed_to_adjacent_cells(self, q):
        q.set(4, 4, SHIP)
        for r in range(1, 9):
            for c in range(1, 9):
                if (r, c) == (4, 4):
                    continue
                assert q.get(r, c) == EMPTY

    def test_clear_resets_cell_to_empty(self, q):
        q.set(2, 6, STAR)
        q.clear(2, 6)
        assert q.get(2, 6) == EMPTY

    def test_overwrite_cell(self, q):
        q.set(1, 1, STAR)
        q.set(1, 1, KLINGON)
        assert q.get(1, 1) == KLINGON

    def test_set_all_corners(self, q):
        corners = [(1,1), (1,8), (8,1), (8,8)]
        tokens  = [SHIP, BASE, STAR, KLINGON]
        for (r, c), tok in zip(corners, tokens):
            q.set(r, c, tok)
        for (r, c), tok in zip(corners, tokens):
            assert q.get(r, c) == tok

    def test_set_invalid_token_raises(self, q):
        with pytest.raises(AssertionError):
            q.set(1, 1, "TOOLONG")

    def test_is_empty_true_for_default(self, q):
        assert q.is_empty(5, 5) is True

    def test_is_empty_false_after_set(self, q):
        q.set(5, 5, STAR)
        assert q.is_empty(5, 5) is False


# ---------------------------------------------------------------------------
# find()
# ---------------------------------------------------------------------------

class TestFind:

    @pytest.fixture
    def q(self):
        return Quadrant()

    def test_find_returns_empty_list_when_not_present(self, q):
        assert q.find(KLINGON) == []

    def test_find_returns_single_position(self, q):
        q.set(3, 7, KLINGON)
        result = q.find(KLINGON)
        assert result == [(3, 7)]

    def test_find_returns_multiple_positions(self, q):
        q.set(1, 1, STAR)
        q.set(4, 4, STAR)
        q.set(8, 8, STAR)
        result = sorted(q.find(STAR))
        assert result == [(1, 1), (4, 4), (8, 8)]

    def test_find_does_not_return_other_tokens(self, q):
        q.set(2, 2, SHIP)
        q.set(3, 3, KLINGON)
        assert q.find(BASE) == []

    def test_find_after_clear(self, q):
        q.set(5, 5, BASE)
        q.clear(5, 5)
        assert q.find(BASE) == []


# ---------------------------------------------------------------------------
# random_empty()
# ---------------------------------------------------------------------------

class TestRandomEmpty:

    def test_random_empty_returns_valid_coords(self):
        q = Quadrant()
        r, c = q.random_empty()
        assert 1 <= r <= 8
        assert 1 <= c <= 8

    def test_random_empty_returns_empty_sector(self):
        q = Quadrant()
        q.set(3, 3, KLINGON)
        for _ in range(100):
            r, c = q.random_empty()
            assert q.is_empty(r, c)

    def test_random_empty_avoids_filled_sectors(self):
        """Fill all but one sector, confirm random_empty always returns that one."""
        q = Quadrant()
        target = (5, 5)
        for r in range(1, 9):
            for c in range(1, 9):
                if (r, c) != target:
                    q.set(r, c, STAR)
        for _ in range(20):
            r, c = q.random_empty()
            assert (r, c) == target

    def test_random_empty_distribution_is_uniform(self):
        """Over many calls, all 64 sectors should be chosen at least once."""
        random.seed(999)
        q = Quadrant()
        seen = set()
        for _ in range(2000):
            seen.add(q.random_empty())
        assert len(seen) == 64, f"Only {len(seen)} of 64 sectors were returned"


# ---------------------------------------------------------------------------
# display_symbol()
# ---------------------------------------------------------------------------

class TestDisplaySymbol:

    @pytest.fixture
    def q(self):
        return Quadrant()

    def test_empty_sector_stock_mode(self, q):
        sym, key = q.display_symbol(1, 1, DISPLOOK_STOCK)
        assert key == "empty"
        assert sym == "   "

    def test_star_sector_stock_mode(self, q):
        q.set(3, 3, STAR)
        sym, key = q.display_symbol(3, 3, DISPLOOK_STOCK)
        assert key == "star"
        assert sym == " * "

    def test_klingon_sector_stock_mode(self, q):
        q.set(2, 4, KLINGON)
        sym, key = q.display_symbol(2, 4, DISPLOOK_STOCK)
        assert key == "klingon"
        assert sym == "+K+"

    def test_ship_sector_stock_mode(self, q):
        q.set(7, 7, SHIP)
        sym, key = q.display_symbol(7, 7, DISPLOOK_STOCK)
        assert key == "ship"
        assert sym == "<*>"

    def test_base_sector_stock_mode(self, q):
        q.set(5, 2, BASE)
        sym, key = q.display_symbol(5, 2, DISPLOOK_STOCK)
        assert key == "base"
        assert sym == ">!<"

    def test_grid_mode_empty_is_underscored(self, q):
        sym, key = q.display_symbol(1, 1, DISPLOOK_GRID)
        assert key == "empty"
        assert "_" in sym, f"Grid mode empty should have underscores, got {sym!r}"
        assert " " not in sym, f"Grid mode empty should not have spaces, got {sym!r}"

    def test_grid_mode_star_not_underscored(self, q):
        """Stars keep their spaces in grid mode — only empty cells get underscores."""
        q.set(4, 4, STAR)
        sym, key = q.display_symbol(4, 4, DISPLOOK_GRID)
        assert key == "star"
        # Grid mode star symbol is " * " — spaces are part of the star glyph
        assert "*" in sym

    def test_dots_mode_empty_is_dot(self, q):
        sym, key = q.display_symbol(1, 1, DISPLOOK_DOTS)
        assert key == "empty"
        assert "." in sym

    def test_symbol_always_3_chars(self, q):
        positions_and_tokens = [
            ((1,1), EMPTY), ((2,2), STAR), ((3,3), KLINGON),
            ((4,4), SHIP),  ((5,5), BASE),
        ]
        for (r, c), tok in positions_and_tokens:
            q.set(r, c, tok)
        for mode in [DISPLOOK_STOCK, DISPLOOK_GRID, DISPLOOK_DOTS]:
            for r in range(1, 9):
                for c in range(1, 9):
                    sym, _ = q.display_symbol(r, c, mode)
                    assert len(sym) == 3, (
                        f"Mode {mode} at ({r},{c}) returned {sym!r} (len={len(sym)})"
                    )


# ---------------------------------------------------------------------------
# populate()
# ---------------------------------------------------------------------------

class TestPopulate:

    def _make_state(self, klingons=1, bases=1, stars=3, k_strength=200):
        from state import GameState
        s = GameState()
        s.sec_row        = 4
        s.sec_col        = 4
        s.klingons_here  = klingons
        s.bases_here     = bases
        s.stars_here     = stars
        s.klingon_strength = k_strength
        return s

    def test_ship_placed_at_enterprise_position(self):
        state = self._make_state()
        q = Quadrant()
        q.populate(state)
        assert q.get(4, 4) == SHIP

    def test_correct_number_of_klingons(self):
        state = self._make_state(klingons=3)
        q = Quadrant()
        q.populate(state)
        assert len(q.find(KLINGON)) == 3

    def test_correct_number_of_stars(self):
        state = self._make_state(stars=5)
        q = Quadrant()
        q.populate(state)
        assert len(q.find(STAR)) == 5

    def test_base_placed_when_present(self):
        state = self._make_state(bases=1)
        q = Quadrant()
        q.populate(state)
        assert len(q.find(BASE)) == 1

    def test_no_base_when_bases_zero(self):
        state = self._make_state(bases=0)
        q = Quadrant()
        q.populate(state)
        assert len(q.find(BASE)) == 0

    def test_no_klingons_when_zero(self):
        state = self._make_state(klingons=0)
        q = Quadrant()
        q.populate(state)
        assert len(q.find(KLINGON)) == 0

    def test_no_two_tokens_overlap(self):
        """Every filled sector should contain exactly one token."""
        state = self._make_state(klingons=3, bases=1, stars=6)
        for _ in range(20):  # multiple seeds
            q = Quadrant()
            q.populate(state)
            filled = [(r, c) for r in range(1, 9)
                              for c in range(1, 9)
                              if not q.is_empty(r, c)]
            assert len(filled) == len(set(filled))  # no duplicates
            # Total tokens = 1 ship + 3 klingons + 1 base + 6 stars = 11
            assert len(filled) == 1 + 3 + 1 + 6

    def test_klingon_energy_within_expected_range(self):
        """Each Klingon energy = strength * (0.5..1.5)."""
        from state import GameState
        state = self._make_state(klingons=3, k_strength=200)
        q = Quadrant()
        q.populate(state)
        for k in state.klingons:
            assert 200 * 0.5 <= k.energy <= 200 * 1.5, (
                f"Klingon energy {k.energy} out of expected range [100, 300]"
            )

    def test_populate_adds_klingons_to_state_klingon_list(self):
        from state import GameState
        state = self._make_state(klingons=2)
        q = Quadrant()
        q.populate(state)
        assert len(state.klingons) == 2

    def test_klingon_positions_match_grid(self):
        """state.klingons positions should match KLINGON tokens in the grid."""
        from state import GameState
        state = self._make_state(klingons=3)
        q = Quadrant()
        q.populate(state)
        grid_positions = set(q.find(KLINGON))
        state_positions = {(k.row, k.col) for k in state.klingons}
        assert grid_positions == state_positions

    def test_base_sector_stored_in_state(self):
        """After populate, state.base_sec_row/col should point to the base."""
        from state import GameState
        state = self._make_state(bases=1)
        q = Quadrant()
        q.populate(state)
        base_positions = q.find(BASE)
        assert len(base_positions) == 1
        assert (state.base_sec_row, state.base_sec_col) == base_positions[0]

    def test_clears_previous_contents_on_repopulate(self):
        """Calling populate twice should not accumulate tokens."""
        from state import GameState
        state = self._make_state(klingons=1, stars=2)
        q = Quadrant()
        q.populate(state)
        q.populate(state)
        assert len(q.find(KLINGON)) == 1
        assert len(q.find(STAR))    == 2
