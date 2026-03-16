# SST3 Python Conversion — Task Breakdown
**Version: 0.1.0**  
Converted from BBC BASIC SST3 (Terry Newton, Feb 2021 enhanced version)

---

## Overview

The BBC BASIC source is approximately 700 lines of line-numbered BASIC with shared mutable globals, GOTO-based control flow, packed string arrays for the quadrant grid, and terminal colour codes. The Python rewrite should preserve gameplay fidelity while replacing all of these with idiomatic Python structures.

**Target environment:** Python 3.10+, Linux terminal, no mandatory external dependencies (optional: `rich` for colour/layout).

---

## Key BASIC-to-Python Translation Patterns

Before diving into modules, these patterns appear throughout and must be handled consistently.

| BASIC construct | Python equivalent |
|---|---|
| `G(8,8)` — galaxy array | `numpy` 2-D array or `list[list[int]]` |
| `Q$` — 192-char packed quadrant string | `Quadrant` class with `dict[(row,col)] → str` |
| `D(8)` — damage array, negative = broken | `dict[str, float]` keyed by device name |
| `K(3,3)` — Klingon position/energy | `list[Klingon]` dataclass |
| `C(9,2)` — course direction vectors | `COURSE_VECTORS: dict[int, tuple[float,float]]` |
| `COLOUR RED+BOLD` | `rich.print("[bold red]...")` or `curses` attr |
| `RND(1)` | `random.random()` |
| `FNR(R)` — random 1–8 | `lambda: random.randint(1, 8)` |
| `FND(D)` — Klingon distance | method on `GameState` |
| `ON I GOTO ...` | `dispatch: dict[int, Callable]` |
| `INKEY(-256)` — BBC variant detect | not needed; remove BBC-variant branching |
| Negative `D(I)` = damaged | `damage[device] < 0` |
| Save file `SST3V2 SAVE FILE` header | JSON with `"version": "sst3-py-1"` header |

---

## Module Breakdown

### Phase 1 — Foundation (play a game, no save/combat)

---

#### `config.py`
**BASIC lines:** 1–9, 14300–14430

**Purpose:** All tunable constants and display settings. Nothing here should have side effects.

```python
VERSION = "0.1.0"

# Display modes
DISPLOOK_STOCK     = 0
DISPLOOK_GRID      = 1
DISPLOOK_DOTS      = 2
DISPLOOK_DIV1      = 3

# Default prefs (overridden by prefs file)
DEFAULT_PREFS = {
    "displook": DISPLOOK_GRID,
    "monochrome": False,
    "mono_color": 0,
    "mono_bg": 0,
    "exit_mode": 0,   # 0=sys.exit, 1=return
    "err_trap": 0,
}

# SRS display symbols per mode
SYMBOLS = {
    DISPLOOK_STOCK: {"space": "   ", "star": " * ", "klingon": "+K+", "ship": "<*>", "base": ">!<"},
    DISPLOOK_GRID:  {"space": "   ", "star": " * ", "klingon": " K ", "ship": " E ", "base": " B "},
    DISPLOOK_DOTS:  {"space": " . ", "star": " * ", "klingon": "+K+", "ship": "<*>", "base": ">!<"},
}

DEVICE_NAMES = [
    "Warp engines", "Short range sensors", "Long range sensors",
    "Phaser control", "Photon tubes", "Damage control",
    "Shield control", "Library-computer",
]

SAVE_FILENAME  = "sst3_save.json"
PREFS_FILENAME = "sst3_prefs.json"
```

**Tasks:**
- Define all constants from lines 1–9 and 14310–14430
- Replace `MONOCOL`/`MONOBKG`/`DISPLOOK` with a typed `Prefs` dataclass
- Remove all BBC variant detection (`INKEY(-256)`, `BBC=77/87/115`)

---

#### `state.py`
**BASIC lines:** 330–475, 1220–1226

**Purpose:** Central mutable game state. One `GameState` instance is passed through the entire game.

```python
from dataclasses import dataclass, field
import random

@dataclass
class Klingon:
    row: int
    col: int
    energy: float

@dataclass
class GameState:
    # Time
    stardate: float       # T
    start_stardate: float # T0
    mission_days: int     # T9

    # Enterprise
    quadrant: tuple[int,int]  # Q1, Q2
    sector: tuple[int,int]    # S1, S2
    energy: float         # E
    max_energy: float     # E0
    torpedoes: int        # P
    max_torpedoes: int    # P0
    shields: float        # S

    # Galaxy
    galaxy: list          # G(8,8) — int per quadrant: Kk*100 + Bb*10 + Stars
    scanned: list         # Z(8,8) — player-revealed galaxy data
    damage: dict          # D(8) keyed by device index 0–7
    klingons: list        # K(3,3) → list[Klingon]

    # Totals
    total_klingons: int   # K9
    initial_klingons: int # K7
    total_bases: int      # B9
    klingon_strength: float # S9
    first_shot_chance: float # R8
    difficulty: int

    # Transient quadrant state
    quadrant_grid: object       # Quadrant instance
    klingons_here: int    # K3
    bases_here: int       # B3
    stars_here: int       # S3
    docked: bool          # D0
    base_sector: tuple    # B4, B5
    klingon_fire_flag: bool # Z8
```

**Tasks:**
- Replace all BASIC globals (T, T0, T9, Q1, Q2, S1, S2, E, E0, P, P0, S, K9...) with fields
- Implement `@classmethod new_game(difficulty)` that runs lines 370–1226 logic
- Add `def distance_to_klingon(self, k: Klingon) -> float` (replaces `FND`)
- Validate all field types

---

#### `galaxy.py`
**BASIC lines:** 810–1160

**Purpose:** Galaxy population — place Klingons, starbases, and stars into the 8×8 galaxy grid.

**Tasks:**
- `def populate_galaxy(state: GameState) -> None` — replaces lines 820–1040
- Enforce "at least one starbase" rule (lines 1100–1160)
- Extract `def random_sector() -> tuple[int,int]` (replaces `FNR(1):FNR(1)`)
- Randomize starting position for Enterprise

---

#### `quadrant.py`
**BASIC lines:** 1600–1910, 8580–8700, 8820–8900

**Purpose:** Manages the 8×8 sector grid within a quadrant. Replaces the `Q$` packed string.

```python
class Quadrant:
    """8×8 grid of sectors. Each cell holds a token: EMPTY, STAR, KLINGON, SHIP, BASE."""
    
    EMPTY   = "   "
    STAR    = " * "
    KLINGON = "+K+"
    SHIP    = "<*>"
    BASE    = ">!<"
    
    def __init__(self):
        self._grid: dict[tuple[int,int], str] = {}
    
    def get(self, row: int, col: int) -> str: ...
    def set(self, row: int, col: int, token: str) -> None: ...
    def find(self, token: str) -> list[tuple[int,int]]: ...
    def random_empty(self) -> tuple[int,int]: ...
    def populate(self, state: GameState) -> None: ...  # lines 1680–1910
```

**Tasks:**
- Replace `Q$` string indexing with this class (the BASIC index formula is `S8 = INT(Z2-.5)*3 + INT(Z1-.5)*24 + 1`)
- Implement `populate()` — place ship, Klingons, bases, stars
- Implement `random_empty()` — replaces `GOSUB 8590`

---

#### `names.py`
**BASIC lines:** 9010–9260

**Purpose:** Map `(quadrant_row, quadrant_col)` to a region+sector name like `"ANTARES IV"`.

**Tasks:**
- Convert `ON Z4 GOTO` / `ON Z5 GOTO` cascade to two lookup tables
- `def quadrant_name(row: int, col: int, region_only: bool = False) -> str`
- No side effects

---

#### `display.py`
**BASIC lines:** 6430–7260, 14300–14430

**Purpose:** All terminal output. Isolates colour/formatting so the rest of the code never calls `print` directly.

**Tasks:**
- Choose colour library: `rich` (recommended, pip install) or stdlib `curses`
- Implement `def print_srs(state: GameState, prefs: Prefs) -> None` — the main short-range sensor display (lines 6430–7260). This is the most complex rendering function.
- Implement colour helpers: `cprint(text, colour, bold=False)`
- Map BASIC colour names to rich/curses equivalents:

  | BASIC | rich |
  |---|---|
  | `RED+BOLD` | `[bold red]` |
  | `CYAN+BOLD` | `[bold cyan]` |
  | `GREEN` | `[green]` |
  | `MAGENTA+BOLD` | `[bold magenta]` |
  | `YELLOW+BOLD` | `[bold yellow]` |

- Implement the SRS grid rendering with the four `DISPLOOK` modes (separators, symbols)
- The right-side status panel shows: stardate, condition, quadrant, sector, torpedoes, total energy, shields, klingons remaining — each colour-coded by threshold

---

### Phase 2 — Gameplay (navigation + combat loop)

---

#### `navigation.py`
**BASIC lines:** 2300–3980

**Purpose:** Warp drive movement — course entry, energy consumption, quadrant crossing, collision detection.

**Tasks:**
- `def cmd_nav(state: GameState) -> None`
- Course direction vector table: replace `C(9,2)` with `COURSE_VECTORS = {1: (0,1), 2: (-1,1), ...}`
  - BASIC packs course 1–9 where 9 = 1 (wrap). Courses are circular: direction = interpolation between adjacent vectors.
  - Fractional course support: `C1 = 1.5` means halfway between courses 1 and 2
- Warp factor validation: max 8, max 0.2 if warp engines damaged
- Energy check: `energy - N >= 0` else offer shield cross-circuit
- Klingon movement on warp (lines 2590–2700): Klingons reposition when Enterprise moves
- Quadrant boundary crossing (lines 3500–3870): handle galaxy edge clamping, Starfleet denial message
- Repair tick: `D[i] += D6` each warp (lines 2770–2880), D6=1 if warp≥1 else warp*1
- Random damage event on warp: 20% chance (line 2880)
- Energy deduction via `maneuver_energy(state, N)` (lines 3910–3980)

---

#### `combat.py`
**BASIC lines:** 4260–5490

**Purpose:** Player offensive weapons — phasers and photon torpedoes.

**Tasks:**

**Phasers** (`cmd_phasers`):
- Check device D[3] (phaser control) not damaged
- Check K3 > 0 (Klingons present)
- Computer-degraded accuracy if D[7] < 0
- Energy split `H1 = X / K3` per Klingon
- Hit formula: `H = int((H1 / distance) * (random() + 2))`
- Threshold: if `H <= 0.15 * klingon.energy` → no damage message
- Destroy Klingon if energy ≤ 0, update galaxy map, check win condition
- Call `klingons_fire(state)` after phasers

**Torpedoes** (`cmd_torpedo`):
- Check D[4] (photon tubes) not damaged
- Course entry same as navigation (1–9, fractional)
- Track torpedo sector by sector, print each position
- Hit detection order: empty space → Klingon → star → starbase
- Starbase destruction: court martial warning, check if only base gone
- Call `klingons_fire(state)` after torpedo

---

#### `klingons.py`
**BASIC lines:** 6000–6200, 1985–1986, 2580–2700

**Purpose:** Enemy AI — firing and repositioning.

**Tasks:**
- `def klingons_fire(state: GameState) -> None` — replaces `GOSUB 6000`
  - Skip if K3 = 0 or docked
  - For each Klingon: hit = `int((k.energy / distance) * (2 + random()))`
  - Reduce shields, reduce Klingon energy by `3 + random()`
  - Damage device if hit large enough (lines 6120–6170)
  - Game over if shields ≤ 0
- `def klingons_reposition(state: GameState) -> None` — lines 2590–2700
  - Each Klingon moves to a random empty sector when Enterprise warps
- First-shot check: `if Z8 and random() < R8` → Klingons fire before player

---

#### `sensors.py`
**BASIC lines:** 4000–4230, 7280–8520

**Purpose:** Passive sensors (LRS) and the library computer sub-menu.

**Tasks:**

**Long range sensors** (`cmd_lrs`):
- Print 3×3 grid around current quadrant
- Show `***` for unscanned, 3-digit code for scanned
- Update `Z(I,J)` (scanned array) on scan

**Library computer** (`cmd_computer`):
1. Status report — Klingons left, stardates remaining, bases
2. Torpedo data — direction/distance to each Klingon
3. Starbase nav data — direction/distance to base in this quadrant
4. Direction/distance calculator — user enters two coordinate pairs
5. Galaxy region name map — 8×8 grid of names
6. Cumulative galactic record — 8×8 grid of scanned values with `><` markers

Direction/distance formula from lines 8220–8470:
- `dx = final_col - initial_col`, `dy = initial_row - final_row`
- Match BASIC quadrant logic to assign course 1–8 + fractional offset
- Game distance = `max(abs(dx), abs(dy))`, actual = `sqrt(dx²+dy²)`

---

### Phase 3 — Ship systems + end game

---

#### `shields.py`
**BASIC lines:** 5530–5660

**Purpose:** Shield energy management.

**Tasks:**
- `def cmd_shields(state: GameState) -> None`
- Check D[6] (shield control) operational
- Prompt for new shield level (0 to E+S)
- Redistribute energy between shields and main energy

---

#### `damage.py`
**BASIC lines:** 5690–5980

**Purpose:** Damage control report and repair authorization.

**Tasks:**
- `def cmd_damage(state: GameState) -> None`
- If D[5] (damage control) broken: show report but no repair offer
- Show all 8 devices with repair status (green positive, red negative)
- Repair estimate: `D3 = sum(0.1 for each damaged) + D4`; cap at 0.9
- If authorized: set all D[i] < 0 → 0, advance stardate by D3+0.1

---

#### `endgame.py`
**BASIC lines:** 6210–6410

**Purpose:** Win/loss detection and scoring.

**Tasks:**
- `def check_time_expired(state: GameState) -> bool`
- `def check_enterprise_destroyed(state: GameState) -> bool`
- `def check_stranded(state: GameState) -> bool` (lines 1990–2050)
- `def victory(state: GameState) -> None` — efficiency rating `= 1000 * (K7 / (T - T0))²`
- `def defeat(state: GameState, reason: str) -> None`
- `def play_again() -> bool` — prompt with "AYE" confirmation

---

### Phase 4 — Persistence + polish

---

#### `saveload.py`
**BASIC lines:** 10000–12540

**Purpose:** Save and restore game state to/from JSON.

The BASIC save format writes raw variable values line by line. Replace with JSON for readability and forward compatibility.

```python
SAVE_VERSION = "sst3-py-1"

def save_game(state: GameState, path: Path) -> None:
    data = {
        "version": SAVE_VERSION,
        "galaxy": state.galaxy,
        "scanned": state.scanned,
        "damage": state.damage,
        "klingons": [asdict(k) for k in state.klingons],
        # ... all other fields
    }
    path.write_text(json.dumps(data, indent=2))

def load_game(path: Path) -> GameState | None: ...
def delete_save(path: Path) -> None: ...
def save_exists(path: Path) -> bool: ...
```

**Tasks:**
- Map all BASIC save variables (line 10100–10110) to JSON keys
- Handle missing/corrupt save file gracefully
- `cmd_sae(state)` — save and exit
- Prompt to restore on startup (line 11010–11030)
- Delete save on game completion or "AYE" restart

---

#### `prefs.py`
**BASIC lines:** 15000–16380

**Purpose:** Load/save user preferences from JSON.

**Tasks:**
- `def load_prefs(path: Path) -> Prefs`
- `def save_prefs(prefs: Prefs, path: Path) -> None`
- `def cmd_set(prefs: Prefs) -> None` — interactive preference editor
  - Mono/color mode
  - Display look (0–4)
  - Exit mode
  - Error handling mode
  - Save/remove prefs file option

---

#### `main.py`
**BASIC lines:** 200–230, 1310–1990, 2060–2290

**Purpose:** Top-level entry point — startup, command dispatch loop.

```python
VERSION = "0.1.0"

COMMANDS = {
    "NAV": cmd_nav,
    "SRS": cmd_srs,
    "LRS": cmd_lrs,
    "PHA": cmd_phasers,
    "TOR": cmd_torpedo,
    "SHE": cmd_shields,
    "DAM": cmd_damage,
    "COM": cmd_computer,
    "XXX": cmd_resign,
    "SAE": cmd_sae,
    "STO": cmd_stop,
    "SET": cmd_set,
}

def game_loop(state: GameState, prefs: Prefs) -> None:
    while True:
        display_srs(state, prefs)
        maybe_klingons_fire_first(state)
        check_stranded(state)
        cmd = input("COMMAND: ").strip().upper()[:3]
        if cmd not in COMMANDS:
            print_command_list()
            continue
        COMMANDS[cmd](state)
        check_time_expired(state)

def main():
    prefs = load_prefs(PREFS_PATH)
    print_title()
    state = load_or_new_game(prefs)
    enter_quadrant(state)
    game_loop(state, prefs)

if __name__ == "__main__":
    main()
```

**Tasks:**
- Print title ASCII art (lines 221–226)
- Startup: check for save file, prompt restore or difficulty
- `enter_quadrant(state)` — runs lines 1310–1590 (print quadrant name, combat area warning)
- Main command dispatch replacing `ON I GOTO` (line 2140)
- "Command not found" help text (lines 2170–2270)
- `cmd_resign()` — XXX command
- `cmd_stop()` — STO (prints GOTO 1980 message, exits)

---

## Cross-Cutting Concerns

### Condition display
Condition (DOCKED / GREEN / YELLOW / RED) is computed in `display.py`:
- DOCKED: base adjacent
- RED: K3 > 0
- YELLOW: energy < 10% of max
- GREEN: otherwise

### Docking
On every quadrant entry and after every move, scan sectors adjacent to Enterprise. If `>!<` found within 1 sector, dock: refuel to E0, rearm to P0, drop shields. (lines 6430–6620)

### Stardate arithmetic
BASIC uses `T*10` rounded for display. Python: `round(state.stardate, 1)`. Stardates advance by warp factor for sub-warp, 1.0 for full-warp, and fractional amounts for repairs.

### Random number seeding
BASIC `RND(1)` is unseeded. Python: do not seed `random` (use OS entropy). Add `--seed N` CLI flag for reproducibility during testing.

---

## Gotchas / BASIC Quirks to Watch

1. **`Q$` indexing:** BASIC arrays are 1-indexed; rows/columns run 1–8. Python 0-indexed. Pick one convention and be explicit. Recommend keeping 1-indexed internally to match BASIC logic, convert at display layer.

2. **Course wrapping:** Course 9 = Course 1. Fractional courses (e.g. 1.5) interpolate between adjacent direction vectors. The BASIC formula is `X1 = C(C1,1) + (C(C1+1,1) - C(C1,1)) * (C1 - INT(C1))`.

3. **`Z8` first-shot flag:** Set to 0 on quadrant entry, set to 1 after first SRS display if T > T0. Klingons fire before player if `Z8=1` and `random() < R8`. Reset to 0 after they fire.

4. **Klingon energy degradation:** After firing, each Klingon's energy divides by `3 + random()` (line 6060). This is intentional — they weaken as combat drags on.

5. **Galaxy value encoding:** `G(I,J) = K*100 + B*10 + stars`. Extract: `K3 = G // 100`, `B3 = (G % 100) // 10`, `S3 = G % 10`.

6. **Damage values:** Positive = operational (excess repair), 0 = nominal, negative = damaged. The value magnitude is not used for severity — only the sign matters for functionality checks. The repair rate per warp is `D6 = 1` if warp≥1 else warp value.

7. **`D4` random repair bonus:** `D4 = 0.5 * random()`, set on quadrant entry. Added to repair time estimate in damage control.

8. **Starbase `D0` flag:** `D0=1` if docked. When docked, Klingon fire is suppressed entirely (line 6010). Also used as flag in damage report to offer repairs (line 5700: `if D0=0 then 1990`).

---

## Suggested File Layout

```
sst3/
├── sst3.py            # single-file entry point (imports all modules)
├── config.py
├── state.py
├── galaxy.py
├── quadrant.py
├── names.py
├── display.py
├── navigation.py
├── combat.py
├── klingons.py
├── sensors.py
├── shields.py
├── damage.py
├── endgame.py
├── saveload.py
├── prefs.py
├── main.py
└── tests/
    ├── test_galaxy.py
    ├── test_quadrant.py
    ├── test_navigation.py
    └── test_combat.py
```

Alternatively, ship as a single `sst3.py` file (≈800–1000 lines) with functions grouped by the same logical sections. The multi-file layout is better for iterative development.

---

## Testing Strategy

Each phase should be testable without completing the prior phase:

- **Phase 1:** Render a hardcoded `GameState` to the terminal with `print_srs()`. Visually verify the grid matches the BASIC output.
- **Phase 2:** Unit test `combat.py` with seeded random — given known Klingon positions and energy levels, verify hit calculations match BASIC formulas.
- **Phase 3:** Verify save/load round-trips: `save_game(state)` → `load_game()` → all fields equal.
- **Phase 4:** Full game playthrough with `--seed` to reproduce a deterministic sequence.

---

*End of conversion plan — Version 0.1.0*
