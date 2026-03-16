"""
gui_assets.py  –  SST3 Python Edition GUI
Asset management — colours, fonts, and sprite loading/caching.
"""

import os
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


# ---------------------------------------------------------------------------
# Sprite loading and caching
# ---------------------------------------------------------------------------
_ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "assets", "sprites")

# Maps entity key → list of frame filenames (for animation in Phase 5)
_SPRITE_FILES = {
    "ship":      ["enterprise_1.png", "enterprise_2.png", "enterprise_3.png"],
    "klingon":   ["klingon_1.png", "klingon_2.png", "klingon_3.png"],
    "base":      ["starbase_1.png", "starbase_2.png"],
    "star":      ["star_2.png", "star_1.png", "star_3.png"],
    "explosion": ["explosion_1.png", "explosion_2.png", "explosion_3.png",
                  "explosion_4.png", "explosion_5.png"],
    "phasor":    ["phasor_1.png", "phasor_2.png", "phasor_3.png",
                  "phasor_4.png"],
    "photon":    ["photon_1.png", "photon_2.png", "photon_3.png",
                  "photon_4.png"],
}


class SpriteCache:
    """Load sprites once, scale and cache per target size."""

    def __init__(self):
        # key → list[Surface]  (original full-size frames)
        self._originals: dict[str, list[pygame.Surface]] = {}
        # (key, w, h, frame_index) → Surface
        self._scaled: dict[tuple, pygame.Surface] = {}
        self._load_all()

    def _load_all(self):
        for key, filenames in _SPRITE_FILES.items():
            frames = []
            for fn in filenames:
                path = os.path.join(_ASSET_DIR, fn)
                if os.path.exists(path):
                    surf = pygame.image.load(path).convert_alpha()
                    frames.append(surf)
            if frames:
                self._originals[key] = frames

    def get(self, key: str, width: int, height: int,
            frame: int = 0) -> pygame.Surface | None:
        """Return a sprite scaled to (width, height), or None if missing."""
        frames = self._originals.get(key)
        if not frames:
            return None
        idx = frame % len(frames)
        cache_key = (key, width, height, idx)
        if cache_key not in self._scaled:
            self._scaled[cache_key] = pygame.transform.smoothscale(
                frames[idx], (width, height))
        return self._scaled[cache_key]

    def clear_cache(self):
        """Drop scaled cache (call on window resize)."""
        self._scaled.clear()


# Module-level singleton
_sprites: SpriteCache | None = None


def init_sprites():
    """Call once after pygame.init() and display mode set."""
    global _sprites
    _sprites = SpriteCache()


def sprite(key: str, width: int, height: int,
           frame: int = 0) -> pygame.Surface | None:
    """Get a cached, scaled sprite. Returns None if sprites not loaded."""
    if _sprites is None:
        return None
    return _sprites.get(key, width, height, frame)


def clear_sprite_cache():
    """Call on window resize to flush scaled sprites."""
    if _sprites is not None:
        _sprites.clear_cache()
