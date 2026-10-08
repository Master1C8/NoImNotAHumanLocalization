#!/usr/bin/env python3
"""Group serialized TMP text by scene role without accepting source scope."""

import argparse
import json
from collections import Counter
from pathlib import Path

from probe_assets import ROOT, digest, require


SCOPE = ROOT / "Documentation/text-source-scope-v6.json"
INVENTORY = ROOT / "Source/localization-inventory-v2/static-text.jsonl"
DEFAULT_OUTPUT = ROOT / "Documentation/static-text-role-triage-v1.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT / "Documentation"), "Output must be in Documentation")
    require(not output.exists(), "Preserve the previous triage output")

    scope = json.loads(SCOPE.read_text())
    static = [json.loads(line) for line in INVENTORY.open()]
    require(len(static) == scope["staticText"]["objects"] == 106,
            "Static inventory or source scope changed")
    paths = {row["textPathId"]: row["scenePath"]
             for row in scope["staticText"]["level0ScenePaths"]}
    linked = {row["textPathId"]: row["links"]
              for row in scope["staticText"]["resolvedUiLocalizationBindings"]}
    missing = {row["textPathId"]: row
               for row in scope["staticText"]["missingUiSourceKeyBindings"]}
    require(len(paths) == 102 and len(linked) == 23 and len(missing) == 1,
            "Scene binding counts changed")

    rows = []
    for source in static:
        stable_id = source["stableId"]
        parts = stable_id.split(":")
        require(len(parts) == 4 and parts[0] == "tmp" and parts[3] == "m_text",
                "Unexpected static stable ID")
        file_name, text_id = parts[1], int(parts[2])
        scene_path = paths.get(text_id) if file_name == "level0" else None
        if file_name == "sharedassets0.assets":
            role = "sharedDebugUi"
        elif text_id in linked:
            role = "uiTableBinding"
        elif text_id in missing:
            role = "orphanUiBinding"
        elif scene_path and "InGameDevMenu" in scene_path:
            role = "developerMenu"
        elif scene_path and "IngameDebugConsole" in scene_path:
            role = "debugConsole"
        elif scene_path and "GachaWindow" in scene_path:
            role = "gachaWindowPlaceholderOrDynamic"
        elif scene_path and "Settings" in scene_path:
            role = "settingsPlaceholderOrDynamic"
        elif scene_path and "EndingShower" in scene_path:
            role = "endingDisplayPlaceholderOrDynamic"
        elif scene_path == ["Canvas", "NotBg", "Version"]:
            role = "dynamicVersion"
        else:
            raise ValueError("Unclassified static text: " + stable_id)
        rows.append({"stableId": stable_id, "source": source["source"],
                     "scenePath": scene_path, "roleGroup": role,
                     "uiBindings": linked.get(text_id, []),
                     "orphanUiBinding": missing.get(text_id)})

    counts = dict(sorted(Counter(row["roleGroup"] for row in rows).items()))
    require(counts == {"debugConsole": 10, "developerMenu": 27,
                       "dynamicVersion": 1, "endingDisplayPlaceholderOrDynamic": 3,
                       "gachaWindowPlaceholderOrDynamic": 24, "orphanUiBinding": 1,
                       "settingsPlaceholderOrDynamic": 13, "sharedDebugUi": 4,
                       "uiTableBinding": 23}, "Static role group counts changed")
    result = {"schemaVersion": 1, "gameVersion": scope["gameVersion"],
              "status": "scene-role triage; inclusion and runtime remain unaccepted",
              "scopeReportSha256": digest(SCOPE),
              "staticInventorySha256": digest(INVENTORY),
              "groupCounts": counts,
              "notes": [
                  "UI table bindings identify 23 localized text objects, not 23 additional translation rows.",
                  "The orphan UI binding has a serialized Russian fallback and a supplemental Thai draft; its runtime patch path is unverified.",
                  "Developer/debug groups are scene roles, not a proven runtime exclusion.",
                  "Gacha, settings, ending and version groups contain serialized placeholders or dynamic text; verify each consumer before accepting scope."],
              "rows": rows}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(output.relative_to(ROOT)),
                      "objects": len(rows), "groupCounts": counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
