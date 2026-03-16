"""
gui_input.py  –  SST3 Python Edition GUI
Modal input dialogs for all commands.

Each dialog runs its own mini event loop (blocking the main loop)
and returns a result or None if cancelled.
"""

import pygame
from gui_assets import COLORS, font

# ---------------------------------------------------------------------------
# Generic numeric input dialog
# ---------------------------------------------------------------------------

def numeric_input(screen, clock, prompt, bounds=None, allow_float=True,
                  fps=30):
    """
    Show a modal dialog asking for a number.
    Returns float/int or None if cancelled.
    """
    value = ""
    result = None

    while True:
        w, h = screen.get_size()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(
                    (event.w, event.h), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                elif event.key == pygame.K_RETURN:
                    if value:
                        try:
                            result = float(value) if allow_float else int(value)
                            if bounds:
                                lo, hi = bounds
                                if result < lo or result > hi:
                                    value = ""
                                    continue
                            return result
                        except ValueError:
                            value = ""
                    else:
                        return None
                elif event.key == pygame.K_BACKSPACE:
                    value = value[:-1]
                else:
                    ch = event.unicode
                    if ch and ch in "0123456789.-":
                        value += ch

        # Draw overlay
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        s = min(w / 1800, h / 1000)
        box_w = int(500 * s)
        box_h = int(180 * s)
        bx = (w - box_w) // 2
        by = (h - box_h) // 2

        pygame.draw.rect(screen, COLORS["dialog_bg"],
                         (bx, by, box_w, box_h))
        pygame.draw.rect(screen, COLORS["dialog_border"],
                         (bx, by, box_w, box_h), 2)

        pf = font(max(10, int(18 * s)))
        vf = font(max(12, int(24 * s)))
        hf = font(max(9, int(13 * s)))

        pt = pf.render(prompt, True, COLORS["bright_cyan"])
        screen.blit(pt, (bx + int(20 * s), by + int(20 * s)))

        # Input field
        field_rect = pygame.Rect(bx + int(20 * s), by + int(60 * s),
                                 box_w - int(40 * s), int(40 * s))
        pygame.draw.rect(screen, (10, 10, 20), field_rect)
        pygame.draw.rect(screen, COLORS["bright_cyan"], field_rect, 1)

        display_val = value + "_"
        vt = vf.render(display_val, True, COLORS["bright_white"])
        screen.blit(vt, (field_rect.x + 8, field_rect.y + 6))

        # Hint
        hint = "Enter to confirm, Esc to cancel"
        if bounds:
            hint = f"Range: {bounds[0]}-{bounds[1]}  |  " + hint
        ht = hf.render(hint, True, COLORS["white"])
        screen.blit(ht, (bx + int(20 * s), by + int(110 * s)))

        pygame.display.flip()
        clock.tick(fps)


# ---------------------------------------------------------------------------
# Multi-field dialog (NAV needs course + warp)
# ---------------------------------------------------------------------------

def nav_input(screen, clock, fps=30):
    """
    Two-step dialog: course (1-9), then warp factor (0-8).
    Returns (course, warp) or None if cancelled.
    """
    course = numeric_input(screen, clock,
                           "COURSE (1-9):", bounds=(1, 9), fps=fps)
    if course is None:
        return None
    warp = numeric_input(screen, clock,
                         "WARP FACTOR (0-8):", bounds=(0, 8), fps=fps)
    if warp is None:
        return None
    return (course, warp)


def phaser_input(screen, clock, available_energy, fps=30):
    """
    Ask for phaser energy to fire.
    Returns energy float or None.
    """
    prompt = f"PHASERS LOCKED ON TARGET.  ENERGY ({int(available_energy)} avail):"
    return numeric_input(screen, clock, prompt,
                         bounds=(1, available_energy), fps=fps)


def torpedo_input(screen, clock, fps=30):
    """
    Ask for torpedo course.
    Returns course float or None.
    """
    return numeric_input(screen, clock,
                         "PHOTON TORPEDO COURSE (1-9):", bounds=(1, 9),
                         fps=fps)


def shield_input(screen, clock, current_shields, available, fps=30):
    """
    Ask for new shield energy level.
    Returns level float or None.
    """
    prompt = f"ENERGY TO SHIELDS (now {int(current_shields)}, max {int(available)}):"
    return numeric_input(screen, clock, prompt,
                         bounds=(0, available), fps=fps)


# ---------------------------------------------------------------------------
# Info overlay (LRS, DAM, COM — modal, press Esc/Enter to dismiss)
# ---------------------------------------------------------------------------

def info_overlay(screen, clock, title, lines, fps=30):
    """
    Show a scrollable info panel. Each line is (text, color).
    Blocks until Esc or Enter is pressed.
    """
    scroll = 0

    while True:
        w, h = screen.get_size()
        s = min(w / 1800, h / 1000)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(
                    (event.w, event.h), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN,
                                 pygame.K_SPACE):
                    return
                elif event.key == pygame.K_UP:
                    scroll = max(0, scroll - 1)
                elif event.key == pygame.K_DOWN:
                    scroll += 1
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    return
                elif event.button == 4:  # scroll up
                    scroll = max(0, scroll - 2)
                elif event.button == 5:  # scroll down
                    scroll += 2

        # Draw
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        box_w = int(800 * s)
        line_h = max(16, int(22 * s))
        box_h = min(int(700 * s), (len(lines) + 4) * line_h + int(60 * s))
        bx = (w - box_w) // 2
        by = (h - box_h) // 2

        pygame.draw.rect(screen, COLORS["dialog_bg"],
                         (bx, by, box_w, box_h))
        pygame.draw.rect(screen, COLORS["dialog_border"],
                         (bx, by, box_w, box_h), 2)

        tf = font(max(12, int(22 * s)))
        lf = font(max(10, int(16 * s)))
        hf = font(max(9, int(12 * s)))

        tt = tf.render(title, True, COLORS["bright_cyan"])
        screen.blit(tt, (bx + int(16 * s), by + int(12 * s)))

        # Lines
        y = by + int(48 * s)
        max_visible = (box_h - int(80 * s)) // line_h
        scroll = min(scroll, max(0, len(lines) - max_visible))
        visible = lines[scroll:scroll + max_visible]

        for text, color in visible:
            lt = lf.render(text, True, color)
            screen.blit(lt, (bx + int(16 * s), y))
            y += line_h

        # Hint at bottom
        ht = hf.render("Esc/Enter/Click to close  |  Scroll: arrows/wheel",
                        True, COLORS["white"])
        screen.blit(ht, (bx + int(16 * s), by + box_h - int(24 * s)))

        pygame.display.flip()
        clock.tick(fps)


# ---------------------------------------------------------------------------
# Confirmation dialog (Y/N)
# ---------------------------------------------------------------------------

def confirm_dialog(screen, clock, prompt, fps=30):
    """
    Show a Y/N confirmation dialog.
    Returns True (yes) or False (no/cancel).
    """
    while True:
        w, h = screen.get_size()
        s = min(w / 1800, h / 1000)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(
                    (event.w, event.h), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_y:
                    return True
                if event.key in (pygame.K_n, pygame.K_ESCAPE):
                    return False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                box_w = int(500 * s)
                box_h = int(140 * s)
                bx = (w - box_w) // 2
                by = (h - box_h) // 2
                btn_w = int(80 * s)
                btn_h = int(36 * s)
                btn_y = by + int(85 * s)
                # Yes button
                yes_x = bx + box_w // 2 - btn_w - int(10 * s)
                if yes_x <= mx <= yes_x + btn_w and btn_y <= my <= btn_y + btn_h:
                    return True
                # No button
                no_x = bx + box_w // 2 + int(10 * s)
                if no_x <= mx <= no_x + btn_w and btn_y <= my <= btn_y + btn_h:
                    return False

        # Draw
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        box_w = int(500 * s)
        box_h = int(140 * s)
        bx = (w - box_w) // 2
        by = (h - box_h) // 2

        pygame.draw.rect(screen, COLORS["dialog_bg"],
                         (bx, by, box_w, box_h))
        pygame.draw.rect(screen, COLORS["dialog_border"],
                         (bx, by, box_w, box_h), 2)

        pf = font(max(10, int(18 * s)))
        bf = font(max(10, int(16 * s)))

        pt = pf.render(prompt, True, COLORS["bright_cyan"])
        screen.blit(pt, (bx + int(20 * s), by + int(20 * s)))

        # Buttons
        btn_w = int(80 * s)
        btn_h = int(36 * s)
        btn_y = by + int(85 * s)

        yes_rect = pygame.Rect(bx + box_w // 2 - btn_w - int(10 * s),
                                btn_y, btn_w, btn_h)
        no_rect = pygame.Rect(bx + box_w // 2 + int(10 * s),
                               btn_y, btn_w, btn_h)

        pygame.draw.rect(screen, COLORS["bright_green"], yes_rect)
        pygame.draw.rect(screen, COLORS["bright_white"], yes_rect, 1)
        yt = bf.render("YES (Y)", True, COLORS["black"])
        screen.blit(yt, yt.get_rect(center=yes_rect.center))

        pygame.draw.rect(screen, COLORS["bright_red"], no_rect)
        pygame.draw.rect(screen, COLORS["bright_white"], no_rect, 1)
        nt = bf.render("NO (N)", True, COLORS["black"])
        screen.blit(nt, nt.get_rect(center=no_rect.center))

        hint_f = font(max(9, int(12 * s)))
        ht = hint_f.render("Press Y or N", True, COLORS["white"])
        screen.blit(ht, (bx + int(20 * s), by + int(55 * s)))

        pygame.display.flip()
        clock.tick(fps)
