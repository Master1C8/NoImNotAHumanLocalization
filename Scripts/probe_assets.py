#!/usr/bin/env python3
"""Bounded, read-only source discovery and isolated Unity bundle round trips.

This is a technical probe, not a complete translation inventory or renderer test.
Only outputs below this project's outputs/ directory may be written.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path

import UnityPy

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GAME = Path("/Volumes/KINGSTONMAC/Applications/No Im not a Human.app/Contents/SharedSupport/prefix/drive_c/KS Games/No Im not a Human")
EXPECTED_UNITY = "6000.3.10f1"
EXPECTED_BUILD_GUID = "c003ddc7de634775a85305fef3b9a0d3"
UI_ID = 55224523648913408  # UI Shared Data: Common_NewGame
SAMPLES = {
    "th": "กิ กี กุ กู เก แก กำ น้ำ ABC 123",
    "id": "Aa Bb Cc é ABC 123",
    "cs": "Příliš žluťoučký kůň ABC 123",
    "hu": "Árvíztűrő tükörfúrógép ABC 123",
    "nl": "IJ ij ë ï é ABC 123",
    "fa": "پژوهش فارسی می‌روم ABC 123",
    "ro": "Ăă Ââ Îî Șș Țț ABC 123",
    "hi": "क्ष कि की कु कू प्र ज्ञ हिंदी ABC 123",
    "fil": "Aa Ññ é ABC 123",
    "el": "Ελληνικά ά έ ή ί ό ύ ώ ABC 123",
    "bg": "Аа Ъъ Ьь Йй български ABC 123",
    "sr": "Ђђ Јј Љљ Њњ Ћћ Џџ српски ABC 123",
    "sw": "Aa Bb Cc ng’ ABC 123",
    "he": "עברית שלום שָׁלוֹם ABC 123",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def objects(env):
    result = {}
    for obj in env.objects:
        key = (obj.assets_file.name, obj.path_id)
        if key in result:
            raise ValueError(f"Duplicate object identity: {key}")
        result[key] = obj
    return result


def trees(env):
    return {key: obj.read_typetree() for key, obj in objects(env).items()}


def select_ui(env):
    matches = []
    for key, obj in objects(env).items():
        if obj.type.name == "MonoBehaviour":
            tree = obj.read_typetree()
            if tree.get("m_Name") == "UI_ru":
                matches.append((key, obj, tree))
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one Russian UI table, found {len(matches)}")
    key, obj, tree = matches[0]
    if tree["m_LocaleId"]["m_Code"] != "ru":
        raise ValueError("Wrong source language")
    ids = [entry["m_Id"] for entry in tree["m_TableData"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate Russian UI IDs")
    rows = [entry for entry in tree["m_TableData"] if entry["m_Id"] == UI_ID]
    if len(rows) != 1 or rows[0]["m_Localized"] != "Новая игра":
        raise ValueError("Unsupported original Common_NewGame value")
    return key, obj, tree


def run(game: Path, output: Path):
    if UnityPy.__version__ != "1.25.4":
        raise ValueError("This probe requires pinned UnityPy 1.25.4")
    data = game / "NoImNotAHuman_Data"
    aa = data / "StreamingAssets/aa/StandaloneWindows64"
    source = aa / "localization-string-tables-russian(ru)_assets_all.bundle"
    shared = aa / "localization-assets-shared_assets_all.bundle"
    locales = aa / "localization-locales_assets_all.bundle"
    boot = (data / "boot.config").read_text()
    if f"build-guid={EXPECTED_BUILD_GUID}" not in boot.splitlines():
        raise ValueError("Game build changed: establish scope again")
    inputs = [source, shared, locales, data / "globalgamemanagers", data / "boot.config",
              data / "StreamingAssets/aa/catalog.bin", game / "GameAssembly.dll"]
    hashes = {str(p.relative_to(game)): digest(p) for p in inputs}
    env = UnityPy.load(str(source))
    key, _, ui = select_ui(env)
    if str(objects(env)[key].assets_file.unity_version) != EXPECTED_UNITY:
        raise ValueError("Unexpected Unity version")
    original_trees = trees(env)
    original_raw = {k: v.get_raw_data() for k, v in objects(env).items()}
    # Prove the runtime key binding, rather than selecting a similarly worded row.
    shared_env = UnityPy.load(str(shared))
    shared_ui = [o.read_typetree() for o in shared_env.objects
                 if o.type.name == "MonoBehaviour" and o.peek_name() == "UI Shared Data"]
    if len(shared_ui) != 1:
        raise ValueError("Missing or ambiguous UI Shared Data")
    bindings = [row for row in shared_ui[0]["m_Entries"] if row["m_Id"] == UI_ID]
    if len(bindings) != 1 or bindings[0]["m_Key"] != "Common_NewGame":
        raise ValueError("The stable UI binding changed")
    output.mkdir(parents=True, exist_ok=False)
    noop = UnityPy.load(str(source))
    _, obj, tree = select_ui(noop)
    obj.save_typetree(tree)
    noop_path = output / "no-op.bundle"
    noop_path.write_bytes(noop.file.save(packer="lz4"))
    reopened = UnityPy.load(str(noop_path))
    require(trees(reopened) == original_trees, "No-op changed serialized values")
    require({k: v.get_raw_data() for k, v in objects(reopened).items()} == original_raw, "No-op changed object bytes")
    results = []
    for locale, sample in SAMPLES.items():
        probe = UnityPy.load(str(source))
        _, obj, tree = select_ui(probe)
        row = next(e for e in tree["m_TableData"] if e["m_Id"] == UI_ID)
        row["m_Localized"] = sample
        obj.save_typetree(tree)
        path = output / f"{locale}-sample.bundle"
        path.write_bytes(probe.file.save(packer="lz4"))
        actual = trees(UnityPy.load(str(path)))
        expected = copy.deepcopy(original_trees)
        next(e for e in expected[key]["m_TableData"] if e["m_Id"] == UI_ID)["m_Localized"] = sample
        require(actual == expected, f"Unexpected serialized change for {locale}")
        results.append({"siteLocale": locale, "probeCarrierLocale": "ru",
                        "finalRuntimeLocale": None, "sample": sample,
                        "artifact": str(path.relative_to(ROOT)), "sha256": digest(path),
                        "staticRoundTrip": "passed", "runtime": "not-run", "visual": "not-run"})
    table_summary = []
    for tree in original_trees.values():
        if "m_TableData" in tree:
            entries = tree["m_TableData"]
            ids = [row["m_Id"] for row in entries]
            table_summary.append({"name": tree["m_Name"], "serializedRows": len(entries),
                                  "uniqueIds": len(set(ids)), "duplicateIds": len(ids)-len(set(ids))})
    official = []
    for obj in UnityPy.load(str(locales)).objects:
        if obj.type.name == "MonoBehaviour":
            tree = obj.read_typetree()
            official.append({"name": tree["m_Name"], "runtimeCode": tree["m_Identifier"]["m_Code"]})
    for p in inputs:
        require(digest(p) == hashes[str(p.relative_to(game))], f"Source changed during probe: {p}")
    report = {"schemaVersion": 1, "game": "No, I'm not a Human", "sourceLocale": "ru",
              "gameVersion": "1.3.19", "unityVersion": EXPECTED_UNITY,
              "buildGuid": EXPECTED_BUILD_GUID, "sourceRoot": str(game), "inputs": hashes,
              "tools": {name: importlib.metadata.version(name) for name in ["UnityPy", "fonttools", "dnfile", "dncil"]},
              "noOp": {"artifact": str(noop_path.relative_to(ROOT)), "sha256": digest(noop_path),
                       "allObjectBytesEqual": True, "allSerializedValuesEqual": True},
              "uiBinding": {"key": "Common_NewGame", "id": UI_ID, "sourceValue": "Новая игра"},
              "tableSummary": table_summary, "officialRuntimeLocales": official,
              "probes": results, "sourceUnchanged": True,
              "coverage": "One bounded menu binding; every object in its Russian bundle compared. No complete source inventory or renderer acceptance claimed."}
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({"report": str(output / "report.json"), "noOp": "passed",
                      "sampleRoundTrips": len(results), "sourceUnchanged": True, "runtime": "not-run"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, default=DEFAULT_GAME)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "outputs"):
        parser.error("Output must be below the canonical project's outputs/ directory")
    run(args.game.resolve(), output)
