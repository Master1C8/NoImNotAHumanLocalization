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
python Scripts/probe_assets.py --output outputs/new-assets-run
python Scripts/probe_fonts.py --output outputs/new-fonts-run
```

`--game` accepts the actual Windows game directory, not the macOS wrapper.
The default points at the owner's KINGSTONMAC installation. These scripts only
write new directories under this project's `outputs/`; existing results are
never overwritten. They check the build GUID and recheck original input hashes.

The asset probe selects `UI_ru/Common_NewGame` by its shared numeric ID, checks
the Russian source value, rewrites a no-op and one synthetic sample for every
target locale, reopens each bundle, and compares every serialized object in the
Russian string bundle. Its carrier locale remains `ru`. It does not create
target runtime locales, modify the Addressables catalog, or prove rendering.
Validation remains enabled with Python optimization (`-O`).

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
save isolation, locale restoration, and machine-readable evidence. Its Java
17 and ImageMagick dependencies are absent on this workstation. Computer Use
cannot currently attach to the Wine window; screenshot review has not run.
Do not substitute blind clicks or treat the user's menu confirmation as visual
acceptance. Resolve the capture boundary before batching samples.

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
