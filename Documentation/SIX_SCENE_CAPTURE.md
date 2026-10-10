# Six-scene screenshot scenario

The owner approved JPEG 960×600 at quality 60, matching the six compressed
reference images, on October 10, 2026. Native captures are retained separately.
The scenario is currently trained for Russian, game 1.3.19, and the existing
1440×900 logical / 2880×1800 native isolated Wine window.

Oculix recognizes nine states and produces these six files:

1. `ru-01-main-menu.jpg`
2. `ru-02-settings.jpg`
3. `ru-03-collection.jpg` — the reviewed lower collection page, progress `3/11`.
4. `ru-04-entrance.jpg` — the entrance interaction prompt after approaching.
5. `ru-05-neighbor.jpg` — the first neighbor dialogue with answer buttons.
6. `ru-06-school-intro.jpg` — the intro line “Да, готовим её в школу”.

## Commands

Run from the canonical project. Native recognition/input require execution
outside the shell sandbox with the existing macOS permissions.

Double-click `Capture Six Screenshots.command` in the project folder to run
the Russian route. It chooses a unique output directory and opens the six
JPEGs in Finder after the game stops and restoration succeeds. The game must
not already be running. The command-line equivalents are:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B Scripts/visual-qa/capture_six_scenes.py verify --output outputs/new-scene-controls
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B Scripts/visual-qa/capture_six_scenes.py replay --output outputs/new-six-scenes
```

Use a new output directory for each run. The runner refuses replacement and a
running fixture. Review the output's `scenario.json`, `status.json`, JPEGs,
native frames and per-state recognition receipts before accepting a run.
Recognition proves the selected screen; visual review remains a separate gate.
The scenario does not publish or upload screenshots.

Training is checked in under `Resources/VisualQA/six-scenes-ru-v6`. Its marker
hashes, exact source references and regions are recorded in `recipe.json`.
`train` creates this directory only when absent; it must not replace reviewed
training. Static verification reads the original Russian run's native frames.

## Ownership and recovery

The existing `capture_russian_reference.py` adapter temporarily applies the
original Russian payload to the existing disposable fixture and copies the
reviewed source progress checkpoint. The original game and its saves are
read-only. The fixture's prior cloud-save directory is moved intact aside.
After capture or a scene failure, the adapter stops only verified fixture
processes, preserves the disposable progress, and restores the prior payload,
loader, preferences and cloud-save directory with hash checks.

The run freezes native/Jython helpers and trained markers and verifies the
loaded Python source hashes before transitions. Do not modify its execution
sources while it is live. A lost launcher does not prove the game exited:
inspect the exact run's `status.json`, owned window and process identities
before any retry. Partial setup needs reconciliation; do not start another run.

## Recognition regressions

Native PNGs can have an alpha channel while template crops use RGB. Normalize
both with the same Java buffer conversion before OpenCV matching. A Java
`getSubimage()` shares the parent raster's stride and offset; copy it into a
standalone buffer before handing it to Finder. Regression: the exact Settings
crop must match its own full native frame. Do not lower similarity to conceal
either decoding defect.

The menu buttons are visible behind Settings, and the neighbor's first sentence
remains visible after answers appear. The menu requires absence of the
Settings marker; the dialogue-only state requires absence of answer buttons.
Verification pairs thirteen positive controls with twenty neighboring negative
controls, including both directions of the dialogue/answers transition.

The first live run exposed animation in the broad menu-logo reference region.
Version 2 recognizes the static New Game label, retains the Settings exclusion,
and adds that run's fresh menu as another hashed positive control. Version 1
is preserved in the first run's immutable training snapshot.

Version 3 fixes the subtitle region to contain the whole line and recognizes
its bright glyphs separately from the moving video background. Its positive
controls include two different video frames; its negative control includes
the next subtitle in the same shot. A matching video background alone is not
acceptance of the requested line.

If shutdown times out, `scenario.json` retains `cleanupError` and
`status.json` retains exact process identities in phase `stopping`. Reconcile
the processes before resuming the same run's restoration:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B Scripts/visual-qa/capture_six_scenes.py restore --output outputs/the-existing-run
```

Restoration rejects an already restored run. The verified fixture-process wait
allows 45 seconds for Wine children to exit; it never terminates other Wine
sessions by name.

Russian subtitle templates do not prove other locales. Retrain text-dependent
markers or use independently verified locale-specific semantic guards before
claiming multilingual capture. Save selection bypasses the language picker.

## Focus during movies and recognition

The native adapter focuses the exact fixture before input, but Java startup or
a movie transition can subsequently change the foreground application. The
Oculix worker therefore activates the verified fixture after its own startup
and rechecks foreground PID throughout every scene wait. It records recovery
events, waits 1.2 seconds after activation, and rejects a captured frame if
focus changed while capturing. PID/window identity or geometry changes stop
the run. It never sends navigation input to another foreground application.

Run the bundled Jython entry point and Finder directly from the Oculix JAR,
without opening its IDE. The IDE initializes and moves the mouse on startup,
can take focus, and can reject startup when its mouse-usability probe fails.
Native input remains in the guarded project adapter.

Regression scenario: recognition starts after the launcher focused Wine, then
Chrome becomes foreground while the intro plays. The worker must restore the
same owned game window, continue the existing session, and recognize the next
scene without restarting the game or overwriting the checkpoint.

Version 5 recognizes two small door features within a larger search region.
The game's camera depends on cursor position, so the same doorway can shift
vertically and slightly change perspective. Both reviewed camera positions
must pass at similarity 0.90, while close-up entrance and neighbor frames must
fail. After positioning the cursor, recognize the doorway again before holding
W; a pre-move full-frame reference is no longer the current camera state.

Version 6 also searches the entrance prompt within a bounded area: the prompt
is attached to the doorway and shifts with camera tilt. The original and the
fresh post-W frame are positive controls. Keep the similarity threshold and
neighboring-screen rejections intact. Focus is checked after Finder returns,
so its lazy Java initialization cannot bypass the foreground gate.

## Verified delivery

`outputs/six-scenes-russian-replay-v6` completed all twelve recognition gates
and captured all six JPEGs without manual navigation. Every final image was
visually reviewed. The fixture stopped; payload, preferences and cloud saves
were restored with hash checks, and original-game payload/cloud-save hashes
remained unchanged. The JPEG set totals 303,592 bytes.

The delivered folder is `dist/six-scenes-ru-v6`: `jpeg/` contains only the six
images, `screenshots.zip` contains those same six files, and `manifest.json`
records their hashes. The complete package was staged and validated before a
single directory rename exposed it. Individual fixture-file restoration is
checked separately; it is not a cross-file transaction.

See `SIX_SCENE_CAPTURE_VALIDATION.json` for code/helper hashes, thirteen
positive and twenty negative recognition controls, per-state focus recovery,
cleanup, review and delivery evidence. Native captures remain under the run
directory. The launcher passed shell syntax validation; the underlying replay
command was exercised directly. Terminal may require the existing macOS
Accessibility/Screen Recording permissions when used as a different host.

## All localization packages

For the owner-requested 14-locale extension, use `Capture All Locales.command`
and `Documentation/ALL_LOCALE_SIX_SCENE_CAPTURE.md`. The original Russian
reference and its accepted six images remain version-bound evidence. The
multilingual route learns full locale captions separately from door navigation
and records native versus pinned fixture-renderer execution explicitly.
