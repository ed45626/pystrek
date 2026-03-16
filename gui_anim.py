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


def rotate_ship_to(screen, clock, lay, state, messages, target_row, target_col,
                   fps=30, grid_override=None):
    """Blocking animation: smoothly rotate the Enterprise to face (target_row,
    target_col) before firing. Modifies gui_main._ship_current_angle."""
    import math
    from gui_main import (
        _ship_current_angle, _ship_target_angle,
        _angle_diff, _ROTATION_SPEED,
    )
    import gui_main as _gm

    ship_r, ship_c = state.sec_row, state.sec_col
    dx = target_col - ship_c
    dy = ship_r - target_row
    desired = math.degrees(math.atan2(dy, dx))

    # Override the target angle
    _gm._ship_target_angle = desired

    # Spin until we reach it (max 90 frames = 3s safety)
    for _ in range(90):
        diff = _angle_diff(_gm._ship_current_angle, desired)
        if abs(diff) < _ROTATION_SPEED + 1:
            _gm._ship_current_angle = desired % 360
            break
        _gm._ship_current_angle += _ROTATION_SPEED if diff > 0 else -_ROTATION_SPEED
        _gm._ship_current_angle %= 360
        _pump_events()
        _redraw_scene(screen, state, messages, lay, grid_override)
        pygame.display.flip()
        clock.tick(fps)


def play_ship_move(screen, clock, lay, state, messages,
                   from_row, from_col, to_row, to_col, fps=30):
    """Animate the Enterprise sliding smoothly from one sector cell to another.
    The actual state has already been updated; we draw the ship at interpolated
    pixel positions overlaid on the grid."""
    import math
    from gui_main import (
        _draw_title_bar, _draw_grid, _draw_status_panel,
        _draw_command_bar, _draw_message_log,
        _ship_current_angle,
    )
    import gui_main as _gm

    # Point ship in movement direction
    dx = to_col - from_col
    dy = from_row - to_row
    if dx != 0 or dy != 0:
        move_angle = math.degrees(math.atan2(dy, dx))
        _gm._ship_current_angle = move_angle % 360
        _gm._ship_target_angle = move_angle % 360

    sx, sy = lay.cell_center(from_row, from_col)
    ex, ey = lay.cell_center(to_row, to_col)
    move_frames = 10

    for i in range(move_frames):
        _pump_events()
        t = (i + 1) / move_frames
        # Ease-in-out
        t = t * t * (3 - 2 * t)
        px = int(sx + (ex - sx) * t)
        py = int(sy + (ey - sy) * t)

        # Redraw scene (ship is already at to_row,to_col in state,
        # so we draw grid but override the ship position visually)
        screen.fill(COLORS["black"])
        _draw_title_bar(screen, state, lay)
        # Draw grid without the ship (we'll draw it at interpolated pos)
        _draw_grid(screen, state.quadrant_grid, lay, hide_ship=True)
        _draw_status_panel(screen, state, lay)
        _draw_command_bar(screen, lay)
        _draw_message_log(screen, messages, lay)

        # Draw ship at interpolated position
        ent_rect = lay.entity_rect("ship", px, py)
        spr = sprite("ship", ent_rect.width, ent_rect.height,
                      angle=_gm._ship_current_angle)
        if spr is not None:
            spr_rect = spr.get_rect(center=(px, py))
            screen.blit(spr, spr_rect)
        else:
            pygame.draw.rect(screen, COLORS["bright_cyan"], ent_rect)

        pygame.display.flip()
        clock.tick(fps)


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


def _draw_beam(screen, sx, sy, bx, by, outer_color, mid_color, core_color,
               beam_w, alpha=255):
    """Draw a 3-layer beam: outer glow, mid beam, bright core."""
    if alpha < 255:
        # Use a temporary surface for transparency
        w, h = screen.get_size()
        tmp = pygame.Surface((w, h), pygame.SRCALPHA)
        glow_w = beam_w * 3
        pygame.draw.line(tmp, (*outer_color[:3], min(alpha, 40)),
                         (sx, sy), (bx, by), glow_w)
        pygame.draw.line(tmp, (*mid_color[:3], min(alpha, 180)),
                         (sx, sy), (bx, by), beam_w)
        core_w = max(2, beam_w // 2)
        pygame.draw.line(tmp, (*core_color[:3], alpha),
                         (sx, sy), (bx, by), core_w)
        screen.blit(tmp, (0, 0))
    else:
        # Outer glow
        glow_w = beam_w * 3
        glow_surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        pygame.draw.line(glow_surf, (*outer_color[:3], 40),
                         (sx, sy), (bx, by), glow_w)
        screen.blit(glow_surf, (0, 0))
        # Mid beam
        pygame.draw.line(screen, mid_color, (sx, sy), (bx, by), beam_w)
        # Bright core
        core_w = max(2, beam_w // 2)
        pygame.draw.line(screen, core_color, (sx, sy), (bx, by), core_w)


def play_phasor_hit(screen, clock, lay, state, messages,
                    from_row, from_col, to_row, to_col, fps=30,
                    grid_override=None):
    """Animate a phasor beam from Enterprise to target Klingon.
    Blue beam with glow — extends to target then fades out."""
    sx, sy = lay.cell_center(from_row, from_col)
    ex, ey = lay.cell_center(to_row, to_col)
    extend_frames = 10   # beam extends to target
    hold_frames = 4      # beam holds at full
    fade_frames = 6      # beam fades out
    total = extend_frames + hold_frames + fade_frames
    beam_w = max(4, int(7 * lay.scale))

    for i in range(total):
        _pump_events()
        _redraw_scene(screen, state, messages, lay, grid_override)

        if i < extend_frames:
            # Extend phase
            progress = (i + 1) / extend_frames
            bx = int(sx + (ex - sx) * progress)
            by = int(sy + (ey - sy) * progress)
            alpha = 255
        elif i < extend_frames + hold_frames:
            # Hold at full
            bx, by = ex, ey
            alpha = 255
        else:
            # Fade out
            fade_i = i - extend_frames - hold_frames
            bx, by = ex, ey
            alpha = max(0, 255 - int(255 * fade_i / fade_frames))

        # Blue beam colors
        _draw_beam(screen, sx, sy, bx, by,
                   outer_color=(60, 100, 255),    # blue glow
                   mid_color=(80, 140, 255),       # mid blue
                   core_color=(180, 220, 255),     # bright white-blue core
                   beam_w=beam_w, alpha=alpha)

        # Phasor sprite at beam tip
        if alpha > 100:
            spr_size = int(40 * lay.scale)
            frame_idx = i // (total // 4 + 1)
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
    """Animate enemy fire from Klingon to Enterprise (red/orange beam with glow)."""
    sx, sy = lay.cell_center(from_row, from_col)
    ex, ey = lay.cell_center(to_row, to_col)
    extend_frames = 8
    hold_frames = 3
    fade_frames = 4
    total = extend_frames + hold_frames + fade_frames
    beam_w = max(3, int(6 * lay.scale))

    for i in range(total):
        _pump_events()
        _redraw_scene(screen, state, messages, lay, grid_override)

        if i < extend_frames:
            progress = (i + 1) / extend_frames
            bx = int(sx + (ex - sx) * progress)
            by = int(sy + (ey - sy) * progress)
            alpha = 255
        elif i < extend_frames + hold_frames:
            bx, by = ex, ey
            alpha = 255
        else:
            fade_i = i - extend_frames - hold_frames
            bx, by = ex, ey
            alpha = max(0, 255 - int(255 * fade_i / fade_frames))

        # Red/orange beam colors
        _draw_beam(screen, sx, sy, bx, by,
                   outer_color=(255, 80, 40),      # red glow
                   mid_color=(255, 120, 60),        # orange mid
                   core_color=(255, 200, 140),      # bright yellow-white core
                   beam_w=beam_w, alpha=alpha)

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
