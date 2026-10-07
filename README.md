# No, I'm not a Human localization

Canonical project: `/Users/antonkrutov/Desktop/no I'm not a human`.
Standard localization from Russian, version 1.3.19, Unity 6000.3.10f1, IL2CPP.

The current scope is the early technical probe. No game translation, exhaustive
source inventory, final language adapter, installer or release exists yet.
See [the shared checkpoint](Documentation/localization-state.json).

## Reproduce the bounded static checks

Create an isolated Python environment and install `requirements-probe.txt`.
The verified environment used Python 3.9; all direct analysis tools are pinned.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-probe.txt
.venv/bin/python -O -m unittest discover -s Tests -v
.venv/bin/python Scripts/probe_assets.py --output outputs/new-assets-run
.venv/bin/python Scripts/probe_fonts.py --output outputs/new-fonts-run
```

`--game` accepts the actual Windows game directory, not the macOS wrapper.
The default points at the owner's KINGSTONMAC installation. These scripts only
write new directories under this project's `outputs/`; existing results are
never overwritten. They check the build GUID and recheck original input hashes.

The asset probe selects `UI_ru/Common_NewGame` by its shared numeric ID, checks
the Russian source value, rewrites a no-op and one synthetic sample for every
target locale, reopens each bundle, and compares every serialized object in the
Russian string bundle. Its carrier locale remains `ru`. It does not create
target runtime locales or prove rendering. For each rebuilt bundle it also produces
a matching copy of the Addressables catalog with that bundle's CRC and size
updated. It compares all 26 bundle locations and every byte outside the two
integrity fields; source catalogs are never modified and CRC checking stays enabled.
Validation remains enabled with Python optimization (`-O`).

Runtime regression: rebuilding the Russian bundle without changing its old
catalog produced `No translation found`. The runtime logged expected CRC
`93218230`, calculated CRC `2b91d6f2`, and refused the bundle. Read-back equality
alone therefore does not establish runtime acceptance. Always use the bundle
and catalog from the same completed probe report. Install both only into the
stopped isolated fixture, verify both hashes, then launch and check the same
Russian menu. Two separate file replacements are not a transaction; never
launch between them. No installer/rollback protocol is provided by this probe.

The font probe reads embedded font cmaps and three exact font-role assets.
It generates custom type trees from the game's shipped managed backup using
`CheckedTypeTreeGenerator.load_local_dll_folder`. Narrow the object scope before
generation: unrelated Yarn editor classes require DLLs absent from the build.
The backup DLLs are analysis inputs; editing them cannot patch the live IL2CPP
game. Cmap coverage does not prove TMP atlas coverage, shaping or fallback.

## Native locale binding probe

```sh
.venv/bin/python -O Scripts/build_locale_probe.py --output outputs/new-native-build
```

This technical adapter registers `th,id,cs,hu,nl,fa,ro,hi,fil,el,bg,sr,sw,he`
as separate Unity locales. It retains all 18 official locale objects and their
catalog bindings. Each new locale has nine Russian carrier string tables and
one Russian carrier image table. Only `UI/Common_NewGame` contains a synthetic
script sample. The carrier content is untranslated and is not a source inventory.
Fourteen native language-name keys are added to shared UI data and all official
UI tables. Every original string is retained. All three font-role dictionaries
receive the new codes; original mappings and original font assets are preserved.
The Hebrew probe has its own dynamic font, material and atlas, using the game's
embedded Liberation Sans. Probe font assignments are not final visual styling.

The binary catalog uses Unity's official Addressables 2.9.0 package schema,
format version 2. New key/location storage is appended. Existing asset locations,
providers, dependencies and key order are retained; changed bundles get their
verified CRC and size. Reopened object bytes, container bindings and independent
UI sample/code pairs are checked. The verified build is
`outputs/native-locale-probe-v6/report.json`; it contains 24 artifacts.

Three concrete regressions are encoded in the recipe:

- UnityPy 1.25.4's `get_raw_data()` and `read_typetree()` keep reading the original
  reader after `save_typetree()`. Use `serialized_bytes()` and `current_tree()`
  for accumulated mutations. Fourteen saved locale objects are insufficient if
  repeated container edits retain only the last binding; compare the complete
  saved container set against the saved assets.
- The generated MonoBehaviour header lacks alignment after `m_Enabled`.
  Correct that node, compare native script/game-object pointers, and require a
  byte-exact no-op before editing generated fields.
- TypeTreeGeneratorAPI 0.0.10 puts native load/generate calls inside `assert`.
  Python `-O` removes the calls themselves. The checked wrapper executes them
  explicitly and checks their results under optimization.

Install only into the stopped isolated fixture with a previous installation
receipt. The installer verifies every previous and replacement hash and preserves
backups. It makes per-file atomic replacements, not a multi-file transaction;
launch only after the complete receipt says `allInstalledHashesVerified: true`.
An injected failure between the two replacements is tested with real files:
the first file remains new, the second remains old, backups survive and the
receipt stays unverified. The test replaces process inventory and a copy failure;
it does not prove actual Wine process isolation. After any installation failure,
preserve receipts/backups and reconcile the stopped fixture's exact hashes before
retrying or launching.

```sh
.venv/bin/python Scripts/install_locale_probe.py \
  --build outputs/new-native-build \
  --previous-receipt outputs/native-locale-install-v3/receipt.json \
  --output outputs/new-native-install
```

The saved-locale runner edits only `TextSettingsData.SelectedLanguage` in this
fixture's stopped Wine prefix. It preserves other logical settings, launches
one case, captures menu and settings, saves the fresh log, and terminates only
processes verified through the fixture app path, exact command and start time.
It waits for surviving Wine children to exit. Startup window resizing is a
transient readiness condition; a running case is resumed without another launch.
Native screenshots and saved preferences must agree before crediting a locale.

```sh
.venv/bin/python Scripts/run_saved_locale_probe.py \
  --codes cs hu nl ro hi fil el bg sr sw he \
  --reference outputs/native-fa-menu-v1/native.png \
  --output outputs/new-saved-locale-check
```

This runner is calibrated for the observed 1440×900 window and 2880×1800 native
frame. It initializes Python helpers before work and pins every later Swift
helper read. Do not edit a live run's execution version. Every frame still needs
visual review: capture readiness and process completion do not establish script
shaping, bidi, layout, dialogue progression or final font appearance.

## Runtime fixture and guards

The isolated wrapper is `runtime/No Human Probe.app`. Its bundle ID is
`fun.vnrevival.no-human.probe`; its prefix is inside that copied wrapper. The
original application and saves are outside the fixture. All game payloads,
wrapper files and extracted outputs are ignored by Git.

Before modifying a fixture payload, verify that its exact game process has
stopped. Verify prefix/symlink resolution, pin the original and replacement
hashes, then replace only the intended copied bundle. Capture the actual game
surface and independently prove the active locale and changed binding. A
running process or menu confirmation alone does not prove resource loading.
Use exact task-owned process identities for cleanup, never kill Wine by name.

The workstation's Stardew visual-QA architecture is the capture reference:
process ownership, expected-screen guards, native unannotated frames, timeouts,
save isolation, locale restoration, and machine-readable evidence. Oculix,
Java 17 and ImageMagick are now available. The project capture adapter uses
native window capture and fresh-image Oculix recognition, with immutable helper
copies per run. Screen access must run outside the shell sandbox. Computer Use
could not attach to Wine; the native adapter captured the full 2880×1800 frame.
The Russian failure log is historical evidence, not acceptance of the corrected
catalog. Its native frame is no longer present in the recorded output directory;
do not credit that capture as current visual evidence. The corrected Russian
settings frame and fresh Unity log are recorded in
`outputs/runtime-catalog-verified-20261007/evidence.json`: Russian labels render
and no CRC/resource-provider failure was logged. After the owner pressed Back,
the unobscured Russian menu passed visual review; all five action labels are
present in `outputs/runtime-catalog-menu-20261007/evidence.json`. The isolated
fixture was verified stopped. The automated Back click had correctly refused
input when another app was active. That Russian no-op result is historical;
the current native adapter is recorded separately below.

For an already-running authorized fixture, capture without input or save actions:

```sh
.venv/bin/python Scripts/visual-qa/run_capture.py --output outputs/new-capture
```

An optional `--marker <path>` checks an expected visual state. Automated capture
and visual review remain separate; inspect every frame before accepting it.
The runner rejects a missing or ambiguous fixture window. Do not substitute
blind clicks or treat the owner's menu confirmation as visual acceptance.
Capture-only runs use native window capture without initializing Oculix's mouse
subsystem. Wine fullscreen may use window layer 26; exact fixture ownership,
window title and uniqueness remain required. Guarded clicks compare a fresh
native region against a reviewed reference, focus the exact fixture with
Accessibility, and refuse input if focus is lost. A changed hover color is not
equivalent to a changed language; use a stable text region for selector guards.
Opening a dropdown is not selecting its next item. The earlier assumed-cycle
batch was rejected after its captured frames contradicted the intended locales.

## Shared stage binding

All 14 locales follow the same fixed stages from `vn-localization`:
`scope → probe → source → glossary → translate-edit → editorial → resources →
package → runtime → delivery`.

`scope` is established. All 14 native locales load their independent menu
samples and appear in settings in the isolated v6 build. Full frames were
reviewed for locale/table binding, with their hashes recorded in
[the native evidence matrix](Documentation/native-locale-evidence.json).
The eleven saved-locale cases have fresh logs with no recorded CRC mismatch,
asset-load failure, missing translation, missing key or null-reference exception.
Thai and Indonesian also passed explicit dropdown selection. These observations
cover menu/settings only. Later stages
are not started and require their universal source/glossary/editorial gates.
No translation coverage denominator exists until the visible stable-ID
inventory is reconciled. The nine Russian table row counts include potential
unused/demo content and must not be presented as the translation workload.

Native locale, table and font bindings now exist as an isolated technical probe.
Exercise menu, dense UI, dialogue, mixed RTL/LTR text and progression on this
adapter before mass translation investment. Menu samples intentionally stress a
narrow binding and may overflow; their presence is not layout acceptance. Keep
unverified shaping and other surfaces explicit, and never remove target locales
or patch managed backup DLLs as a substitute for repairing the live mechanism.

Hindi fails the full shaping check. The same embedded Noto Sans font renders
the conjuncts and pre-base vowel correctly through CoreText, while the native
menu differs. The localized menu binding resolves through `LocalizeStringEvent`
1956 → `RTLTextMeshProBridge` 1959 → `RTLTextMeshPro` 1958 in `level0`.
Its existing active feature is `kern`. The bounded `probe_menu_features.py`
experiment adds `liga` to this component only and compares every other object.
Native runtime improved some conjuncts but still failed the complete unchanged
Hindi sample. This is partial improvement, not a complete rendering fix.
The experimental `level0` was restored byte-for-byte before the final Russian
control launch; the copied prefix is reset to `ru` and the fixture is stopped.

Persian and Hebrew mixed menu samples show RTL order, but their settings selector
endonyms are reversed/unshaped. Do not generalize the menu result to that path,
or infer that the Arabic-only preprocessor executes everywhere from analysis DLLs.
The same-font CoreText images are diagnostic references, not game acceptance.
[Unity's Advanced Text Generator documentation](https://docs.unity3d.com/6000.0/Documentation/Manual/UIE-advanced-text-generator.html)
describes a UI Toolkit renderer; it is not evidence of a switch available on this
game's existing TMP components. Full shaping repair remains separate work.

The shared technical gate remains blocked for Hindi and the Persian/Hebrew
selector, and incomplete for the remaining surfaces in every locale. No target
set was reduced and no dependent mass work started. A substantial rendering
adapter needs an owner decision under the shared EARLY-PROBE workflow.
