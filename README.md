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
`TypeTreeGenerator.load_local_dll_folder`. Narrow the object scope before
generation: unrelated Yarn editor classes require DLLs absent from the build.
The backup DLLs are analysis inputs; editing them cannot patch the live IL2CPP
game. Cmap coverage does not prove TMP atlas coverage, shaping or fallback.

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
and no CRC/resource-provider failure was logged. The unobscured main-menu
check is pending manual return; guarded input was refused when another app
was active. New target-language selection and rendering remain unverified.

For an already-running authorized fixture, capture without input or save actions:

```sh
.venv/bin/python Scripts/visual-qa/run_capture.py --output outputs/new-capture
```

An optional `--marker <path>` checks an expected visual state. Automated capture
and visual review remain separate; inspect every frame before accepting it.
The runner rejects a missing or ambiguous fixture window. Do not substitute
blind clicks or treat the owner's menu confirmation as visual acceptance.

## Shared stage binding

All 14 locales follow the same fixed stages from `vn-localization`:
`scope → probe → source → glossary → translate-edit → editorial → resources →
package → runtime → delivery`.

`scope` is established. `probe` uses the two scripts above and the shared
matrix in the checkpoint. It remains unverified for runtime. Later stages
are not started and require their universal source/glossary/editorial gates.
No translation coverage denominator exists until the visible stable-ID
inventory is reconciled. The nine Russian table row counts include potential
unused/demo content and must not be presented as the translation workload.

The next technical decision is how to expose independent target language
selection, populate all three font-role mappings, and register/load their
Addressables tables while preserving official languages. Do not guess target
runtime codes, reuse another game's renderer patch without proof, or remove
locales. Exercise menu, dense UI, dialogue, mixed RTL/LTR text and progression
on the final adapter before mass translation investment.
