"""
galaxy.py  –  SST3 Python Edition
Version 0.1.0

Galaxy population and quadrant entry logic.
Equivalent to BASIC lines 370-1230 and 1310-1590.
"""

import random
from config import (
    GALAXY_SIZE, DEFAULT_ENERGY, DEFAULT_TORPEDOES,
    galaxy_encode, galaxy_decode, DIFFICULTY
)
from state import GameState, Prefs
from quadrant import Quadrant
from names import quadrant_name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _rnd_sector() -> int:
    """Random integer 1-8.  Replaces FNR(1) = INT(RND(1)*7.98+1.01)."""
    return random.randint(1, 8)


# ---------------------------------------------------------------------------
# Galaxy population  (BASIC lines 820-1160)
# ---------------------------------------------------------------------------
def populate_galaxy(state: GameState) -> None:
    """
    Fill the 8×8 galaxy grid with Klingons, starbases, and stars.
    Also sets state.total_klingons (K9), state.total_bases (B9),
    state.mission_days (T9).
    """
    total_k = 0
    total_b = 0

    for r in range(1, GALAXY_SIZE + 1):
        for c in range(1, GALAXY_SIZE + 1):
            k = b = 0
            roll = random.random()
            if roll > 0.98:
                k = 3
            elif roll > 0.95:
                k = 2
            elif roll > 0.80:
                k = 1
            total_k += k

            if random.random() > 0.96:
                b = 1
                total_b += 1

            stars = _rnd_sector()    # 1-8 stars
            state.galaxy_set(r, c, galaxy_encode(k, b, stars))

    state.total_klingons   = total_k
    state.initial_klingons = total_k

    # Mission time: must be enough to defeat all Klingons
    t9 = 25 + int(random.random() * 10)
    state.mission_days = max(t9, total_k + 1)

    # Ensure at least one starbase exists  (BASIC lines 1100-1160)
    if total_b == 0:
        # Add a base somewhere other than the Enterprise's starting quadrant
        r, c = _rnd_sector(), _rnd_sector()
        k, b, s = galaxy_decode(state.galaxy_get(r, c))
        state.galaxy_set(r, c, galaxy_encode(k, 1, s))
        total_b = 1

        # Also ensure that quadrant has at least one Klingon (line 1150)
        # (Adds a Klingon if the Enterprise's starting quad has none there)
        eq_r, eq_c = state.quad_row, state.quad_col
        ek, eb, es = galaxy_decode(state.galaxy_get(eq_r, eq_c))
        if ek < 1:
            state.galaxy_set(eq_r, eq_c, galaxy_encode(1, eb, es))
            state.total_klingons += 1
            state.initial_klingons += 1

    state.total_bases = total_b


# ---------------------------------------------------------------------------
# New game initialisation  (BASIC lines 370-1230)
# ---------------------------------------------------------------------------
def init_new_game(difficulty: int = 0) -> GameState:
    """
    Create and return a fully initialised GameState for a new game.
    Equivalent to BASIC lines 370-1230 (excluding save-file restore).
    """
    state = GameState()
    state.difficulty = difficulty

    # Starting stardate: 2000-3900 in steps of 100  (BASIC line 370)
    state.stardate       = int(random.random() * 20 + 20) * 100.0
    state.start_stardate = state.stardate

    # Difficulty presets  (BASIC lines 1221-1226)
    energy, k_strength, r8 = DIFFICULTY.get(difficulty, DIFFICULTY[0])
    if difficulty > 0:
        # Add ±20% variance to Klingon strength and first-shot chance
        k_strength = int(k_strength + k_strength * 0.2 * (random.random() - 0.5))
        r8 = r8 + r8 * (random.random() - 0.5)
        r8 = min(r8, 1.0)

    state.energy           = energy
    state.max_energy       = energy
    state.torpedoes        = DEFAULT_TORPEDOES
    state.max_torpedoes    = DEFAULT_TORPEDOES
    state.klingon_strength = k_strength
    state.first_shot_chance = r8

    # Enterprise starting position
    state.quad_row = _rnd_sector()
    state.quad_col = _rnd_sector()
    state.sec_row  = _rnd_sector()
    state.sec_col  = _rnd_sector()

    # Populate the galaxy
    populate_galaxy(state)

    return state


# ---------------------------------------------------------------------------
# Docking check  (BASIC lines 6430-6620)
# ---------------------------------------------------------------------------
def check_docking(state: GameState) -> None:
    """
    Scan the eight sectors adjacent to the Enterprise.
    If a starbase is found, dock: refuel, re-arm, drop shields.
    Sets state.docked.
    """
    from quadrant import BASE
    grid = state.quadrant_grid
    if grid is None:
        state.docked = False
        return

    found_base = False
    for dr in range(-1, 2):
        for dc in range(-1, 2):
            if dr == 0 and dc == 0:
                continue
            nr, nc = state.sec_row + dr, state.sec_col + dc
            if 1 <= nr <= 8 and 1 <= nc <= 8:
                if grid.get(nr, nc) == BASE:
                    found_base = True

    if found_base and not state.docked:
        from display import cprint
        cprint("SHIELDS DROPPED FOR DOCKING PURPOSES", "bold cyan")
        state.shields  = 0.0
        state.energy   = state.max_energy
        state.torpedoes = state.max_torpedoes

    state.docked = found_base


# ---------------------------------------------------------------------------
# Enter quadrant  (BASIC lines 1310-1590)
# ---------------------------------------------------------------------------
def enter_quadrant(state: GameState, is_start: bool = False) -> None:
    """
    Set up state for the current quadrant: decode galaxy value, build the
    sector grid, print entry messages, check for docking.
    """
    from display import cprint

    import random as _r
    state.d4 = 0.5 * _r.random()   # random repair-time bonus

    # Clamp position to galaxy bounds
    state.quad_row = max(1, min(GALAXY_SIZE, state.quad_row))
    state.quad_col = max(1, min(GALAXY_SIZE, state.quad_col))

    # Reveal this quadrant in the scanned map
    gval = state.galaxy_get(state.quad_row, state.quad_col)
    state.scanned_set(state.quad_row, state.quad_col, gval)

    # Decode quadrant contents
    state.klingons_here, state.bases_here, state.stars_here = galaxy_decode(gval)

    # Entry message
    name = quadrant_name(state.quad_row, state.quad_col)
    if is_start:
        print()
        cprint("YOUR MISSION BEGINS WITH YOUR STARSHIP LOCATED", "white")
        cprint(f"IN THE GALACTIC QUADRANT, '{name}'.", "white")
    else:
        cprint(f"\nNOW ENTERING {name} QUADRANT . . .", "bold white")
    print()

    # Combat area warning
    if state.klingons_here > 0:
        cprint("COMBAT AREA      CONDITION RED", "bold red")
        if state.shields <= 200:
            cprint("   SHIELDS DANGEROUSLY LOW", "bold yellow")
        print()

    # Build sector grid
    state.quadrant_grid = Quadrant()
    state.quadrant_grid.populate(state)

    # Docking check
    check_docking(state)

    # Klingons may fire first on subsequent entries (Z8 flag)
    # Z8 is set True here; it's cleared after they fire in the game loop.
    state.fire_first = not is_start


# ---------------------------------------------------------------------------
# Print orders  (BASIC lines 1230-1276)
# ---------------------------------------------------------------------------
def print_orders(state: GameState) -> None:
    """Print mission orders after difficulty selection."""
    from display import cprint
    cprint("YOUR ORDERS ARE AS FOLLOWS:", "white")
    print()
    k = state.total_klingons
    cprint(f"   DESTROY THE {k} KLINGON WARSHIP{'S' if k != 1 else ''} WHICH HAVE INVADED THE", "white")
    cprint("   GALAXY BEFORE THEY CAN ATTACK FEDERATION HEADQUARTERS", "white")
    cprint(f"   ON STARDATE {state.start_stardate + state.mission_days:.0f}, "
           f"THIS GIVES YOU {state.mission_days} DAYS.  THERE "
           f"{'ARE' if state.total_bases != 1 else 'IS'}", "white")
    cprint(f"   {state.total_bases} STARBASE{'S' if state.total_bases != 1 else ''} "
           "IN THE GALAXY FOR RESUPPLYING YOUR SHIP.", "white")
    cprint(f"   THE KLINGONS HAVE AN AVERAGE STRENGTH OF "
           f"{state.klingon_strength:.0f} UNITS", "white", end="")
    if state.first_shot_chance == 0:
        print(".")
    else:
        print()
        pct = int(state.first_shot_chance * 100)
        if state.first_shot_chance < 1.0:
            cprint(f"   AND HAVE AN ESTIMATED {pct}% CHANCE OF FIRING FIRST.", "white")
        else:
            cprint("   AND ALWAYS SHOOT FIRST.", "white")
    print()
