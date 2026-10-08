#!/usr/bin/env python3
"""Resolve scene paths and serialized localization events for every TMP object."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import UnityPy

from probe_assets import DEFAULT_GAME, EXPECTED_UNITY, ROOT, digest, require
from unity_types import CheckedTypeTreeGenerator, generated_tree


AUDIT = ROOT / "outputs/text-path-audit-v2/report.json"
INVENTORY = ROOT / "Source/localization-inventory-v3/static-text.jsonl"
STRINGS = ROOT / "Source/localization-inventory-v3/strings.jsonl"
DEFAULT_OUTPUT = ROOT / "Documentation/static-text-scope-v2.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT / "Documentation"), "Output must be in Documentation")
    require(not output.exists(), "Preserve the previous static scope audit")
    audit = json.loads(AUDIT.read_text())
    source = {row["stableId"]: row for row in
              (json.loads(line) for line in INVENTORY.open())}
    require(len(audit["rows"]) == len(source) == 244, "Static source count changed")
    table = {}
    for line in STRINGS.open():
        row = json.loads(line)
        table[("GUID:" + row["stableId"].split(":")[1],
               int(row["stableId"].rsplit(":", 1)[1]))] = row

    generator = CheckedTypeTreeGenerator(EXPECTED_UNITY)
    generator.load_local_dll_folder(str(DEFAULT_GAME /
        "NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed"))
    by_file = defaultdict(list)
    for row in audit["rows"]:
        by_file[row["file"]].append(row)
    result_rows = []
    unreadable = []
    for name, text_rows in by_file.items():
        path = DEFAULT_GAME / "NoImNotAHuman_Data" / name
        relative = str(path.relative_to(DEFAULT_GAME))
        require(digest(path) == audit["sourceFiles"][relative],
                "Original static source file changed")
        env = UnityPy.load(str(path))
        env.typetree_generator = generator
        game_objects = {}
        transforms = {}
        object_transform = {}
        for obj in env.file.objects.values():
            if obj.type.name == "GameObject":
                try:
                    tree = obj.read_typetree()
                except (EOFError, ValueError):
                    continue
                game_objects[obj.path_id] = tree
                for component in tree.get("m_Component", []):
                    component_id = component["component"]["m_PathID"]
                    child = env.file.objects.get(component_id)
                    if child and child.type.name in ("Transform", "RectTransform"):
                        object_transform[obj.path_id] = component_id
            elif obj.type.name in ("Transform", "RectTransform"):
                try:
                    tree = obj.read_typetree()
                    transforms[obj.path_id] = (tree["m_GameObject"]["m_PathID"],
                                               tree["m_Father"]["m_PathID"])
                except (EOFError, ValueError):
                    continue

        def ancestry(game_object_id):
            items, seen = [], set()
            while game_object_id and game_object_id not in seen:
                seen.add(game_object_id)
                go = game_objects.get(game_object_id)
                items.append({"gameObjectId": game_object_id,
                              "name": go.get("m_Name") if go else None,
                              "initialActive": go.get("m_IsActive") if go else None})
                transform = object_transform.get(game_object_id)
                parent = transforms.get(transform, (0, 0))[1]
                game_object_id = transforms.get(parent, (0, 0))[0]
            return list(reversed(items))

        text_ids = {row["id"] for row in text_rows}
        go_text_ids = defaultdict(set)
        for row in text_rows:
            go_text_ids[row["gameObject"]["m_PathID"]].add(row["id"])
        component_go = {}
        events = []
        for obj in env.file.objects.values():
            if obj.type.name != "MonoBehaviour":
                continue
            try:
                tree, _ = generated_tree(obj)
            except (EOFError, ValueError) as error:
                unreadable.append({"file": name, "pathId": obj.path_id,
                                   "error": type(error).__name__})
                continue
            go = tree.get("m_GameObject", {})
            if go.get("m_FileID") == 0:
                component_go[obj.path_id] = go.get("m_PathID")
            reference = tree.get("m_StringReference")
            if reference is None:
                continue
            calls = tree.get("m_UpdateString", {}).get("m_PersistentCalls", {}).get("m_Calls", [])
            for call in calls:
                events.append((obj.path_id, reference, call))
        linked = defaultdict(list)
        unresolved_events = []
        for event_id, reference, call in events:
            pointer = call.get("m_Target", {})
            target_id = pointer.get("m_PathID")
            method = call.get("m_MethodName")
            if pointer.get("m_FileID") == 0 and target_id in text_ids and method == "set_text":
                text_id = target_id
            elif pointer.get("m_FileID") == 0 and method == "SetRTLText" and \
                    call.get("m_TargetAssemblyTypeName") == "RTLTextMeshProBridge, Assembly-CSharp":
                candidates = go_text_ids.get(component_go.get(target_id), set())
                if len(candidates) != 1:
                    unresolved_events.append({"eventPathId": event_id, "targetPathId": target_id,
                                              "method": method, "reason": "bridge has no unique TMP sibling"})
                    continue
                text_id = next(iter(candidates))
            else:
                unresolved_events.append({"eventPathId": event_id, "targetPathId": target_id,
                                          "method": method, "reason": "target is not a local TMP text"})
                continue
            collection = reference["m_TableReference"]["m_TableCollectionName"]
            key_id = reference["m_TableEntryReference"]["m_KeyId"]
            source_row = table.get((collection, key_id))
            linked[text_id].append({"eventPathId": event_id,
                                    "targetComponentPathId": target_id,
                                    "collection": collection, "keyId": key_id,
                                    "sourceStableId": source_row["stableId"] if source_row else None,
                                    "method": method})
        for row in text_rows:
            stable_id = f"tmp:{name}:{row['id']}:m_text"
            require(source[stable_id]["source"] == row["fields"]["m_text"],
                    "Static source text differs from inventory")
            result_rows.append({"stableId": stable_id, "source": source[stable_id]["source"],
                                "class": row["class"],
                                "originalText": row["fields"]["originalText"],
                                "sceneAncestry": ancestry(row["gameObject"]["m_PathID"]),
                                "localizedStringBindings": linked.get(row["id"], [])})
        if unresolved_events:
            unreadable.extend({"file": name, **row} for row in unresolved_events)

    require(len(result_rows) == 244 and
            len({row["stableId"] for row in result_rows}) == 244,
            "Static scope output count changed")
    counts = Counter()
    for row in result_rows:
        if not row["localizedStringBindings"]:
            counts["unbound"] += 1
        elif all(link["collection"] == "" and link["keyId"] == 0
                 for link in row["localizedStringBindings"]):
            counts["unconfiguredEventBinding"] += 1
        elif all(link["sourceStableId"] for link in row["localizedStringBindings"]):
            counts["boundToSourceTable"] += 1
        else:
            counts["boundToMissingSourceKey"] += 1
    require(counts == {"unbound": 168, "unconfiguredEventBinding": 15,
                       "boundToSourceTable": 60, "boundToMissingSourceKey": 1},
            "Static binding category counts changed")
    result = {"schemaVersion": 1, "gameVersion": "1.3.19",
              "status": "static text and serialized-binding audit; runtime roles pending",
              "textPathAuditSha256": digest(AUDIT),
              "staticInventorySha256": digest(INVENTORY),
              "stringInventorySha256": digest(STRINGS),
              "sourceFiles": audit["sourceFiles"],
              "counts": dict(counts),
              "unreadableOrUnresolvedComponents": unreadable,
              "rows": result_rows}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(output.relative_to(ROOT)),
                      "objects": len(result_rows), "counts": dict(counts),
                      "unreadableOrUnresolved": len(unreadable)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
