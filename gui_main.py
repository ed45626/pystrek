"""
gui_main.py  –  SST3 Python Edition GUI
Phase 1: Core window, 8×8 tactical grid with coloured rectangles,
         status panel, read-only game state display, difficulty picker.

Window is resizable.  All coordinates are computed from a scale factor
so the layout adapts to any resolution.

Launch:  python gui_main.py
"""

import sys
import os
import io
import contextlib

# Ensure the pystrek package directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
from galaxy import init_new_game, enter_quadrant
from quadrant import EMPTY, STAR, KLINGON, SHIP, BASE
from gui_assets import (
    COLORS, ENTITY_COLORS, CONDITION_COLORS, STATUS_STYLES,
    init_fonts, font,
)

# ---------------------------------------------------------------------------
# Reference layout (designed at 1800×1000, scales from there)
# ---------------------------------------------------------------------------
REF_W, REF_H = 1800, 1000
GRID_SIZE = 8
FPS = 30

# Reference coordinates (at 1800×1000)
_REF_CELL   = 80           # pixels per cell at reference size
_REF_GRID   = _REF_CELL * GRID_SIZE   # 640
_REF_GRID_X = 24
_REF_GRID_Y = 60
_REF_PANEL_X = _REF_GRID_X + _REF_GRID + 30
_REF_PANEL_Y = _REF_GRID_Y
_REF_CMDBAR_Y = _REF_GRID_Y + _REF_GRID + 20
_REF_MSGLOG_Y = _REF_CMDBAR_Y + 50

# Entity rectangle sizes at reference (centred in cell)
_REF_RECT_SIZES = {
    "ship":    (56, 56),
    "klingon": (46, 46),
    "base":    (40, 50),
    "star":    (12, 12),
}

# Entity labels drawn inside rectangles
_ENTITY_LABELS = {
    "ship":    "E",
    "klingon": "K",
    "base":    "B",
    "star":    "*",
}

# Token key helper
_TOKEN_MAP = {STAR: "star", KLINGON: "klingon", SHIP: "ship", BASE: "base"}


def _token_key(token: str) -> str:
    return _TOKEN_MAP.get(token, "empty")


# ---------------------------------------------------------------------------
# Suppress TUI stdout from galaxy.py / enter_quadrant
# ---------------------------------------------------------------------------
@contextlib.contextmanager
def _suppress_stdout():
    """Temporarily redirect stdout to discard TUI print calls."""
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        yield
    finally:
        sys.stdout = old


# ---------------------------------------------------------------------------
# Scaled layout — recomputed whenever the window is resized
# ---------------------------------------------------------------------------
class Layout:
    """All pixel coordinates / sizes, computed from current window size."""

    def __init__(self, w, h):
        self.win_w = w
        self.win_h = h
        sx = w / REF_W
        sy = h / REF_H
        self.scale = min(sx, sy)
        s = self.scale

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

        # Font sizes (scaled)
        self.font_title  = max(10, int(20 * s))
        self.font_label  = max(9,  int(16 * s))
        self.font_value  = max(10, int(22 * s))
        self.font_entity = max(10, int(22 * s))
        self.font_coord  = max(8,  int(14 * s))
        self.font_btn    = max(9,  int(16 * s))
        self.font_msg    = max(9,  int(15 * s))
        self.font_tip    = max(9,  int(15 * s))

    def cell_center(self, row, col):
        """Pixel center of grid cell (1-indexed row/col)."""
        cx = self.grid_x + (col - 1) * self.cell + self.cell // 2
        cy = self.grid_y + (row - 1) * self.cell + self.cell // 2
        return cx, cy

    def entity_rect(self, key, cx, cy):
        """Scaled rectangle for an entity centred at (cx, cy)."""
        rw, rh = _REF_RECT_SIZES.get(key, (38, 38))
        w = int(rw * self.scale)
        h = int(rh * self.scale)
        return pygame.Rect(cx - w // 2, cy - h // 2, w, h)

    def star_radius(self):
        return max(3, int(7 * self.scale))


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def _draw_grid(surface, grid, lay):
    """Draw the 8×8 tactical grid with entity rectangles."""
    bg_rect = pygame.Rect(lay.grid_x, lay.grid_y, lay.grid, lay.grid)
    pygame.draw.rect(surface, COLORS["grid_bg"], bg_rect)

    # Grid lines
    for i in range(GRID_SIZE + 1):
        x = lay.grid_x + i * lay.cell
        pygame.draw.line(surface, COLORS["grid_line"],
                         (x, lay.grid_y), (x, lay.grid_y + lay.grid))
        y = lay.grid_y + i * lay.cell
        pygame.draw.line(surface, COLORS["grid_line"],
                         (lay.grid_x, y), (lay.grid_x + lay.grid, y))

    # Entities
    label_font = font(lay.font_entity)

    for row in range(1, 9):
        for col in range(1, 9):
            token = grid.get(row, col)
            key = _token_key(token)
            color = ENTITY_COLORS.get(key)
            if color is None:
                continue

            cx, cy = lay.cell_center(row, col)

            if key == "star":
                pygame.draw.circle(surface, color, (cx, cy),
                                   lay.star_radius())
            else:
                ent_rect = lay.entity_rect(key, cx, cy)
                pygame.draw.rect(surface, color, ent_rect)
                pygame.draw.rect(surface, COLORS["bright_white"],
                                 ent_rect, 1)
                lbl = _ENTITY_LABELS.get(key, "?")
                txt = label_font.render(lbl, True, COLORS["black"])
                tr = txt.get_rect(center=(cx, cy))
                surface.blit(txt, tr)

    # Grid border
    pygame.draw.rect(surface, COLORS["bright_white"], bg_rect, 2)

    # Row/col labels
    coord_font = font(lay.font_coord)
    for i in range(GRID_SIZE):
        # column numbers (top)
        txt = coord_font.render(str(i + 1), True, COLORS["bright_white"])
        x = lay.grid_x + i * lay.cell + lay.cell // 2 - txt.get_width() // 2
        surface.blit(txt, (x, lay.grid_y - txt.get_height() - 2))
        # row numbers (left)
        txt = coord_font.render(str(i + 1), True, COLORS["bright_white"])
        y = lay.grid_y + i * lay.cell + lay.cell // 2 - txt.get_height() // 2
        surface.blit(txt, (lay.grid_x - txt.get_width() - 4, y))


def _draw_status_panel(surface, state, lay):
    """Draw the right-side status panel."""
    hdr_font = font(lay.font_title)
    val_font = font(lay.font_value)
    lbl_font = font(lay.font_label)

    panel_rect = pygame.Rect(lay.panel_x, lay.panel_y,
                             lay.panel_w, lay.panel_h)
    pygame.draw.rect(surface, COLORS["panel_bg"], panel_rect)
    pygame.draw.rect(surface, COLORS["panel_border"], panel_rect, 1)

    # Title
    title = hdr_font.render("STATUS", True, COLORS["bright_white"])
    surface.blit(title, (lay.panel_x + int(12 * lay.scale),
                         lay.panel_y + int(10 * lay.scale)))

    # Status rows
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
    """Return list of (label, value_str, colour) for the status panel."""
    rows = []

    deadline = state.start_stardate + state.mission_days - 7
    sd_color = (STATUS_STYLES["stardate_warn"]
                if state.stardate > deadline
                else COLORS["bright_white"])
    rows.append(("STARDATE", f"{state.stardate:.1f}", sd_color))

    cond = state.condition()
    cc = CONDITION_COLORS.get(cond, COLORS["bright_white"])
    rows.append(("CONDITION", cond, cc))

    rows.append(("QUADRANT", f"{state.quad_row},{state.quad_col}",
                 COLORS["bright_green"]))
    rows.append(("SECTOR", f"{state.sec_row},{state.sec_col}",
                 COLORS["bright_green"]))

    tc = (STATUS_STYLES["torpedoes_low"] if state.torpedoes < 4
          else STATUS_STYLES["torpedoes_ok"])
    rows.append(("PHOTON TORPEDOES", str(int(state.torpedoes)), tc))

    total = int(state.energy + state.shields)
    if total < 400:
        ec = STATUS_STYLES["energy_crit"]
    elif total < 1000:
        ec = STATUS_STYLES["energy_low"]
    else:
        ec = STATUS_STYLES["energy_ok"]
    rows.append(("TOTAL ENERGY", str(total), ec))

    s = int(state.shields)
    if s < 250:
        sc = STATUS_STYLES["shields_crit"]
    elif s < 700:
        sc = STATUS_STYLES["shields_low"]
    else:
        sc = STATUS_STYLES["shields_ok"]
    rows.append(("SHIELDS", str(s), sc))

    rows.append(("KLINGONS REMAINING",
                 str(int(state.total_klingons)),
                 STATUS_STYLES["klingons"]))

    return rows


def _draw_command_bar(surface, lay):
    """Draw placeholder command buttons (non-interactive in Phase 1)."""
    btn_font = font(lay.font_btn)
    buttons = ["NAV", "PHA", "TOR", "SHE", "LRS", "DAM", "COM"]
    bw = int(70 * lay.scale)
    bh = int(36 * lay.scale)
    gap = int(10 * lay.scale)

    strip = pygame.Rect(0, lay.cmdbar_y - 4, lay.win_w, bh + 8)
    pygame.draw.rect(surface, COLORS["panel_bg"], strip)

    x = lay.grid_x
    label = btn_font.render("COMMAND:", True, COLORS["bright_white"])
    surface.blit(label, (x, lay.cmdbar_y + (bh - label.get_height()) // 2))
    x += label.get_width() + int(14 * lay.scale)

    for name in buttons:
        rect = pygame.Rect(x, lay.cmdbar_y, bw, bh)
        pygame.draw.rect(surface, COLORS["button_bg"], rect)
        pygame.draw.rect(surface, COLORS["panel_border"], rect, 1)
        txt = btn_font.render(name, True, COLORS["button_text"])
        tr = txt.get_rect(center=rect.center)
        surface.blit(txt, tr)
        x += bw + gap


def _draw_message_log(surface, messages, lay):
    """Draw the bottom message log area."""
    log_rect = pygame.Rect(0, lay.msglog_y, lay.win_w, lay.msglog_h)
    pygame.draw.rect(surface, COLORS["msg_bg"], log_rect)
    pygame.draw.line(surface, COLORS["panel_border"],
                     (0, lay.msglog_y), (lay.win_w, lay.msglog_y))

    msg_font = font(lay.font_msg)
    line_h = msg_font.get_linesize() + 2
    y = lay.msglog_y + 4
    max_lines = max(1, lay.msglog_h // line_h)
    visible = messages[-max_lines:]
    for msg, color in visible:
        txt = msg_font.render(msg, True, color)
        surface.blit(txt, (int(12 * lay.scale), y))
        y += line_h


def _draw_title_bar(surface, state, lay):
    """Draw the top title/info bar."""
    bar = pygame.Rect(0, 0, lay.win_w, lay.grid_y - 4)
    pygame.draw.rect(surface, COLORS["panel_bg"], bar)

    title_font = font(lay.font_title)
    from names import quadrant_name
    qname = quadrant_name(state.quad_row, state.quad_col)
    title = f"SST3  \u2014  {qname}  ({state.quad_row},{state.quad_col})"
    txt = title_font.render(title, True, COLORS["bright_cyan"])
    surface.blit(txt, (lay.grid_x, (lay.grid_y - 4) // 2 - txt.get_height() // 2))

    cond = state.condition()
    cc = CONDITION_COLORS.get(cond, COLORS["bright_white"])
    cond_txt = title_font.render(cond, True, cc)
    surface.blit(cond_txt, (lay.win_w - cond_txt.get_width() - 20,
                            (lay.grid_y - 4) // 2 - cond_txt.get_height() // 2))


def _draw_hover_info(surface, grid, mx, my, lay):
    """If mouse is over a grid cell, draw a small tooltip."""
    if not (lay.grid_x <= mx < lay.grid_x + lay.grid and
            lay.grid_y <= my < lay.grid_y + lay.grid):
        return

    col = (mx - lay.grid_x) // lay.cell + 1
    row = (my - lay.grid_y) // lay.cell + 1
    if not (1 <= row <= 8 and 1 <= col <= 8):
        return

    token = grid.get(row, col)
    key = _token_key(token)

    names = {
        "ship": "USS Enterprise",
        "klingon": "Klingon Warship",
        "base": "Starbase",
        "star": "Star",
        "empty": "Empty Space",
    }
    text = f"{names.get(key, '?')}  [{row},{col}]"

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
# Difficulty selection dialog  (blocking — runs its own event loop)
# ---------------------------------------------------------------------------
_DIFFICULTY_LABELS = [
    ("0  DEFAULT",  "Standard game — 3000 energy, normal Klingons"),
    ("1  EASY",     "3000 energy, tougher Klingons, 25% first shot"),
    ("2  MEDIUM",   "4000 energy, strong Klingons, 50% first shot"),
    ("3  HARD",     "5000 energy, very strong Klingons, always fire first"),
]


def _difficulty_dialog(screen, clock):
    """Show a difficulty selection dialog. Returns 0-3."""
    selected = 0

    while True:
        w, h = screen.get_size()
        s = min(w / REF_W, h / REF_H)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(
                    (event.w, event.h), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return selected
                elif event.key == pygame.K_UP:
                    selected = (selected - 1) % 4
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % 4
                elif event.key in (pygame.K_0, pygame.K_KP0):
                    return 0
                elif event.key in (pygame.K_1, pygame.K_KP1):
                    return 1
                elif event.key in (pygame.K_2, pygame.K_KP2):
                    return 2
                elif event.key in (pygame.K_3, pygame.K_KP3):
                    return 3
                elif event.key == pygame.K_ESCAPE:
                    return 0
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check if click is on a difficulty option
                mx, my = event.pos
                box_w = int(700 * s)
                box_h = int(400 * s)
                bx = (w - box_w) // 2
                by = (h - box_h) // 2
                opt_y_start = by + int(90 * s)
                opt_h = int(70 * s)
                for i in range(4):
                    oy = opt_y_start + i * opt_h
                    if bx <= mx <= bx + box_w and oy <= my <= oy + opt_h:
                        return i

        screen.fill(COLORS["black"])

        # Dialog box
        box_w = int(700 * s)
        box_h = int(400 * s)
        bx = (w - box_w) // 2
        by = (h - box_h) // 2
        dialog_rect = pygame.Rect(bx, by, box_w, box_h)
        pygame.draw.rect(screen, COLORS["dialog_bg"], dialog_rect)
        pygame.draw.rect(screen, COLORS["dialog_border"], dialog_rect, 2)

        # Title
        tf = font(max(12, int(24 * s)))
        title = tf.render("SELECT DIFFICULTY", True, COLORS["bright_cyan"])
        screen.blit(title, (bx + (box_w - title.get_width()) // 2,
                            by + int(20 * s)))

        # Subtitle
        sf = font(max(9, int(14 * s)))
        sub = sf.render("Press 0-3 or click, Enter to confirm",
                        True, COLORS["white"])
        screen.blit(sub, (bx + (box_w - sub.get_width()) // 2,
                          by + int(55 * s)))

        # Options
        opt_font = font(max(10, int(20 * s)))
        desc_font = font(max(9, int(14 * s)))
        opt_y = by + int(90 * s)
        opt_h = int(70 * s)

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
            screen.blit(lt, (rect.x + int(14 * s),
                             rect.y + int(8 * s)))
            dt = desc_font.render(desc, True, COLORS["white"])
            screen.blit(dt, (rect.x + int(14 * s),
                             rect.y + int(8 * s) + lt.get_height() + 4))
            opt_y += opt_h

        pygame.display.flip()
        clock.tick(FPS)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    pygame.init()
    init_fonts()

    # Start at 1800×1000 (or fit within display)
    info = pygame.display.Info()
    start_w = min(REF_W, info.current_w - 80)
    start_h = min(REF_H, info.current_h - 80)
    screen = pygame.display.set_mode((start_w, start_h), pygame.RESIZABLE)
    pygame.display.set_caption("SST3 Python Edition")
    clock = pygame.time.Clock()

    # Difficulty dialog
    difficulty = _difficulty_dialog(screen, clock)

    # Initialise game — suppress TUI print output from enter_quadrant
    with _suppress_stdout():
        state = init_new_game(difficulty=difficulty)
        enter_quadrant(state, is_start=True)

    # Build initial layout
    lay = Layout(*screen.get_size())

    # Message log
    diff_names = ["DEFAULT", "EASY", "MEDIUM", "HARD"]
    messages = [
        ("SST3 Python Edition \u2014 GUI Phase 1",
         COLORS["bright_cyan"]),
        (f"Difficulty: {diff_names[difficulty]}  |  "
         f"Stardate {state.stardate:.1f}  |  "
         f"Destroy {state.total_klingons} Klingon(s) in "
         f"{state.mission_days} days",
         COLORS["bright_white"]),
        ("Grid display only \u2014 press R for new game, Esc to quit.",
         COLORS["bright_yellow"]),
    ]

    running = True
    while running:
        mx, my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(
                    (event.w, event.h), pygame.RESIZABLE)
                lay = Layout(event.w, event.h)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    difficulty = _difficulty_dialog(screen, clock)
                    with _suppress_stdout():
                        state = init_new_game(difficulty=difficulty)
                        enter_quadrant(state, is_start=True)
                    messages.append(
                        (f"--- New game (difficulty {difficulty}) ---",
                         COLORS["bright_green"]))

        # --- Draw ---
        screen.fill(COLORS["black"])
        _draw_title_bar(screen, state, lay)
        _draw_grid(screen, state.quadrant_grid, lay)
        _draw_status_panel(screen, state, lay)
        _draw_command_bar(screen, lay)
        _draw_message_log(screen, messages, lay)
        _draw_hover_info(screen, state.quadrant_grid, mx, my, lay)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
