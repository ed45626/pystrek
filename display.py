"""
display.py  –  SST3 Python Edition
Version 0.1.0

All terminal output lives here.  The rest of the game never calls print()
directly — it calls functions from this module.

Colour is implemented with ANSI escape codes (no external dependencies).
If stdout is not a TTY the helper strips codes automatically.
"""

import sys
from config import (
    VERSION, DISPLOOK_GRID, DISPLOOK_DIV1, DISPLOOK_DIV2,
    DEVICE_NAMES, DEV_SRS, DEV_LRS, DEV_COMPUTER, galaxy_decode
)
from names import quadrant_name

# ---------------------------------------------------------------------------
# ANSI colour helpers
# ---------------------------------------------------------------------------
_TTY = sys.stdout.isatty()

_STYLES = {
    "reset":          "\033[0m",
    "white":          "\033[37m",
    "bold white":     "\033[1m\033[97m",
    "red":            "\033[31m",
    "bold red":       "\033[1m\033[91m",
    "green":          "\033[32m",
    "bold green":     "\033[1m\033[92m",
    "cyan":           "\033[36m",
    "bold cyan":      "\033[1m\033[96m",
    "yellow":         "\033[33m",
    "bold yellow":    "\033[1m\033[93m",
    "magenta":        "\033[35m",
    "bold magenta":   "\033[1m\033[95m",
}


def _esc(style: str) -> str:
    return _STYLES.get(style, "") if _TTY else ""


def _reset() -> str:
    return _STYLES["reset"] if _TTY else ""


def ansi(text: str, style: str = "white") -> str:
    """Wrap text with an ANSI style, resetting afterwards."""
    return f"{_esc(style)}{text}{_reset()}"


def cprint(text: str, style: str = "white", end: str = "\n") -> None:
    """Print text with the given ANSI style."""
    print(f"{_esc(style)}{text}{_reset()}", end=end)


# ---------------------------------------------------------------------------
# Title screen  (BASIC lines 221-226)
# ---------------------------------------------------------------------------
def render_title() -> None:
    print()
    cprint("                                    ,------*------,", "bold cyan")
    cprint("                    ,-------------   '---  ------'", "bold cyan")
    cprint("                     '-------- --'      / /", "bold cyan")
    cprint("                         ,---' '-------/ /--,", "bold cyan")
    cprint("                          '----------------'", "bold cyan")
    print()
    cprint("                    THE USS ENTERPRISE --- NCC-1701", "bold white")
    print()
    cprint(f"            SST3 Python Edition  v{VERSION}  (BBC BASIC port)", "white")
    print()


# ---------------------------------------------------------------------------
# SRS display  (BASIC lines 6430-7260)
# ---------------------------------------------------------------------------
_SRS_STATUS_LABELS = [
    "STARDATE",
    "CONDITION",
    "QUADRANT",
    "SECTOR",
    "PHOTON TORPEDOES",
    "TOTAL ENERGY",
    "SHIELDS",
    "KLINGONS REMAINING",
]

# Style constants for SRS cell tokens
_CELL_STYLES = {
    "star":    "green",
    "klingon": "bold red",
    "ship":    "bold cyan",
    "base":    "bold magenta",
    "empty":   "white",
}


def _srs_border(displook: int) -> str:
    """Top/bottom border line for the SRS grid."""
    if displook == DISPLOOK_GRID:
        return " ___ ___ ___ ___ ___ ___ ___ ___"
    if displook == DISPLOOK_DIV1:
        return "---- --- --- --- --- --- --- ----"
    if displook == DISPLOOK_DIV2:
        return "--=---=---=---=---=---=---=---=--"
    return "---------------------------------"


def _srs_status(row_idx: int, state) -> tuple:
    """
    Return (label_str, value_str, style) for the right-side status panel.
    row_idx is 0-based (0=STARDATE ... 7=KLINGONS REMAINING).
    """
    label = f"       {_SRS_STATUS_LABELS[row_idx]:<20}"

    if row_idx == 0:   # STARDATE
        val = f"{state.stardate:.1f}"
        deadline = state.start_stardate + state.mission_days - 7
        style = "bold magenta" if state.stardate > deadline else "white"

    elif row_idx == 1:  # CONDITION
        cond = state.condition()
        val = cond
        style = {
            "DOCKED": "bold green",
            "*RED*":  "bold red",
            "YELLOW": "bold yellow",
            "GREEN":  "bold green",
        }.get(cond, "white")

    elif row_idx == 2:  # QUADRANT
        val = f"{state.quad_row},{state.quad_col}"
        style = "green"

    elif row_idx == 3:  # SECTOR
        val = f"{state.sec_row},{state.sec_col}"
        style = "green"

    elif row_idx == 4:  # PHOTON TORPEDOES
        val = str(int(state.torpedoes))
        style = "bold magenta" if state.torpedoes < 4 else "cyan"

    elif row_idx == 5:  # TOTAL ENERGY
        total = int(state.energy + state.shields)
        val = str(total)
        style = "bold red" if total < 400 else ("bold yellow" if total < 1000 else "green")

    elif row_idx == 6:  # SHIELDS
        val = str(int(state.shields))
        style = ("bold red" if state.shields < 250
                 else ("bold yellow" if state.shields < 700 else "green"))

    else:               # KLINGONS REMAINING
        val = str(int(state.total_klingons))
        style = "bold yellow"

    return label, val, style


def render_srs(state, prefs) -> None:
    """
    Short Range Sensor display + status panel.
    Equivalent to BASIC GOSUB 6430.
    """
    if not state.is_device_ok(DEV_SRS):
        print()
        cprint("*** SHORT RANGE SENSORS ARE OUT ***", "bold cyan")
        print()
        return

    grid = state.quadrant_grid
    displook = prefs.displook
    border_char = "|" if displook == DISPLOOK_GRID else " "

    top = _srs_border(displook)
    # In grid mode the top border is consumed (printed once, then cleared)
    cprint(top, "white")

    for row in range(1, 9):
        # Build the grid portion of this line
        line_parts = []
        line_parts.append(ansi(border_char, "white"))

        for col in range(1, 9):
            sym, token_key = grid.display_symbol(row, col, displook)
            line_parts.append(ansi(sym, _CELL_STYLES[token_key]))
            line_parts.append(ansi(border_char, "white"))

        # Status panel (right side)
        label, val, vstyle = _srs_status(row - 1, state)
        line_parts.append(ansi(label, "white"))
        line_parts.append(ansi(val, vstyle))

        print("".join(line_parts))

    # Bottom border (empty for grid mode — top border used, not repeated)
    if displook != DISPLOOK_GRID:
        cprint(top, "white")

    print()


# ---------------------------------------------------------------------------
# LRS display  (BASIC lines 4000-4230)
# ---------------------------------------------------------------------------
def render_lrs(state, prefs) -> None:
    """Long Range Sensor scan — 3×3 grid centred on current quadrant."""
    if not state.is_device_ok(DEV_LRS):
        cprint("LONG RANGE SENSORS ARE INOPERABLE", "magenta")
        return

    cprint(f"LONG RANGE SCAN FOR QUADRANT {state.quad_row},{state.quad_col}", "green")
    sep = ansi("-------------------", "white")
    print(sep)

    for dr in range(-1, 2):
        r = state.quad_row + dr
        row_cells = []
        for dc in range(-1, 2):
            c = state.quad_col + dc
            if 1 <= r <= 8 and 1 <= c <= 8:
                val = state.galaxy_get(r, c)
                state.scanned_set(r, c, val)   # reveal to player
                row_cells.append(f"{val:03d}")
            else:
                row_cells.append(None)         # out of galaxy

        # Render row
        parts = []
        for cell in row_cells:
            if cell is None:
                parts.append(ansi(": ", "white") + ansi("***", "bold cyan") + ansi(" ", "white"))
            else:
                parts.append(ansi(": ", "white") + ansi(cell, "bold cyan") + ansi(" ", "white"))
        parts.append(ansi(":", "white"))
        print("".join(parts))
        print(sep)

    print()


# ---------------------------------------------------------------------------
# COM option 1 — Status report  (BASIC lines 7900-8020)
# ---------------------------------------------------------------------------
def render_status_report(state) -> None:
    cprint("   STATUS REPORT:", "bold cyan")
    k = int(state.total_klingons)
    cprint(f"KLINGON{'S' if k != 1 else ''} LEFT: {k}", "bold cyan")
    cprint(f"MISSION MUST BE COMPLETED IN {state.time_remaining():.1f} STARDATES", "bold cyan")
    b = int(state.total_bases)
    if b == 0:
        print()
        cprint("YOUR STUPIDITY HAS LEFT YOU ON YOUR OWN IN", "white")
        cprint("  THE GALAXY -- YOU HAVE NO STARBASES LEFT!", "white")
    else:
        s = "S" if b > 1 else ""
        cprint(f"THE FEDERATION IS MAINTAINING {b} STARBASE{s} IN THE GALAXY", "bold cyan")
    print()


# ---------------------------------------------------------------------------
# COM option 4 — Direction/distance calculator  (BASIC lines 8150-8470)
# ---------------------------------------------------------------------------
import math as _math


def calc_direction_distance(r1: int, c1: int, r2: int, c2: int) -> tuple:
    """
    Return (course, game_dist, actual_dist) from sector (r1,c1) to (r2,c2).
    Equivalent to BASIC lines 8220-8470.

    Coordinate mapping:
        X (BASIC) = c2 - c1  (column delta)
        A (BASIC) = r1 - r2  (row delta, reversed: row grows downward)

    Course wheel: 1=E, 2=NE, 3=N, 4=NW, 5=W, 6=SW, 7=S, 8=SE

    The BASIC algorithm:
        Branch on sign of X, then sign of A, then set a base course C1
        equal to the nearest cardinal/diagonal in that quadrant.
        Add a fractional offset based on the ratio of the two deltas.

    Key invariant:
        When both deltas are non-zero and unequal, the formula is:
            C1 + (larger - smaller + larger) / larger   [if larger > smaller]
            C1 + smaller / larger                       [if smaller <= larger]
        which always yields a value strictly between C1 and C1+1.
    """
    dx = c2 - c1   # X in BASIC
    dy = r1 - r2   # A in BASIC

    if dx == 0 and dy == 0:
        return None, 0.0, 0.0

    # -- BASIC lines 8240-8330: X >= 0 cases --
    if dx >= 0:
        if dy >= 0:
            # BASIC: X not<0, A not<0 → C1=1 at line 8280
            # (Line 8270 "IF A=0 THEN C1=5" only fires when both X=0,A=0,
            #  which we already handled above.)
            course = 1.0
            if abs(dy) <= abs(dx):
                # Line 8330: C1 + ABS(A)/ABS(X)   [safe: dx>0 here]
                course += abs(dy) / abs(dx)
            else:
                # Line 8310: C1 + ((ABS(A)-ABS(X))+ABS(A))/ABS(A)
                course += (abs(dy) - abs(dx) + abs(dy)) / abs(dy)
        else:
            # X >= 0, A < 0 (BASIC line 8250→8410: C1=7)
            course = 7.0
            if abs(dy) >= abs(dx):
                # Line 8450: C1 + ABS(X)/ABS(A)   [safe: dy != 0]
                course += abs(dx) / abs(dy)
            else:
                # Line 8430: C1 + ((ABS(X)-ABS(A))+ABS(X))/ABS(X)
                course += (abs(dx) - abs(dy) + abs(dx)) / abs(dx)

    # -- BASIC lines 8350-8450: X < 0 cases --
    else:
        if dy > 0:
            # Line 8350: X<0, A>0 → C1=3
            course = 3.0
            if abs(dy) >= abs(dx):
                # Line 8450: C1 + ABS(X)/ABS(A)
                course += abs(dx) / abs(dy)
            else:
                # Line 8430: C1 + ((ABS(X)-ABS(A))+ABS(X))/ABS(X)
                course += (abs(dx) - abs(dy) + abs(dx)) / abs(dx)
        else:
            # Line 8360/8410: X<0, A<=0 → C1=5
            course = 5.0
            if abs(dy) <= abs(dx):
                # Line 8330: C1 + ABS(A)/ABS(X)
                course += abs(dy) / abs(dx)
            else:
                # Line 8310: C1 + ((ABS(A)-ABS(X))+ABS(A))/ABS(A)
                course += (abs(dy) - abs(dx) + abs(dy)) / abs(dy)

    game_dist   = max(abs(dx), abs(dy))
    actual_dist = _math.sqrt(dx ** 2 + dy ** 2)
    return course, game_dist, actual_dist


def render_direction_calculator(state) -> None:
    """Interactive direction/distance calculator."""
    cprint("DIRECTION/DISTANCE CALCULATOR:", "bold white")
    cprint(f"YOU ARE AT QUADRANT {state.quad_row},{state.quad_col} "
           f"SECTOR {state.sec_row},{state.sec_col}", "bold white")
    cprint("PLEASE ENTER", "bold white")
    try:
        raw = input("  INITIAL COORDINATES (row,col): ").strip()
        r1, c1 = [int(x) for x in raw.replace(",", " ").split()]
        raw = input("    FINAL COORDINATES (row,col): ").strip()
        r2, c2 = [int(x) for x in raw.replace(",", " ").split()]
    except (ValueError, TypeError):
        cprint("INVALID ENTRY", "bold cyan")
        return

    if not all(1 <= v <= 8 for v in (r1, c1, r2, c2)):
        cprint("INVALID ENTRY", "bold cyan")
        return
    if r1 == r2 and c1 == c2:
        cprint("INVALID ENTRY", "bold cyan")
        return

    course, game_dist, actual_dist = calc_direction_distance(r1, c1, r2, c2)
    cprint(f"DIRECTION = {course:.2f}", "bold cyan")
    cprint(f"DISTANCE  = {game_dist} UNITS  (ACTUAL = {actual_dist:.4f})", "white")
    print()


# ---------------------------------------------------------------------------
# COM option 5 — Galaxy region name map  (BASIC lines 7400-7550)
# ---------------------------------------------------------------------------
def render_galaxy_map() -> None:
    print()
    cprint("                        THE GALAXY", "bold green")
    _render_galactic_grid(show_names=True, state=None)


# ---------------------------------------------------------------------------
# COM option 6 — Cumulative galactic record  (BASIC lines 7540-7850)
# ---------------------------------------------------------------------------
def render_cum_record(state) -> None:
    print()
    cprint(f"        COMPUTER RECORD OF GALAXY FOR QUADRANT "
           f"{state.quad_row},{state.quad_col}", "bold green")
    print()
    _render_galactic_grid(show_names=False, state=state)


def _render_galactic_grid(show_names: bool, state) -> None:
    """
    Shared renderer for COM options 5 and 6.
    show_names=True → region names (galaxy map)
    show_names=False → scanned values (cumulative record)
    """
    header = "       1     2     3     4     5     6     7     8"
    sep    = "     ----- ----- ----- ----- ----- ----- ----- -----"
    cprint(header, "white")
    cprint(sep, "white")

    for r in range(1, 9):
        if show_names:
            # Two region names per row (west half / east half), centered
            west = quadrant_name(r, 1, region_only=True)
            east = quadrant_name(r, 5, region_only=True)
            w_pad = (15 - len(west)) // 2
            e_pad = (24 - len(east)) // 2
            row_str = f"  {r}  {' '*w_pad}{west}{' '*(15-w_pad-len(west))}"
            row_str += f"{' '*e_pad}{east}"
            cprint(row_str, "bold green")
        else:
            parts = [f"  {r} "]
            for c in range(1, 9):
                marker_open  = ">" if (r == state.quad_row and c == state.quad_col) else " "
                marker_close = "<" if (r == state.quad_row and c == state.quad_col) else " "
                val = state.scanned_get(r, c)
                if val == 0:
                    cell = "***"
                else:
                    cell = f"{val:03d}"
                parts.append(f" {marker_open}{cell}{marker_close}")
            cprint("".join(parts), "white")

        cprint(sep, "white")

    print()


# ---------------------------------------------------------------------------
# Damage control report  (BASIC lines 5690-5980)
# ---------------------------------------------------------------------------
def render_damage(state) -> None:
    if not state.is_device_ok(5):   # DEV_DAMAGE=5
        cprint("DAMAGE CONTROL REPORT NOT AVAILABLE", "bold magenta")
        return

    print()
    cprint("DEVICE              STATE OF REPAIR", "white")
    for i, name in enumerate(DEVICE_NAMES):
        val = state.damage[i]
        style = "green" if val >= 0 else "bold red"
        cprint(f"  {name:<22}{val:+.2f}", style)
    print()


# ---------------------------------------------------------------------------
# Preferences UI  (BASIC lines 16000-16380)
# ---------------------------------------------------------------------------
def run_prefs_editor(prefs) -> None:
    """Interactive preferences editor.  Modifies prefs in place."""
    cprint("\n=== PREFERENCES ===\n", "bold white")

    # Colour mode
    ans = input("MONOCHROME OR COLOR DISPLAY (M/C) [C]: ").strip().upper() or "C"
    if ans == "M":
        prefs.monochrome = True
    elif ans == "C":
        prefs.monochrome = False

    # Display look
    ans = input("SRS DISPLAY 0=STOCK 1=GRID 2=DOTS 3=DIV1 4=DIV2 "
                f"[{prefs.displook}]: ").strip()
    if ans:
        try:
            v = int(ans)
            if 0 <= v <= 4:
                prefs.displook = v
            else:
                cprint("OUT OF RANGE — unchanged", "bold cyan")
        except ValueError:
            pass

    # Exit mode
    ans = input(f"ON EXIT 0=QUIT 1=RETURN [{prefs.exit_mode}]: ").strip()
    if ans:
        try:
            v = int(ans)
            if v in (0, 1):
                prefs.exit_mode = v
        except ValueError:
            pass

    cprint("\nPreferences updated (not yet saved — use SAE to save).", "cyan")
    print()


# ---------------------------------------------------------------------------
# Command list  (BASIC lines 2170-2270)
# ---------------------------------------------------------------------------
def print_command_list() -> None:
    cprint("ENTER ONE OF THE FOLLOWING:", "bold cyan")
    cmds = [
        ("NAV", "TO SET COURSE"),
        ("SRS", "FOR SHORT RANGE SENSOR SCAN"),
        ("LRS", "FOR LONG RANGE SENSOR SCAN"),
        ("PHA", "TO FIRE PHASERS"),
        ("TOR", "TO FIRE PHOTON TORPEDOES"),
        ("SHE", "TO RAISE OR LOWER SHIELDS"),
        ("DAM", "FOR DAMAGE CONTROL REPORTS"),
        ("COM", "TO CALL ON LIBRARY-COMPUTER"),
        ("XXX", "TO RESIGN YOUR COMMAND"),
        ("SAE", "TO SAVE AND EXIT"),
        ("STO", "TO STOP THE PROGRAM"),
        ("SET", "TO SET PREFERENCES"),
    ]
    for cmd, desc in cmds:
        print(f"  {cmd}  ({desc})")
    print()
