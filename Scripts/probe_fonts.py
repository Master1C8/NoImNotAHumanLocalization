#!/usr/bin/env python3
"""Read-only font mapping/cmap discovery; never claims in-game shaping support."""
import argparse
import io
import json
from pathlib import Path

import UnityPy
from fontTools.ttLib import TTFont
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator

from probe_assets import ROOT, DEFAULT_GAME, EXPECTED_UNITY, EXPECTED_BUILD_GUID, SAMPLES, digest


def run(game, output):
    data = game / "NoImNotAHuman_Data"
    if UnityPy.__version__ != "1.25.4":
        raise ValueError("This probe requires pinned UnityPy 1.25.4")
    if f"build-guid={EXPECTED_BUILD_GUID}" not in (data / "boot.config").read_text().splitlines():
        raise ValueError("Game build changed: establish scope again")
    managed = game / "NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed"
    inputs = [data / name for name in ("resources.assets", "sharedassets0.assets")]
    inputs += [managed / name for name in ("Assembly-CSharp.dll", "RTLTMPro.dll", "Unity.TextMeshPro.dll")]
    hashes = {str(p.relative_to(game)): digest(p) for p in inputs}
    generator = TypeTreeGenerator(EXPECTED_UNITY)
    generator.load_local_dll_folder(str(managed))
    mappings, fonts = [], []
    # Narrow before generating type trees: unrelated editor classes lack shipped DLLs.
    roles = {"resources.assets": {1453: "HandwriteFonts", 1454: "SerifFonts"},
             "sharedassets0.assets": {2601: "BaseFonts"}}
    for filename, selected in roles.items():
        env = UnityPy.load(str(data / filename))
        for obj in env.objects:
            if obj.type.name == "Font":
                tree = obj.read_typetree()
                raw = bytes(tree["m_FontData"])
                with TTFont(io.BytesIO(raw)) as font:
                    cmap = font.getBestCmap() or {}
                fonts.append({"assetFile": filename, "pathId": obj.path_id, "name": tree["m_Name"],
                              "embeddedFontSha256": __import__("hashlib").sha256(raw).hexdigest(),
                              "missingSampleCharacters": {
                                  locale: sorted(set(c for c in sample if not c.isspace() and ord(c) not in cmap))
                                  for locale, sample in SAMPLES.items()}})
        env.typetree_generator = generator
        for path_id, expected_name in selected.items():
            obj = next(o for o in env.objects if o.path_id == path_id)
            tree = obj.read_typetree()
            if tree["m_Name"] != expected_name:
                raise ValueError("Font role identity changed; re-establish asset scope")
            rows = tree["<Fonts>k__BackingField"]["_serializedList"]
            codes = [r["Key"] for r in rows]
            if len(codes) != len(set(codes)):
                raise ValueError("Duplicate font mapping code")
            mappings.append({"assetFile": filename, "pathId": path_id, "role": expected_name,
                             "entries": rows, "absentTargetCodes": [c for c in SAMPLES if c not in codes]})
    if any(digest(p) != hashes[str(p.relative_to(game))] for p in inputs):
        raise ValueError("Source changed during font discovery")
    output.mkdir(parents=True, exist_ok=False)
    report = {"schemaVersion": 1, "inputs": hashes, "unityVersion": EXPECTED_UNITY,
              "fontMappings": mappings, "fonts": fonts, "sourceUnchanged": True,
              "coverage": "Embedded font cmap and selected font-role dictionaries only. No TMP atlas, dynamic loading, fallback, shaping, bidi, metrics, clipping or progression acceptance."}
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"report": str(output / "report.json"), "fontRoles": len(mappings), "fonts": len(fonts)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, default=DEFAULT_GAME)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "outputs"):
        parser.error("Output must be below the canonical project's outputs/ directory")
    run(args.game.resolve(), output)
