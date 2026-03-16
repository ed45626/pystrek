"""
shields.py  –  SST3 Python Edition
Version 0.3.0

Shield energy management — pure game logic, zero I/O.

Public API
----------
execute_shields(state, ShieldsCommand) -> list[Event]
    Validate the requested shield level, redistribute energy, and return
    a list of Event objects describing what happened.

Equivalent BASIC lines: 5530-5660.
"""

from typing import List

from commands import ShieldsCommand
from config import DEV_SHIELDS
from events import (
    Event,
    ShieldControlInoperable,
    ShieldsUnchanged,
    ShieldsSet,
)


def execute_shields(state, command: ShieldsCommand) -> List[Event]:
    """
    Set shields to command.level.  Mutates state in place.
    Returns a complete list[Event].  Never raises, never prints.

    Energy conservation: state.energy + state.shields is always preserved.
    """
    events: List[Event] = []

    # Device check
    if not state.is_device_ok(DEV_SHIELDS):
        events.append(ShieldControlInoperable())
        return events

    x         = command.level
    available = state.energy + state.shields

    # Negative request
    if x < 0:
        events.append(ShieldsUnchanged(reason='negative',
                                        current_shields=state.shields))
        return events

    # No change
    if x == state.shields:
        events.append(ShieldsUnchanged(reason='same',
                                        current_shields=state.shields))
        return events

    # Exceeds available energy
    if x > available:
        events.append(ShieldsUnchanged(reason='overspend',
                                        current_shields=state.shields))
        return events

    # Apply change
    shields_before = state.shields
    energy_before  = state.energy
    state.energy   = available - x
    state.shields  = x

    events.append(ShieldsSet(
        shields_before=shields_before,
        shields_after=state.shields,
        energy_before=energy_before,
        energy_after=state.energy,
    ))
    return events
