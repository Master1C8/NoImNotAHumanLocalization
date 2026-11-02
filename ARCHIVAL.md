# Source-only archival

The editable source includes every one of the 5,239 current authored input files declared by the accepted payload, the final glossary, current source inventory/protection rules, fonts/licenses, native source and build tools. Every authored input was rehashed against the released provenance. Historical reviews, earlier inventories and extracted source textures remain recoverable from Git `902eaa98f0d1074d7c2b95f5d8b77fd678508a1c` and are indexed in `ARCHIVAL-EVIDENCE.json`.

## Restore and build

```sh
python3 -B Scripts/restore_archival_inputs.py
uv venv --python 3.14.6 .venv
uv pip install --python .venv/bin/python ziglang==0.15.2
.venv/bin/python -B Launcher/build.py --payload outputs/launcher-retained-payload-0.2.1 --out outputs/NEW-REBUILD --zig .venv/lib/python3.14/site-packages/ziglang/zig
```

Use a new output path. Requires macOS Swift/Clang/Command Line Tools and Zig 0.15.2. The normal builder now uses only this checkout; the historical Stardew adaptation revision is provenance, not a dependency on another Desktop project. Compiler caches are local to the fresh output directory.

Authenticated cold restoration reproduced all nine exact payload files from the accepted Windows release; `nohuman-normal-build` then built both platforms using that restored payload, with architecture/signature checks and both archives below 100 MB. These checks were performed on 2026-11-03; no installer/game was launched. The accepted release `release-0.2.1-4b1fdd732a3e` remains unchanged on GitHub.

For changed game resources follow `Launcher/README.md` with the matching original game, exact current authored inputs and the owning localization workflow. Historical prerequisite records can be inspected with `git show REV:path` or restored from the indexed revision. No historical model job is authorized by that record.

After verification remove `.venv/`, `.build/`, `outputs/`, `dist/`, generated source-analysis textures and bytecode again. Preserve editable inputs, current source and normal Git metadata. `PreservedSaves/` is private owner data and remains protected locally; it is not uploaded or deleted by this archive.

The earlier raw glossary-corpus-v2 export is reproducible extraction, not authored
translation source. All 52,788 source rows were compared by stable ID and source
SHA-256 against the retained canonical v3 inventory before retiring it. Recreate
it with `Scripts/extract_glossary_corpus.py` and the matching original game; that
extractor validates game/source hashes before writing. Old derived context exports
and .NET obj caches are also disposable. No player saves are selected.
