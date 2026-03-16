"""
config.py  –  SST3 Python Edition
Version 0.1.0

All tunable constants and display configuration.
No side effects; safe to import from anywhere.
"""

VERSION = "0.3.0"
SAVE_VERSION = "sst3-py-1"

# ---------------------------------------------------------------------------
# Display mode constants  (DISPLOOK in BASIC)
# ---------------------------------------------------------------------------
DISPLOOK_STOCK = 0   # Standard: dashes, spaces, classic symbols
DISPLOOK_GRID  = 1   # Grid lines with underscore-filled empty sectors
DISPLOOK_DOTS  = 2   # Dot-filled empty sectors
DISPLOOK_DIV1  = 3   # Alternate division borders
DISPLOOK_DIV2  = 4   # Second alternate division borders

# SRS cell symbols keyed by display mode.
# Modes 3 and 4 use STOCK symbols with different border lines.
SYMBOLS = {
    DISPLOOK_STOCK: {
        "empty":   "   ",
        "star":    " * ",
        "klingon": "+K+",
        "ship":    "<*>",
        "base":    ">!<",
    },
    DISPLOOK_GRID: {
        "empty":   "   ",   # spaces → '_' applied at render time
        "star":    " * ",
        "klingon": " K ",
        "ship":    " E ",
        "base":    " B ",
    },
    DISPLOOK_DOTS: {
        "empty":   " . ",
        "star":    " * ",
        "klingon": "+K+",
        "ship":    "<*>",
        "base":    ">!<",
    },
}
SYMBOLS[DISPLOOK_DIV1] = SYMBOLS[DISPLOOK_STOCK].copy()
SYMBOLS[DISPLOOK_DIV2] = SYMBOLS[DISPLOOK_STOCK].copy()

# ---------------------------------------------------------------------------
# Device indices  (0-based, matching the D[] damage array)
# ---------------------------------------------------------------------------
DEV_WARP     = 0
DEV_SRS      = 1
DEV_LRS      = 2
DEV_PHASERS  = 3
DEV_TORPS    = 4
DEV_DAMAGE   = 5
DEV_SHIELDS  = 6
DEV_COMPUTER = 7

DEVICE_NAMES = [
    "Warp engines",
    "Short range sensors",
    "Long range sensors",
    "Phaser control",
    "Photon tubes",
    "Damage control",
    "Shield control",
    "Library-computer",
]

# ---------------------------------------------------------------------------
# Galaxy dimensions
# ---------------------------------------------------------------------------
GALAXY_SIZE          = 8
MAX_KLINGONS_PER_QUAD = 3

# Galaxy value encoding:  value = K*100 + B*10 + stars
def galaxy_encode(k: int, b: int, s: int) -> int:
    return k * 100 + b * 10 + s

def galaxy_decode(val: int) -> tuple:
    """Returns (klingons, bases, stars)."""
    k = val // 100
    b = (val % 100) // 10
    s = val % 10
    return k, b, s

# ---------------------------------------------------------------------------
# Default game settings
# ---------------------------------------------------------------------------
DEFAULT_ENERGY    = 3000.0
DEFAULT_TORPEDOES = 10

# Difficulty presets  (energy, klingon_strength, first_shot_chance)
DIFFICULTY = {
    0: (3000.0, 200.0, 0.0),
    1: (3000.0, 250.0, 0.25),
    2: (4000.0, 300.0, 0.5),
    3: (5000.0, 350.0, 1.0),
}

# ---------------------------------------------------------------------------
# Persistence filenames
# ---------------------------------------------------------------------------
SAVE_FILENAME  = "sst3_save.json"
PREFS_FILENAME = "sst3_prefs.json"
