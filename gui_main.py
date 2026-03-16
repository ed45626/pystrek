"""
gui_main.py  –  SST3 Python Edition GUI
Phase 1: Core window, 8×8 tactical grid with coloured rectangles,
         status panel, and read-only game state display.

Launch:  python gui_main.py
"""

import sys
import os

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
# Layout constants
# ---------------------------------------------------------------------------
WINDOW_W, WINDOW_H = 1024, 768
GRID_SIZE = 8
CELL_PX   = 64                       # pixels per cell
GRID_PX   = CELL_PX * GRID_SIZE      # 512
GRID_X, GRID_Y = 16, 48              # top-left of grid area
PANEL_X   = GRID_X + GRID_PX + 24    # status panel left edge
PANEL_Y   = GRID_Y
CMDBAR_Y  = GRID_Y + GRID_PX + 16    # command bar top
MSGLOG_Y  = CMDBAR_Y + 44            # message log top
MSGLOG_H  = WINDOW_H - MSGLOG_Y - 8

FPS = 30

# Entity rectangle sizes (centred in cell)
_RECT_SIZES = {
    "ship":    (44, 44),
    "klingon": (36, 36),
    "base":    (32, 40),
    "star":    (10, 10),
}

# Entity labels drawn inside rectangles
_ENTITY_LABELS = {
    "ship":    "E",
    "klingon": "K",
    "base":    "B",
    "star":    "*",
}


# ---------------------------------------------------------------------------
# Token key helper
# ---------------------------------------------------------------------------
_TOKEN_MAP = {STAR: "star", KLINGON: "klingon", SHIP: "ship", BASE: "base"}


def _token_key(token: str) -> str:
    return _TOKEN_MAP.get(token, "empty")


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def _draw_grid(surface, grid):
    """Draw the 8×8 tactical grid with entity rectangles."""
    # Background
    bg_rect = pygame.Rect(GRID_X, GRID_Y, GRID_PX, GRID_PX)
    pygame.draw.rect(surface, COLORS["grid_bg"], bg_rect)

    # Grid lines
    for i in range(GRID_SIZE + 1):
        # vertical
        x = GRID_X + i * CELL_PX
        pygame.draw.line(surface, COLORS["grid_line"],
                         (x, GRID_Y), (x, GRID_Y + GRID_PX))
        # horizontal
        y = GRID_Y + i * CELL_PX
        pygame.draw.line(surface, COLORS["grid_line"],
                         (GRID_X, y), (GRID_X + GRID_PX, y))

    # Entities
    label_font = font(18)
    small_font = font(10)

    for row in range(1, 9):
        for col in range(1, 9):
            token = grid.get(row, col)
            key = _token_key(token)
            color = ENTITY_COLORS.get(key)
            if color is None:
                continue

            cx = GRID_X + (col - 1) * CELL_PX + CELL_PX // 2
            cy = GRID_Y + (row - 1) * CELL_PX + CELL_PX // 2

            w, h = _RECT_SIZES.get(key, (30, 30))
            ent_rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)

            if key == "star":
                # Draw stars as small filled circles
                pygame.draw.circle(surface, color, (cx, cy), 5)
            else:
                # Filled rectangle + border
                pygame.draw.rect(surface, color, ent_rect)
                pygame.draw.rect(surface, COLORS["bright_white"],
                                 ent_rect, 1)
                # Label
                lbl = _ENTITY_LABELS.get(key, "?")
                txt = label_font.render(lbl, True, COLORS["black"])
                tr = txt.get_rect(center=(cx, cy))
                surface.blit(txt, tr)

    # Grid border
    pygame.draw.rect(surface, COLORS["bright_white"], bg_rect, 2)

    # Row/col labels
    coord_font = font(12)
    for i in range(GRID_SIZE):
        # column numbers (top)
        txt = coord_font.render(str(i + 1), True, COLORS["white"])
        x = GRID_X + i * CELL_PX + CELL_PX // 2 - txt.get_width() // 2
        surface.blit(txt, (x, GRID_Y - 16))
        # row numbers (left)
        txt = coord_font.render(str(i + 1), True, COLORS["white"])
        y = GRID_Y + i * CELL_PX + CELL_PX // 2 - txt.get_height() // 2
        surface.blit(txt, (GRID_X - 14, y))


def _draw_status_panel(surface, state):
    """Draw the right-side status panel."""
    hdr_font = font(14)
    val_font = font(18)
    lbl_font = font(13)

    # Panel background
    pw = WINDOW_W - PANEL_X - 16
    ph = GRID_PX
    panel_rect = pygame.Rect(PANEL_X, PANEL_Y, pw, ph)
    pygame.draw.rect(surface, COLORS["panel_bg"], panel_rect)
    pygame.draw.rect(surface, COLORS["panel_border"], panel_rect, 1)

    # Title
    title = hdr_font.render("STATUS", True, COLORS["bright_white"])
    surface.blit(title, (PANEL_X + 10, PANEL_Y + 8))

    # Status rows
    rows = _build_status_rows(state)
    y = PANEL_Y + 34
    for label, value, color in rows:
        lt = lbl_font.render(label, True, COLORS["white"])
        surface.blit(lt, (PANEL_X + 10, y))
        vt = val_font.render(value, True, color)
        surface.blit(vt, (PANEL_X + 10, y + 17))
        y += 50
        if y > PANEL_Y + ph - 20:
            break


def _build_status_rows(state):
    """Return list of (label, value_str, colour) for the status panel."""
    rows = []

    # Stardate
    deadline = state.start_stardate + state.mission_days - 7
    sd_color = (STATUS_STYLES["stardate_warn"]
                if state.stardate > deadline
                else COLORS["white"])
    rows.append(("STARDATE", f"{state.stardate:.1f}", sd_color))

    # Condition
    cond = state.condition()
    cc = CONDITION_COLORS.get(cond, COLORS["white"])
    rows.append(("CONDITION", cond, cc))

    # Quadrant
    rows.append(("QUADRANT", f"{state.quad_row},{state.quad_col}",
                 COLORS["green"]))

    # Sector
    rows.append(("SECTOR", f"{state.sec_row},{state.sec_col}",
                 COLORS["green"]))

    # Torpedoes
    tc = (STATUS_STYLES["torpedoes_low"] if state.torpedoes < 4
          else STATUS_STYLES["torpedoes_ok"])
    rows.append(("PHOTON TORPEDOES", str(int(state.torpedoes)), tc))

    # Total energy
    total = int(state.energy + state.shields)
    if total < 400:
        ec = STATUS_STYLES["energy_crit"]
    elif total < 1000:
        ec = STATUS_STYLES["energy_low"]
    else:
        ec = STATUS_STYLES["energy_ok"]
    rows.append(("TOTAL ENERGY", str(total), ec))

    # Shields
    s = int(state.shields)
    if s < 250:
        sc = STATUS_STYLES["shields_crit"]
    elif s < 700:
        sc = STATUS_STYLES["shields_low"]
    else:
        sc = STATUS_STYLES["shields_ok"]
    rows.append(("SHIELDS", str(s), sc))

    # Klingons remaining
    rows.append(("KLINGONS REMAINING",
                 str(int(state.total_klingons)),
                 STATUS_STYLES["klingons"]))

    return rows


def _draw_command_bar(surface):
    """Draw placeholder command buttons (non-interactive in Phase 1)."""
    btn_font = font(14)
    buttons = ["NAV", "PHA", "TOR", "SHE", "LRS", "DAM", "COM"]
    bw, bh = 60, 30
    gap = 8
    x = GRID_X

    # Background strip
    strip = pygame.Rect(0, CMDBAR_Y - 4, WINDOW_W, bh + 8)
    pygame.draw.rect(surface, COLORS["panel_bg"], strip)

    label = btn_font.render("COMMAND:", True, COLORS["white"])
    surface.blit(label, (x, CMDBAR_Y + 5))
    x += label.get_width() + 12

    for name in buttons:
        rect = pygame.Rect(x, CMDBAR_Y, bw, bh)
        pygame.draw.rect(surface, COLORS["button_bg"], rect)
        pygame.draw.rect(surface, COLORS["panel_border"], rect, 1)
        txt = btn_font.render(name, True, COLORS["button_text"])
        tr = txt.get_rect(center=rect.center)
        surface.blit(txt, tr)
        x += bw + gap


def _draw_message_log(surface, messages):
    """Draw the bottom message log area."""
    log_rect = pygame.Rect(0, MSGLOG_Y, WINDOW_W, MSGLOG_H)
    pygame.draw.rect(surface, COLORS["msg_bg"], log_rect)
    pygame.draw.line(surface, COLORS["panel_border"],
                     (0, MSGLOG_Y), (WINDOW_W, MSGLOG_Y))

    msg_font = font(13)
    y = MSGLOG_Y + 4
    # Show last N messages that fit
    line_h = 18
    max_lines = MSGLOG_H // line_h
    visible = messages[-max_lines:]
    for msg, color in visible:
        txt = msg_font.render(msg, True, color)
        surface.blit(txt, (10, y))
        y += line_h


def _draw_title_bar(surface, state):
    """Draw the top title/info bar."""
    bar = pygame.Rect(0, 0, WINDOW_W, GRID_Y - 4)
    pygame.draw.rect(surface, COLORS["panel_bg"], bar)

    title_font = font(16)
    from names import quadrant_name
    qname = quadrant_name(state.quad_row, state.quad_col)
    title = f"SST3  —  {qname}  ({state.quad_row},{state.quad_col})"
    txt = title_font.render(title, True, COLORS["bright_cyan"])
    surface.blit(txt, (GRID_X, 14))

    # Condition indicator in top-right
    cond = state.condition()
    cc = CONDITION_COLORS.get(cond, COLORS["white"])
    cond_txt = title_font.render(cond, True, cc)
    surface.blit(cond_txt, (WINDOW_W - cond_txt.get_width() - 20, 14))


# ---------------------------------------------------------------------------
# Hover tooltip
# ---------------------------------------------------------------------------
def _draw_hover_info(surface, grid, mx, my):
    """If mouse is over a grid cell, draw a small tooltip."""
    # Check if mouse is within the grid
    if not (GRID_X <= mx < GRID_X + GRID_PX and
            GRID_Y <= my < GRID_Y + GRID_PX):
        return

    col = (mx - GRID_X) // CELL_PX + 1
    row = (my - GRID_Y) // CELL_PX + 1
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

    tip_font = font(13)
    txt_surf = tip_font.render(text, True, COLORS["bright_white"])
    tw, th = txt_surf.get_size()
    pad = 4

    # Position tooltip above cursor
    tx = min(mx + 12, WINDOW_W - tw - pad * 2 - 4)
    ty = max(my - th - pad * 2 - 4, 0)

    bg = pygame.Rect(tx, ty, tw + pad * 2, th + pad * 2)
    pygame.draw.rect(surface, (20, 20, 30), bg)
    pygame.draw.rect(surface, COLORS["panel_border"], bg, 1)
    surface.blit(txt_surf, (tx + pad, ty + pad))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    pygame.init()
    init_fonts()

    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption("SST3 Python Edition")
    clock = pygame.time.Clock()

    # Initialise a new game (reuses existing engine, zero modifications)
    state = init_new_game(difficulty=0)
    enter_quadrant(state, is_start=True)

    # Message log
    messages = [
        ("SST3 Python Edition — GUI Phase 1", COLORS["bright_cyan"]),
        (f"Stardate {state.stardate:.1f}  —  "
         f"Destroy {state.total_klingons} Klingon(s) in "
         f"{state.mission_days} days", COLORS["white"]),
        ("Grid display only — no input yet.", COLORS["yellow"]),
    ]

    running = True
    while running:
        mx, my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                # Phase 1: R key refreshes with a new game (for testing)
                elif event.key == pygame.K_r:
                    state = init_new_game(difficulty=0)
                    enter_quadrant(state, is_start=True)
                    messages.append(
                        ("--- New game started ---",
                         COLORS["bright_green"]))

        # --- Draw ---
        screen.fill(COLORS["black"])

        _draw_title_bar(screen, state)
        _draw_grid(screen, state.quadrant_grid)
        _draw_status_panel(screen, state)
        _draw_command_bar(screen)
        _draw_message_log(screen, messages)
        _draw_hover_info(screen, state.quadrant_grid, mx, my)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
