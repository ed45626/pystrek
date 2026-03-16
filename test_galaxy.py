"""
test_galaxy.py  –  SST3 Python Edition
Version 0.1.0

Tests for galaxy.py: populate_galaxy(), init_new_game(), enter_quadrant(),
check_docking(), print_orders().
"""

import random
import pytest
from state import GameState, Prefs, Klingon
from config import galaxy_decode, galaxy_encode, DIFFICULTY
from galaxy import populate_galaxy, init_new_game, enter_quadrant, check_docking


# ---------------------------------------------------------------------------
# populate_galaxy()
# ---------------------------------------------------------------------------

class TestPopulateGalaxy:

    @pytest.fixture
    def state(self):
        s = GameState()
        s.quad_row = 4
        s.quad_col = 4
        s.sec_row  = 1
        s.sec_col  = 1
        return s

    def test_all_64_cells_populated(self, state):
        populate_galaxy(state)
        for r in range(1, 9):
            for c in range(1, 9):
                assert state.galaxy_get(r, c) >= 0

    def test_total_klingons_positive(self, state):
        random.seed(42)
        populate_galaxy(state)
        assert state.total_klingons > 0

    def test_total_bases_positive(self, state):
        random.seed(1)
        populate_galaxy(state)
        assert state.total_bases > 0

    def test_at_least_one_base_guaranteed(self, state):
        """Galaxy always has >= 1 starbase after populate (BASIC lines 1100-1160)."""
        for seed in range(50):
            random.seed(seed)
            s2 = GameState()
            s2.quad_row, s2.quad_col = 1, 1
            populate_galaxy(s2)
            assert s2.total_bases >= 1, f"Seed {seed}: no starbases generated"

    def test_total_klingons_matches_galaxy_sum(self, state):
        random.seed(7)
        populate_galaxy(state)
        actual_k = sum(
            galaxy_decode(state.galaxy_get(r, c))[0]
            for r in range(1, 9)
            for c in range(1, 9)
        )
        assert actual_k == state.total_klingons

    def test_total_bases_matches_galaxy_sum(self, state):
        random.seed(7)
        populate_galaxy(state)
        actual_b = sum(
            galaxy_decode(state.galaxy_get(r, c))[1]
            for r in range(1, 9)
            for c in range(1, 9)
        )
        assert actual_b == state.total_bases

    def test_stars_in_each_cell_are_1_to_8(self, state):
        random.seed(3)
        populate_galaxy(state)
        for r in range(1, 9):
            for c in range(1, 9):
                _, _, stars = galaxy_decode(state.galaxy_get(r, c))
                assert 1 <= stars <= 8, (
                    f"({r},{c}): stars={stars}, expected 1-8"
                )

    def test_klingons_per_cell_are_0_to_3(self, state):
        random.seed(5)
        populate_galaxy(state)
        for r in range(1, 9):
            for c in range(1, 9):
                k, _, _ = galaxy_decode(state.galaxy_get(r, c))
                assert 0 <= k <= 3, f"({r},{c}): klingons={k}, expected 0-3"

    def test_bases_per_cell_are_0_or_1(self, state):
        random.seed(5)
        populate_galaxy(state)
        for r in range(1, 9):
            for c in range(1, 9):
                _, b, _ = galaxy_decode(state.galaxy_get(r, c))
                assert b in (0, 1), f"({r},{c}): bases={b}, expected 0 or 1"

    def test_mission_days_at_least_total_klingons(self, state):
        """Mission must be beatable: T9 >= K9 + 1 (BASIC line 1040)."""
        for seed in range(20):
            random.seed(seed)
            s2 = GameState()
            s2.quad_row, s2.quad_col = 3, 3
            populate_galaxy(s2)
            assert s2.mission_days > s2.total_klingons, (
                f"Seed {seed}: mission_days={s2.mission_days} <= "
                f"total_klingons={s2.total_klingons}"
            )

    def test_initial_klingons_equals_total_klingons(self, state):
        random.seed(9)
        populate_galaxy(state)
        assert state.initial_klingons == state.total_klingons


# ---------------------------------------------------------------------------
# init_new_game()
# ---------------------------------------------------------------------------

class TestInitNewGame:

    @pytest.mark.parametrize("difficulty", [0, 1, 2, 3])
    def test_valid_difficulty_levels(self, difficulty):
        random.seed(10 + difficulty)
        state = init_new_game(difficulty)
        assert state is not None

    def test_energy_matches_difficulty(self):
        for level, (energy, _, _) in DIFFICULTY.items():
            random.seed(0)
            state = init_new_game(level)
            # Level 0 is exact; higher levels may have variance added
            if level == 0:
                assert state.energy == energy
            else:
                assert state.energy == energy   # no variance on energy itself

    def test_enterprise_position_in_range(self):
        for seed in range(10):
            random.seed(seed)
            state = init_new_game(0)
            assert 1 <= state.quad_row <= 8
            assert 1 <= state.quad_col <= 8
            assert 1 <= state.sec_row  <= 8
            assert 1 <= state.sec_col  <= 8

    def test_stardate_in_valid_range(self):
        """Starting stardate should be 2000–3900 in hundreds (BASIC line 370)."""
        for seed in range(20):
            random.seed(seed)
            state = init_new_game(0)
            assert 2000 <= state.stardate <= 3900
            assert state.stardate % 100 == 0

    def test_start_stardate_equals_stardate(self):
        random.seed(0)
        state = init_new_game(0)
        assert state.start_stardate == state.stardate

    def test_max_energy_equals_energy(self):
        random.seed(0)
        state = init_new_game(0)
        assert state.max_energy == state.energy

    def test_torpedoes_at_max(self):
        from config import DEFAULT_TORPEDOES
        random.seed(0)
        state = init_new_game(0)
        assert state.torpedoes     == DEFAULT_TORPEDOES
        assert state.max_torpedoes == DEFAULT_TORPEDOES

    def test_damage_all_zero(self):
        random.seed(0)
        state = init_new_game(0)
        assert all(d == 0.0 for d in state.damage)

    def test_shields_start_at_zero(self):
        random.seed(0)
        state = init_new_game(0)
        assert state.shields == 0.0

    def test_difficulty_0_no_first_shot_chance(self):
        random.seed(0)
        state = init_new_game(0)
        assert state.first_shot_chance == 0.0

    def test_difficulty_3_first_shot_chance_positive(self):
        """Level 3 always_shoots_first but variance may reduce below 1.0."""
        for seed in range(10):
            random.seed(seed)
            state = init_new_game(3)
            assert state.first_shot_chance > 0.0

    def test_first_shot_chance_never_exceeds_1(self):
        for seed in range(30):
            random.seed(seed)
            for level in range(4):
                state = init_new_game(level)
                assert state.first_shot_chance <= 1.0


# ---------------------------------------------------------------------------
# check_docking()
# ---------------------------------------------------------------------------

class TestCheckDocking:

    def _state_with_base_at(self, ship_r, ship_c, base_r, base_c):
        from quadrant import Quadrant, SHIP, BASE
        state = GameState()
        state.sec_row   = ship_r
        state.sec_col   = ship_c
        state.bases_here = 1
        state.energy     = 1000.0
        state.max_energy = 3000.0
        state.torpedoes  = 5
        state.max_torpedoes = 10
        state.shields    = 200.0

        q = Quadrant()
        q.set(ship_r, ship_c, SHIP)
        q.set(base_r, base_c, BASE)
        state.base_sec_row = base_r
        state.base_sec_col = base_c
        state.quadrant_grid = q
        state.docked = False
        return state

    def test_docks_when_base_adjacent(self):
        state = self._state_with_base_at(4, 4, 4, 5)  # base one step right
        check_docking(state)
        assert state.docked is True

    def test_docks_when_base_diagonally_adjacent(self):
        state = self._state_with_base_at(4, 4, 5, 5)
        check_docking(state)
        assert state.docked is True

    def test_does_not_dock_when_base_far(self):
        state = self._state_with_base_at(1, 1, 5, 5)
        check_docking(state)
        assert state.docked is False

    def test_docking_restores_energy(self):
        state = self._state_with_base_at(4, 4, 4, 5)
        check_docking(state)
        assert state.energy == state.max_energy

    def test_docking_restores_torpedoes(self):
        state = self._state_with_base_at(4, 4, 4, 5)
        check_docking(state)
        assert state.torpedoes == state.max_torpedoes

    def test_docking_drops_shields(self):
        state = self._state_with_base_at(4, 4, 4, 5)
        check_docking(state)
        assert state.shields == 0.0

    def test_no_dock_when_no_grid(self):
        state = GameState()
        state.quadrant_grid = None
        check_docking(state)
        assert state.docked is False

    def test_all_eight_adjacent_sectors_trigger_dock(self):
        offsets = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
        for dr, dc in offsets:
            state = self._state_with_base_at(4, 4, 4+dr, 4+dc)
            check_docking(state)
            assert state.docked is True, f"Should dock with base at offset ({dr},{dc})"


# ---------------------------------------------------------------------------
# enter_quadrant()
# ---------------------------------------------------------------------------

class TestEnterQuadrant:

    @pytest.fixture
    def state(self):
        random.seed(42)
        s = init_new_game(0)
        return s

    def test_quadrant_grid_created(self, state, capsys):
        enter_quadrant(state, is_start=True)
        assert state.quadrant_grid is not None

    def test_klingons_here_decoded_from_galaxy(self, state, capsys):
        gval = state.galaxy_get(state.quad_row, state.quad_col)
        k, b, s = galaxy_decode(gval)
        enter_quadrant(state, is_start=True)
        assert state.klingons_here == k

    def test_scanned_updated_on_entry(self, state, capsys):
        r, c = state.quad_row, state.quad_col
        state.scanned_set(r, c, 0)   # clear it first
        enter_quadrant(state, is_start=True)
        assert state.scanned_get(r, c) == state.galaxy_get(r, c)

    def test_ship_placed_in_quadrant_grid(self, state, capsys):
        from quadrant import SHIP
        enter_quadrant(state, is_start=True)
        assert state.quadrant_grid.get(state.sec_row, state.sec_col) == SHIP

    def test_fire_first_false_on_start(self, state, capsys):
        enter_quadrant(state, is_start=True)
        assert state.fire_first is False

    def test_fire_first_true_on_subsequent_entry(self, state, capsys):
        enter_quadrant(state, is_start=False)
        assert state.fire_first is True

    def test_klingons_list_populated(self, state, capsys):
        """If the quadrant has klingons, state.klingons should be non-empty."""
        # Force a known quadrant with klingons
        for r in range(1, 9):
            for c in range(1, 9):
                k, b, s = galaxy_decode(state.galaxy_get(r, c))
                if k > 0:
                    state.quad_row = r
                    state.quad_col = c
                    state.sec_row  = 1
                    state.sec_col  = 1
                    enter_quadrant(state, is_start=True)
                    assert len(state.klingons) == k
                    return
        pytest.skip("No quadrant with klingons found (unlikely)")
