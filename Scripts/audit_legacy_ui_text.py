#!/usr/bin/env python3
"""Account for legacy Unity UI.Text fields outside the game text inventory."""

import json
from collections import Counter
from pathlib import Path

import UnityPy

from audit_all_static_text import FILES
from probe_assets import DEFAULT_GAME, EXPECTED_UNITY, ROOT, digest, require
from unity_types import CheckedTypeTreeGenerator, generated_tree


OUTPUT = ROOT / "Documentation/legacy-ui-text-scope-v1.json"
LEGACY_TEXT_SCRIPT = (1, 1205)  # UnityEngine.UI.Text in globalgamemanagers.assets.


def main():
    require(not OUTPUT.exists(), "Preserve the previous legacy UI text audit")
    generator = CheckedTypeTreeGenerator(EXPECTED_UNITY)
    generator.load_local_dll_folder(str(DEFAULT_GAME /
        "NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed"))
    rows = []
    source_files = {}
    for name in FILES:
        path = DEFAULT_GAME / "NoImNotAHuman_Data" / name
        source_files[str(path.relative_to(DEFAULT_GAME))] = digest(path)
        env = UnityPy.load(str(path))
        env.typetree_generator = generator
        candidates = []
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            head = obj.parse_monobehaviour_head()
            if (head.m_Script.m_FileID, head.m_Script.m_PathID) == LEGACY_TEXT_SCRIPT:
                candidates.append(obj)
        if not candidates:
            continue
        game_objects, transforms, object_transform = {}, {}, {}
        for obj in env.objects:
            if obj.type.name == "GameObject":
                tree = obj.read_typetree()
                game_objects[obj.path_id] = tree
                for component in tree.get("m_Component", []):
                    component_id = component["component"]["m_PathID"]
                    child = env.file.objects.get(component_id)
                    if child and child.type.name in ("Transform", "RectTransform"):
                        object_transform[obj.path_id] = component_id
            elif obj.type.name in ("Transform", "RectTransform"):
                tree = obj.read_typetree()
                transforms[obj.path_id] = (tree["m_GameObject"]["m_PathID"],
                                           tree["m_Father"]["m_PathID"])

        def ancestry(game_object_id):
            names, seen = [], set()
            while game_object_id and game_object_id not in seen:
                seen.add(game_object_id)
                game_object = game_objects.get(game_object_id)
                require(game_object is not None, "Legacy text GameObject missing")
                names.append(game_object["m_Name"])
                transform = object_transform.get(game_object_id)
                parent = transforms.get(transform, (0, 0))[1]
                game_object_id = transforms.get(parent, (0, 0))[0]
            return list(reversed(names))

        for obj in candidates:
            tree, _ = generated_tree(obj)
            require(isinstance(tree.get("m_Text"), str), "Legacy UI text missing")
            require(tree["m_GameObject"]["m_FileID"] == 0,
                    "Legacy UI text has external GameObject")
            path_names = ancestry(tree["m_GameObject"]["m_PathID"])
            rows.append({"file": name, "pathId": obj.path_id,
                         "gameObjectPath": path_names, "source": tree["m_Text"]})
    require(len(rows) == 149 and
            all(row["file"] == "resources.assets" and
                row["gameObjectPath"][0].startswith("DebugUI") for row in rows),
            "Legacy UI Text scope changed; inspect before exclusion")
    result = {"schemaVersion": 1, "gameVersion": "1.3.19",
              "script": {"fileId": 1, "pathId": 1205,
                         "class": "UnityEngine.UI.Text"},
              "sourceFiles": source_files,
              "counts": {"allLegacyText": len(rows), "gameSceneText": 0,
                         "resourcesDebugUiTemplates": len(rows)},
              "rootCounts": dict(Counter(row["gameObjectPath"][0] for row in rows)),
              "decision": "Exclude Unity rendering pipeline DebugUI resource templates from game localization; re-audit if any root or source file changes.",
              "rows": rows}
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(OUTPUT.relative_to(ROOT)),
                      "objects": len(rows), "gameSceneText": 0}))


if __name__ == "__main__":
    main()
