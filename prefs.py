"""
prefs.py  –  SST3 Python Edition
Version 0.3.0

Persistent user preferences stored as JSON.

Equivalent to BASIC lines 15000-16380 (save/load prefs file) and the
preference editor already in display.py (run_prefs_editor).

Preferences are always loaded at startup, and can be saved or deleted
from within the SET command.
"""

import json
from pathlib import Path
from typing import Optional

from config import PREFS_FILENAME
from state import Prefs

PREFS_VERSION = "sst3-prefs-1"


def load_prefs(path: Optional[Path] = None) -> Prefs:
    """
    Load preferences from *path* (default: PREFS_FILENAME in cwd).
    Returns defaults silently if the file is missing or unreadable.
    Prints a warning and returns defaults if the file is corrupt.
    """
    if path is None:
        path = Path(PREFS_FILENAME)

    if not path.exists():
        return Prefs()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("PREF FILE CORRUPT — using defaults")
        return Prefs()

    if data.get("version") != PREFS_VERSION:
        print("PREF FILE VERSION MISMATCH — using defaults")
        return Prefs()

    return Prefs.from_dict(data)


def save_prefs(prefs: Prefs, path: Optional[Path] = None) -> bool:
    """
    Write preferences to *path*.
    Returns True on success, False on IO error.
    """
    if path is None:
        path = Path(PREFS_FILENAME)

    try:
        data = prefs.to_dict()
        data["version"] = PREFS_VERSION
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True
    except OSError as exc:
        print(f"COULD NOT SAVE PREFERENCES: {exc}")
        return False


def delete_prefs(path: Optional[Path] = None) -> None:
    """Delete the prefs file silently."""
    if path is None:
        path = Path(PREFS_FILENAME)
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass
