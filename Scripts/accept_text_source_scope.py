#!/usr/bin/env python3
"""Pin the reviewed text-only source scope for game version 1.3.19."""

import json
from pathlib import Path

import UnityPy

from probe_assets import DEFAULT_GAME, ROOT, digest, require


OUTPUT = ROOT / "Documentation/text-source-acceptance-v1.json"
REPORTS = {
    "inventory": ROOT / "Documentation/localization-source-inventory-v3.json",
    "tableScope": ROOT / "Documentation/text-source-scope-v7.json",
    "staticScope": ROOT / "Documentation/static-text-scope-v2.json",
    "legacyUiText": ROOT / "Documentation/legacy-ui-text-scope-v1.json",
    "embeddedTextAssets": ROOT / "Documentation/embedded-text-assets-scope-v2.json",
    "otherSerializedText": ROOT / "Documentation/other-serialized-text-scope-v2.json",
}


def main():
    require(not OUTPUT.exists(), "Preserve prior source acceptance")
    reports = {name: json.loads(path.read_text()) for name, path in REPORTS.items()}
    scope = reports["tableScope"]
    static = reports["staticScope"]
    require(scope["selectedCandidateTables"] ==
            {"Dialogs": 16100, "UI": 259, "ChecksDialogs": 1} and
            scope["selectedCandidateRows"] == 16360,
            "Selected string table scope changed")
    source_static = ROOT / "Source/localization-inventory-v3/static-text.jsonl"
    source_strings = ROOT / "Source/localization-inventory-v3/strings.jsonl"
    require(static["staticInventorySha256"] == digest(source_static) and
            static["stringInventorySha256"] == digest(source_strings) and
            len(static["rows"]) == 244,
            "Static inventory or binding audit changed")
    selected_static = {row["stableId"] for row in static["rows"]
                       if row["source"] and
                       (not row["localizedStringBindings"] or
                        any(link["sourceStableId"] is None
                            for link in row["localizedStringBindings"]))}
    require(len(selected_static) == 178, "Selected supplemental TMP count changed")
    legacy = reports["legacyUiText"]
    require(legacy["counts"] == {"allLegacyText": 149, "gameSceneText": 0,
                                 "resourcesDebugUiTemplates": 149},
            "Legacy UI text classification changed")
    embedded = reports["embeddedTextAssets"]
    require(len(embedded["textAssets"]) == 18 and
            not embedded["twineComponentsInSerializedAssets"] and
            not embedded["serializedStoryReferencesInResources"] and
            not any(embedded["literalFakePeopleNamesInGlobalMetadata"].values()),
            "Embedded story may have a runtime consumer")
    other = reports["otherSerializedText"]
    require(other["candidateFields"] == 338 and
            other["uniqueNontechnicalValues"] == 60 and
            not other["rawCyrillicSpansInUnreadable"],
            "Other serialized text audit changed")
    bundle_dir = DEFAULT_GAME / "NoImNotAHuman_Data/StreamingAssets/aa/StandaloneWindows64"
    bundles = sorted(bundle_dir.glob("*.bundle"))
    require(len(bundles) == 26, "Addressable bundle count changed")
    bundle_rows = []
    for path in bundles:
        env = UnityPy.load(str(path))
        game_objects = sum(obj.type.name == "GameObject" for obj in env.objects)
        text_assets = sum(obj.type.name == "TextAsset" for obj in env.objects)
        require(game_objects == text_assets == 0,
                "Addressable bundle contains a new text surface")
        bundle_rows.append({"path": str(path.relative_to(DEFAULT_GAME)),
                            "sha256": digest(path),
                            "gameObjects": game_objects, "textAssets": text_assets})
    result = {"schemaVersion": 1, "gameVersion": "1.3.19",
              "sourceLocale": "ru", "scope": "text only; images and textures excluded by owner",
              "decision": "accepted source-ID inventory for authored text and editorial review",
              "selectedStringRows": 16360,
              "selectedSupplementalStaticRows": len(selected_static),
              "selectedTotalRows": 16360 + len(selected_static),
              "sourceStringsSha256": digest(source_strings),
              "sourceStaticSha256": digest(source_static),
              "evidence": {name: {"path": str(path.relative_to(ROOT)),
                                  "sha256": digest(path)}
                           for name, path in REPORTS.items()},
              "addressableBundles": bundle_rows,
              "excluded": [
                  "149 Unity rendering DebugUI resource-template Text fields",
                  "Embedded FakePeople_RU/EN Twine stories without a serialized consumer or literal metadata resource name",
                  "Unused historical string-table rows outside current Dialogs, UI and the referenced ChecksDialogs key",
              ],
              "reopenConditions": [
                  "A runtime path reaches the embedded Twine story or another historical table",
                  "An unreadable component or dynamically created object exposes an unlisted display string",
                  "Any source asset, extractor, stable-ID map or consumer binding changes",
              ],
              "runtimeReachability": "not fully verified; source decision must be reopened if a listed condition occurs",
              "rendererFeasibility": "pending", "semanticReview": "pending"}
    require(result["selectedTotalRows"] == 16538, "Text denominator changed")
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(OUTPUT.relative_to(ROOT)),
                      "selectedRows": result["selectedTotalRows"],
                      "bundles": len(bundle_rows)}))


if __name__ == "__main__":
    main()
