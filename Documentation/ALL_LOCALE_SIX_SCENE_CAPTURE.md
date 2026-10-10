# Six scenes across all localization packages

The owner requested the accepted JPEG 960×600, quality 60 screenshot route for
all languages in `Documentation/localization-state.json:targetLocales`. The
current roster is Thai, Indonesian, Czech, Hungarian, Dutch, Persian, Romanian,
Hindi, Filipino, Greek, Bulgarian, Serbian, Swahili and Hebrew: 14 locales and
84 final images. This task does not publish screenshots or change translations.

Double-click `Capture All Locales.command` from the canonical project folder.
The launcher uses the existing isolated Wine fixture and refuses another live
fixture session. It captures the menu, settings, lower collection page at
`3/11`, entrance prompt after walking to the door, first neighbor dialogue with
answers, and the complete translated school subtitle in the introduction.
Native 2880×1800 frames remain separate from JPEG deliverables. All application
navigation uses the exact verified fixture PID and window; the game must retain
focus before native input. No global Wine termination is used.

The route chooses the latest numbered, verified `runtime-preview-v<N>` archive when present,
otherwise the verified `preview-v1` archive. It validates every selected archive
before installing the first locale, including UnityFS block decoding and CRC boundaries.
Hungarian uses the corrected v2 envelope; see
`Documentation/UNITY_BUNDLE_COMPRESSION_REPAIR.md`. Locale identity is tied to the archive,
its 31 installed payload hashes, preferences, canonical target text, and actual
visual review. The original game and source cloud checkpoint are read-only.

```sh
.venv/bin/python -B Scripts/visual-qa/capture_all_locales.py plan
.venv/bin/python -B Scripts/visual-qa/capture_all_locales.py capture --output outputs/new-all-locales
.venv/bin/python -B Scripts/visual-qa/capture_all_locales.py capture --resume --output outputs/the-existing-batch
```

A capture failure stops the batch. Before retrying, inspect `batch.json`, the
locale's `scenario.json` and `status.json`, its owned process identities and
restoration receipts. Never overwrite a failed run, start a second fixture,
or change helpers read by a live job. Reviewed complete runs may be reused
only with matching package/checkpoint/viewport and unchanged frame hashes;
the original execution pins and source provenance must remain visible.

## Caption timing and door navigation

Localized dialogue duration differs from Russian. The school sentence can be
rendered over the playground after the video has already cut away from the
cat in the apartment. Requiring the Russian background and translated caption
together incorrectly waits through the transition to gameplay and prevents
the subsequent W command. The introduction observer therefore retains fresh
native movie frames while recognizing the actual doorway. Once the doorway
appears, the route positions the cursor, recognizes its new camera angle,
holds W, recognizes the entrance prompt, and opens the door.

The observer centers the pointer only after a freshly recognized doorway,
records the exact window/PID and guarded move, then re-recognizes the doorway
and requires its camera region to remain settled for 0.6 seconds. Every later
doorway wait also uses this stability gate. A first transition frame alone
cannot authorize the next action. Regression: Dutch v4 recognized the forward
view, but the camera then pitched down toward the menu click position; the
fresh action comparison correctly rejected RMSE 0.0679745. The repaired run
must prove guarded centering, a settled returned frame, W and the neighbor
panel without raising the action comparison threshold. Failed v4 evidence is
retained after checked restoration.

Collection scrolling is also a semantic transition: each fresh collection
footer authorizes one scroll, then the final target rows are recognized again.
The observer records native before-scroll frames and exact window/PID input
receipts, with a four-scroll limit. Regression: Serbian v6 stopped midway
after one wheel event, showing locked rows despite the unchanged 3/11 counter;
counter presence alone must never accept the final collection screenshot.

Regression: the complete Indonesian school caption appears on the playground,
not the cat shot. The route must still reach the door, hold W, open it and show
answers.

The entrance guard uses two glyph-free popup/frame edges. A `Space` glyph
template is not language-neutral: Persian substitutes its UI font even for
Latin key labels. Regression: the saved Persian entrance prompt must pass,
as must the six saved locale controls; far-door and neighbor frames must
fail. A recognition failure must not trigger another blind W command.

Independently match the complete school sentence, including its final
word; the immediately preceding partly typed frame must fail the caption gate.

macOS Vision nominates complete caption frames from stored native evidence.
OCR is a separate read-only process and never sends application input. A score
threshold and full-length check reject partial captions. Unsupported scripts
or low confidence remain explicitly pending independent review; they are not
silently accepted as English. Reviewed locale-specific white-glyph templates
are frozen under `Resources/VisualQA/locale-captions-v1`. Oculix uses the
matching archive-bound template on repeat runs, independent of movie timing.
Template hashes, full native sources, expected text and neighboring positive/
negative controls must remain available.

The caption gate checks bright foreground pixels as well as image similarity.
At least 99% of the template's white pixels must be present in the matched
frame. Regression: the Swahili frame ending in `shul` passed the older 0.97
image score because the blank background dominated the comparison; only the
following frame containing the complete `shule.` is acceptable. The current
matcher must reject that saved partial frame and accept the saved full frame.
`Scripts/visual-qa/verify_caption_training.py` freezes the current matcher and
checks every learned caption against its original full/neighbor controls.
An upgrade writes each locale's receipt only after its own controls pass;
it is not a transaction across all locale receipts. Original execution
snapshots remain unchanged.

Validate a learned template on a fresh live repeat as well as stored frames.
The first Persian repeat contained a partly typed school sentence and then
the next sentence, but missed the short complete interval: repeated per-pixel
Java calls and repeated template decoding slowed the observer. The matcher
now thresholds buffers through bulk raster access, caches the immutable
template/foreground indices, and prepares learned templates before starting
the movie. Thresholds and foreground coverage are unchanged. All 14 stored
caption controls must pass again after a matcher change; a live repeat must
actually select `caption.png`, retain the full sentence, reach the neighbor
and restore the fixture. An OCR fallback or a manually selected frame does
not prove this automatic repeat.

## Restoration and delivery boundary

Every locale backs up all 31 fixture payload files before the first replacement,
freezes its archive and helpers, moves its prior cloud-save directory intact
aside, and copies the accepted source checkpoint. The diagnostic loader is
disabled for native rendering. Persian, Hebrew and Hindi use explicitly pinned
fixture-only renderer descriptors, recorded separately from the archive.
Persian uses `Resources/VisualQA/capture-renderer-v1.json`; Hindi uses
`capture-renderer-hi-v1.json`, and Hebrew uses `capture-renderer-he-v1.json`.
The Hindi overlay changes three font-role bindings and adds four
verified font objects, preserving every authored text and all other original
serialized objects. The module is backed up and restored byte-for-byte.
On completion or failure,
only verified fixture processes are stopped, and payload, loader, preferences
and cloud saves are restored with hashes. A failure after the first payload
write must restore without launching the game. This is per-file replacement
with checked recovery, not a transaction across all game files.

Each of the 84 images requires visual review of actual language, readable text,
wrapping/clipping, required scene and completeness. RTL reviews additionally
check word order and mixed Latin/digit counters. OCR nomination, archive
validation and successful navigation do not replace this review.

After reviews pass, package into a new canonical release directory:

```sh
.venv/bin/python -B Scripts/visual-qa/capture_all_locales.py package --output outputs/the-reviewed-batch --destination dist/the-new-release
```

The complete JPEG directory, ZIP member hashes/counts/CRC and manifest are
validated in staging before a single directory rename exposes the release.
No upload, publication, deployment or source-save mutation is performed.

## Rendering corrections found by this route

The accepted six-screen route is not a full-game localization acceptance gate.
It records actual archive, font overlay and loaded module versions separately.
The original Persian renderer produces a reversed selector endonym. Module
0.3.0 repairs it but its broad base-setter routing also reshapes Yarn dialogue,
which the native game already renders correctly. The bounded 0.3.1 build routes
only components owned by `TMP_Dropdown`; menu, selector and actual neighbor
line must all be inspected on a new run. The canonical recipe is
`Scripts/build_capture_renderer.py`, built from a frozen committed 0.3.0
checkpoint; concurrent owner radio edits are preserved. This probe is local
evidence, not a published game release.

Hindi settings include labels which bypass those serialized font roles. The
0.3.2 Hindi-only recipe (`--bind-hindi`) binds the existing verified loaded
`VN Probe Hindi Shaped Dynamic` asset before parsing any Devanagari input,
requiring exactly one matching asset, then uses the existing shaping path.
It changes no authored strings or RTL behavior. Regression: both Y-axis labels
logged `RENDERER_HI_UNBOUND` with ChakraPetch in v5; the repaired run must show
`RENDERER_HI_BOUND` for them and no unbound/error messages. Persian retains
its independently pinned 0.3.1 module.

Hebrew uses the separate 0.3.3 recipe (`--bind-hebrew`). Its missing strokes
were overlapping letters, not missing source glyphs or JPEG compression:
native atlas readback contained the narrow yod/vav glyphs, the rendered
material referenced that exact atlas, and mesh diagnostics showed overlapping
neighbors in `להמשיך`. A controlled run with the same archive, font, viewport
and material but without font features separated the letters and restored
readability. The repair removes only the `kern` feature for Hebrew input,
retaining other OpenType features, authored strings, glyph metrics and the
game's RTL processing. Settings labels which bypass locale font roles bind
the same unique loaded Hebrew asset. Regression: `להמשיך`, `אוסף` and `חזור`
must contain every separate letter; the settings, collection, full caption,
entrance and actual neighbor line must also pass on a fresh six-scene run.
Font coverage and a valid atlas alone do not establish rendered readability.

Hungarian, Dutch and Filipino volume labels split inside a word at the original fixed
size 36. `Scripts/build_settings_layout.py` changes all nine localized volume
labels across menu/pause scenes through the same mechanism: one-line fitting,
minimum 18 and maximum 36. All text, fonts and other fields remain exact.
Hungarian v3 retains the compression repair; Dutch and Filipino use v2. Runtime frames
must prove the final label fits before these replacements are accepted.

OCR is a nomination aid, not the authority for classifying neighboring frames.
Thai frame 0023 contains the complete final glyph despite OCR dropping it.
A hash-bound `caption-neighbor-review.json` can classify actual complete,
partial and different native frames after visual inspection; it must cover
the immediate predecessor and a genuine rejected control. Original OCR
observations remain intact.

A second Ctrl-C during restoration is ignored until checked recovery completes.
The signal tests exercise that wrapper with recovery replaced; the real
first-write injection separately exercises module and 31-file recovery without
launching the game. The interrupted Romanian run was recovered through the
explicit restore operation; its original failure and restoration evidence remain.

The fixture wrapper can spawn its own `ShutdownScript.app` after Wine exits.
Recovery may close that exact app only after the game apps are gone, with its
executable, fresh launch time and unchanged PID identity verified against this
run. The wrapper exits naturally afterward. Unknown applications or processes
remain blockers; broad Wine/process-name termination is never used.

Persian OCR can also hallucinate a complete line from a partial native frame.
Inspect the actual hash-bound neighbors in each run; frame numbers from another
execution are not reusable evidence. The v3 Persian 0022 frame is partial, while
0023 is complete; the caption gate must reject 0022 regardless of its OCR text.
