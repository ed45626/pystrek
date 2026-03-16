"""
main.py  –  SST3 Python Edition
Version 0.3.0

Entry point, command dispatch loop, and all command handlers.

Phase 1: SRS, LRS, COM, DAM, SET, XXX, STO
Phase 2: NAV, PHA, TOR, SHE  +  win/lose/time-expired logic
Phase 3: SAE (save & exit), prefs persistence, save restore on startup,
         save deleted on game end, DAM repair authorisation
"""

import sys
import os
from pathlib import Path

from config import VERSION, SAVE_FILENAME, PREFS_FILENAME
from state import GameState, Prefs
from galaxy import init_new_game, enter_quadrant, print_orders
from display import (
    render_title, render_srs, render_lrs, render_damage,
    render_status_report, render_direction_calculator,
    render_galaxy_map, render_cum_record,
    run_prefs_editor, print_command_list, cprint, ansi
)
from navigation import execute_nav
from commands  import NavCommand, PhaserCommand, TorpedoCommand, ShieldsCommand
from events import (
    InvalidCourse, InvalidWarp, WarpEnginesDamaged, InsufficientEnergy,
    ShieldsCrossCircuit, NavigationBlocked, GalacticPerimeterDenied,
    QuadrantEntered, ShipMoved, Docked,
    DeviceRepaired, DeviceDamaged, DeviceImproved,
    StarbaseProtection, KlingonFired, EnterpriseDestroyed,
    PhasersInoperative, NoEnemiesInQuadrant, ComputerDamagesAccuracy,
    InsufficientPhaserEnergy, PhaserFired, KlingonHit, KlingonNoDamage,
    KlingonDestroyed, Victory,
    TorpedoesExpended, TubesDamaged, InvalidTorpedoCourse,
    TorpedoFired, TorpedoTracked, TorpedoMissed, TorpedoAbsorbedByStar,
    StarbaseDestroyed, KlingonsCounterFire, KlingonsAmbush,
    ShieldControlInoperable, ShieldsUnchanged, ShieldsSet,
    is_fatal, is_victory,
)
from combat    import execute_phasers, execute_torpedo
from shields   import execute_shields
from klingons  import execute_klingons_fire
from saveload  import save_game, load_game, save_exists, delete_save
from prefs     import load_prefs, save_prefs, delete_prefs

_SAVE_PATH  = Path(SAVE_FILENAME)
_PREFS_PATH = Path(PREFS_FILENAME)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_srs(state: GameState, prefs: Prefs) -> None:
    render_srs(state, prefs)


def cmd_lrs(state: GameState, prefs: Prefs) -> None:
    render_lrs(state, prefs)


def cmd_dam(state: GameState, prefs: Prefs) -> None:
    """
    DAM — damage control report with optional repair authorisation.
    BASIC lines 5690-5980.
    """
    from config import DEV_DAMAGE

    dam_ctrl_ok = state.is_device_ok(DEV_DAMAGE)

    if not dam_ctrl_ok:
        cprint("DAMAGE CONTROL REPORT NOT AVAILABLE", "bold magenta")

    # Repair offer when docked
    if state.docked:
        damaged = [i for i in range(8) if state.damage[i] < 0]
        if damaged:
            d3 = min(len(damaged) * 0.1 + state.d4, 0.9)
            cprint("TECHNICIANS STANDING BY TO EFFECT REPAIRS TO YOUR SHIP;", "bold cyan")
            cprint(f"ESTIMATED TIME TO REPAIR: {d3:.2f} STARDATES", "bold cyan")
            try:
                ans = input("WILL YOU AUTHORIZE THE REPAIR ORDER? (Y/N) ").strip().upper()
            except (EOFError, KeyboardInterrupt):
                ans = "N"
            if ans == "Y":
                for i in range(8):
                    if state.damage[i] < 0:
                        state.damage[i] = 0.0
                state.stardate += d3 + 0.1
                cprint("REPAIRS COMPLETED.", "bold green")
                print()

    if not dam_ctrl_ok:
        return

    render_damage(state)


def cmd_com(state: GameState, prefs: Prefs) -> None:
    if not state.is_device_ok(7):
        cprint("COMPUTER DISABLED", "bold cyan")
        return
    while True:
        try:
            raw = input("COMPUTER ACTIVE AND AWAITING COMMAND (0-6, 0=list): ").strip()
            if not raw:
                _print_com_list(); continue
            choice = int(raw)
        except (ValueError, EOFError):
            _print_com_list(); continue
        if choice < 0 or choice > 6:
            return
        if choice == 0:
            _print_com_list()
        elif choice == 1:
            render_status_report(state); return
        elif choice == 2:
            _com_torpedo_data(state); return
        elif choice == 3:
            _com_base_nav(state); return
        elif choice == 4:
            render_direction_calculator(state); return
        elif choice == 5:
            render_galaxy_map(); return
        elif choice == 6:
            render_cum_record(state); return


def _print_com_list() -> None:
    cprint("FUNCTIONS AVAILABLE FROM LIBRARY-COMPUTER:", "bold cyan")
    for n, label in [
        (1, "STATUS REPORT"), (2, "PHOTON TORPEDO DATA"),
        (3, "STARBASE NAV DATA"), (4, "DIRECTION/DISTANCE CALCULATOR"),
        (5, "GALAXY 'REGION NAME' MAP"), (6, "CUMULATIVE GALACTIC RECORD"),
    ]:
        cprint(f"   {n} = {label}", "bold cyan")
    print()


def _com_torpedo_data(state):
    from display import calc_direction_distance
    klingons = state.alive_klingons()
    if not klingons:
        cprint("SCIENCE OFFICER SPOCK REPORTS  'SENSORS SHOW NO ENEMY SHIPS", "bold cyan")
        cprint("                                IN THIS QUADRANT'", "bold cyan")
        return
    label = "S" if len(klingons) > 1 else ""
    cprint(f"FROM ENTERPRISE TO KLINGON BATTLE CRUISER{label}", "bold cyan")
    for k in klingons:
        course, gdist, adist = calc_direction_distance(
            state.sec_row, state.sec_col, k.row, k.col)
        cprint(f"DIRECTION = {course:.2f}", "bold cyan")
        cprint(f"DISTANCE  = {gdist} UNITS  (ACTUAL = {adist:.4f})", "white")
    print()


def _com_base_nav(state):
    from display import calc_direction_distance
    if state.bases_here < 1:
        cprint("MR. SPOCK REPORTS,  'SENSORS SHOW NO STARBASES IN THIS QUADRANT.'", "cyan")
        return
    cprint("FROM ENTERPRISE TO STARBASE:", "bold cyan")
    course, gdist, adist = calc_direction_distance(
        state.sec_row, state.sec_col, state.base_sec_row, state.base_sec_col)
    cprint(f"DIRECTION = {course:.2f}", "bold cyan")
    cprint(f"DISTANCE  = {gdist} UNITS  (ACTUAL = {adist:.4f})", "white")
    print()


def cmd_set(state: GameState, prefs: Prefs) -> None:
    run_prefs_editor(prefs)
    try:
        ans = input("SAVE PREFERENCES? (Y/N) ").strip().upper()
    except (EOFError, KeyboardInterrupt):
        return
    if ans == "Y":
        if save_prefs(prefs, _PREFS_PATH):
            cprint("PREFERENCES SAVED.", "green")
    else:
        if _PREFS_PATH.exists():
            try:
                ans2 = input("REMOVE PREFERENCES FILE? (Y/N) ").strip().upper()
            except (EOFError, KeyboardInterrupt):
                return
            if ans2 == "Y":
                delete_prefs(_PREFS_PATH)
                cprint("PREFERENCES FILE REMOVED.", "cyan")
    print()


def cmd_sae(state: GameState, prefs: Prefs) -> str:
    """SAE — save and exit.  BASIC lines 10000-10130."""
    cprint("SAVING DATA...", "white")
    if save_game(state, _SAVE_PATH):
        cprint(f"GAME SAVED TO {_SAVE_PATH}", "green")
        return "quit"
    else:
        cprint("SAVE FAILED — continuing.", "bold cyan")
        return None


def cmd_xxx(state: GameState, prefs: Prefs):
    k = int(state.total_klingons)
    cprint(f"THERE WERE {k} KLINGON BATTLE CRUISER{'S' if k != 1 else ''} LEFT AT", "white")
    cprint("THE END OF YOUR MISSION.", "white")
    print()
    if state.total_bases > 0:
        cprint("THE FEDERATION IS IN NEED OF A NEW STARSHIP COMMANDER", "white")
        cprint("FOR A SIMILAR MISSION -- IF THERE IS A VOLUNTEER,", "white")
        try:
            ans = input("LET HIM STEP FORWARD AND ENTER 'AYE'  ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            return "quit"
        if ans == "AYE":
            return "restart"
    cprint("OK, GOODBYE...", "white")
    return "quit"


def cmd_sto(state: GameState, prefs: Prefs) -> str:
    cprint("PROGRAM STOPPED.", "white")
    return "quit"


# ---------------------------------------------------------------------------
# Wrappers and dispatch
# ---------------------------------------------------------------------------

def _cmd_nav(s, p): return _run_nav(s, p)
def _cmd_pha(s, p): return _run_phasers(s, p)
def _cmd_tor(s, p): return _run_torpedo(s, p)
def _cmd_she(s, p): return _run_shields(s, p)

def _run_nav(state, prefs):
    """TUI handler for NAV: collect input, call execute_nav, render events."""
    # ── Collect course ─────────────────────────────────────────────────────
    warp_max = "8" if state.is_device_ok(0) else "0.2"  # DEV_WARP = 0
    try:
        raw = input("COURSE (1-9): ").strip()
        c1  = float(raw)
    except (ValueError, EOFError):
        cprint("   LT. SULU REPORTS, 'INCORRECT COURSE DATA, SIR!'", "cyan")
        return None

    # ── Collect warp factor ────────────────────────────────────────────────
    cprint(f"WARP FACTOR (0-{warp_max})", "bold white", end="")
    try:
        raw = input(": ").strip()
        w1  = float(raw)
    except (ValueError, EOFError):
        return None

    # ── Execute ────────────────────────────────────────────────────────────
    cmd    = NavCommand(course=c1, warp=w1)
    events = execute_nav(state, cmd)

    # ── Render events ──────────────────────────────────────────────────────
    return render_nav_events(state, events)


def render_nav_events(state, events) -> str:
    """
    Translate a list[Event] from execute_nav into terminal output.
    Returns 'destroyed' if the Enterprise was destroyed, else None.
    This is the only place that knows how to present navigation events as text.
    """
    for ev in events:

        if isinstance(ev, InvalidCourse):
            cprint("   LT. SULU REPORTS, 'INCORRECT COURSE DATA, SIR!'", "cyan")
            _print_course_diagram()

        elif isinstance(ev, WarpEnginesDamaged):
            cprint(f"WARP ENGINES ARE DAMAGED.  MAXIMUM SPEED = WARP 0.2", "cyan")

        elif isinstance(ev, InvalidWarp):
            cprint(f"CHIEF ENGINEER SCOTT REPORTS 'THE ENGINES WON'T TAKE "
                   f"WARP {ev.warp}!'", "cyan")

        elif isinstance(ev, InsufficientEnergy):
            cprint("ENGINEERING REPORTS   'INSUFFICIENT ENERGY AVAILABLE", "cyan")
            cprint(f"                       FOR MANEUVERING AT WARP {ev.required}!'", "cyan")
            if not ev.shields_damaged and ev.shield_energy >= ev.required - ev.available:
                cprint(f"DEFLECTOR CONTROL ROOM ACKNOWLEDGES {int(ev.shield_energy)} "
                       f"UNITS OF ENERGY", "cyan")
                cprint("                         PRESENTLY DEPLOYED TO SHIELDS.", "cyan")

        elif isinstance(ev, StarbaseProtection):
            cprint("STARBASE SHIELDS PROTECT THE ENTERPRISE", "bold green")

        elif isinstance(ev, KlingonFired):
            cprint(f"{ev.damage} UNIT HIT ON ENTERPRISE FROM SECTOR "
                   f"{ev.from_sector[0]},{ev.from_sector[1]}", "bold red")
            if ev.shields_after > 0:
                cprint(f"      <SHIELDS DOWN TO {int(ev.shields_after)} UNITS>", "bold cyan")
            if ev.device_name:
                cprint(f"DAMAGE CONTROL REPORTS {ev.device_name.upper()} "
                       f"DAMAGED BY THE HIT", "bold magenta")

        elif isinstance(ev, EnterpriseDestroyed):
            return "destroyed"

        elif isinstance(ev, ShieldsCrossCircuit):
            cprint("SHIELD CONTROL SUPPLIES ENERGY TO COMPLETE THE MANEUVER.", "cyan")

        elif isinstance(ev, NavigationBlocked):
            sr, sc = ev.stopped_sector
            cprint(f"WARP ENGINES SHUT DOWN AT SECTOR {sr},{sc} "
                   f"DUE TO BAD NAVIGATION", "bold cyan")

        elif isinstance(ev, GalacticPerimeterDenied):
            qr, qc = ev.clamped_quadrant
            sr, sc = ev.clamped_sector
            cprint("LT. UHURA REPORTS MESSAGE FROM STARFLEET COMMAND:", "cyan")
            cprint("  'PERMISSION TO ATTEMPT CROSSING OF GALACTIC PERIMETER", "white")
            cprint("  IS HEREBY *DENIED*.  SHUT DOWN YOUR ENGINES.'", "white")
            cprint("CHIEF ENGINEER SCOTT REPORTS  'WARP ENGINES SHUT DOWN", "cyan")
            cprint(f"  AT SECTOR {sr},{sc} OF QUADRANT {qr},{qc}.'", "cyan")

        elif isinstance(ev, DeviceRepaired):
            cprint("DAMAGE CONTROL REPORT:  ", "cyan", end="")
            cprint(f"{ev.device_name.upper()} REPAIR COMPLETED.", "green")

        elif isinstance(ev, DeviceDamaged):
            cprint("DAMAGE CONTROL REPORT:  ", "cyan", end="")
            cprint(f"{ev.device_name.upper()} DAMAGED", "bold magenta")
            print()

        elif isinstance(ev, DeviceImproved):
            cprint("DAMAGE CONTROL REPORT:  ", "cyan", end="")
            cprint(f"{ev.device_name.upper()} STATE OF REPAIR IMPROVED", "green")
            print()

        elif isinstance(ev, QuadrantEntered):
            cprint(f"\nNOW ENTERING {ev.quadrant_name} QUADRANT . . .", "bold white")
            print()
            if ev.klingons > 0:
                cprint("COMBAT AREA      CONDITION RED", "bold red")
                if state.shields <= 200:
                    cprint("   SHIELDS DANGEROUSLY LOW", "bold yellow")
                print()

        elif isinstance(ev, Docked):
            cprint("SHIELDS DROPPED FOR DOCKING PURPOSES", "bold cyan")

        elif isinstance(ev, ShipMoved):
            pass   # SRS redraw handles the visual update

    return None

def _run_phasers(state, prefs):
    """TUI handler for PHA: collect energy input, execute, render events."""
    if not state.is_device_ok(3):   # DEV_PHASERS
        cprint("PHASERS INOPERATIVE", "cyan")
        return None
    if state.klingons_here <= 0:
        cprint("SCIENCE OFFICER SPOCK REPORTS  'SENSORS SHOW NO ENEMY SHIPS", "cyan")
        cprint("                                IN THIS QUADRANT'", "cyan")
        return None
    if not state.is_device_ok(7):   # DEV_COMPUTER
        cprint("COMPUTER FAILURE HAMPERS ACCURACY", "bold magenta")
    cprint(f"PHASERS LOCKED ON TARGET;  ENERGY AVAILABLE = {int(state.energy)} UNITS", "bold cyan")
    try:
        raw = input("NUMBER OF UNITS TO FIRE: ").strip()
        x   = float(raw)
    except (ValueError, EOFError):
        return None
    cmd    = PhaserCommand(energy=x)
    events = execute_phasers(state, cmd)
    return render_combat_events(state, events)


def _run_torpedo(state, prefs):
    """TUI handler for TOR: collect course input, execute, render events."""
    if state.torpedoes <= 0:
        cprint("ALL PHOTON TORPEDOES EXPENDED", "bold cyan")
        return None
    if not state.is_device_ok(4):   # DEV_TORPS
        cprint("PHOTON TUBES ARE NOT OPERATIONAL", "bold cyan")
        return None
    try:
        raw = input("PHOTON TORPEDO COURSE (1-9): ").strip()
        c1  = float(raw)
    except (ValueError, EOFError):
        cprint("ENSIGN CHEKOV REPORTS,  'INCORRECT COURSE DATA, SIR!'", "cyan")
        return None
    cmd    = TorpedoCommand(course=c1)
    events = execute_torpedo(state, cmd)
    return render_combat_events(state, events)


def render_combat_events(state, events) -> str:
    """
    Translate a list[Event] from execute_phasers / execute_torpedo into
    terminal output.  Returns 'victory', 'destroyed', 'resigned', or None.
    This is the only place that knows how to present combat events as text.
    """
    for ev in events:

        if isinstance(ev, PhasersInoperative):
            cprint("PHASERS INOPERATIVE", "cyan")

        elif isinstance(ev, NoEnemiesInQuadrant):
            cprint("SCIENCE OFFICER SPOCK REPORTS  'SENSORS SHOW NO ENEMY SHIPS", "cyan")
            cprint("                                IN THIS QUADRANT'", "cyan")

        elif isinstance(ev, ComputerDamagesAccuracy):
            cprint("COMPUTER FAILURE HAMPERS ACCURACY", "bold magenta")

        elif isinstance(ev, InsufficientPhaserEnergy):
            cprint(f"PHASERS LOCKED ON TARGET;  ENERGY AVAILABLE = "
                   f"{int(ev.available)} UNITS", "bold cyan")

        elif isinstance(ev, PhaserFired):
            pass   # energy prompt already printed by _run_phasers

        elif isinstance(ev, KlingonNoDamage):
            r, c = ev.sector
            cprint(f"SENSORS SHOW NO DAMAGE TO ENEMY AT {r},{c}", "bold cyan")

        elif isinstance(ev, KlingonHit):
            r, c = ev.sector
            cprint(f"{ev.damage} UNIT HIT ON KLINGON AT SECTOR {r},{c}", "bold cyan")
            cprint(f"   (SENSORS SHOW {int(ev.klingon_energy_after)} UNITS REMAINING)",
                   "bold magenta")

        elif isinstance(ev, KlingonDestroyed):
            r, c = ev.sector
            cprint("*** KLINGON DESTROYED ***", "bold green")

        elif isinstance(ev, Victory):
            return "victory"

        # --- Torpedo events ---

        elif isinstance(ev, TorpedoesExpended):
            cprint("ALL PHOTON TORPEDOES EXPENDED", "bold cyan")

        elif isinstance(ev, TubesDamaged):
            cprint("PHOTON TUBES ARE NOT OPERATIONAL", "bold cyan")

        elif isinstance(ev, InvalidTorpedoCourse):
            cprint("ENSIGN CHEKOV REPORTS,  'INCORRECT COURSE DATA, SIR!'", "cyan")

        elif isinstance(ev, TorpedoFired):
            cprint("TORPEDO TRACK:", "bold cyan")

        elif isinstance(ev, TorpedoTracked):
            r, c = ev.sector
            cprint(f"               {r},{c}", "cyan")

        elif isinstance(ev, TorpedoMissed):
            cprint("TORPEDO MISSED", "cyan")

        elif isinstance(ev, TorpedoAbsorbedByStar):
            r, c = ev.sector
            cprint(f"STAR AT {r},{c} ABSORBED TORPEDO ENERGY.", "bold magenta")

        elif isinstance(ev, StarbaseDestroyed):
            r, c = ev.sector
            cprint("*** STARBASE DESTROYED ***", "bold red")
            if ev.court_martial:
                cprint("THAT DOES IT, CAPTAIN!!  YOU ARE HEREBY RELIEVED OF COMMAND",
                       "white")
                cprint("AND SENTENCED TO 99 STARDATES AT HARD LABOR ON CYGNUS 12!!",
                       "white")
                return "resigned"
            cprint("STARFLEET COMMAND REVIEWING YOUR RECORD TO CONSIDER", "white")
            cprint("COURT MARTIAL!", "white")

        # --- Klingon counter-fire ---

        elif isinstance(ev, KlingonsCounterFire):
            pass   # marker only; KlingonFired events follow

        elif isinstance(ev, KlingonFired):
            cprint(f"{ev.damage} UNIT HIT ON ENTERPRISE FROM SECTOR "
                   f"{ev.from_sector[0]},{ev.from_sector[1]}", "bold red")
            if ev.shields_after > 0:
                cprint(f"      <SHIELDS DOWN TO {int(ev.shields_after)} UNITS>",
                       "bold cyan")
            if ev.device_name:
                cprint(f"DAMAGE CONTROL REPORTS {ev.device_name.upper()} "
                       f"DAMAGED BY THE HIT", "bold magenta")

        elif isinstance(ev, StarbaseProtection):
            cprint("STARBASE SHIELDS PROTECT THE ENTERPRISE", "bold green")

        elif isinstance(ev, EnterpriseDestroyed):
            return "destroyed"

    return None



def _run_shields(state, prefs):
    """TUI handler for SHE: show available energy, collect level, execute, render."""
    if not state.is_device_ok(6):   # DEV_SHIELDS
        cprint("SHIELD CONTROL INOPERABLE", "bold cyan")
        return None
    available = int(state.energy + state.shields)
    cprint(f"ENERGY AVAILABLE = {available}", "bold cyan", end="")
    try:
        raw = input(" NUMBER OF UNITS TO SHIELDS: ").strip()
        x   = float(raw)
    except (ValueError, EOFError):
        cprint("<SHIELDS UNCHANGED>", "bold cyan")
        return None
    cmd    = ShieldsCommand(level=x)
    events = execute_shields(state, cmd)
    return render_shields_events(events)


def render_shields_events(events) -> None:
    """Translate shield events into terminal output."""
    for ev in events:
        if isinstance(ev, ShieldControlInoperable):
            cprint("SHIELD CONTROL INOPERABLE", "bold cyan")

        elif isinstance(ev, ShieldsUnchanged):
            if ev.reason == 'overspend':
                cprint("SHIELD CONTROL REPORTS  'THIS IS NOT THE FEDERATION TREASURY.'",
                       "bold cyan")
            cprint("<SHIELDS UNCHANGED>", "bold cyan")

        elif isinstance(ev, ShieldsSet):
            cprint("DEFLECTOR CONTROL ROOM REPORT:", "bold cyan")
            cprint(f"  'SHIELDS NOW AT {int(ev.shields_after)} UNITS PER YOUR COMMAND.'",
                   "bold cyan")
            print()
    return None


def _print_course_diagram() -> None:
    cprint("   FROM THE MANUAL...", "cyan")
    print()
    cprint("     COURSE IS IN A CIRCULAR NUMERICAL      4  3  2", "white")
    cprint("     VECTOR ARRANGEMENT AS SHOWN             . . .", "white")
    cprint("     INTEGER AND REAL VALUES MAY BE           ...", "white")
    cprint("     USED.  (THUS COURSE 1.5 IS HALF-     5 ---*--- 1", "white")
    cprint("     WAY BETWEEN 1 AND 2                      ...", "white")
    cprint("                                             . . .", "white")
    cprint("     VALUES MAY APPROACH 9.0, WHICH         6  7  8", "white")
    cprint("     ITSELF IS EQUIVALENT TO 1.0", "white")
    cprint("                                            COURSE", "white")
    cprint("     ONE WARP FACTOR IS THE SIZE OF ONE QUADRANT.", "white")
    print()


COMMANDS = {
    "NAV": _cmd_nav, "SRS": cmd_srs,  "LRS": cmd_lrs,
    "PHA": _cmd_pha, "TOR": _cmd_tor, "SHE": _cmd_she,
    "DAM": cmd_dam,  "COM": cmd_com,  "XXX": cmd_xxx,
    "SAE": cmd_sae,  "STO": cmd_sto,  "SET": cmd_set,
}


# ---------------------------------------------------------------------------
# End-game
# ---------------------------------------------------------------------------

def _check_result(state, result):
    return None if result in (None, "ok") else result


def _victory(state: GameState) -> None:
    cprint("CONGRATULATIONS, CAPTAIN!  THE LAST KLINGON BATTLE CRUISER", "bold green")
    cprint("MENACING THE FEDERATION HAS BEEN DESTROYED.", "bold green")
    print()
    elapsed = state.stardate - state.start_stardate
    if elapsed > 0:
        cprint(f"YOUR EFFICIENCY RATING IS {1000*(state.initial_klingons/elapsed)**2:.1f}", "bold green")
    print()


def _defeat(state: GameState, reason: str) -> None:
    if reason == "destroyed":
        cprint("THE ENTERPRISE HAS BEEN DESTROYED.  THE FEDERATION WILL BE CONQUERED", "magenta")
    cprint(f"IT IS STARDATE {state.stardate:.1f}", "white")
    k = int(state.total_klingons)
    cprint(f"THERE WERE {k} KLINGON BATTLE CRUISER{'S' if k != 1 else ''} LEFT AT", "white")
    cprint("THE END OF YOUR MISSION.", "white")
    print()


def _time_expired(state: GameState) -> bool:
    return state.stardate > state.start_stardate + state.mission_days


def _play_again(state: GameState) -> str:
    if state.total_bases > 0:
        cprint("THE FEDERATION IS IN NEED OF A NEW STARSHIP COMMANDER", "white")
        cprint("FOR A SIMILAR MISSION -- IF THERE IS A VOLUNTEER,", "white")
        try:
            ans = input("LET HIM STEP FORWARD AND ENTER 'AYE'  ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            return "quit"
        if ans == "AYE":
            return "restart"
    cprint("OK, GOODBYE...", "white")
    return "quit"


# ---------------------------------------------------------------------------
# Game loop
# ---------------------------------------------------------------------------

def render_klingon_fire_events(events) -> None:
    """
    Render KlingonsAmbush / KlingonsCounterFire context markers and
    the KlingonFired / EnterpriseDestroyed / StarbaseProtection events
    that follow them.  Used by game_loop for first-shot fire.
    (Combat and navigation renderers handle their own counter-fire inline.)
    """
    for ev in events:
        if isinstance(ev, KlingonsAmbush):
            pass   # no text needed — the hits that follow speak for themselves

        elif isinstance(ev, StarbaseProtection):
            cprint("STARBASE SHIELDS PROTECT THE ENTERPRISE", "bold green")

        elif isinstance(ev, KlingonFired):
            cprint(f"{ev.damage} UNIT HIT ON ENTERPRISE FROM SECTOR "
                   f"{ev.from_sector[0]},{ev.from_sector[1]}", "bold red")
            if ev.shields_after > 0:
                cprint(f"      <SHIELDS DOWN TO {int(ev.shields_after)} UNITS>",
                       "bold cyan")
            if ev.device_name:
                cprint(f"DAMAGE CONTROL REPORTS {ev.device_name.upper()} "
                       f"DAMAGED BY THE HIT", "bold magenta")

        elif isinstance(ev, EnterpriseDestroyed):
            pass   # defeat message handled by caller


def game_loop(state: GameState, prefs: Prefs) -> str:

    while True:
        render_srs(state, prefs)

        if state.fire_first:
            fire_evts = [KlingonsAmbush()] + execute_klingons_fire(state)
            state.fire_first = False
            render_klingon_fire_events(fire_evts)
            if is_fatal(fire_evts):
                _defeat(state, "destroyed")
                return _play_again(state)

        if state.energy + state.shields <= 10:
            if state.energy <= 10 and not state.is_device_ok(6):
                cprint("\n** FATAL ERROR **   YOU'VE JUST STRANDED YOUR SHIP IN SPACE", "bold cyan")
                cprint("YOU HAVE INSUFFICIENT MANEUVERING ENERGY, AND SHIELD CONTROL", "bold cyan")
                cprint("IS PRESENTLY INCAPABLE OF CROSS-CIRCUITING TO ENGINE ROOM!!", "bold cyan")
                _defeat(state, "stranded")
                return _play_again(state)

        if _time_expired(state):
            cprint(f"IT IS STARDATE {state.stardate:.1f}", "white")
            cprint("THE FEDERATION HAS BEEN CONQUERED WHILE YOU DITHERED.", "white")
            _defeat(state, "time")
            return _play_again(state)

        try:
            raw = input("COMMAND: ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print()
            return "quit"

        cmd = raw[:3]
        if cmd not in COMMANDS:
            print_command_list()
            continue

        result = COMMANDS[cmd](state, prefs)

        if result == "victory":
            _victory(state); return _play_again(state)
        if result == "destroyed":
            _defeat(state, "destroyed"); return _play_again(state)
        if result in ("quit", "restart", "resigned"):
            if result == "resigned":
                _defeat(state, "resigned")
            return _play_again(state) if result == "resigned" else result

        if _time_expired(state):
            cprint(f"\nIT IS STARDATE {state.stardate:.1f}", "white")
            cprint("YOU RAN OUT OF TIME.  THE FEDERATION HAS BEEN CONQUERED.", "white")
            _defeat(state, "time")
            return _play_again(state)


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

def _show_restore_status(state: GameState) -> None:
    """Condensed current-conditions after restore.  BASIC lines 1212-1218."""
    cprint(f"INTELLIGENCE REPORTS THE AVERAGE KLINGON ENERGY IS "
           f"{int(state.klingon_strength)} UNITS", "cyan")
    if state.first_shot_chance > 0:
        cprint(f"AND THEY HAVE A {int(state.first_shot_chance*100)}% CHANCE OF FIRING ON YOU FIRST", "cyan")
    cprint(f"YOU HAVE {state.time_remaining():.1f} DAYS LEFT TO COMPLETE YOUR MISSION.", "white")
    if state.klingons_here > 0:
        print()
        cprint("COMBAT AREA      CONDITION RED", "bold red")
    if state.shields <= 200:
        cprint("   SHIELDS DANGEROUSLY LOW", "bold yellow")
    print()


def main() -> None:
    os.system("clear")
    render_title()

    prefs = load_prefs(_PREFS_PATH)

    while True:
        state = None

        if save_exists(_SAVE_PATH):
            try:
                ans = input("RESTORE PREVIOUS GAME? (Y/N) ").strip().upper()
            except (EOFError, KeyboardInterrupt):
                ans = "N"
            if ans == "Y":
                state = load_game(_SAVE_PATH)
                if state is None:
                    cprint("SAVE FILE COULD NOT BE LOADED — STARTING NEW GAME.", "bold cyan")
                else:
                    _show_restore_status(state)
                    state.fire_first = False
            else:
                delete_save(_SAVE_PATH)

        if state is None:
            while True:
                try:
                    raw = input("DIFFICULTY LEVEL (0=default, 1=easy, 2=medium, 3=hard): ").strip()
                    level = int(raw) if raw else 0
                    if 0 <= level <= 3:
                        break
                    cprint("PLEASE ENTER 0, 1, 2, OR 3.", "bold cyan")
                except (ValueError, EOFError):
                    level = 0; break
            state = init_new_game(level)
            print()
            print_orders(state)
            enter_quadrant(state, is_start=True)

        result = game_loop(state, prefs)

        # Always delete save when a game session ends (win, loss, or SAE-then-quit)
        # Exception: SAE already wrote the save and returned "quit" — don't delete it.
        # We detect a live save by checking if the file was written this session.
        # Simple rule: if the file exists after the loop, the player used SAE → keep it.
        # All other exits → delete.
        if not save_exists(_SAVE_PATH):
            pass   # SAE wasn't used, nothing to delete
        elif result != "quit":
            delete_save(_SAVE_PATH)
        # If result == "quit" and save exists → SAE was used, leave file in place.

        if result == "restart":
            cprint("\n--- NEW MISSION ---\n", "bold white")
            continue
        break

    cprint(f"\nSST3 Python Edition v{VERSION}  —  End of session.", "white")
    sys.exit(0)


if __name__ == "__main__":
    main()
