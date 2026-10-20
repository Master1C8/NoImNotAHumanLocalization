# No Human Launcher 0.2.1

Open the macOS application or extract the Windows archive and open `No Human Launcher.exe`. The launcher always installs all 14 languages together. Choose and switch languages in the game's own settings, alongside the 18 original languages. Your selected language and unrelated game settings are preserved; the launcher does not choose a language or replace saves.

Requires installed game version 1.3.19, build GUID `c003ddc7de634775a85305fef3b9a0d3`. macOS 14 or later, Intel and Apple Silicon, using the existing Sikarugir game wrapper. Windows x64; tested through the owner's separate CrossOver `kjh` installation. The game must be closed while installation is in progress. Steam installations launch through their local app manifest; standalone installations launch their existing executable.

Languages: Thai, Indonesian, Czech, Hungarian, Dutch, Persian, Romanian, Hindi, Filipino, Greek, Bulgarian, Serbian, Swahili and Hebrew.

The archives include `vnrevival-locales.json` for the site's locale audit. Each declared language comes from the pinned reviewed profile inventory and references the shared compressed payload. The launcher uses the installed game's original icon on each platform.

The package contains renderer 0.4.1, including radio-noise handling and the retained Hindi/Hebrew font bindings. A native static-text adapter follows the game's selected locale for the 178 serialized static fields, preserves gameplay's dynamic replacements, and retains the original text for original locales. The Hindi and Hebrew bindings are combined from their exact reviewed renderer sources. The verified version-bound interop cache is bundled for first launch. Generation-only Unity base libraries are omitted; automatic regeneration is disabled because this installer accepts only the exact game and metadata hashes. GameAssembly and IL2CPP metadata hashes are checked before installation.

## Adaptation and provenance

Base: `StardewTranslationInstaller`, revision `d4154ff15c7c27c801d197750db36c39bc460aa8`. The base checkout is unchanged. The SwiftUI phase/progress/retry/folder/launch layout and native Win32 worker UI are reused. Game branding, discovery, storefront launch and engine integration are adapted here.

The Unity adapter replaces Stardew-specific XNB installation with content-addressed Zstandard 1.5.7 compressed chunks, reusing pinned original-game chunks to keep the complete language set below 100 MB per delivery archive. The native decoder verifies an embedded SHA-256 inventory pin, every payload file and every reconstructed game file. Cached package versions use separate inventory-hash directories, so a compression-only update preserves earlier cache evidence. Existing original bytes are retained. Changed-content updates recognize only the exact prior published file hashes bundled in the new binary-pinned payload; unknown owner changes remain protected. Unknown modifications, other mods, symlink/reparse-point paths and foreign ownership receipts are rejected. An exclusive lock and a transaction journal protect installation and switching; recovery restores the previous files and installation receipt before continuing. Backups and evidence are retained in `VNRevival-NoHuman` inside the selected game folder.

The game-specific text plugin binds exact serialized stable IDs; it reads and responds to the native localization selection. Multilingual picker labels bind their own script's font and its matching atlas material, independently of the selected locale. It never forces or writes `SelectedLanguage`. Wine uses an application-specific `winhttp=native,builtin` override. A conflicting override is preserved and reported.

## Rebuild

From the canonical checkout:

1. Run `.venv/bin/python Launcher/combine_languages.py --out outputs/launcher-combined-v5` and `.venv/bin/python Launcher/build_renderer.py --out outputs/launcher-renderer-v2`; review the per-locale current-input pins/deltas and renderer merge. These recipes reject stale originals and preserve old output directories. Use new versioned paths and update the consuming recipe on later revisions.
2. Build `Launcher/NativeLanguages/NativeLanguages.csproj` with .NET, keeping intermediate output under `outputs/` or a temporary directory. The current recipe consumes `outputs/launcher-native-languages-v3/bin/NoHuman.NativeLanguages.dll`; use `-p:OutputPath=<absolute-output-directory>/bin/` and review that exact binary.
3. Run `python3 Launcher/prepare_payload.py --output outputs/launcher-payload-NEW` against the pinned original game, current combined output, renderer and exact previous published inventory (`outputs/launcher-payload-v11`).
4. Set `Launcher/payload_pin.h` to the resulting `inventory.tsv` SHA-256.
5. Run `python3 Launcher/build.py --payload outputs/launcher-payload-NEW --out outputs/launcher-build-NEW --zig /path/to/zig` on macOS with Swift/Clang, Zig 0.15.2 and the pinned Homebrew Zstandard 1.5.7 library.
6. Run `Launcher/test_engine.py`, including `--previous-engine` / `--previous-payload` for a changed-content upgrade from the actual published package, and verify the actual packaged UI and game on each platform before copying the archives to `dist/`.

Build recipes refuse to overwrite prior build directories. The macOS app is ad hoc signed. No notarization or Windows publisher certificate is implied.

## Third-party software

Bundled notices are in `Licenses/`. BepInEx build BE.788 source: https://github.com/BepInEx/BepInEx/tree/5b766a3 ; Zstandard 1.5.7 source: https://github.com/facebook/zstd/tree/v1.5.7 ; HarfBuzzSharp: https://github.com/mono/SkiaSharp ; Noto Devanagari: https://github.com/notofonts/devanagari . BepInEx's bundled .NET runtime and Unity interop dependencies retain their respective upstream licenses. No changes are made to those upstream libraries.

## Local provenance builds

The release recipe records this repository's exact clean source commit and the
retained payload's complete file inventory. The original Stardew adaptation
revision is historical provenance; it does not require Stardew's current HEAD
to remain at that revision. No Stardew source is read into this build.
Historical release notes and original acceptance statements remain in
`Documentation/launcher-readme-history-20261020.md` and their original records.
A new build record does not rewrite those historical dates or statuses.
