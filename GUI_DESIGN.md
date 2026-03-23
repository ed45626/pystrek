# SST3 Python Edition — GUI Design Document

## Overview

This document outlines the design for a cross-platform graphical interface for
SST3 Python Edition, using **Pygame** with sprite-based rendering, full mouse
support, and keyboard hotkeys. The existing architecture (Command/Event
separation) makes this a clean drop-in: **zero changes to game logic modules**.

---

## 1. Why Pygame

| Requirement               | Pygame                                    |
|---------------------------|-------------------------------------------|
| Sprite-based rendering    | `pygame.sprite.Sprite` / `Group` built-in |
| Cross-platform packaging  | PyInstaller / cx_Freeze → Win, Mac, Linux |
| Mouse support             | Full click, hover, drag events            |
| Hotkey integration        | `KEYDOWN` events with modifier detection  |
| Dependency weight         | Single pip install, no C++ build chain    |
| Pixel art / retro feel    | Perfect fit for a classic Star Trek game  |
| Sound effects             | `pygame.mixer` built-in                   |
| License                   | LGPL — fine for bundled distribution      |

**Alternatives considered:**
- **Pyglet** — lighter but weaker sprite/group management, smaller community
- **Arcade** — modern but heavier, OpenGL 3.3+ required (excludes some VMs)
- **Tkinter + Canvas** — no sprite system, poor animation support
- **Godot/Unity** — overkill for a turn-based grid game, breaks Python-only stack

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────┐
│                   gui_main.py                       │
│  Pygame event loop, scene manager, hotkey dispatch  │
├────────────┬────────────┬───────────────────────────┤
│ gui_scenes │ gui_hud    │ gui_sprites               │
│ Title      │ StatusPanel│ ShipSprite                 │
│ Setup      │ CommandBar │ KlingonSprite              │
│ Play       │ MessageLog │ StarSprite                 │
│ GameOver   │ MiniMap    │ BaseSprite                 │
│            │            │ TorpedoSprite (animated)   │
│            │            │ PhaserBeam (animated)      │
│            │            │ ExplosionSprite (animated) │
├────────────┴────────────┴───────────────────────────┤
│              gui_assets.py                          │
│  Sprite sheet loader, sound manager, font cache     │
├─────────────────────────────────────────────────────┤
│        Existing game engine (UNCHANGED)             │
│  state.py  config.py  navigation.py  combat.py     │
│  klingons.py  shields.py  galaxy.py  quadrant.py   │
│  commands.py  events.py  saveload.py  names.py     │
└─────────────────────────────────────────────────────┘
```

### Key principle: the GUI is a **new consumer** of the existing Command/Event API

- **Input**: GUI collects player intent → builds `NavCommand`, `PhaserCommand`,
  `TorpedoCommand`, `ShieldsCommand` (same frozen dataclasses)
- **Output**: GUI receives `list[Event]` → animates sprites, updates HUD,
  plays sounds (replaces `render_nav_events` / `render_combat_events`)
- **State**: GUI reads `GameState` for display (same as TUI `render_srs`)

No game logic module is modified. `main.py` and `display.py` remain the TUI
frontend. The GUI is a parallel frontend selected at launch.

---

## 3. Window Layout (1024×768 target, scalable)

```
┌──────────────────────────────────────────────────────────┐
│  MENU BAR (File | Game | View | Help)            [≡] [×] │
├──────────────────────────────────────────────────────────┤
│                        │                                  │
│   TACTICAL GRID        │   STATUS PANEL                   │
│   (8×8 sector map)     │   ┌──────────────────────┐      │
│                        │   │ STARDATE    2345.6   │      │
│   512×512 pixels       │   │ CONDITION   *RED*    │      │
│   64×64 per cell       │   │ QUADRANT    3,7      │      │
│                        │   │ SECTOR      4,2      │      │
│   Sprites rendered     │   │ TORPEDOES   8        │      │
│   here with animations │   │ ENERGY      2450     │      │
│                        │   │ SHIELDS     500      │      │
│                        │   │ KLINGONS    11       │      │
│                        │   └──────────────────────┘      │
│                        │                                  │
│                        │   MINIMAP (8×8 galaxy)           │
│                        │   ┌──────────────────────┐      │
│                        │   │  LRS-style overview  │      │
│                        │   │  click to see detail  │      │
│                        │   └──────────────────────┘      │
├──────────────────────────────────────────────────────────┤
│  COMMAND BAR  [NAV] [PHA] [TOR] [SHE] [LRS] [DAM] [COM] │
├──────────────────────────────────────────────────────────┤
│  MESSAGE LOG  (scrollable, last 50 lines)                │
│  > 250 UNIT HIT ON KLINGON AT SECTOR 3,5                 │
│  > *** KLINGON DESTROYED ***                              │
└──────────────────────────────────────────────────────────┘
```

---

## 4. Sprite System

### 4.1 Sprite Sheet

All game entities are 64×64 pixel sprites on a single PNG sprite sheet
(`assets/sprites.png`). Recommended pixel-art style: 16×16 source scaled 4×
for crisp retro look.

| Entity     | Frames | Description                                |
|------------|--------|--------------------------------------------|
| Enterprise | 1-4    | Idle + facing directions (N/E/S/W)         |
| Klingon    | 2      | Idle + damaged                             |
| Starbase   | 1      | Static                                     |
| Star       | 2      | Twinkle animation (subtle)                 |
| Torpedo    | 4      | Projectile animation (rotated per heading) |
| Phaser     | 3      | Beam pulse animation                       |
| Explosion  | 6      | Destruction sequence                       |
| Shield hit | 3      | Shield flash on Enterprise                 |
| Empty      | 1      | Grid cell background / space tile          |

### 4.2 Sprite Classes

```python
class ShipSprite(pygame.sprite.Sprite):
    """The USS Enterprise. Handles movement animation between cells."""
    def __init__(self, sheet, cell_size=64):
        super().__init__()
        self.frames = sheet.load_strip("enterprise", 4)
        self.image = self.frames[0]
        self.rect = self.image.get_rect()
        self._target = None  # (px, py) for smooth movement

    def move_to(self, row, col, animate=True):
        """Animate movement to grid cell (row, col)."""
        ...

    def update(self, dt):
        """Per-frame update: interpolate toward target position."""
        ...
```

Each sprite type follows this pattern. The `Group` system handles draw ordering
and collision detection automatically.

### 4.3 Animation Pipeline

Events drive animations sequentially:

```python
def handle_events(self, events: list[Event]):
    """Queue animations from game events, play in order."""
    for ev in events:
        if isinstance(ev, TorpedoFired):
            self.queue_animation(TorpedoAnimation(ev.course))
        elif isinstance(ev, TorpedoTracked):
            self.queue_animation(TorpedoMoveAnimation(ev.sector))
        elif isinstance(ev, KlingonDestroyed):
            self.queue_animation(ExplosionAnimation(ev.sector))
            self.queue_animation(RemoveSpriteAnimation(ev.sector))
        elif isinstance(ev, KlingonFired):
            self.queue_animation(PhaserBeamAnimation(
                ev.from_sector, self.ship_pos))
            self.queue_animation(ShieldFlashAnimation())
        elif isinstance(ev, ShipMoved):
            self.queue_animation(ShipMoveAnimation(
                ev.from_sector, ev.to_sector))
        # ... etc for all 30+ event types
```

---

## 5. Mouse Support

### 5.1 Tactical Grid Interactions

| Action                    | Mouse Gesture                    |
|---------------------------|----------------------------------|
| Select sector             | Left-click on grid cell          |
| Fire torpedo at sector    | Right-click on Klingon           |
| Set navigation course     | Left-click empty cell → confirm  |
| View sector info          | Hover → tooltip (entity, coords) |
| Fire phasers (all)        | Click [PHA] button               |

### 5.2 Click-to-Navigate

When clicking an empty cell on the tactical grid:

1. Calculate course and warp factor from Enterprise position to target cell
   (reuse `calc_direction_distance` from `display.py`)
2. Show projected path overlay (dotted line)
3. Popup: "NAV to sector {r},{c} — Course {c:.1f}, Warp {w:.1f}? [Go / Cancel]"
4. On confirm → build `NavCommand`, execute, animate

### 5.3 Right-Click Context Menu

Right-clicking on a sprite shows context-appropriate actions:

- **Klingon**: "Fire Phasers" / "Fire Torpedo" / "Torpedo Data"
- **Starbase**: "Dock (NAV)" / "Navigation Data"
- **Star**: "Sector Info"
- **Empty**: "Navigate Here" / "Set Waypoint"

### 5.4 Minimap Interactions

- Left-click quadrant on minimap → show LRS data in tooltip
- Double-click → set warp navigation to that quadrant

### 5.5 Command Bar

Clickable buttons replacing typed commands:

```
[NAV]  [PHA]  [TOR]  [SHE]  [LRS]  [DAM]  [COM]  [SAE]  [SET]
```

Each opens a modal dialog or inline input panel matching the TUI prompts.

---

## 6. Hotkey Integration

### 6.1 Primary Hotkeys (match TUI commands)

| Key       | Action              | Notes                          |
|-----------|---------------------|--------------------------------|
| `N`       | Navigation          | Opens course/warp input        |
| `S`       | Short Range Sensors | Refreshes tactical display     |
| `L`       | Long Range Sensors  | Opens LRS overlay              |
| `P`       | Fire Phasers        | Opens energy input             |
| `T`       | Fire Torpedo        | Opens course input             |
| `H`       | Shields             | Opens shield energy input      |
| `D`       | Damage Report       | Opens damage panel             |
| `C`       | Computer            | Opens computer submenu         |
| `F5`      | Quick Save          | SAE equivalent                 |
| `F9`      | Quick Load          | Restore from save              |
| `Escape`  | Cancel / Menu       | Cancel current action or menu  |

### 6.2 Combat Hotkeys

| Key       | Action                          |
|-----------|---------------------------------|
| `1`-`9`   | Fire torpedo on course 1-9      |
| `Ctrl+P`  | Fire phasers (max energy)       |
| `Tab`     | Cycle target (next Klingon)     |
| `Space`   | Confirm action / skip animation |

### 6.3 Navigation Hotkeys

| Key           | Action                      |
|---------------|-----------------------------|
| Arrow keys    | Navigate to adjacent sector  |
| `Ctrl+Arrow`  | Warp to adjacent quadrant    |
| `Numpad 1-9`  | Set course direction (1-9)   |
| `+` / `-`     | Increase / decrease warp     |
| `Enter`       | Confirm navigation           |

### 6.4 Modifier Keys

| Modifier   | Behavior                                |
|------------|-----------------------------------------|
| `Ctrl`     | Command modifier (Ctrl+S = save, etc.)  |
| `Shift`    | Alternate action (Shift+click = info)   |
| `Alt`      | Menu bar access (Alt+F = File menu)     |

---

## 7. Scene / State Machine

```
    ┌─────────┐
    │  TITLE  │──── New Game ────┐
    └─────────┘                  │
         │                       ▼
    Restore Save          ┌───────────┐
         │                │   SETUP   │
         │                │ Difficulty │
         ▼                └─────┬─────┘
    ┌─────────┐                 │
    │  PLAY   │◄────────────────┘
    │         │
    │  Loop:  │
    │  - Render grid + HUD
    │  - Handle input (mouse/keys)
    │  - Build Command
    │  - Execute engine
    │  - Animate Events
    │  - Check win/lose
    │         │
    └────┬────┘
         │
    ┌────▼─────┐
    │ GAMEOVER │──── Play Again? ──→ SETUP
    │ Victory  │
    │ Defeat   │──── Quit ──→ EXIT
    └──────────┘
```

---

## 8. Packaging for Distribution

### 8.1 PyInstaller (recommended)

```bash
# Single-file executable
pyinstaller --onefile --windowed \
    --add-data "assets:assets" \
    --icon assets/icon.ico \
    --name "SST3" \
    gui_main.py

# Output:
#   dist/SST3.exe      (Windows)
#   dist/SST3           (Linux)
#   dist/SST3.app       (macOS — use --osx-bundle-identifier)
```

### 8.2 Platform-Specific Notes

| Platform | Packaging Tool     | Notes                              |
|----------|--------------------|------------------------------------|
| Windows  | PyInstaller        | `.exe`, optional NSIS installer    |
| macOS    | PyInstaller + py2app| `.app` bundle, needs code signing  |
| Linux    | PyInstaller        | AppImage or `.deb` via fpm         |
| All      | cx_Freeze           | Alternative to PyInstaller         |

### 8.3 Requirements

```
# requirements-gui.txt
pygame>=2.5.0
pyinstaller>=6.0   # build-time only
```

The TUI mode remains zero-dependency (stdlib only). GUI mode adds only
`pygame` as a runtime dependency.

---

## 9. Asset Pipeline

### 9.1 Directory Structure

```
pystrek/
├── assets/
│   ├── sprites.png          # 64×64 sprite sheet (all entities)
│   ├── sprites.json         # Sprite atlas metadata
│   ├── font.ttf             # Monospace font (e.g., Press Start 2P, IBM Plex Mono)
│   ├── sounds/
│   │   ├── phaser.wav
│   │   ├── torpedo.wav
│   │   ├── explosion.wav
│   │   ├── shield_hit.wav
│   │   ├── warp.wav
│   │   ├── dock.wav
│   │   ├── alert_red.wav
│   │   └── victory.wav
│   ├── icon.ico             # Windows icon
│   └── icon.png             # Linux/Mac icon
├── gui_main.py
├── gui_scenes.py
├── gui_hud.py
├── gui_sprites.py
├── gui_assets.py
└── ... (existing modules unchanged)
```

### 9.2 Sprite Sheet Loader

```python
class SpriteSheet:
    def __init__(self, path, cell_size=64):
        self.sheet = pygame.image.load(path).convert_alpha()
        self.cell_size = cell_size

    def get_sprite(self, col, row):
        rect = pygame.Rect(
            col * self.cell_size, row * self.cell_size,
            self.cell_size, self.cell_size)
        image = pygame.Surface(rect.size, pygame.SRCALPHA)
        image.blit(self.sheet, (0, 0), rect)
        return image

    def load_strip(self, name, count):
        """Load a horizontal strip of frames by name from atlas metadata."""
        ...
```

---

## 10. GUI Event Handler (Core Integration)

This is the critical bridge between the existing engine and the GUI:

```python
class GUIEventRenderer:
    """
    Replaces render_nav_events() / render_combat_events() / etc.
    Translates engine Events into sprite animations + HUD updates.
    """

    def __init__(self, grid, hud, message_log, sound_mgr):
        self.grid = grid
        self.hud = hud
        self.log = message_log
        self.sound = sound_mgr
        self._animation_queue = []

    def process(self, events: list):
        """Process a list of Events from the game engine."""
        for ev in events:
            self._dispatch(ev)

    def _dispatch(self, ev):
        if isinstance(ev, TorpedoFired):
            self.log.add("TORPEDO TRACK:", "cyan")
            self.sound.play("torpedo")

        elif isinstance(ev, TorpedoTracked):
            r, c = ev.sector
            self.log.add(f"  {r},{c}", "cyan")
            self._animation_queue.append(
                TorpedoMoveAnim(self.grid, ev.sector))

        elif isinstance(ev, KlingonDestroyed):
            self.log.add("*** KLINGON DESTROYED ***", "green")
            self.sound.play("explosion")
            self._animation_queue.append(
                ExplosionAnim(self.grid, ev.sector))

        elif isinstance(ev, KlingonHit):
            r, c = ev.sector
            self.log.add(
                f"{ev.damage} UNIT HIT ON KLINGON AT {r},{c}", "cyan")
            self._animation_queue.append(
                PhaserBeamAnim(self.grid, self.grid.ship_pos, ev.sector))

        elif isinstance(ev, KlingonFired):
            self.log.add(
                f"{ev.damage} UNIT HIT FROM {ev.from_sector}", "red")
            self.sound.play("shield_hit")
            self._animation_queue.append(
                ShieldFlashAnim(self.grid))

        elif isinstance(ev, Victory):
            self.log.add("CONGRATULATIONS! MISSION COMPLETE!", "green")
            self.sound.play("victory")

        elif isinstance(ev, EnterpriseDestroyed):
            self.sound.play("explosion")
            self._animation_queue.append(
                ExplosionAnim(self.grid, self.grid.ship_pos))

        # ... handle all 30+ event types

        self.hud.refresh()  # update status panel after each event
```

---

## 11. Input Dialog System

Modal dialogs replace TUI `input()` calls:

```python
class InputDialog:
    """
    Pygame-rendered modal dialog for numeric/text input.
    Supports mouse-click confirmation and keyboard entry.
    """

    def __init__(self, prompt, input_type="float", bounds=None):
        self.prompt = prompt
        self.input_type = input_type
        self.bounds = bounds  # (min, max) or None
        self.value = ""
        self.done = False
        self.result = None

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self._submit()
            elif event.key == pygame.K_ESCAPE:
                self.done = True  # cancelled
            elif event.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]
            else:
                char = event.unicode
                if char and char in "0123456789.-":
                    self.value += char

    def draw(self, surface):
        # Draw semi-transparent overlay
        # Draw dialog box with prompt and current value
        # Draw [OK] and [Cancel] buttons (clickable)
        ...
```

### Command-specific dialogs:

| Command | Dialog                                              |
|---------|-----------------------------------------------------|
| NAV     | Two fields: Course (1-9), Warp Factor (0-8)         |
| PHA     | Slider or text: Energy to fire (0 to available)     |
| TOR     | Course selector (1-9) with visual compass overlay   |
| SHE     | Slider: Shield energy (0 to energy+shields)         |
| COM     | Submenu buttons (1-6)                               |
| DAM     | Read-only panel + "Authorize Repairs?" button       |

---

## 12. Torpedo Course Selector (Visual)

Instead of typing a number 1-9, the torpedo course selector is a visual compass
overlay on the tactical grid:

```
              3
            / | \
          4   |   2
         /    |    \
       5 ---- * ---- 1    ← Enterprise at center
         \    |    /
          6   |   8
            \ | /
              7
```

- Mouse: hover over direction → highlight path → click to fire
- Keyboard: press 1-9 to fire immediately
- Shows projected torpedo path as dotted line before confirming

---

## 13. Sound Design

| Event                 | Sound                    | Duration |
|-----------------------|--------------------------|----------|
| Phaser fire           | Ascending electronic hum | 0.5s     |
| Torpedo launch        | Deep thump + whoosh      | 0.3s     |
| Torpedo tracking      | Quiet pulse per step     | 0.1s     |
| Explosion (Klingon)   | Burst + crackle          | 0.8s     |
| Shield hit            | Metallic clang + buzz    | 0.4s     |
| Enterprise destroyed  | Long explosion           | 2.0s     |
| Warp engage           | Rising hum               | 1.0s     |
| Dock at starbase      | Gentle chime             | 0.5s     |
| Red alert             | Klaxon                   | 1.5s     |
| Victory fanfare       | Triumphant brass         | 3.0s     |
| Device damaged        | Spark/crackle            | 0.3s     |
| Device repaired       | Positive chime           | 0.3s     |

All sounds should be 16-bit WAV, 22050 Hz, mono. Keep total asset size under
2 MB for fast packaging.

---

## 14. Launch Modes

```bash
# TUI mode (unchanged, no dependencies)
python main.py

# GUI mode
python gui_main.py

# Or via flag on a unified entry point
python sst3.py --gui     # launches GUI
python sst3.py --tui     # launches TUI (default)
python sst3.py           # auto-detect: GUI if pygame available, else TUI
```

---

## 15. Implementation Phases

### Phase 1: Core Window + Static Grid
- Pygame window with 8x8 grid rendering
- Placeholder colored rectangles for entities (no sprites yet)
- Status panel with game state values
- Basic game loop: render state, no interaction yet
- **Deliverable**: Visual display of any GameState

### Phase 2: Mouse + Keyboard Input
- Command bar (clickable buttons)
- Input dialogs for NAV, PHA, TOR, SHE
- Hotkey dispatch (N, P, T, H, L, D, C)
- Full game playable via GUI (using colored rectangles)
- **Deliverable**: Fully playable GUI with placeholder graphics

### Phase 3: Sprites + Animation
- Create/commission sprite sheet
- Replace rectangles with sprites
- Torpedo travel animation
- Phaser beam animation
- Explosion animation
- Ship movement interpolation
- **Deliverable**: Polished visual experience

### Phase 4: Sound + Polish
- Sound effects integration
- Minimap (galaxy overview)
- Right-click context menus
- Tooltip hover info
- Visual torpedo course selector
- Settings dialog (replaces SET command)
- **Deliverable**: Feature-complete GUI

### Phase 5: Packaging
- PyInstaller configs for Win/Mac/Linux
- Icon and metadata
- CI/CD build pipeline (GitHub Actions)
- **Deliverable**: Downloadable executables

---

## 16. File Manifest (New Files)

| File              | Purpose                                    |
|-------------------|--------------------------------------------|
| `gui_main.py`     | Entry point, Pygame init, scene manager    |
| `gui_scenes.py`   | Title, Setup, Play, GameOver scenes        |
| `gui_hud.py`      | Status panel, command bar, message log     |
| `gui_sprites.py`  | All sprite classes + animation system      |
| `gui_assets.py`   | Sprite sheet loader, sound manager, fonts  |
| `gui_input.py`    | Input dialogs, course selector, modals     |
| `gui_events.py`   | GUIEventRenderer (Event → animation bridge)|
| `sst3.py`         | Unified entry point (--gui / --tui)        |
| `assets/`         | Sprites, sounds, fonts, icons              |
| `sst3.spec`       | PyInstaller spec file                      |
| `requirements-gui.txt` | pygame dependency                     |

**Total new Python files**: 7 (approximately 1500-2500 lines total)
**Existing files modified**: 0

---

## 17. Testing Strategy

- All game logic tests remain unchanged (`test_*.py`)
- GUI-specific tests use `pygame.display.set_mode()` in headless mode
  (`SDL_VIDEODRIVER=dummy`)
- Test `GUIEventRenderer` by passing known event lists and verifying
  animation queue contents
- Smoke test: launch GUI, play 3 turns, verify no crashes
- CI: run headless GUI tests on all three platforms

---

## Summary

The existing SST3 Python architecture is **ideal** for a GUI layer:

1. **Command/Event pattern** = GUI builds the same Commands, consumes the same Events
2. **No I/O in game logic** = zero modifications to engine modules
3. **Pygame** = lightweight, sprite-native, cross-platform, easy to package
4. **Incremental delivery** = playable at Phase 2 (colored rectangles), polished at Phase 4
5. **Hotkeys + mouse** = parallel input paths, both always available
