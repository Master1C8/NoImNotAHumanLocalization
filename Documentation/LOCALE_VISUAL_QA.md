# Exact archive visual QA

This is a separate runtime stage after the completed text-only delivery. It does
not reopen unchanged semantic acceptance or authorize publication. Images and
textures remain excluded. The owner authorized in-game checking on October 10,
2026; use the existing `runtime/No Human Probe.app` only.

Use `game-localization-visual-qa` and its references. Start one representative
locale, inspect each native frame, and stop the sequential batch on the first
failed locale. Capture recognition, active locale, visual quality and gameplay
progression are separate assertions. An overall failure must not be converted
to a pass because the ZIP installed or the logs contain no lookup warnings.

## Runner

`Scripts/run_locale_visual_qa.py` adapts the existing native capture and guarded
input architecture. The project adapter is used because Computer Use could not
attach to the Wine window in the recorded earlier investigation. It requires
the verified 31-file Thai fixture checkpoint, exact current locale ZIP, stopped
game/Wine processes, captured helper hashes and native screen/input permission.
It applies the exact one-locale ZIP, disables the diagnostic Wine loader and
selects the real target locale with typewriter enabled. It does not insert
synthetic text. The initial menu path is guarded against a Settings overlay.

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B Scripts/run_locale_visual_qa.py \
  --action start --locale id --run outputs/locale-visual-qa-v2/id
```

Run screen operations outside the shell sandbox. Read the actual frame before
each `click`; supply a reference from that exact run, native image region and
logical click point. The existing adapter checks a fresh window image, exact
fixture ownership, bounds, focus and overlay marker before input. `capture`
only captures the current owned window. A lost observer or timeout does not
authorize launching the case again: inspect status, the window and process
identities first. Preserve the helper version until the run is stopped.

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B Scripts/run_locale_visual_qa.py \
  --action finish --run outputs/locale-visual-qa-v2/id
```

Finish terminates only recognized fixture processes, waits for Wine children,
restores all changed payload files from verified per-file backups, restores the
diagnostic loader and exact preferences, and checks the pinned original files.
An interrupted overlay is not transactional: preserve the receipt/backups and
reconcile each exact file before launching. Do not edit the live execution
version or force past a state/image mismatch.

## Saves and regression lessons

The game has two relevant save roots inside the copied Wine prefix:

- `users/Sikarugir/AppData/LocalLow/Trioskaz/NoImNotAHuman` contains Unity logs.
- `users/Public/Documents/Steam/RUNE/3180070` contains emulator cloud saves,
  mappings, statistics and achievements. This directory must also be inventoried
  before launch. A Unity log-only comparison does not establish save preservation.

Verify resolved roots and every descendant against external links, capture both
inventories/backups, and record actual changes. Do not claim the late discovery
of a save root supplies a missing pre-launch hash. The first Indonesian run
captured the second root after launch but before gameplay; it was unchanged from
that checkpoint through shutdown, and no gameplay action was sent. Later runs
must capture both roots before launch. The focused guard tests use the same
ordinary file contents as a positive control, then replace only the file or
directory with an escaping link and assert the intended rejection.

For source-layout diagnosis, derive the TMP schema from the original scene and
read the packaged component with that schema. The overlay package does not
contain `globalgamemanagers.assets`, so attempting schema generation from that
partial directory alone fails. Inspect `m_enableAutoSizing` explicitly; it does
not contain the substring `font`. The first diagnosis omitted that field and
incorrectly described automatic sizing as disabled. The completed evidence
corrects this: it is enabled, with a 24–28 range, and the observed label still
overflows. Keep the actual field and visual finding together rather than
inferring renderer state from an incomplete property list.

## Current result

See `Documentation/locale-visual-qa-v1/report.json`. The exact Indonesian archive
loaded the correct menu/settings text without observed missing-glyph or resource
lookup warnings, but its exit label extends beyond its button. This is a visual
failure. The remaining 12 locales and dialogue/gameplay checks are pending.
The sequential batch is stopped under the skill's first-failure rule. A layout
repair requires a separately requested fix; this check has not changed any
authored translations, fonts, delivered archives or game UI assets.
