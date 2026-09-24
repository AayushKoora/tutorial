# Flappy Bird Feature — Design Document

## The Problem

The PyQt application currently has a single page: a calculator UI (`calculator_app.py`) with no navigation framework connecting it to anything else. The goal is to replace that calculator page with a playable Flappy Bird recreation, without introducing any page-navigation system — this remains a one-page application. The feature needs a real game loop (start, play, lose, restart), spacebar-controlled jumping, randomized pipe obstacles with basic collision detection, and a session-scoped high score. Because PyQt's widget/event model isn't suited to a real-time game loop, the game itself will run in Pygame, launched from a single "Play" button on the Qt page.

## The Technical Plan

The app splits into two independent modules connected by a single function call:

- **`flappy_app.py` (PyQt)** — owns exactly one page: a title, a high-score label, and a "Play" button. It holds no game logic and never imports Pygame internals beyond calling one entry point.
- **`flappy_game.py` (Pygame)** — owns the entire game: its own native window, physics (gravity/jump), pipe spawning and scrolling, collision detection, scoring, rendering, and an in-session restart loop (`PLAYING` ↔ `GAME_OVER`). It never imports PyQt6.

These two modules are connected by one in-process, blocking function call: clicking "Play" calls `flappy_game.run_game()` directly on the same thread. That call doesn't return until the Pygame window is closed, at which point it returns the session's best score as a plain integer. There is no IPC, threading, or subprocess boundary — it's a normal nested Python function call, which means the Qt window is inert (unresponsive, unpainted) for the whole time the game is being played. That tradeoff is accepted in exchange for a much simpler wiring: the score comes back as a direct return value with no serialization.

Inside `flappy_game.py`, a small state machine governs a play session:
- `PLAYING`: gravity applies each frame, pipes scroll and spawn, collisions are checked.
- `GAME_OVER`: triggered by a collision; pressing space resets bird/pipes/score and returns to `PLAYING` **without closing the window**.
- Closing the window (from either state) ends the call and returns `session_best` — the highest live score reached across any life in that session, not just whatever the live score happens to be when the window closes.

All visuals are placeholder shapes (no image assets), each drawn with a filled color plus a darker-toned outline so adjacent shapes (e.g. ground against sky) have a visible seam instead of blending together.

## Alternatives Considered (and Ruled Out)

- **Embedding a live Pygame surface inside a Qt widget** (hacking the SDL window handle into a Qt container) — technically possible but fragile and platform-dependent. Ruled out in favor of Pygame owning its own separate native window entirely.
- **Subprocess model** (launching Pygame as a separate OS process instead of an in-process call) — would keep the Qt window responsive during play, but requires an out-of-band channel (temp file, stdout parsing, socket) just to pass the final score back. Ruled out for simplicity; the in-process blocking call was preferred since a temporarily frozen Qt window was an accepted tradeoff.
- **Persistent high score** (saved to disk via `QSettings` or a file) — ruled out; high score is explicitly session-memory-only per requirements, reset on every app restart.
- **Difficulty scaling** (pipes speeding up or gaps narrowing over time) — ruled out; gap position and gap size are randomized per-pipe, but the randomization range and pipe speed stay constant for the whole run.
- **Sprite/image assets** for the bird, pipes, ground, and sky — ruled out in favor of placeholder geometric shapes with colored borders, to keep initial scope small.
- **On-screen jump button** — ruled out in favor of spacebar-only input, handled entirely inside Pygame's own event loop.
- **Keeping the calculator page alongside the new page** (requiring a navigation system, e.g. `QStackedWidget`) — ruled out; the calculator page is fully replaced so the app can remain single-page with no routing.

## Known Risks (Accepted)

- **Frozen main window during play.** Because the Qt event loop isn't running while `run_game()` blocks, the Qt window's own OS-level close button does nothing while a game is in progress — the OS may show it as unresponsive. This is accepted as-is (no `closeEvent` override, no watchdog); the user must close the Pygame window first, which returns control to Qt and makes the main window responsive again.
- **Sequential Qt → Pygame framework handoff on macOS.** Running PyQt6 (Cocoa via Qt's own event loop wrapper) and then Pygame/SDL (its own Cocoa video backend) sequentially in the same process, on the same thread, is a different risk from the "embedding a live Pygame surface inside Qt" alternative already ruled out above — this is two full GUI frameworks each briefly owning the OS event loop and NSApplication-level resources, one after another, not at the same time. Known rough edges in this combination include menu bar/dock icon ownership and keyboard focus handoff when the Pygame window opens or closes. This is accepted as a known platform risk rather than validated with a spike; if it manifests, `flappy_game.run_game()` is the sole seam for a future subprocess-based fix (see Alternatives Considered).

## Detailed Implementation

### File: `requirements.txt` — *modify*
Add `pygame-ce` as a dependency alongside the existing `PyQt6` entry — **not** upstream `pygame`. Confirmed via `pip index versions` / `pip download` against this repo's actual venv (Python 3.14.6): upstream `pygame` has no published wheel for `cp314` as of this writing, while `pygame-ce` (the actively maintained community fork) ships a `cp314` wheel today. `pygame-ce` is a drop-in replacement — code still does `import pygame` and the public API used here (`pygame.init`, `pygame.display`, `pygame.draw`, `pygame.Rect`, `pygame.event`, `pygame.time.Clock`) is unaffected. Rationale: the game loop, window, rendering, and input handling all run through Pygame, so it must be installed alongside the existing Qt dependency, and it must actually be installable on the Python version already in use.

### File: `calculator_app.py` — *removed (replaced by `flappy_app.py`)*
The calculator-specific code (`BUTTONS` grid, `CalculatorPage`, `CalculatorApp`) is deleted outright rather than modified in place. Rationale: the feature requirement is to fully replace the calculator page, not to keep calculator logic reachable from anywhere — deleting it avoids leaving dead code behind, and renaming the file (see below) makes the module's new purpose unambiguous rather than keeping a `calculator_app.py` that no longer contains a calculator.

### File: `flappy_app.py` — *new (functionally replaces `calculator_app.py`)*
Contains the entire PyQt side, structured as:
- `LauncherPage(QWidget)`: a `QVBoxLayout` holding a title `QLabel`, a high-score `QLabel`, and a "Play" `QPushButton`.
- `MainWindow(QMainWindow)`: sets `LauncherPage` as its central widget (mirrors the shape of the old `CalculatorApp` class, just pointed at the new page). Holds `self.high_score = 0` as session-memory-only state — a plain instance attribute, no file or `QSettings` persistence.
- `on_play_clicked()`: connected to the Play button's `clicked` signal. Calls `flappy_game.run_game()` (blocking) wrapped in `try/except`; on success, receives the returned score, updates `self.high_score` if beaten, and refreshes the high-score label's text. On exception (e.g. `pygame.init()`/display setup failure), shows a `QMessageBox.critical()` with the error instead of letting it propagate and crash the app. The Qt window remains usable after either outcome.
- `main()`: unchanged in shape from the current entry point — builds `QApplication`, shows `MainWindow`, runs `app.exec()`.

Rationale for a new file rather than editing `calculator_app.py` in place: keeps the rename explicit in git history (old file deleted, new file added) rather than silently repurposing a file whose name no longer matches its contents, and matches the two-module architecture (Qt-only, Pygame-only) called out in the Technical Plan.

### Replay flow (across multiple Play clicks)

The user can click "Play" repeatedly for the life of the app: each click makes a fresh call to `run_game()`, which internally starts `session_best` at 0 and runs its own `PLAYING`/`GAME_OVER` loop until its window is closed, at which point it returns that round's best score and control returns to a now-responsive Qt window. `MainWindow.high_score` is the one piece of state that persists *across* these calls (in-process only, cleared on app restart) — it's updated in `on_play_clicked` by comparing each round's returned score against the running best, independent of whatever `flappy_game.py` tracks internally per round.

### File: `flappy_game.py` — *new*
Contains the entire Pygame side, with no PyQt imports. Structured as:

**Tuning constants** (module-level, "standard arcade feel" preset):

| Constant | Value | Notes |
|---|---|---|
| `SCREEN_WIDTH` | 480 px | |
| `SCREEN_HEIGHT` | 720 px | |
| `FPS` | 60 | |
| `GRAVITY` | 0.5 px/frame² | applied to bird's vertical velocity each frame |
| `JUMP_VELOCITY` | -8 px/frame | set (not added) on each jump input |
| `PIPE_SPEED` | 3 px/frame | horizontal scroll speed for pipes and ground |
| `PIPE_SPACING` | 260 px | horizontal gap between consecutive pipes' `x` |
| `GAP_SIZE_MIN` / `GAP_SIZE_MAX` | 130 px / 170 px | randomized per pipe within this range, subject to the bird-size floor below |
| `PIPE_WIDTH` | 70 px | |
| `BIRD_RADIUS` | 15 px | |
| `GROUND_HEIGHT` | 80 px | height of the ground strip, reserved at the bottom of the screen |

- **State**: a bird (position, vertical velocity), a list of active pipes, `live_score`, `session_best`, and a `state` flag (`PLAYING` / `GAME_OVER`).
- **Pipe generation**: each pipe stores `x`, a randomized `gap_y` and randomized `gap_size` (drawn fresh per pipe, independent of prior pipes), and a `scored` flag. New pipes are appended once the most recent pipe has scrolled left past `PIPE_SPACING`; pipes whose right edge has scrolled off the left of the screen are dropped from the list.
  - **Playability guarantee**: `gap_size` is drawn from `[GAP_SIZE_MIN, GAP_SIZE_MAX]` but floored at `BIRD_RADIUS * 2 * 3` (≈3x the bird's diameter) — since `GAP_SIZE_MIN` (130px) is already above that floor with this preset, the floor is a defensive clamp rather than an active constraint given the current constants. `gap_y` (the gap's vertical center) is then clamped to `[gap_size / 2, SCREEN_HEIGHT - GROUND_HEIGHT - gap_size / 2]` so the gap always sits fully between the ceiling and the ground strip, regardless of the randomized `gap_size` drawn for that pipe.
- **Physics**: `apply_gravity(bird)` each frame while `PLAYING`; a jump handler that sets the bird's vertical velocity to `JUMP_VELOCITY` on `KEYDOWN` + `SPACE`.
- **Collision**: per-frame `pygame.Rect.colliderect()` checks between the bird and each pipe's top/bottom rectangles, plus explicit ground/ceiling boundary checks. A ceiling hit (bird's top edge reaches y=0) ends the game exactly like a ground or pipe hit — there is a single uniform collision rule, no special-cased "clamp at ceiling" behavior. Any hit transitions `state` to `GAME_OVER` and sets `session_best = max(session_best, live_score)`.
- **Scoring**: a pipe's `scored` flag flips to `True` (and `live_score += 1`) the first frame the bird's x-position passes the pipe's **right/trailing edge** (`pipe.x + PIPE_WIDTH`) — i.e. scoring happens only once the bird has fully cleared the pipe, not as soon as it enters the gap.
- **Restart**: while `state == GAME_OVER`, `KEYDOWN` + `SPACE` resets bird position/velocity, clears the pipe list, zeroes `live_score`, and sets `state = PLAYING` — all within the same Pygame window, no window teardown.
- **Rendering**: one draw function per element (background/sky, ground, pipes, bird, live score text, game-over overlay), each shape drawn as a filled color followed by a darker-toned outline of the same shape on top (e.g. `pygame.draw.rect(..., width=0)` then `pygame.draw.rect(..., width=3)`), per the color/border table below.
- **`run_game() -> int`**: the sole public entry point. Initializes Pygame and the window, runs the `while True:` loop (event handling → conditional update → render → `clock.tick(FPS)`), and on a `pygame.QUIT` event calls `pygame.quit()` and returns `session_best` to the caller.

Placeholder shape/color/border table used by the rendering functions:

| Element | Shape | Fill | Border |
|---|---|---|---|
| Bird | circle | yellow | dark orange |
| Pipes (top + bottom rects) | rectangle | green | dark green |
| Ground | rectangle strip | brown | dark brown |
| Sky | background fill | light blue | — |

Rationale: isolating all of this in one module with a single-function public interface (`run_game() -> int`) is what makes the Qt side's integration trivial — `flappy_app.py` needs to know nothing about pipes, gravity, or collision, only that calling one function eventually hands back an integer.

### File: `README.md` — *modify (optional, recommended)*
Update the placeholder notes to briefly describe what the app now does (launches to a Flappy Bird play screen) and how to run it (`pip install -r requirements.txt`, then run `flappy_app.py`). Rationale: the current README content is scratch notes from initial setup ("this is aayush's branch", "welcome") and doesn't reflect the app's actual purpose after this change; not required for the feature to function, but prevents the README from being actively misleading.

### File: `hello.py` — *unchanged*
No relation to this feature; left as-is.

## Manual Acceptance Checklist

- [ ] `pip install -r requirements.txt` succeeds in the existing venv (Python 3.14) with `pygame-ce` installed, no build step required.
- [ ] Launching `flappy_app.py` shows the Qt page with title, "0" high score, and a "Play" button — no calculator UI remains.
- [ ] Clicking "Play" opens a separate Pygame window; the Qt window becomes unresponsive but does not crash.
- [ ] Spacebar makes the bird jump; gravity pulls it back down each frame.
- [ ] Colliding with a pipe, the ground, or the ceiling ends the round (all three behave identically).
- [ ] After game over, pressing space resets bird/pipes/score and resumes play in the same window (no flicker/reopen).
- [ ] Across at least 10 generated pipes, no pipe's gap is ever impossibly small or clipped off-screen.
- [ ] Closing the Pygame window returns control to the Qt window, which becomes responsive again and shows an updated high score if beaten.
- [ ] Clicking "Play" again after a round starts a fresh game (score reset to 0) and can still beat the previously set high score.
- [ ] Quitting and relaunching `flappy_app.py` resets the high score to 0 (no persistence).
