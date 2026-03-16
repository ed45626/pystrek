"""
gui_assets.py  –  SST3 Python Edition GUI
Phase 1: Asset management — colours, fonts, and future sprite loading.

No external asset files are needed for Phase 1 (coloured rectangles only).
"""

import pygame

# ---------------------------------------------------------------------------
# Colour palette  (matches TUI ANSI styles from display.py — brightened)
# ---------------------------------------------------------------------------
COLORS = {
    "black":        (0,   0,   0),
    "white":        (220, 220, 220),
    "bright_white": (255, 255, 255),
    "red":          (220, 60,  60),
    "bright_red":   (255, 100, 100),
    "green":        (80,  220, 80),
    "bright_green": (130, 255, 130),
    "cyan":         (80,  220, 220),
    "bright_cyan":  (130, 255, 255),
    "yellow":       (220, 220, 60),
    "bright_yellow":(255, 255, 120),
    "magenta":      (200, 80,  200),
    "bright_magenta":(255, 130, 255),
    "grid_line":    (50,  80,  50),
    "grid_bg":      (8,   14,  8),
    "panel_bg":     (18,  18,  30),
    "panel_border": (70,  70,  110),
    "button_bg":    (45,  45,  70),
    "button_hover": (70,  70,  110),
    "button_text":  (220, 220, 220),
    "msg_bg":       (12,  12,  18),
    "dialog_bg":    (25,  25,  45),
    "dialog_border":(100, 100, 160),
    "highlight":    (80,  80,  140),
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
    "torpedoes_ok":  COLORS["bright_cyan"],
    "energy_crit":   COLORS["bright_red"],
    "energy_low":    COLORS["bright_yellow"],
    "energy_ok":     COLORS["bright_green"],
    "shields_crit":  COLORS["bright_red"],
    "shields_low":   COLORS["bright_yellow"],
    "shields_ok":    COLORS["bright_green"],
    "klingons":      COLORS["bright_yellow"],
}


# ---------------------------------------------------------------------------
# Font cache  (bold=True for all fonts)
# ---------------------------------------------------------------------------
class FontCache:
    """Lazy-loading cache for pygame fonts at various sizes."""

    def __init__(self, font_name=None):
        self._name = font_name  # None = pygame default monospace
        self._cache: dict[int, pygame.font.Font] = {}

    def get(self, size: int) -> pygame.font.Font:
        if size not in self._cache:
            self._cache[size] = pygame.font.SysFont(
                self._name or "monospace", size, bold=True
            )
        return self._cache[size]


# Module-level singleton — initialised after pygame.init()
_fonts: FontCache | None = None


def init_fonts(font_name=None):
    """Call once after pygame.init()."""
    global _fonts
    _fonts = FontCache(font_name)


def font(size: int = 16) -> pygame.font.Font:
    """Get a cached bold font at the given pixel size."""
    if _fonts is None:
        init_fonts()
    return _fonts.get(size)
