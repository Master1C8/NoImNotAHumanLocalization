# Runtime renderer probe

The owner approved a separate runtime text module after the native-locale probe
showed Hindi shaping failure and Persian/Hebrew selector failure. The work remains
an early technical probe. All 14 targets are retained; mass localization is gated.

## Integration

The actual game is Unity 6000.3.10f1 / IL2CPP metadata 39, build GUID
`c003ddc7de634775a85305fef3b9a0d3`. BepInEx 6 build 788 successfully generated
interop assemblies and loaded the module through Wine 11.0. The backed-up managed
assemblies are schema evidence, not the patched runtime.

The official loader ZIP SHA-256 is
`f4cc496bd098a0df4164b81e3737297707f13a47c2478dba2f60eefab784817a`.
`Scripts/install_runtime_loader.py` installs new files only and sets winhttp to
native,builtin only for NoImNotAHuman.exe in the copied prefix. The loader's
console is disabled in that copy; logging remains enabled. The first console-stop
attempt and later no-process reconciliation are retained under
`outputs/runtime-loader-launch-v1`.

The module uses HarfBuzzSharp.NativeAssets.Win32 8.3.1.1's x64 DLL. Its package
SHA-256 is `526e22c0b773f57b5a0d202cb6135975ebfa74c8b2ece0681ceae8accacc632a`;
DLL SHA-256 is `eb76238c9e8e41d44b5a5b18167c4c5b39ca5db4277af5dbe92d730f0fc14a7d`.
Installation outputs retain LICENSE.txt and THIRD-PARTY-NOTICES.txt. The extracted
Noto Sans font remains an internal game-derived probe input; this probe does not prepare a
redistributable font or complete release package. The embedded license names SIL
Open Font License 1.1; packaging/license verification remains a release task.

## Hindi

`Scripts/prepare_renderer_probe.py` requires the installed v6 asset hashes and a
stopped fixture. It retains every original font object and changes only Hindi's
three role bindings. New objects in sharedassets0.assets are:

- 900010: dynamic TMP font; 900011: owned material; 900012: owned atlas.
- 900013: owned Unity Font with U+E000 + source glyph ID mapping.

The exact Noto Sans SemiBold source has 4,503 glyphs, 1,000 units/em and SHA-256
`e691fe27813ec6ed11d0a5be4c6c1f6739996ed682462eaa3244a6185217dd6c`.
Only the clone omits GSUB/GPOS/kern; HarfBuzz uses the unchanged source. TMP receives
HarfBuzz glyph order, advances and offsets through private-use glyphs and supported
space/voffset tags. Script runs remain together through nobr; whitespace, Latin
and numbers retain their logical input.

The renderer hook temporarily substitutes TMP's parsing input, then restores
m_text in the finalizer, including exception paths. This avoids storing prepared
glyphs in the public logical text. Rendered character counts still differ from
Unicode/source counts: typewriter and progression require separate verification.

Formatting tags supported by the adapter remain byte-for-byte. Font/style/material/
sprite, font-weight and noparse tags retain their original input until their selected faces are bound and
verified. Tags splitting a syllable, richText=false, unbound font roles, long words,
wrapping, dynamic values and dialogue are not accepted by this menu probe.

## RTL

The language dropdown bypasses RTLTextMeshPro's derived setter. Route that bypass
through the existing component. Protect both the derived setter and UpdateText;
UpdateText can execute later outside the setter's call stack. Protecting only the
setter caused a second transformation of Hebrew menu Latin/numeric runs in v0.1.0.
Versions 0.2.0 and 0.2.1 prevent that reentry; source endonyms are never manually reversed.

This adapter reuses the game's RTL engine. It does not establish complete Unicode
bidi or Arabic/Hebrew mark positioning on arbitrary paragraphs.

## Build and installation

Use an isolated .NET SDK, not a system installation. The observed SDK was 8.0.424
osx-arm64, verified against Microsoft's release metadata SHA-512. The plugin targets
net6.0 for the loader's .NET 6.0.7 runtime; the SDK restored reference pack 6.0.36.
Nullable metadata emission is disabled because the generated IL2CPP mscorlib exposes
incompatible compiler-attribute definitions. The plugin references only required
loader and generated game assemblies.

```sh
DOTNET_CLI_HOME=/private/tmp/no-human-dotnet-home \
DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_GENERATE_ASPNET_CERTIFICATE=false \
/private/tmp/no-human-dotnet-sdk/dotnet build RuntimePlugin/NoHuman.TextRenderer.csproj

.venv/bin/python Scripts/install_renderer_module.py \
  --build outputs/renderer-build/bin/net6.0/NoHuman.TextRenderer.dll \
  --font-build outputs/renderer-font-v3 \
  --package outputs/renderer-dependencies-v1/harfbuzzsharp.nativeassets.win32.8.3.1.1.nupkg \
  --previous outputs/renderer-module-install-v1/receipt.json \
  --output outputs/new-module-install
```

The shown previous receipt belongs to the v0.1.0 → v0.2.0 installation. For further
updates use the actual latest installed receipt. Never reuse a previous receipt
whose file hashes differ from the current fixture. Reconcile incomplete writes
from the per-file backups and receipts before continuing. These installers do not
provide multi-file transactions or automatic rollback; no launch is allowed between
writes. Production, original-prefix writes and release publication are out of scope.

## Verification and reusable regressions

The C# harness links the actual adapter and uses macOS HarfBuzz. It exercises
conjuncts, prebase vowels, join controls, repeated shaping/cache behavior, preserved
Latin/numbers, supported markup and retained font-changing markup. It does not
replace or validate the Wine native DLL, IL2CPP hooks, TMP layout or gameplay.

```sh
DOTNET_CLI_HOME=/private/tmp/no-human-dotnet-home \
DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_GENERATE_ASPNET_CERTIFICATE=false \
/private/tmp/no-human-dotnet-sdk/dotnet run \
  --project Tests/Renderer/ShaperTests.csproj -- outputs/renderer-font-v3/hi-source.ttf
.venv/bin/python -O -m unittest discover -s Tests -v
```

- Shared fontTools cmap dictionaries: validate reserved-codepoint absence before
  modifying any subtable, then update all applicable maps. Checking each map after
  changing a shared dictionary falsely reports a source collision.
- Exception between real module replacements: first applied file stays new, later
  files stay old, completed stays false, and exact originals remain in backups.
  File enumeration order is not assumed by the regression.
- Hindi original text: runtime logs must pair RENDERER_HI with
  RENDERER_LOGICAL_RESTORED for the same component and exact logical string.
- RTL delayed update: mixed Hebrew + ABC 123 must pass through UpdateText without
  another RENDERER_RTL_ROUTE for the menu; caption remains correctly ordered.
- Native screenshots and resource logs remain mandatory. A successful build or a
  macOS shaping test alone cannot accept the game's rendering.

Latest artifact-bound runtime findings are in `runtime-renderer-evidence.json`.
Full renderer gate surfaces (dialogue, next semantic state, dense UI and dynamic
values) remain pending; final font styling and translation have not started.
