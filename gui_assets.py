"""
gui_assets.py  –  SST3 Python Edition GUI
Phase 1: Asset management — colours, fonts, and future sprite loading.

No external asset files are needed for Phase 1 (coloured rectangles only).
"""

import pygame

# ---------------------------------------------------------------------------
# Colour palette  (matches TUI ANSI styles from display.py)
# ---------------------------------------------------------------------------
COLORS = {
    "black":        (0,   0,   0),
    "white":        (200, 200, 200),
    "bright_white": (255, 255, 255),
    "red":          (200, 50,  50),
    "bright_red":   (255, 80,  80),
    "green":        (50,  200, 50),
    "bright_green": (100, 255, 100),
    "cyan":         (50,  200, 200),
    "bright_cyan":  (100, 255, 255),
    "yellow":       (200, 200, 50),
    "bright_yellow":(255, 255, 100),
    "magenta":      (180, 50,  180),
    "bright_magenta":(255, 100, 255),
    "grid_line":    (40,  60,  40),
    "grid_bg":      (8,   12,  8),
    "panel_bg":     (15,  15,  25),
    "panel_border": (50,  50,  80),
    "button_bg":    (40,  40,  60),
    "button_hover": (60,  60,  90),
    "button_text":  (200, 200, 200),
    "msg_bg":       (10,  10,  15),
}

# Map entity token_keys to rectangle colours
ENTITY_COLORS = {
    "ship":    COLORS["bright_cyan"],
    "klingon": COLORS["bright_red"],
    "base":    COLORS["bright_magenta"],
    "star":    COLORS["bright_yellow"],
    "empty":   None,   # not drawn
}

# Map condition strings to colours
CONDITION_COLORS = {
    "DOCKED": COLORS["bright_green"],
    "*RED*":  COLORS["bright_red"],
    "YELLOW": COLORS["bright_yellow"],
    "GREEN":  COLORS["bright_green"],
}

# Status panel value colouring thresholds (mirrors display.py logic)
STATUS_STYLES = {
    "stardate_warn": COLORS["bright_magenta"],
    "torpedoes_low": COLORS["bright_magenta"],
    "torpedoes_ok":  COLORS["cyan"],
    "energy_crit":   COLORS["bright_red"],
    "energy_low":    COLORS["bright_yellow"],
    "energy_ok":     COLORS["green"],
    "shields_crit":  COLORS["bright_red"],
    "shields_low":   COLORS["bright_yellow"],
    "shields_ok":    COLORS["green"],
    "klingons":      COLORS["bright_yellow"],
}


# ---------------------------------------------------------------------------
# Font cache
# ---------------------------------------------------------------------------
class FontCache:
    """Lazy-loading cache for pygame fonts at various sizes."""

    def __init__(self, font_name=None):
        self._name = font_name  # None = pygame default monospace
        self._cache: dict[int, pygame.font.Font] = {}

    def get(self, size: int) -> pygame.font.Font:
        if size not in self._cache:
            self._cache[size] = pygame.font.SysFont(
                self._name or "monospace", size
            )
        return self._cache[size]


# Module-level singleton — initialised after pygame.init()
_fonts: FontCache | None = None


def init_fonts(font_name=None):
    """Call once after pygame.init()."""
    global _fonts
    _fonts = FontCache(font_name)


def font(size: int = 16) -> pygame.font.Font:
    """Get a cached font at the given pixel size."""
    if _fonts is None:
        init_fonts()
    return _fonts.get(size)
