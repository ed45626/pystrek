"""
gui_anim.py  –  SST3 Python Edition GUI
Phase 5: Animation system — combat effects and idle sprite cycling.
"""

import pygame
from gui_assets import COLORS, sprite, font


# ---------------------------------------------------------------------------
# Global tick counter for idle animations (incremented each frame)
# ---------------------------------------------------------------------------
_tick = 0


def advance_tick():
    """Call once per main-loop frame."""
    global _tick
    _tick += 1


def idle_frame(key, cycle_speed=20):
    """Return the current animation frame index for idle cycling.

    cycle_speed: number of game ticks per animation frame (lower = faster).
    """
    return _tick // cycle_speed


# ---------------------------------------------------------------------------
# Scene redraw helper (used by all animation functions)
# ---------------------------------------------------------------------------
def _redraw_scene(screen, state, messages, lay, grid_override=None):
    """Redraw the full game scene. If grid_override is provided, use it
    instead of state.quadrant_grid so entities destroyed during combat
    still appear during animations."""
    from gui_main import (
        _draw_title_bar, _draw_grid, _draw_status_panel,
        _draw_command_bar, _draw_message_log,
    )
    screen.fill(COLORS["black"])
    _draw_title_bar(screen, state, lay)
    grid = grid_override if grid_override is not None else state.quadrant_grid
    _draw_grid(screen, grid, lay)
    _draw_status_panel(screen, state, lay)
    _draw_command_bar(screen, lay)
    _draw_message_log(screen, messages, lay)


# ---------------------------------------------------------------------------
# Blocking combat animation helpers
# ---------------------------------------------------------------------------
def _pump_events():
    """Drain event queue, handling quit. Returns False if quit requested."""
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            raise SystemExit
    return True


def play_explosion(screen, clock, lay, state, messages, row, col, fps=30,
                   grid_override=None):
    """Play explosion animation at (row, col) — used for KlingonDestroyed."""
    from gui_assets import _SPRITE_FILES
    total_frames = len(_SPRITE_FILES.get("explosion", [1]))
    duration_frames = 25
    frames_per_sprite = max(1, duration_frames // total_frames)

    cx, cy = lay.cell_center(row, col)
    base_size = int(64 * lay.scale * 1.2)

    for i in range(duration_frames):
        _pump_events()
        _redraw_scene(screen, state, messages, lay, grid_override)

        frame_idx = i // frames_per_sprite
        spr = sprite("explosion", base_size, base_size, frame=frame_idx)
        if spr is not None:
            rect = spr.get_rect(center=(cx, cy))
            screen.blit(spr, rect)

        pygame.display.flip()
        clock.tick(fps)


def play_phasor_hit(screen, clock, lay, state, messages,
                    from_row, from_col, to_row, to_col, fps=30,
                    grid_override=None):
    """Animate a phasor beam from Enterprise to target Klingon."""
    sx, sy = lay.cell_center(from_row, from_col)
    ex, ey = lay.cell_center(to_row, to_col)
    beam_frames = 18
    beam_w = max(4, int(6 * lay.scale))

    for i in range(beam_frames):
        _pump_events()
        _redraw_scene(screen, state, messages, lay, grid_override)

        # Draw phasor beam — grows from source to target
        progress = min(1.0, (i + 1) / (beam_frames * 0.6))
        bx = int(sx + (ex - sx) * progress)
        by = int(sy + (ey - sy) * progress)
        # Beam color pulses
        intensity = 180 + int(75 * (1 - (i / beam_frames)))
        beam_color = (100, 150, min(255, intensity))
        pygame.draw.line(screen, beam_color, (sx, sy), (bx, by), beam_w)
        # Bright core
        core_w = max(2, beam_w // 2)
        pygame.draw.line(screen, (180, 220, 255), (sx, sy), (bx, by), core_w)

        # Phasor sprite at beam tip
        spr_size = int(40 * lay.scale)
        frame_idx = i // (beam_frames // 4 + 1)
        spr = sprite("phasor", spr_size, spr_size, frame=frame_idx)
        if spr is not None:
            rect = spr.get_rect(center=(bx, by))
            screen.blit(spr, rect)

        pygame.display.flip()
        clock.tick(fps)


def play_torpedo_track(screen, clock, lay, state, messages,
                       sectors, fps=30, grid_override=None):
    """Animate a photon torpedo moving through a list of (row, col) sectors."""
    if not sectors:
        return

    frames_per_sector = 4
    spr_size = int(36 * lay.scale)

    for si, (row, col) in enumerate(sectors):
        cx, cy = lay.cell_center(row, col)
        for f in range(frames_per_sector):
            _pump_events()
            _redraw_scene(screen, state, messages, lay, grid_override)

            # Draw torpedo sprite
            frame_idx = (si * frames_per_sector + f) // 3
            spr = sprite("photon", spr_size, spr_size, frame=frame_idx)
            if spr is not None:
                rect = spr.get_rect(center=(cx, cy))
                screen.blit(spr, rect)
            else:
                # Fallback red circle
                pygame.draw.circle(screen, COLORS["bright_red"],
                                   (cx, cy), max(4, int(8 * lay.scale)))

            pygame.display.flip()
            clock.tick(fps)


def play_klingon_fires(screen, clock, lay, state, messages,
                       from_row, from_col, to_row, to_col, fps=30,
                       grid_override=None):
    """Animate enemy fire from Klingon to Enterprise (green beam)."""
    sx, sy = lay.cell_center(from_row, from_col)
    ex, ey = lay.cell_center(to_row, to_col)
    beam_frames = 14
    beam_w = max(3, int(5 * lay.scale))

    for i in range(beam_frames):
        _pump_events()
        _redraw_scene(screen, state, messages, lay, grid_override)

        progress = min(1.0, (i + 1) / (beam_frames * 0.6))
        bx = int(sx + (ex - sx) * progress)
        by = int(sy + (ey - sy) * progress)
        # Red/orange beam for enemy fire
        intensity = 180 + int(75 * (1 - (i / beam_frames)))
        beam_color = (min(255, intensity), 80, 60)
        pygame.draw.line(screen, beam_color, (sx, sy), (bx, by), beam_w)
        core_color = (255, 140, 100)
        core_w = max(2, beam_w // 2)
        pygame.draw.line(screen, core_color, (sx, sy), (bx, by), core_w)

        pygame.display.flip()
        clock.tick(fps)


def play_enterprise_hit(screen, clock, lay, state, messages, fps=30,
                        grid_override=None):
    """Flash the screen briefly when Enterprise is hit."""
    for i in range(6):
        _pump_events()
        _redraw_scene(screen, state, messages, lay, grid_override)

        # Red flash overlay on odd frames
        if i % 2 == 0:
            overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            overlay.fill((255, 40, 40, 50))
            screen.blit(overlay, (0, 0))

        pygame.display.flip()
        clock.tick(fps)
