"""
gui_main.py  –  SST3 Python Edition GUI
Fully playable GUI with coloured rectangles, hotkeys, clickable
command bar, modal input dialogs, and event rendering to message log.

Window is resizable.  All coordinates scale from a 1800×1000 reference.

Launch:  python gui_main.py
"""

import sys
import os
import io
import contextlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
from galaxy import init_new_game, enter_quadrant
from quadrant import EMPTY, STAR, KLINGON, SHIP, BASE
from gui_assets import (
    COLORS, ENTITY_COLORS, CONDITION_COLORS, STATUS_STYLES,
    init_fonts, font, init_sprites, sprite, clear_sprite_cache,
    star_sprite_key,
)
from gui_input import (
    numeric_input, nav_input, phaser_input, torpedo_input, shield_input,
    info_overlay, confirm_dialog,
)
from commands import NavCommand, PhaserCommand, TorpedoCommand, ShieldsCommand
from navigation import execute_nav
from combat import execute_phasers, execute_torpedo
from shields import execute_shields
from klingons import execute_klingons_fire
from config import DEVICE_NAMES, DEV_COMPUTER, DEV_SRS, DEV_LRS, galaxy_decode
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
from display import calc_direction_distance
from gui_anim import (
    advance_tick, idle_frame,
    play_explosion, play_phasor_hit, play_torpedo_track,
    play_klingon_fires, play_enterprise_hit,
)

# ---------------------------------------------------------------------------
# Reference layout (designed at 1800×1000, scales from there)
# ---------------------------------------------------------------------------
REF_W, REF_H = 1800, 1000
GRID_SIZE = 8
FPS = 30

_REF_CELL   = 80
_REF_GRID   = _REF_CELL * GRID_SIZE
_REF_GRID_X = 24
_REF_GRID_Y = 60

_REF_RECT_SIZES = {
    "ship":    (64, 64),
    "klingon": (64, 34),
    "base":    (44, 54),
    "star":    (30, 30),
}

_ENTITY_LABELS = {"ship": "E", "klingon": "K", "base": "B", "star": "*"}
_TOKEN_MAP = {STAR: "star", KLINGON: "klingon", SHIP: "ship", BASE: "base"}

# Command bar button definitions: (label, hotkey_key_constant)
_CMD_BUTTONS = [
    ("NAV", pygame.K_n),
    ("PHA", pygame.K_p),
    ("TOR", pygame.K_t),
    ("SHE", pygame.K_h),
    ("LRS", pygame.K_l),
    ("DAM", pygame.K_d),
    ("COM", pygame.K_c),
]


def _token_key(token: str) -> str:
    return _TOKEN_MAP.get(token, "empty")


@contextlib.contextmanager
def _suppress_stdout():
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        yield
    finally:
        sys.stdout = old


# ---------------------------------------------------------------------------
# Scaled layout
# ---------------------------------------------------------------------------
class Layout:
    def __init__(self, w, h):
        self.win_w = w
        self.win_h = h
        sx = w / REF_W
        sy = h / REF_H
        self.scale = s = min(sx, sy)

        self.cell   = int(_REF_CELL * s)
        self.grid   = self.cell * GRID_SIZE
        self.grid_x = int(_REF_GRID_X * s)
        self.grid_y = int(_REF_GRID_Y * s)
        self.panel_x = self.grid_x + self.grid + int(30 * s)
        self.panel_y = self.grid_y
        self.panel_w = w - self.panel_x - int(16 * s)
        self.panel_h = self.grid
        self.cmdbar_y = self.grid_y + self.grid + int(20 * s)
        self.msglog_y = self.cmdbar_y + int(50 * s)
        self.msglog_h = h - self.msglog_y - int(8 * s)

        self.font_title  = max(10, int(20 * s))
        self.font_label  = max(9,  int(16 * s))
        self.font_value  = max(10, int(22 * s))
        self.font_entity = max(10, int(22 * s))
        self.font_coord  = max(8,  int(14 * s))
        self.font_btn    = max(9,  int(16 * s))
        self.font_msg    = max(9,  int(15 * s))
        self.font_tip    = max(9,  int(15 * s))

        # Pre-compute button rects for hit testing
        self.btn_rects = []
        btn_font = font(self.font_btn)
        bw = int(70 * s)
        bh = int(36 * s)
        gap = int(10 * s)
        x = self.grid_x
        label = btn_font.render("COMMAND:", True, COLORS["bright_white"])
        x += label.get_width() + int(14 * s)
        for name, _hotkey in _CMD_BUTTONS:
            self.btn_rects.append(pygame.Rect(x, self.cmdbar_y, bw, bh))
            x += bw + gap

    def cell_center(self, row, col):
        cx = self.grid_x + (col - 1) * self.cell + self.cell // 2
        cy = self.grid_y + (row - 1) * self.cell + self.cell // 2
        return cx, cy

    def entity_rect(self, key, cx, cy):
        rw, rh = _REF_RECT_SIZES.get(key, (38, 38))
        w = int(rw * self.scale)
        h = int(rh * self.scale)
        return pygame.Rect(cx - w // 2, cy - h // 2, w, h)

    def star_radius(self):
        return max(3, int(7 * self.scale))

    def hit_button(self, mx, my):
        """Return button index (0-6) or -1 if no button hit."""
        for i, rect in enumerate(self.btn_rects):
            if rect.collidepoint(mx, my):
                return i
        return -1

    def hit_cell(self, mx, my):
        """Return (row, col) 1-indexed if mouse is inside the grid, else None."""
        if not (self.grid_x <= mx < self.grid_x + self.grid and
                self.grid_y <= my < self.grid_y + self.grid):
            return None
        col = (mx - self.grid_x) // self.cell + 1
        row = (my - self.grid_y) // self.cell + 1
        if 1 <= row <= 8 and 1 <= col <= 8:
            return (row, col)
        return None


# ---------------------------------------------------------------------------
# Drawing helpers (unchanged from Phase 1, just pass lay)
# ---------------------------------------------------------------------------
def _draw_grid(surface, grid, lay):
    bg_rect = pygame.Rect(lay.grid_x, lay.grid_y, lay.grid, lay.grid)
    pygame.draw.rect(surface, COLORS["grid_bg"], bg_rect)

    for i in range(GRID_SIZE + 1):
        x = lay.grid_x + i * lay.cell
        pygame.draw.line(surface, COLORS["grid_line"],
                         (x, lay.grid_y), (x, lay.grid_y + lay.grid))
        y = lay.grid_y + i * lay.cell
        pygame.draw.line(surface, COLORS["grid_line"],
                         (lay.grid_x, y), (lay.grid_x + lay.grid, y))

    label_font = font(lay.font_entity)
    for row in range(1, 9):
        for col in range(1, 9):
            token = grid.get(row, col)
            key = _token_key(token)
            color = ENTITY_COLORS.get(key)
            if color is None:
                continue
            cx, cy = lay.cell_center(row, col)
            ent_rect = lay.entity_rect(key, cx, cy)
            # Idle animation: cycle frames for ship, stars, bases
            spr_key = star_sprite_key(row, col) if key == "star" else key
            frame = idle_frame(spr_key, cycle_speed=15) if key in ("ship", "star", "base") else 0
            spr = sprite(spr_key, ent_rect.width, ent_rect.height, frame=frame)
            if spr is not None:
                surface.blit(spr, ent_rect)
            elif key == "star":
                pygame.draw.circle(surface, color, (cx, cy), lay.star_radius())
            else:
                pygame.draw.rect(surface, color, ent_rect)
                pygame.draw.rect(surface, COLORS["bright_white"], ent_rect, 1)
                lbl = _ENTITY_LABELS.get(key, "?")
                txt = label_font.render(lbl, True, COLORS["black"])
                surface.blit(txt, txt.get_rect(center=(cx, cy)))

    pygame.draw.rect(surface, COLORS["bright_white"], bg_rect, 2)

    coord_font = font(lay.font_coord)
    for i in range(GRID_SIZE):
        txt = coord_font.render(str(i + 1), True, COLORS["bright_white"])
        x = lay.grid_x + i * lay.cell + lay.cell // 2 - txt.get_width() // 2
        surface.blit(txt, (x, lay.grid_y - txt.get_height() - 2))
        txt = coord_font.render(str(i + 1), True, COLORS["bright_white"])
        y = lay.grid_y + i * lay.cell + lay.cell // 2 - txt.get_height() // 2
        surface.blit(txt, (lay.grid_x - txt.get_width() - 4, y))


def _draw_status_panel(surface, state, lay):
    hdr_font = font(lay.font_title)
    val_font = font(lay.font_value)
    lbl_font = font(lay.font_label)

    panel_rect = pygame.Rect(lay.panel_x, lay.panel_y,
                             lay.panel_w, lay.panel_h)
    pygame.draw.rect(surface, COLORS["panel_bg"], panel_rect)
    pygame.draw.rect(surface, COLORS["panel_border"], panel_rect, 1)

    title = hdr_font.render("STATUS", True, COLORS["bright_white"])
    surface.blit(title, (lay.panel_x + int(12 * lay.scale),
                         lay.panel_y + int(10 * lay.scale)))

    rows = _build_status_rows(state)
    y = lay.panel_y + int(42 * lay.scale)
    row_spacing = max(40, int(62 * lay.scale))
    for label, value, color in rows:
        lt = lbl_font.render(label, True, COLORS["bright_white"])
        surface.blit(lt, (lay.panel_x + int(12 * lay.scale), y))
        vt = val_font.render(value, True, color)
        surface.blit(vt, (lay.panel_x + int(12 * lay.scale),
                          y + lt.get_height() + 2))
        y += row_spacing
        if y > lay.panel_y + lay.panel_h - 20:
            break


def _build_status_rows(state):
    rows = []
    deadline = state.start_stardate + state.mission_days - 7
    sd_color = (STATUS_STYLES["stardate_warn"] if state.stardate > deadline
                else COLORS["bright_white"])
    rows.append(("STARDATE", f"{state.stardate:.1f}", sd_color))
    cond = state.condition()
    rows.append(("CONDITION", cond,
                 CONDITION_COLORS.get(cond, COLORS["bright_white"])))
    rows.append(("QUADRANT", f"{state.quad_row},{state.quad_col}",
                 COLORS["bright_green"]))
    rows.append(("SECTOR", f"{state.sec_row},{state.sec_col}",
                 COLORS["bright_green"]))
    tc = (STATUS_STYLES["torpedoes_low"] if state.torpedoes < 4
          else STATUS_STYLES["torpedoes_ok"])
    rows.append(("PHOTON TORPEDOES", str(int(state.torpedoes)), tc))
    total = int(state.energy + state.shields)
    ec = (STATUS_STYLES["energy_crit"] if total < 400
          else STATUS_STYLES["energy_low"] if total < 1000
          else STATUS_STYLES["energy_ok"])
    rows.append(("TOTAL ENERGY", str(total), ec))
    s = int(state.shields)
    sc = (STATUS_STYLES["shields_crit"] if s < 250
          else STATUS_STYLES["shields_low"] if s < 700
          else STATUS_STYLES["shields_ok"])
    rows.append(("SHIELDS", str(s), sc))
    rows.append(("KLINGONS REMAINING",
                 str(int(state.total_klingons)),
                 STATUS_STYLES["klingons"]))
    return rows


def _draw_command_bar(surface, lay, hover_btn=-1):
    btn_font = font(lay.font_btn)
    bw = int(70 * lay.scale)
    bh = int(36 * lay.scale)

    strip = pygame.Rect(0, lay.cmdbar_y - 4, lay.win_w, bh + 8)
    pygame.draw.rect(surface, COLORS["panel_bg"], strip)

    x = lay.grid_x
    label = btn_font.render("COMMAND:", True, COLORS["bright_white"])
    surface.blit(label, (x, lay.cmdbar_y + (bh - label.get_height()) // 2))

    for i, (name, _hotkey) in enumerate(_CMD_BUTTONS):
        rect = lay.btn_rects[i]
        bg = COLORS["button_hover"] if i == hover_btn else COLORS["button_bg"]
        pygame.draw.rect(surface, bg, rect)
        border = COLORS["bright_cyan"] if i == hover_btn else COLORS["panel_border"]
        pygame.draw.rect(surface, border, rect, 1)
        txt = btn_font.render(name, True, COLORS["button_text"])
        surface.blit(txt, txt.get_rect(center=rect.center))


def _draw_message_log(surface, messages, lay):
    log_rect = pygame.Rect(0, lay.msglog_y, lay.win_w, lay.msglog_h)
    pygame.draw.rect(surface, COLORS["msg_bg"], log_rect)
    pygame.draw.line(surface, COLORS["panel_border"],
                     (0, lay.msglog_y), (lay.win_w, lay.msglog_y))
    msg_font = font(lay.font_msg)
    line_h = msg_font.get_linesize() + 2
    y = lay.msglog_y + 4
    max_lines = max(1, lay.msglog_h // line_h)
    for msg, color in messages[-max_lines:]:
        txt = msg_font.render(msg, True, color)
        surface.blit(txt, (int(12 * lay.scale), y))
        y += line_h


def _draw_title_bar(surface, state, lay):
    bar = pygame.Rect(0, 0, lay.win_w, lay.grid_y - 4)
    pygame.draw.rect(surface, COLORS["panel_bg"], bar)
    title_font = font(lay.font_title)
    from names import quadrant_name
    qname = quadrant_name(state.quad_row, state.quad_col)
    title = f"SST3  \u2014  {qname}  ({state.quad_row},{state.quad_col})"
    txt = title_font.render(title, True, COLORS["bright_cyan"])
    surface.blit(txt, (lay.grid_x,
                       (lay.grid_y - 4) // 2 - txt.get_height() // 2))
    cond = state.condition()
    cc = CONDITION_COLORS.get(cond, COLORS["bright_white"])
    ct = title_font.render(cond, True, cc)
    surface.blit(ct, (lay.win_w - ct.get_width() - 20,
                      (lay.grid_y - 4) // 2 - ct.get_height() // 2))


def _draw_hover_info(surface, grid, mx, my, lay, state=None):
    if not (lay.grid_x <= mx < lay.grid_x + lay.grid and
            lay.grid_y <= my < lay.grid_y + lay.grid):
        return
    col = (mx - lay.grid_x) // lay.cell + 1
    row = (my - lay.grid_y) // lay.cell + 1
    if not (1 <= row <= 8 and 1 <= col <= 8):
        return
    token = grid.get(row, col)
    key = _token_key(token)
    names = {"ship": "USS Enterprise", "klingon": "Klingon Warship",
             "base": "Starbase", "star": "Star", "empty": "Empty Space"}
    text = f"{names.get(key, '?')}  [{row},{col}]"

    # Add distance/direction and action hint for non-ship entities
    if state is not None and key != "ship":
        result = calc_direction_distance(
            state.sec_row, state.sec_col, row, col)
        if result[0] is not None:
            course, _, adist = result
            text += f"  D={course:.1f} R={adist:.1f}"
        if key == "klingon":
            text += "  [Click=Torpedo  Shift=Phaser]"
        elif key in ("empty", "base"):
            text += "  [Click=Navigate]"

    tip_font = font(lay.font_tip)
    txt_surf = tip_font.render(text, True, COLORS["bright_white"])
    tw, th = txt_surf.get_size()
    pad = int(5 * lay.scale)
    tx = min(mx + 14, lay.win_w - tw - pad * 2 - 4)
    ty = max(my - th - pad * 2 - 6, 0)
    bg = pygame.Rect(tx, ty, tw + pad * 2, th + pad * 2)
    pygame.draw.rect(surface, (25, 25, 40), bg)
    pygame.draw.rect(surface, COLORS["panel_border"], bg, 1)
    surface.blit(txt_surf, (tx + pad, ty + pad))


# ---------------------------------------------------------------------------
# Event → message log rendering
# ---------------------------------------------------------------------------
_C = COLORS  # shorthand

def _render_events(events, messages):
    """Translate a list of engine Events into message log entries."""
    for ev in events:
        if isinstance(ev, InvalidCourse):
            messages.append((f"LT. SULU REPORTS, 'INCORRECT COURSE DATA, SIR!'",
                             _C["bright_red"]))
        elif isinstance(ev, InvalidWarp):
            messages.append((f"CHIEF ENGINEER SCOTT REPORTS 'THE ENGINES WON'T "
                             f"TAKE WARP {ev.warp:.1f}!'",
                             _C["bright_red"]))
        elif isinstance(ev, WarpEnginesDamaged):
            messages.append(("WARP ENGINES ARE DAMAGED. MAX SPEED = WARP 0.2",
                             _C["bright_red"]))
        elif isinstance(ev, InsufficientEnergy):
            messages.append(("ENGINEERING REPORTS 'INSUFFICIENT ENERGY FOR MANEUVERING"
                             " AT WARP REQUESTED'",
                             _C["bright_red"]))
            if ev.shield_energy > 0 and not ev.shields_damaged:
                messages.append(("DEFLECTOR CONTROL ROOM ACKNOWLEDGES "
                                 f"{int(ev.shield_energy)} UNITS OF ENERGY PRESENTLY "
                                 "DEPLOYED TO SHIELDS.",
                                 _C["bright_cyan"]))
        elif isinstance(ev, ShieldsCrossCircuit):
            messages.append((f"SHIELD CONTROL SUPPLIES ENERGY TO COMPLETE THE MANEUVER "
                             f"(shields: {int(ev.shields_after)})",
                             _C["bright_yellow"]))
        elif isinstance(ev, NavigationBlocked):
            r, c = ev.obstacle_sector
            messages.append((f"WARP ENGINES SHUT DOWN AT SECTOR "
                             f"{ev.stopped_sector[0]},{ev.stopped_sector[1]} "
                             f"DUE TO BAD NAVIGATION",
                             _C["bright_yellow"]))
        elif isinstance(ev, GalacticPerimeterDenied):
            messages.append(("PERMISSION TO CROSS GALACTIC PERIMETER DENIED",
                             _C["bright_cyan"]))
        elif isinstance(ev, QuadrantEntered):
            messages.append((f"NOW ENTERING {ev.quadrant_name} QUADRANT . . .",
                             _C["bright_white"]))
            if ev.klingons > 0:
                messages.append(("COMBAT AREA      CONDITION RED",
                                 _C["bright_red"]))
        elif isinstance(ev, ShipMoved):
            messages.append((f"Ship moved to sector "
                             f"{ev.to_sector[0]},{ev.to_sector[1]}  "
                             f"(energy used: {int(ev.energy_used)}, "
                             f"stardate: {ev.stardate_after:.1f})",
                             _C["bright_white"]))
        elif isinstance(ev, Docked):
            messages.append(("SHIELDS DROPPED FOR DOCKING PURPOSES",
                             _C["bright_cyan"]))
            messages.append(("STARBASE RESUPPLY: ENERGY AND TORPEDOES RESTORED",
                             _C["bright_green"]))
        elif isinstance(ev, DeviceRepaired):
            messages.append((f"DAMAGE CONTROL REPORT: {ev.device_name.upper()} REPAIR COMPLETED",
                             _C["bright_green"]))
        elif isinstance(ev, DeviceDamaged):
            messages.append((f"DAMAGE CONTROL REPORT: {ev.device_name.upper()} DAMAGED",
                             _C["bright_red"]))
        elif isinstance(ev, DeviceImproved):
            messages.append((f"DAMAGE CONTROL REPORT: {ev.device_name.upper()} STATE IMPROVED",
                             _C["bright_green"]))
        elif isinstance(ev, StarbaseProtection):
            messages.append(("STARBASE SHIELDS PROTECT THE ENTERPRISE",
                             _C["bright_cyan"]))
        elif isinstance(ev, KlingonsAmbush):
            messages.append(("KLINGON SHIPS FIRE FIRST!",
                             _C["bright_red"]))
        elif isinstance(ev, KlingonsCounterFire):
            messages.append(("KLINGONS RETURN FIRE!",
                             _C["bright_red"]))
        elif isinstance(ev, KlingonFired):
            r, c = ev.from_sector
            messages.append((f"{ev.damage} UNIT HIT ON ENTERPRISE FROM SECTOR "
                             f"{r},{c}  (shields: {int(ev.shields_after)})",
                             _C["bright_red"]))
            if ev.device_name:
                messages.append((f"DAMAGE CONTROL REPORTS {ev.device_name.upper()} "
                                 "DAMAGED BY THE HIT",
                                 _C["bright_magenta"]))
        elif isinstance(ev, EnterpriseDestroyed):
            messages.append(("*** THE ENTERPRISE HAS BEEN DESTROYED ***",
                             _C["bright_red"]))
        elif isinstance(ev, PhasersInoperative):
            messages.append(("PHASER CONTROL IS INOPERATIVE",
                             _C["bright_red"]))
        elif isinstance(ev, NoEnemiesInQuadrant):
            messages.append(("SCIENCE OFFICER SPOCK REPORTS 'SENSORS SHOW NO "
                             "ENEMY SHIPS IN THIS QUADRANT'",
                             _C["bright_cyan"]))
        elif isinstance(ev, ComputerDamagesAccuracy):
            messages.append(("COMPUTER FAILURE HAMPERS ACCURACY",
                             _C["bright_yellow"]))
        elif isinstance(ev, InsufficientPhaserEnergy):
            messages.append((f"INSUFFICIENT ENERGY TO FIRE PHASERS "
                             f"({int(ev.available)} available)",
                             _C["bright_red"]))
        elif isinstance(ev, PhaserFired):
            messages.append((f"PHASERS FIRED: {int(ev.energy_fired)} UNITS",
                             _C["bright_cyan"]))
        elif isinstance(ev, KlingonHit):
            r, c = ev.sector
            messages.append((f"{ev.damage} UNIT HIT ON KLINGON AT SECTOR "
                             f"{r},{c}  (energy left: {int(ev.klingon_energy_after)})",
                             _C["bright_cyan"]))
        elif isinstance(ev, KlingonNoDamage):
            r, c = ev.sector
            messages.append((f"SENSORS SHOW NO DAMAGE TO ENEMY AT SECTOR {r},{c}",
                             _C["bright_yellow"]))
        elif isinstance(ev, KlingonDestroyed):
            messages.append(("*** KLINGON DESTROYED ***",
                             _C["bright_green"]))
            messages.append((f"{ev.total_klingons_remaining} Klingon(s) remaining.",
                             _C["bright_white"]))
        elif isinstance(ev, Victory):
            messages.append(("*** CONGRATULATIONS! THE MISSION IS A SUCCESS! ***",
                             _C["bright_green"]))
            messages.append((f"Rating: {ev.efficiency_rating:.0f}  "
                             f"({ev.elapsed_stardates:.1f} stardates elapsed)",
                             _C["bright_green"]))
        elif isinstance(ev, TorpedoesExpended):
            messages.append(("ALL PHOTON TORPEDOES EXPENDED",
                             _C["bright_red"]))
        elif isinstance(ev, TubesDamaged):
            messages.append(("PHOTON TUBES ARE NOT OPERATIONAL",
                             _C["bright_red"]))
        elif isinstance(ev, InvalidTorpedoCourse):
            messages.append((f"ENSIGN CHEKOV REPORTS, 'INCORRECT COURSE DATA, SIR!'",
                             _C["bright_red"]))
        elif isinstance(ev, TorpedoFired):
            messages.append((f"TORPEDO TRACK: course {ev.course:.1f}",
                             _C["bright_cyan"]))
        elif isinstance(ev, TorpedoTracked):
            r, c = ev.sector
            messages.append((f"  {r},{c}", _C["bright_cyan"]))
        elif isinstance(ev, TorpedoMissed):
            messages.append(("TORPEDO MISSED", _C["bright_yellow"]))
        elif isinstance(ev, TorpedoAbsorbedByStar):
            r, c = ev.sector
            messages.append((f"STAR AT {r},{c} ABSORBS TORPEDO ENERGY",
                             _C["bright_yellow"]))
        elif isinstance(ev, StarbaseDestroyed):
            messages.append(("*** STARBASE DESTROYED ***",
                             _C["bright_red"]))
            if ev.court_martial:
                messages.append(("STARFLEET COMMAND REVIEWING YOUR RECORD TO "
                                 "CONSIDER COURT MARTIAL!",
                                 _C["bright_red"]))
        elif isinstance(ev, ShieldControlInoperable):
            messages.append(("SHIELD CONTROL IS INOPERABLE",
                             _C["bright_red"]))
        elif isinstance(ev, ShieldsUnchanged):
            reason_msgs = {
                "same":      "SHIELDS UNCHANGED",
                "negative":  "SHIELDS UNCHANGED (NEGATIVE VALUE)",
                "overspend": "SHIELD ENERGY EXCEEDS SHIP ENERGY",
                "cancelled": "SHIELD COMMAND CANCELLED",
            }
            messages.append((reason_msgs.get(ev.reason, "SHIELDS UNCHANGED"),
                             _C["bright_yellow"]))
        elif isinstance(ev, ShieldsSet):
            messages.append((f"DEFLECTOR CONTROL ROOM REPORT: "
                             f"SHIELDS NOW AT {int(ev.shields_after)} "
                             f"(energy: {int(ev.energy_after)})",
                             _C["bright_cyan"]))


# ---------------------------------------------------------------------------
# LRS / DAM / COM info builders
# ---------------------------------------------------------------------------
def _build_lrs_lines(state):
    """Build LRS display as list of (text, color) lines."""
    lines = []
    if not state.is_device_ok(DEV_LRS):
        lines.append(("LONG RANGE SENSORS ARE INOPERABLE", _C["bright_magenta"]))
        return lines
    lines.append((f"LONG RANGE SCAN FOR QUADRANT {state.quad_row},{state.quad_col}",
                  _C["bright_green"]))
    lines.append(("-------------------", _C["bright_white"]))
    for dr in range(-1, 2):
        r = state.quad_row + dr
        parts = []
        for dc in range(-1, 2):
            c = state.quad_col + dc
            if 1 <= r <= 8 and 1 <= c <= 8:
                val = state.galaxy_get(r, c)
                state.scanned_set(r, c, val)
                parts.append(f": {val:03d} ")
            else:
                parts.append(": *** ")
        lines.append(("".join(parts) + ":", _C["bright_cyan"]))
        lines.append(("-------------------", _C["bright_white"]))
    return lines


def _build_dam_lines(state):
    """Build damage report as list of (text, color) lines."""
    lines = []
    dam_ok = state.is_device_ok(5)
    if not dam_ok:
        lines.append(("DAMAGE CONTROL REPORT NOT AVAILABLE", _C["bright_magenta"]))
    if state.docked:
        damaged = [i for i in range(8) if state.damage[i] < 0]
        if damaged:
            d3 = min(len(damaged) * 0.1 + state.d4, 0.9)
            lines.append(("TECHNICIANS STANDING BY TO EFFECT REPAIRS",
                          _C["bright_cyan"]))
            lines.append((f"ESTIMATED TIME TO REPAIR: {d3:.2f} STARDATES",
                          _C["bright_cyan"]))
            lines.append(("(Press Y to authorize, N to decline)",
                          _C["bright_white"]))
    if dam_ok:
        lines.append(("", _C["bright_white"]))
        lines.append(("DEVICE              STATE OF REPAIR", _C["bright_white"]))
        for i, name in enumerate(DEVICE_NAMES):
            val = state.damage[i]
            c = _C["bright_green"] if val >= 0 else _C["bright_red"]
            lines.append((f"  {name:<22}{val:+.2f}", c))
    return lines


def _build_com_lines(state):
    """Build computer menu as list of (text, color) lines."""
    lines = []
    if not state.is_device_ok(DEV_COMPUTER):
        lines.append(("COMPUTER DISABLED", _C["bright_cyan"]))
        return lines

    lines.append(("LIBRARY-COMPUTER FUNCTIONS:", _C["bright_cyan"]))
    lines.append(("", _C["bright_white"]))

    # Status report
    lines.append(("--- STATUS REPORT ---", _C["bright_cyan"]))
    k = int(state.total_klingons)
    lines.append((f"KLINGON{'S' if k != 1 else ''} LEFT: {k}", _C["bright_cyan"]))
    lines.append((f"MISSION MUST BE COMPLETED IN {state.time_remaining():.1f} STARDATES",
                  _C["bright_cyan"]))
    b = int(state.total_bases)
    if b == 0:
        lines.append(("YOU HAVE NO STARBASES LEFT!", _C["bright_red"]))
    else:
        lines.append((f"THE FEDERATION IS MAINTAINING {b} STARBASE{'S' if b > 1 else ''} "
                      "IN THE GALAXY", _C["bright_cyan"]))
    lines.append(("", _C["bright_white"]))

    # Torpedo data
    lines.append(("--- PHOTON TORPEDO DATA ---", _C["bright_cyan"]))
    klingons = state.alive_klingons()
    if not klingons:
        lines.append(("SENSORS SHOW NO ENEMY SHIPS IN THIS QUADRANT",
                      _C["bright_cyan"]))
    else:
        for k in klingons:
            result = calc_direction_distance(
                state.sec_row, state.sec_col, k.row, k.col)
            if result[0] is not None:
                course, gdist, adist = result
                lines.append((f"KLINGON AT {k.row},{k.col}: "
                              f"DIRECTION={course:.2f}  DISTANCE={adist:.2f}",
                              _C["bright_cyan"]))
    lines.append(("", _C["bright_white"]))

    # Starbase nav
    lines.append(("--- STARBASE NAV DATA ---", _C["bright_cyan"]))
    if state.bases_here < 1:
        lines.append(("NO STARBASES IN THIS QUADRANT",
                      _C["bright_cyan"]))
    else:
        result = calc_direction_distance(
            state.sec_row, state.sec_col,
            state.base_sec_row, state.base_sec_col)
        if result[0] is not None:
            course, gdist, adist = result
            lines.append((f"STARBASE AT {state.base_sec_row},{state.base_sec_col}: "
                          f"DIRECTION={course:.2f}  DISTANCE={adist:.2f}",
                          _C["bright_cyan"]))
    lines.append(("", _C["bright_white"]))

    # Cumulative galactic record — highlight current quadrant
    lines.append(("--- CUMULATIVE GALACTIC RECORD ---", _C["bright_cyan"]))
    lines.append(("  " + "  ".join(f" {c} " for c in range(1, 9)),
                  _C["white"]))
    for r in range(1, 9):
        row_parts = []
        for c in range(1, 9):
            val = state.scanned_get(r, c)
            cell = f"{val:03d}" if val > 0 else "***"
            if r == state.quad_row and c == state.quad_col:
                cell = f"[{cell}]"
            else:
                cell = f" {cell} "
            row_parts.append(cell)
        is_current_row = (r == state.quad_row)
        color = _C["bright_yellow"] if is_current_row else _C["bright_cyan"]
        lines.append((f"{r} " + " ".join(row_parts), color))

    return lines


# ---------------------------------------------------------------------------
# Difficulty selection dialog
# ---------------------------------------------------------------------------
_DIFFICULTY_LABELS = [
    ("0  DEFAULT",  "Standard game \u2014 3000 energy, normal Klingons"),
    ("1  EASY",     "3000 energy, tougher Klingons, 25% first shot"),
    ("2  MEDIUM",   "4000 energy, strong Klingons, 50% first shot"),
    ("3  HARD",     "5000 energy, very strong Klingons, always fire first"),
]


def _difficulty_dialog(screen, clock):
    selected = 0
    while True:
        w, h = screen.get_size()
        s = min(w / REF_W, h / REF_H)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(
                    (event.w, event.h), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN: return selected
                elif event.key == pygame.K_UP: selected = (selected - 1) % 4
                elif event.key == pygame.K_DOWN: selected = (selected + 1) % 4
                elif event.key in (pygame.K_0, pygame.K_KP0): return 0
                elif event.key in (pygame.K_1, pygame.K_KP1): return 1
                elif event.key in (pygame.K_2, pygame.K_KP2): return 2
                elif event.key in (pygame.K_3, pygame.K_KP3): return 3
                elif event.key == pygame.K_ESCAPE: return 0
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                box_w = int(700 * s); box_h = int(400 * s)
                bx = (w - box_w) // 2; by = (h - box_h) // 2
                opt_y_start = by + int(90 * s); opt_h = int(70 * s)
                for i in range(4):
                    oy = opt_y_start + i * opt_h
                    if bx <= mx <= bx + box_w and oy <= my <= oy + opt_h:
                        return i

        screen.fill(COLORS["black"])
        box_w = int(700 * s); box_h = int(400 * s)
        bx = (w - box_w) // 2; by = (h - box_h) // 2
        pygame.draw.rect(screen, COLORS["dialog_bg"], (bx, by, box_w, box_h))
        pygame.draw.rect(screen, COLORS["dialog_border"], (bx, by, box_w, box_h), 2)

        tf = font(max(12, int(24 * s)))
        title = tf.render("SELECT DIFFICULTY", True, COLORS["bright_cyan"])
        screen.blit(title, (bx + (box_w - title.get_width()) // 2, by + int(20 * s)))

        sf = font(max(9, int(14 * s)))
        sub = sf.render("Press 0-3 or click, Enter to confirm", True, COLORS["white"])
        screen.blit(sub, (bx + (box_w - sub.get_width()) // 2, by + int(55 * s)))

        opt_font = font(max(10, int(20 * s)))
        desc_font = font(max(9, int(14 * s)))
        opt_y = by + int(90 * s); opt_h = int(70 * s)
        for i, (label, desc) in enumerate(_DIFFICULTY_LABELS):
            rect = pygame.Rect(bx + int(20 * s), opt_y,
                               box_w - int(40 * s), opt_h - int(6 * s))
            if i == selected:
                pygame.draw.rect(screen, COLORS["highlight"], rect)
                pygame.draw.rect(screen, COLORS["bright_cyan"], rect, 2)
            else:
                pygame.draw.rect(screen, COLORS["panel_bg"], rect)
                pygame.draw.rect(screen, COLORS["panel_border"], rect, 1)
            lt = opt_font.render(label, True, COLORS["bright_white"])
            screen.blit(lt, (rect.x + int(14 * s), rect.y + int(8 * s)))
            dt = desc_font.render(desc, True, COLORS["white"])
            screen.blit(dt, (rect.x + int(14 * s),
                             rect.y + int(8 * s) + lt.get_height() + 4))
            opt_y += opt_h

        pygame.display.flip()
        clock.tick(FPS)


# ---------------------------------------------------------------------------
# Game-over check helpers
# ---------------------------------------------------------------------------
def _check_stranded(state, messages):
    """Check if ship is stranded (energy + shields <= 10, shields damaged)."""
    if state.energy + state.shields <= 10:
        if state.energy <= 10 and not state.is_device_ok(6):
            messages.append(("** FATAL ERROR **  YOU'VE STRANDED YOUR SHIP IN SPACE",
                             _C["bright_red"]))
            return True
    return False


def _check_time_expired(state, messages):
    if state.stardate >= state.start_stardate + state.mission_days:
        messages.append((f"IT IS STARDATE {state.stardate:.1f}",
                         _C["bright_white"]))
        messages.append(("THE FEDERATION HAS BEEN CONQUERED.",
                         _C["bright_red"]))
        return True
    return False


# ---------------------------------------------------------------------------
# Grid-click actions  (Phase 6: mouse interaction)
# ---------------------------------------------------------------------------
def _handle_grid_click(row, col, state, messages, screen, clock, lay,
                       shift=False):
    """Handle a left-click on grid cell (row, col).
    Returns "ok", "victory", or "destroyed"."""
    token = state.quadrant_grid.get(row, col)
    key = _token_key(token)

    if key == "klingon":
        if shift:
            # Shift+click → fire phasers
            if not state.is_device_ok(DEV_COMPUTER):
                messages.append(("COMPUTER DISABLED — PHASERS CANNOT LOCK",
                                 _C["bright_red"]))
                return "ok"
            klingons = state.alive_klingons()
            if not klingons:
                return "ok"
            energy = state.energy // len(klingons)
            if energy < 1:
                messages.append(("INSUFFICIENT ENERGY FOR PHASERS",
                                 _C["bright_red"]))
                return "ok"
            grid_snap = _snapshot_grid(state.quadrant_grid)
            events = execute_phasers(state, PhaserCommand(energy=energy))
            _render_events(events, messages)
            _animate_combat_events(events, state, messages, screen, clock,
                                   lay, grid_snapshot=grid_snap)
            if is_victory(events):
                return "victory"
            if is_fatal(events):
                return "destroyed"
        else:
            # Click → fire torpedo at Klingon
            if state.torpedoes <= 0:
                messages.append(("ALL PHOTON TORPEDOES EXPENDED",
                                 _C["bright_red"]))
                return "ok"
            result = calc_direction_distance(
                state.sec_row, state.sec_col, row, col)
            if result[0] is None:
                return "ok"
            course = result[0]
            messages.append((f"TORPEDO LOCKED ON [{row},{col}]  COURSE {course:.2f}",
                             _C["bright_cyan"]))
            grid_snap = _snapshot_grid(state.quadrant_grid)
            events = execute_torpedo(state, TorpedoCommand(course=course))
            _render_events(events, messages)
            _animate_combat_events(events, state, messages, screen, clock,
                                   lay, grid_snapshot=grid_snap)
            if is_victory(events):
                return "victory"
            if is_fatal(events):
                return "destroyed"

    elif key == "empty":
        # Click empty space → navigate
        result = calc_direction_distance(
            state.sec_row, state.sec_col, row, col)
        if result[0] is None:
            return "ok"
        course = result[0]
        dist = result[1]  # game_dist (Chebyshev sectors)
        # Auto-calculate warp: sector distance / 8 (one quadrant = warp 1)
        warp = min(dist / 8.0, 0.2) if dist <= 2 else 0.2
        # Prompt for warp — pre-fill info in message
        messages.append((f"COURSE {course:.2f} TO [{row},{col}]  — ENTER WARP FACTOR",
                         _C["bright_cyan"]))
        warp = numeric_input(screen, clock,
                             f"WARP FACTOR (0-8) — course {course:.2f}:",
                             bounds=(0, 8), fps=FPS)
        if warp is None:
            return "ok"
        events = execute_nav(state, NavCommand(course=course, warp=warp))
        _render_events(events, messages)
        if is_victory(events):
            return "victory"
        if is_fatal(events):
            return "destroyed"
        if state.fire_first:
            fire_snap = _snapshot_grid(state.quadrant_grid)
            fire_evts = [KlingonsAmbush()] + execute_klingons_fire(state)
            state.fire_first = False
            _render_events(fire_evts, messages)
            _animate_combat_events(fire_evts, state, messages,
                                   screen, clock, lay,
                                   grid_snapshot=fire_snap)
            if is_fatal(fire_evts):
                return "destroyed"
        if _check_stranded(state, messages):
            return "destroyed"
        if _check_time_expired(state, messages):
            return "destroyed"

    elif key == "star":
        messages.append((f"STAR AT SECTOR [{row},{col}] — NAVIGATION HAZARD",
                         _C["bright_yellow"]))

    elif key == "base":
        result = calc_direction_distance(
            state.sec_row, state.sec_col, row, col)
        if result[0] is not None:
            course, gdist, adist = result
            messages.append((f"STARBASE AT [{row},{col}]: "
                             f"DIRECTION={course:.2f}  DISTANCE={adist:.2f}",
                             _C["bright_cyan"]))
        # Navigate to dock
        if result[0] is not None:
            warp = numeric_input(screen, clock,
                                 f"WARP TO STARBASE? (0-8) — course {course:.2f}:",
                                 bounds=(0, 8), fps=FPS)
            if warp is not None:
                events = execute_nav(state, NavCommand(course=course, warp=warp))
                _render_events(events, messages)
                if is_victory(events):
                    return "victory"
                if is_fatal(events):
                    return "destroyed"
                if _check_stranded(state, messages):
                    return "destroyed"
                if _check_time_expired(state, messages):
                    return "destroyed"

    elif key == "ship":
        messages.append(("THAT'S US, CAPTAIN.", _C["bright_cyan"]))

    return "ok"


def _handle_right_click(row, col, state, messages):
    """Right-click on grid cell — show distance/direction info."""
    token = state.quadrant_grid.get(row, col)
    key = _token_key(token)
    names = {"ship": "USS ENTERPRISE", "klingon": "KLINGON WARSHIP",
             "base": "STARBASE", "star": "STAR", "empty": "EMPTY SPACE"}
    name = names.get(key, "UNKNOWN")

    result = calc_direction_distance(
        state.sec_row, state.sec_col, row, col)
    if result[0] is not None:
        course, gdist, adist = result
        messages.append((f"{name} AT [{row},{col}]: "
                         f"DIRECTION={course:.2f}  DISTANCE={adist:.2f}",
                         _C["bright_green"]))
    else:
        messages.append((f"{name} AT [{row},{col}]: YOUR POSITION",
                         _C["bright_green"]))


# ---------------------------------------------------------------------------
# Combat animation integration
# ---------------------------------------------------------------------------
def _snapshot_grid(grid):
    """Shallow-copy a Quadrant grid so animations show pre-combat state."""
    from quadrant import Quadrant
    snap = Quadrant()
    snap._grid = dict(grid._grid)
    return snap


def _animate_combat_events(events, state, messages, screen, clock, lay,
                           grid_snapshot=None):
    """Play combat animations based on event types.
    grid_snapshot: pre-combat grid so destroyed entities still render
    during beam/torpedo animations until their explosion plays."""
    ship_row, ship_col = state.sec_row, state.sec_col
    go = grid_snapshot  # shorthand

    # Collect torpedo track sectors for batch animation
    torpedo_sectors = []

    for ev in events:
        if isinstance(ev, PhaserFired):
            pass  # beam drawn per KlingonHit below

        elif isinstance(ev, KlingonHit):
            play_phasor_hit(screen, clock, lay, state, messages,
                            ship_row, ship_col,
                            ev.sector[0], ev.sector[1], fps=FPS,
                            grid_override=go)
            # If klingon survived, no need to update snapshot
            # If destroyed, the next KlingonDestroyed event handles it

        elif isinstance(ev, KlingonDestroyed):
            # Flush torpedo track if torpedo killed this klingon
            if torpedo_sectors:
                play_torpedo_track(screen, clock, lay, state, messages,
                                   torpedo_sectors, fps=FPS,
                                   grid_override=go)
                torpedo_sectors = []
            # Explosion plays over the klingon (still in snapshot)
            play_explosion(screen, clock, lay, state, messages,
                           ev.sector[0], ev.sector[1], fps=FPS,
                           grid_override=go)
            # Now remove from snapshot so subsequent animations don't show it
            if go is not None:
                go.clear(ev.sector[0], ev.sector[1])

        elif isinstance(ev, TorpedoFired):
            torpedo_sectors = []

        elif isinstance(ev, TorpedoTracked):
            torpedo_sectors.append(ev.sector)

        elif isinstance(ev, (TorpedoMissed, TorpedoAbsorbedByStar,
                             StarbaseDestroyed)):
            if torpedo_sectors:
                play_torpedo_track(screen, clock, lay, state, messages,
                                   torpedo_sectors, fps=FPS,
                                   grid_override=go)
                torpedo_sectors = []
            if isinstance(ev, StarbaseDestroyed):
                play_explosion(screen, clock, lay, state, messages,
                               ev.sector[0], ev.sector[1], fps=FPS,
                               grid_override=go)
                if go is not None:
                    go.clear(ev.sector[0], ev.sector[1])

        elif isinstance(ev, KlingonFired):
            play_klingon_fires(screen, clock, lay, state, messages,
                               ev.from_sector[0], ev.from_sector[1],
                               ship_row, ship_col, fps=FPS,
                               grid_override=go)
            play_enterprise_hit(screen, clock, lay, state, messages, fps=FPS,
                                grid_override=go)

        elif isinstance(ev, EnterpriseDestroyed):
            play_explosion(screen, clock, lay, state, messages,
                           ship_row, ship_col, fps=FPS,
                           grid_override=go)

    # Flush any remaining torpedo sectors
    if torpedo_sectors:
        play_torpedo_track(screen, clock, lay, state, messages,
                           torpedo_sectors, fps=FPS,
                           grid_override=go)


# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------
def _do_command(cmd_index, state, messages, screen, clock, lay):
    """
    Execute a command by button index. Returns:
      "ok"        — normal, continue playing
      "victory"   — game won
      "destroyed" — game lost
    """
    name = _CMD_BUTTONS[cmd_index][0]

    if name == "NAV":
        result = nav_input(screen, clock, fps=FPS)
        if result is None:
            return "ok"
        course, warp = result
        events = execute_nav(state, NavCommand(course=course, warp=warp))
        _render_events(events, messages)
        if is_victory(events):
            return "victory"
        if is_fatal(events):
            return "destroyed"
        # Handle fire_first after quadrant entry
        if state.fire_first:
            fire_snap = _snapshot_grid(state.quadrant_grid)
            fire_evts = [KlingonsAmbush()] + execute_klingons_fire(state)
            state.fire_first = False
            _render_events(fire_evts, messages)
            _animate_combat_events(fire_evts, state, messages,
                                   screen, clock, lay,
                                   grid_snapshot=fire_snap)
            if is_fatal(fire_evts):
                return "destroyed"
        if _check_stranded(state, messages):
            return "destroyed"
        if _check_time_expired(state, messages):
            return "destroyed"

    elif name == "PHA":
        energy = phaser_input(screen, clock, state.energy, fps=FPS)
        if energy is None:
            return "ok"
        grid_snap = _snapshot_grid(state.quadrant_grid)
        events = execute_phasers(state, PhaserCommand(energy=energy))
        _render_events(events, messages)
        _animate_combat_events(events, state, messages, screen, clock, lay,
                               grid_snapshot=grid_snap)
        if is_victory(events):
            return "victory"
        if is_fatal(events):
            return "destroyed"

    elif name == "TOR":
        course = torpedo_input(screen, clock, fps=FPS)
        if course is None:
            return "ok"
        grid_snap = _snapshot_grid(state.quadrant_grid)
        events = execute_torpedo(state, TorpedoCommand(course=course))
        _render_events(events, messages)
        _animate_combat_events(events, state, messages, screen, clock, lay,
                               grid_snapshot=grid_snap)
        if is_victory(events):
            return "victory"
        if is_fatal(events):
            return "destroyed"

    elif name == "SHE":
        available = state.energy + state.shields
        level = shield_input(screen, clock, state.shields, available, fps=FPS)
        if level is None:
            return "ok"
        events = execute_shields(state, ShieldsCommand(level=level))
        _render_events(events, messages)

    elif name == "LRS":
        lines = _build_lrs_lines(state)
        info_overlay(screen, clock, "LONG RANGE SENSORS", lines, fps=FPS)

    elif name == "DAM":
        lines = _build_dam_lines(state)
        # Check if repair is available
        repair_offered = (state.docked
                          and any(state.damage[i] < 0 for i in range(8)))
        info_overlay(screen, clock, "DAMAGE CONTROL", lines, fps=FPS)
        if repair_offered:
            if confirm_dialog(screen, clock,
                              "AUTHORIZE REPAIRS?", fps=FPS):
                d3 = min(sum(1 for i in range(8) if state.damage[i] < 0) * 0.1
                         + state.d4, 0.9)
                for i in range(8):
                    if state.damage[i] < 0:
                        state.damage[i] = 0.0
                state.stardate += d3 + 0.1
                messages.append(("REPAIRS COMPLETED.", _C["bright_green"]))
                if _check_time_expired(state, messages):
                    return "destroyed"

    elif name == "COM":
        lines = _build_com_lines(state)
        info_overlay(screen, clock, "LIBRARY-COMPUTER", lines, fps=FPS)

    return "ok"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    pygame.init()
    init_fonts()

    info = pygame.display.Info()
    start_w = min(REF_W, info.current_w - 80)
    start_h = min(REF_H, info.current_h - 80)
    screen = pygame.display.set_mode((start_w, start_h), pygame.RESIZABLE)
    pygame.display.set_caption("SST3 Python Edition")
    clock = pygame.time.Clock()

    init_sprites()

    difficulty = _difficulty_dialog(screen, clock)

    with _suppress_stdout():
        state = init_new_game(difficulty=difficulty)
        enter_quadrant(state, is_start=True)

    lay = Layout(*screen.get_size())

    diff_names = ["DEFAULT", "EASY", "MEDIUM", "HARD"]
    messages = [
        ("SST3 Python Edition",
         _C["bright_cyan"]),
        (f"Difficulty: {diff_names[difficulty]}  |  "
         f"Stardate {state.stardate:.1f}  |  "
         f"Destroy {state.total_klingons} Klingon(s) in "
         f"{state.mission_days} days",
         _C["bright_white"]),
        ("Hotkeys: N=Nav  P=Phaser  T=Torpedo  H=Shields  "
         "L=LRS  D=Damage  C=Computer  R=New Game  Esc=Quit",
         _C["bright_yellow"]),
        ("Mouse: Click Klingon=Torpedo  Shift+Click=Phaser  "
         "Click Empty=Navigate  Right-Click=Info",
         _C["white"]),
    ]

    # Handle fire_first on initial entry (shouldn't fire, but be safe)
    if state.fire_first:
        fire_evts = [KlingonsAmbush()] + execute_klingons_fire(state)
        state.fire_first = False
        _render_events(fire_evts, messages)

    game_over = False
    running = True

    while running:
        mx, my = pygame.mouse.get_pos()
        hover_btn = lay.hit_button(mx, my) if not game_over else -1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(
                    (event.w, event.h), pygame.RESIZABLE)
                clear_sprite_cache()
                lay = Layout(event.w, event.h)

            elif event.type == pygame.KEYDOWN and not game_over:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    difficulty = _difficulty_dialog(screen, clock)
                    with _suppress_stdout():
                        state = init_new_game(difficulty=difficulty)
                        enter_quadrant(state, is_start=True)
                    lay = Layout(*screen.get_size())
                    messages.append((f"--- New game (difficulty {difficulty}) ---",
                                     _C["bright_green"]))
                    game_over = False
                    if state.fire_first:
                        fire_evts = [KlingonsAmbush()] + execute_klingons_fire(state)
                        state.fire_first = False
                        _render_events(fire_evts, messages)
                else:
                    # Check hotkeys
                    for i, (_name, hk) in enumerate(_CMD_BUTTONS):
                        if event.key == hk:
                            result = _do_command(i, state, messages,
                                                 screen, clock, lay)
                            if result in ("victory", "destroyed"):
                                game_over = True
                            break

            elif event.type == pygame.KEYDOWN and game_over:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    difficulty = _difficulty_dialog(screen, clock)
                    with _suppress_stdout():
                        state = init_new_game(difficulty=difficulty)
                        enter_quadrant(state, is_start=True)
                    lay = Layout(*screen.get_size())
                    messages.append((f"--- New game (difficulty {difficulty}) ---",
                                     _C["bright_green"]))
                    game_over = False

            elif (event.type == pygame.MOUSEBUTTONDOWN
                  and not game_over):
                if event.button == 1:
                    # Left click: button bar or grid cell
                    btn = lay.hit_button(*event.pos)
                    if btn >= 0:
                        result = _do_command(btn, state, messages,
                                             screen, clock, lay)
                        if result in ("victory", "destroyed"):
                            game_over = True
                    else:
                        cell = lay.hit_cell(*event.pos)
                        if cell is not None:
                            shift = (pygame.key.get_mods() & pygame.KMOD_SHIFT)
                            result = _handle_grid_click(
                                cell[0], cell[1], state, messages,
                                screen, clock, lay, shift=shift)
                            if result in ("victory", "destroyed"):
                                game_over = True
                elif event.button == 3:
                    # Right click: info on grid cell
                    cell = lay.hit_cell(*event.pos)
                    if cell is not None:
                        _handle_right_click(cell[0], cell[1],
                                            state, messages)

        # --- Draw ---
        screen.fill(COLORS["black"])
        _draw_title_bar(screen, state, lay)
        _draw_grid(screen, state.quadrant_grid, lay)
        _draw_status_panel(screen, state, lay)
        _draw_command_bar(screen, lay, hover_btn)
        _draw_message_log(screen, messages, lay)
        if not game_over:
            # Highlight hovered grid cell
            cell = lay.hit_cell(mx, my)
            if cell is not None:
                hr, hc = cell
                hx = lay.grid_x + (hc - 1) * lay.cell
                hy = lay.grid_y + (hr - 1) * lay.cell
                highlight_rect = pygame.Rect(hx, hy, lay.cell, lay.cell)
                token = state.quadrant_grid.get(hr, hc)
                hkey = _token_key(token)
                hcolor = ENTITY_COLORS.get(hkey) or COLORS["white"]
                # Semi-transparent highlight
                hl_surf = pygame.Surface((lay.cell, lay.cell), pygame.SRCALPHA)
                hl_surf.fill((*hcolor[:3], 25))
                screen.blit(hl_surf, (hx, hy))
                pygame.draw.rect(screen, hcolor, highlight_rect, 2)
            _draw_hover_info(screen, state.quadrant_grid, mx, my, lay, state)

        if game_over:
            # Dim overlay with "GAME OVER" / "VICTORY" text
            overlay = pygame.Surface((lay.win_w, lay.win_h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 80))
            screen.blit(overlay, (0, 0))
            go_font = font(max(20, int(48 * lay.scale)))
            if is_victory([ev for ev in []]):  # check messages for victory
                pass  # fall through to generic
            # Check last messages for victory/defeat
            is_win = any("MISSION IS A SUCCESS" in m[0] for m in messages[-10:])
            text = "VICTORY!" if is_win else "GAME OVER"
            color = _C["bright_green"] if is_win else _C["bright_red"]
            go_txt = go_font.render(text, True, color)
            screen.blit(go_txt, go_txt.get_rect(
                center=(lay.win_w // 2, lay.win_h // 2 - int(30 * lay.scale))))
            sub_font = font(max(12, int(22 * lay.scale)))
            sub = sub_font.render("Press R for new game, Esc to quit",
                                  True, _C["bright_white"])
            screen.blit(sub, sub.get_rect(
                center=(lay.win_w // 2, lay.win_h // 2 + int(20 * lay.scale))))

        advance_tick()
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
