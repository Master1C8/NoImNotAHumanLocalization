#!/usr/bin/env python3
"""Pin the base game's orphan wishlist UI binding across official tables."""

import argparse
import json
from pathlib import Path

import UnityPy

from probe_assets import DEFAULT_GAME, ROOT, digest, require


KEY_ID = 86605930199502848
TEXT_ID = 2140
DEFAULT_OUTPUT = ROOT / "Documentation/missing-ui-key-86605930199502848-v1.json"


def table(env, name):
    matches = []
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour" or obj.peek_name() != name:
            continue
        matches.append(obj.read_typetree())
    require(len(matches) == 1, f"Expected one {name} table, found {len(matches)}")
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT / "Documentation"), "Output must be in Documentation")
    require(not output.exists(), "Preserve the previous audit output")

    state = json.loads((ROOT / "Documentation/localization-state.json").read_text())
    scope_path = ROOT / "Documentation/text-source-scope-v6.json"
    scope = json.loads(scope_path.read_text())
    links = [row for row in scope["staticText"]["missingUiSourceKeyBindings"]
             if row["textPathId"] == TEXT_ID and row["keyId"] == KEY_ID]
    require(len(links) == 1, "Missing-key scene binding changed")
    static_path = ROOT / "Source/localization-inventory-v2/static-text.jsonl"
    static = [json.loads(line) for line in static_path.open()]
    source = [row for row in static if row["stableId"] == f"tmp:level0:{TEXT_ID}:m_text"]
    require(len(source) == 1 and source[0]["source"] == "В желаемое",
            "Serialized Russian fallback changed")

    root = DEFAULT_GAME / "NoImNotAHuman_Data/StreamingAssets/aa/StandaloneWindows64"
    shared_path = root / "localization-assets-shared_assets_all.bundle"
    require(digest(shared_path) == state["sourceInputs"][str(shared_path.relative_to(DEFAULT_GAME))],
            "Original shared bundle changed")
    shared = table(UnityPy.load(str(shared_path)), "UI Shared Data")
    shared_ids = {row["m_Id"]: row["m_Key"] for row in shared["m_Entries"]}
    require(KEY_ID not in shared_ids, "Wishlist key is no longer orphaned")

    official = []
    for path in sorted(root.glob("localization-string-tables-*_assets_all.bundle")):
        relative = str(path.relative_to(DEFAULT_GAME))
        require(digest(path) == state["sourceInputs"][relative],
                "Original official table changed: " + relative)
        env = UnityPy.load(str(path))
        ui_tables = []
        for obj in env.objects:
            if obj.type.name == "MonoBehaviour" and obj.peek_name().startswith("UI_"):
                ui_tables.append(obj.read_typetree())
        require(len(ui_tables) == 1, "Expected one UI table: " + relative)
        ui = ui_tables[0]
        rows = [row for row in ui["m_TableData"] if row["m_Id"] == KEY_ID]
        require(len(rows) <= 1, "Duplicate wishlist ID: " + relative)
        official.append({"locale": ui["m_LocaleId"]["m_Code"],
                         "bundle": relative, "sha256": digest(path),
                         "keyPresent": bool(rows),
                         "localizedValue": rows[0]["m_Localized"] if rows else None})
    require(len(official) == 18, "Official locale count changed")
    russian = [row for row in official if row["locale"] == "ru"]
    require(len(russian) == 1 and not russian[0]["keyPresent"],
            "Russian wishlist row changed")

    result = {"schemaVersion": 1, "gameVersion": state["gameVersion"],
              "uiKeyId": KEY_ID, "sceneTextStableId": source[0]["stableId"],
              "serializedRussianFallback": source[0]["source"],
              "sceneBinding": links[0], "scopeReportSha256": digest(scope_path),
              "staticInventorySha256": digest(static_path),
              "sharedUiKeyPresent": False,
              "sharedUiEntryCount": len(shared_ids),
              "sharedBundleSha256": digest(shared_path),
              "officialUiTables": official,
              "officialTablesWithKey": sum(row["keyPresent"] for row in official),
              "conclusion": "The numeric scene binding has no shared UI key. Russian has a serialized fallback but no UI table row; some official locales have an orphan table row. Runtime behavior and the required patch path remain unverified."}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(output.relative_to(ROOT)),
                      "officialTables": len(official),
                      "officialTablesWithKey": result["officialTablesWithKey"],
                      "sharedUiKeyPresent": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
