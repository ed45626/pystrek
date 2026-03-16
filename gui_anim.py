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
# Blocking combat animation helpers
# ---------------------------------------------------------------------------
def _anim_loop(screen, clock, lay, state, messages, draw_fn,
               sprite_key, row, col, duration_frames, fps,
               size_mult=1.0):
    """Run a short blocking animation at grid cell (row, col).

    draw_fn(surface, state, messages, lay, hover_btn)
      — redraws the full scene underneath the animation.
    """
    from gui_main import (
        _draw_title_bar, _draw_grid, _draw_status_panel,
        _draw_command_bar, _draw_message_log,
    )

    total_frames_available = 1  # default
    # Probe how many frames exist for this sprite key
    for n in range(10):
        if sprite(sprite_key, 10, 10, frame=n) is None:
            break
        # If frame n is same surface as frame 0 for n > num_real_frames,
        # sprite() wraps via modulo so they'll always succeed.
        # We rely on _SPRITE_FILES frame counts.
    from gui_assets import _SPRITE_FILES
    total_frames_available = len(_SPRITE_FILES.get(sprite_key, [1]))

    frames_per_sprite = max(1, duration_frames // total_frames_available)

    cx, cy = lay.cell_center(row, col)
    base_w, base_h = int(64 * lay.scale * size_mult), int(64 * lay.scale * size_mult)

    for i in range(duration_frames):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(
                    (event.w, event.h), pygame.RESIZABLE)

        # Redraw scene underneath
        screen.fill(COLORS["black"])
        _draw_title_bar(screen, state, lay)
        _draw_grid(screen, state.quadrant_grid, lay)
        _draw_status_panel(screen, state, lay)
        _draw_command_bar(screen, lay)
        _draw_message_log(screen, messages, lay)

        # Draw animation sprite on top
        frame_idx = i // frames_per_sprite
        spr = sprite(sprite_key, base_w, base_h, frame=frame_idx)
        if spr is not None:
            rect = spr.get_rect(center=(cx, cy))
            screen.blit(spr, rect)

        pygame.display.flip()
        clock.tick(fps)


def play_explosion(screen, clock, lay, state, messages, row, col, fps=30):
    """Play explosion animation at (row, col) — used for KlingonDestroyed."""
    _anim_loop(screen, clock, lay, state, messages, None,
               "explosion", row, col,
               duration_frames=25, fps=fps, size_mult=1.2)


def play_phasor_hit(screen, clock, lay, state, messages,
                    from_row, from_col, to_row, to_col, fps=30):
    """Animate a phasor beam from Enterprise to target Klingon."""
    from gui_main import (
        _draw_title_bar, _draw_grid, _draw_status_panel,
        _draw_command_bar, _draw_message_log,
    )

    sx, sy = lay.cell_center(from_row, from_col)
    ex, ey = lay.cell_center(to_row, to_col)
    beam_frames = 18
    beam_w = max(4, int(6 * lay.scale))

    for i in range(beam_frames):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

        screen.fill(COLORS["black"])
        _draw_title_bar(screen, state, lay)
        _draw_grid(screen, state.quadrant_grid, lay)
        _draw_status_panel(screen, state, lay)
        _draw_command_bar(screen, lay)
        _draw_message_log(screen, messages, lay)

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
                       sectors, fps=30):
    """Animate a photon torpedo moving through a list of (row, col) sectors."""
    from gui_main import (
        _draw_title_bar, _draw_grid, _draw_status_panel,
        _draw_command_bar, _draw_message_log,
    )
    if not sectors:
        return

    frames_per_sector = 4
    spr_size = int(36 * lay.scale)

    for si, (row, col) in enumerate(sectors):
        cx, cy = lay.cell_center(row, col)
        for f in range(frames_per_sector):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit

            screen.fill(COLORS["black"])
            _draw_title_bar(screen, state, lay)
            _draw_grid(screen, state.quadrant_grid, lay)
            _draw_status_panel(screen, state, lay)
            _draw_command_bar(screen, lay)
            _draw_message_log(screen, messages, lay)

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
                       from_row, from_col, to_row, to_col, fps=30):
    """Animate enemy fire from Klingon to Enterprise (green beam)."""
    from gui_main import (
        _draw_title_bar, _draw_grid, _draw_status_panel,
        _draw_command_bar, _draw_message_log,
    )

    sx, sy = lay.cell_center(from_row, from_col)
    ex, ey = lay.cell_center(to_row, to_col)
    beam_frames = 14
    beam_w = max(3, int(5 * lay.scale))

    for i in range(beam_frames):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

        screen.fill(COLORS["black"])
        _draw_title_bar(screen, state, lay)
        _draw_grid(screen, state.quadrant_grid, lay)
        _draw_status_panel(screen, state, lay)
        _draw_command_bar(screen, lay)
        _draw_message_log(screen, messages, lay)

        progress = min(1.0, (i + 1) / (beam_frames * 0.6))
        bx = int(sx + (ex - sx) * progress)
        by = int(sy + (ey - sy) * progress)
        # Green/red beam for enemy fire
        intensity = 180 + int(75 * (1 - (i / beam_frames)))
        beam_color = (min(255, intensity), 80, 60)
        pygame.draw.line(screen, beam_color, (sx, sy), (bx, by), beam_w)
        core_color = (255, 140, 100)
        core_w = max(2, beam_w // 2)
        pygame.draw.line(screen, core_color, (sx, sy), (bx, by), core_w)

        pygame.display.flip()
        clock.tick(fps)


def play_enterprise_hit(screen, clock, lay, state, messages, fps=30):
    """Flash the screen briefly when Enterprise is hit."""
    from gui_main import (
        _draw_title_bar, _draw_grid, _draw_status_panel,
        _draw_command_bar, _draw_message_log,
    )

    for i in range(6):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

        screen.fill(COLORS["black"])
        _draw_title_bar(screen, state, lay)
        _draw_grid(screen, state.quadrant_grid, lay)
        _draw_status_panel(screen, state, lay)
        _draw_command_bar(screen, lay)
        _draw_message_log(screen, messages, lay)

        # Red flash overlay on odd frames
        if i % 2 == 0:
            overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            overlay.fill((255, 40, 40, 50))
            screen.blit(overlay, (0, 0))

        pygame.display.flip()
        clock.tick(fps)
