#!/usr/bin/env python3
"""Audit the current Russian text candidates without declaring translation readiness."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import UnityPy
import dnfile
from dncil.cil.body import CilMethodBody
from dncil.cil.body.reader import CilMethodBodyReaderBytes

from probe_assets import DEFAULT_GAME, EXPECTED_UNITY, ROOT, digest, require
from unity_types import CheckedTypeTreeGenerator, generated_tree


CORPUS = ROOT / "Source/glossary-corpus-v2"
INVENTORY = ROOT / "Source/localization-inventory-v2"
DEFAULT_OUTPUT = ROOT / "Documentation/text-source-scope-v7.json"
UI_GUID = "0cbd8a7a4f543344bb95659de87f67a5"
DIALOGS_GUID = "444ff14f1967f5a4c8eb9e4cf4c913f1"
CHECKS_GUID = "389c6d80595013c41b85a7197838c4b6"


def jsonl(path):
    with path.open() as source:
        return [json.loads(line) for line in source]


def managed_string_database_calls(assembly):
    """Record direct C# localization-table calls; serialized bindings remain separate."""
    pe = dnfile.dnPE(str(assembly))
    methods = pe.net.mdtables.MethodDef.rows
    member_refs = pe.net.mdtables.MemberRef.rows
    generic_index = next(index for index, method in enumerate(methods, 1)
                         if str(method.Name) == "GetLocalization")
    generic_token = 0x06000000 | generic_index
    calls = []
    for method in methods:
        if not method.Rva:
            continue
        body = CilMethodBody(CilMethodBodyReaderBytes(pe.get_data(method.Rva, 12000)))
        for index, instruction in enumerate(body.instructions):
            if instruction.opcode.name not in ("call", "callvirt"):
                continue
            operand = getattr(instruction.operand, "value", None)
            if operand is None:
                continue
            token = int(operand)
            if token == generic_token:
                kind = "GetLocalization"
            elif token >> 24 == 0x0A and 1 <= (token & 0xFFFFFF) <= len(member_refs) and \
                    str(member_refs[(token & 0xFFFFFF) - 1].Name) == "GetTable":
                kind = "GetTable"
            else:
                continue
            literals = []
            for previous in body.instructions[max(0, index - 5):index]:
                if previous.opcode.name != "ldstr":
                    continue
                offset = int(previous.operand.value) & 0xFFFFFF
                raw, _ = pe.net.user_strings.get_with_size(offset)
                literals.append(raw.decode("utf-16le"))
            calls.append({"method": str(method.Name), "call": kind,
                          "precedingStringLiterals": literals})
    require(len(calls) == 16, "Managed localization call count changed: " + str(len(calls)))
    require({literal for call in calls for literal in call["precedingStringLiterals"]
             if literal in ("Dialogs", "UI")} == {"Dialogs", "UI"},
            "Known managed table literals changed")
    require(all("UI" in call["precedingStringLiterals"]
                for call in calls if call["call"] == "GetLocalization"),
            "Generic localization call uses a different table")
    return {"assemblySha256": digest(assembly), "calls": calls}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT / "Documentation"), "Output must be in Documentation")
    require(not output.exists(), "Preserve the previous audit output")

    state = json.loads((ROOT / "Documentation/localization-state.json").read_text())
    report = json.loads((CORPUS / "report.json").read_text())
    inventory_summary = json.loads((ROOT / "Documentation/localization-source-inventory-v2.json").read_text())
    require(state["gameVersion"] == "1.3.19" and state["sourceLocale"] == "ru", "Source version changed")
    require(digest(CORPUS / "strings.jsonl") == report["corpusSha256"], "Corpus changed")
    require(digest(INVENTORY / "strings.jsonl") == inventory_summary["outputs"]["strings.jsonl"], "Inventory changed")
    require(digest(INVENTORY / "static-text.jsonl") == inventory_summary["outputs"]["static-text.jsonl"], "Static inventory changed")
    require(digest(CORPUS / "runtime-bindings.json") == report["runtimeBindingsSha256"], "Runtime bindings changed")

    bindings = json.loads((CORPUS / "runtime-bindings.json").read_text())
    table = bindings["level1:4667"]["stringsTable"]["m_TableReference"]["m_TableCollectionName"]
    require(table == "GUID:" + DIALOGS_GUID, "Current dialogue binding changed")

    source = jsonl(CORPUS / "strings.jsonl")
    candidates = jsonl(INVENTORY / "strings.jsonl")
    require(len(source) == len(candidates), "Corpus/inventory row count differs")
    by_identity = {}
    for row in source:
        identity = (row["guid"], row["id"])
        require(identity not in by_identity, "Duplicate source string identity")
        by_identity[identity] = row
    require(len(by_identity) == len(candidates), "Source identity count differs")
    selected = Counter()
    selected_ids = {"Dialogs": set(), "UI": set()}
    for row in candidates:
        guid, identifier = row["stableId"].split(":")[1:]
        source_row = by_identity.get((guid, int(identifier)))
        require(source_row is not None, "Inventory row lacks a source")
        require((row["collection"], row["key"], row["source"]) ==
                (source_row["collection"], source_row["key"], source_row["text"]),
                "Source/inventory content mismatch")
        if row["collection"] in selected_ids:
            expected_guid = DIALOGS_GUID if row["collection"] == "Dialogs" else UI_GUID
            require(guid == expected_guid, "Selected collection GUID changed")
            selected[row["collection"]] += 1
            selected_ids[row["collection"]].add(int(identifier))
    require(selected == {"Dialogs": 16100, "UI": 259}, "Selected table counts changed")
    require(len(selected_ids["Dialogs"]) == 16100 and len(selected_ids["UI"]) == 259,
            "Selected IDs are not unique")
    collection_guids = {row["collection"]: row["guid"] for row in source}
    scenes = {}
    for index in range(7):
        name = f"level{index}"
        scene = DEFAULT_GAME / "NoImNotAHuman_Data" / name
        raw = scene.read_bytes()
        scenes[name] = {
            "sha256": digest(scene),
            "collectionGuidReferences": {collection: raw.count(guid.encode())
                                         for collection, guid in sorted(collection_guids.items())},
        }
    require(scenes["level0"]["collectionGuidReferences"]["UI"] > 0 and
            scenes["level1"]["collectionGuidReferences"]["UI"] > 0 and
            scenes["level1"]["collectionGuidReferences"]["Dialogs"] > 0,
            "Positive-control scene GUID references missing")

    current = jsonl(CORPUS / "current-dialogs.jsonl")
    require(len(current) == 16100, "Current dialogue snapshot changed")
    require({(row["guid"], row["id"], row["key"], row["text"]) for row in current} ==
            {(row["guid"], row["id"], row["key"], row["text"]) for row in source
             if row["collection"] == "Dialogs"}, "Current dialogue snapshot differs")
    compiled = report["currentScope"]
    require(compiled["compiledLineIds"] == 15693 and not compiled["compiledIdsWithoutRussian"],
            "Compiled line coverage changed")
    require(len(compiled["keysNotFoundInCompiledBytes"]) == 407,
            "Supplemental dialogue count changed")

    asset_guid_references = {}
    for name in ("sharedassets0.assets", "resources.assets"):
        asset = DEFAULT_GAME / "NoImNotAHuman_Data" / name
        require(digest(asset) == state["sourceInputs"][str(asset.relative_to(DEFAULT_GAME))],
                "Original data asset changed: " + name)
        raw = asset.read_bytes()
        asset_guid_references[name] = {
            "sha256": digest(asset),
            "collectionGuidReferences": {collection: raw.count(guid.encode())
                                         for collection, guid in sorted(collection_guids.items())},
        }
    require(asset_guid_references["resources.assets"]["collectionGuidReferences"]["ChecksDialogs"] == 0 and
            asset_guid_references["sharedassets0.assets"]["collectionGuidReferences"]["ChecksDialogs"] == 2,
            "Supplemental ChecksDialogs references changed")
    shared_env = UnityPy.load(str(DEFAULT_GAME / "NoImNotAHuman_Data/sharedassets0.assets"))
    marker = ("GUID:" + CHECKS_GUID).encode()
    supplemental_refs = []
    for obj in shared_env.objects:
        raw = obj.get_raw_data()
        start = raw.find(marker)
        if start < 0:
            continue
        require(obj.type.name == "MonoBehaviour" and raw.count(marker) == 1,
                "Unexpected ChecksDialogs reference object")
        after = start + len(marker)
        pad = (-after) % 4
        require(raw[after:after + pad] == b"\0" * pad,
                "Unexpected ChecksDialogs reference alignment")
        identifier = int.from_bytes(raw[after + pad:after + pad + 8], "little")
        row = by_identity.get((CHECKS_GUID, identifier))
        require(row is not None, "Serialized ChecksDialogs key lacks Russian source")
        supplemental_refs.append({"assetPathId": obj.path_id, "assetName": obj.peek_name(),
                                  "keyId": identifier, "key": row["key"], "source": row["text"]})
    require({(row["assetPathId"], row["assetName"], row["keyId"]) for row in supplemental_refs} ==
            {(2637, "Esenin", 21377524158749), (2668, "Rocker", 21377524158749)},
            "Supplemental ChecksDialogs consumer set changed")
    supplemental_source = by_identity[(CHECKS_GUID, 21377524158749)]
    matching_dialogs = [row for row in current if row["key"] == supplemental_source["key"]]
    require(len(matching_dialogs) == 1 and matching_dialogs[0]["text"] == supplemental_source["text"],
            "Supplemental source no longer matches current dialogue")

    static = jsonl(INVENTORY / "static-text.jsonl")
    text_audit = json.loads((ROOT / "outputs/text-path-audit-v1/report.json").read_text())
    tmp_audit = [row for row in text_audit
                 if row["class"] in ("RTLTextMeshPro", "TextMeshProUGUI")]
    require(len(static) == len(tmp_audit) == 106 and len(text_audit) == 130,
            "Static text audit changed")
    require({row["stableId"] for row in static} ==
            {f"tmp:{row['file']}:{row['id']}:m_text" for row in tmp_audit},
            "Static TMP identities changed")
    level0 = DEFAULT_GAME / "NoImNotAHuman_Data/level0"
    require(digest(level0) == state["sourceInputs"]["NoImNotAHuman_Data/level0"],
            "Original level0 changed")
    env = UnityPy.load(str(level0))
    generator = CheckedTypeTreeGenerator(EXPECTED_UNITY)
    generator.load_local_dll_folder(str(DEFAULT_GAME / "NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed"))
    env.typetree_generator = generator
    level0_ids = {row["id"] for row in tmp_audit if row["file"] == "level0"}
    game_objects = {}
    transforms = {}
    object_transform = {}
    for obj in env.file.objects.values():
        if obj.type.name == "GameObject":
            try:
                tree = obj.read_typetree()
            except (EOFError, ValueError):
                continue
            game_objects[obj.path_id] = tree.get("m_Name", "")
            for component in tree.get("m_Component", []):
                path_id = component["component"]["m_PathID"]
                child = env.file.objects.get(path_id)
                if child and child.type.name in ("Transform", "RectTransform"):
                    object_transform[obj.path_id] = path_id
        elif obj.type.name in ("Transform", "RectTransform"):
            try:
                tree = obj.read_typetree()
                transforms[obj.path_id] = (tree["m_GameObject"]["m_PathID"],
                                           tree["m_Father"]["m_PathID"])
            except (EOFError, ValueError):
                continue

    def scene_path(game_object_id):
        names = []
        seen = set()
        while game_object_id and game_object_id not in seen:
            seen.add(game_object_id)
            names.append(game_objects.get(game_object_id, "<unreadable>"))
            transform = object_transform.get(game_object_id)
            parent = transforms.get(transform, (0, 0))[1]
            game_object_id = transforms.get(parent, (0, 0))[0]
        return list(reversed(names))

    level0_paths = [{"textPathId": row["id"],
                     "scenePath": scene_path(row["gameObject"]["m_PathID"])}
                    for row in tmp_audit if row["file"] == "level0"]
    root_counts = Counter(row["scenePath"][0] if row["scenePath"] else "<unreadable>"
                          for row in level0_paths)
    linked = defaultdict(list)
    unreadable = []
    component_go = {}
    localized_events = []
    go_text_ids = defaultdict(set)
    for row in tmp_audit:
        if row["file"] == "level0":
            go_text_ids[row["gameObject"]["m_PathID"]].add(row["id"])
    for obj in env.file.objects.values():
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            tree, _ = generated_tree(obj)
        except (EOFError, ValueError) as error:
            unreadable.append({"pathId": obj.path_id, "error": type(error).__name__})
            continue
        game_object = tree.get("m_GameObject", {})
        if game_object.get("m_FileID") == 0:
            component_go[obj.path_id] = game_object.get("m_PathID")
        reference = tree.get("m_StringReference")
        if reference is None:
            continue
        calls = tree.get("m_UpdateString", {}).get("m_PersistentCalls", {}).get("m_Calls", [])
        for call in calls:
            localized_events.append((obj.path_id, reference, call))
    for event_id, reference, call in localized_events:
        pointer = call.get("m_Target", {})
        require(pointer.get("m_FileID") == 0, "External localized event target")
        target = pointer.get("m_PathID")
        method = call.get("m_MethodName")
        assembly_type = call.get("m_TargetAssemblyTypeName")
        if target in level0_ids and method == "set_text":
            text_id = target
        elif method == "SetRTLText" and assembly_type == "RTLTextMeshProBridge, Assembly-CSharp":
            candidates = go_text_ids.get(component_go.get(target), set())
            require(len(candidates) == 1,
                    f"Bridge target {target} on GO {component_go.get(target)} resolves to {sorted(candidates)} TMP texts")
            text_id = next(iter(candidates))
        else:
            continue
        linked[text_id].append({
            "eventPathId": event_id,
            "targetComponentPathId": target,
            "collection": reference["m_TableReference"]["m_TableCollectionName"],
            "keyId": reference["m_TableEntryReference"]["m_KeyId"],
            "method": method,
        })
    resolved_ui = defaultdict(list)
    missing_ui = []
    for text_id, links in linked.items():
        for link in links:
            require(link["collection"] == "GUID:" + UI_GUID and
                    link["method"] in ("set_text", "SetRTLText"),
                    "Unexpected serialized text binding: " + repr(link))
            if link["keyId"] in selected_ids["UI"]:
                resolved_ui[text_id].append(link)
            else:
                missing_ui.append({"textPathId": text_id, **link})

    assembly = DEFAULT_GAME / "NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed/Assembly-CSharp.dll"
    managed_calls = managed_string_database_calls(assembly)

    result = {
        "schemaVersion": 1,
        "gameVersion": state["gameVersion"],
        "sourceLocale": "ru",
        "status": "candidate current text scope; source and renderer gates incomplete",
        "localizationScope": "Text only; owner excluded textures and images",
        "sourcePins": {
            "auditScriptSha256": digest(Path(__file__)),
            "corpusReportSha256": digest(CORPUS / "report.json"),
            "inventoryStringsSha256": digest(INVENTORY / "strings.jsonl"),
            "inventoryStaticTextSha256": digest(INVENTORY / "static-text.jsonl"),
            "runtimeBindingsSha256": digest(CORPUS / "runtime-bindings.json"),
            "level0Sha256": digest(level0),
        },
        "sceneGuidReferences": scenes,
        "assetGuidReferences": asset_guid_references,
        "selectedCandidateTables": {"Dialogs": selected["Dialogs"], "UI": selected["UI"],
                                    "ChecksDialogs": 1},
        "selectedCandidateRows": sum(selected.values()) + 1,
        "selectedSupplementalStringRows": [{"stableId": f"string:{CHECKS_GUID}:21377524158749",
                                            "key": supplemental_source["key"],
                                            "source": supplemental_source["text"],
                                            "matchingCurrentDialogId": matching_dialogs[0]["id"],
                                            "serializedReferences": supplemental_refs}],
        "dialogueCompiledLineIds": compiled["compiledLineIds"],
        "dialogueSupplementalTableKeys": len(compiled["keysNotFoundInCompiledBytes"]),
        "managedStringDatabaseCalls": managed_calls,
        "otherCollectionRows": dict(sorted((name, count) for name, count in Counter(
            row["collection"] for row in source).items() if name not in selected)),
        "staticText": {
            "objects": len(static),
            "level0Objects": len(level0_ids),
            "level0RootCounts": dict(sorted(root_counts.items())),
            "level0ScenePaths": level0_paths,
            "resolvedUiLocalizationBindings": [{"textPathId": path_id, "links": links}
                                               for path_id, links in sorted(resolved_ui.items())],
            "missingUiSourceKeyBindings": missing_ui,
            "unresolvedObjects": len(static) - len(resolved_ui),
            "unreadableLevel0Behaviours": unreadable,
        },
        "checks": [
            "Every raw string row matches the extracted source by GUID, ID, key and value.",
            "The current Dialogs snapshot exactly matches the selected dialogue table.",
            "Every compiled dialogue line ID has a Russian source row.",
            "Two shared-asset objects reference one ChecksDialogs key, which has the same Russian text as a current Dialogs key.",
            "The managed StringDatabase call sites use only literal Dialogs and UI table names; serialized and indirect references still require review.",
        ],
        "remaining": [
            "Resolve serialized UI bindings with absent Russian table keys and classify unresolved TMP roles; scene GUID absence alone is not proof of inactivity.",
            "Build and verify the complete preserve-exactly manifest for selected text.",
            "Pass the shared renderer feasibility gate before mass translation.",
        ],
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"selectedCandidateRows": result["selectedCandidateRows"],
                      "staticText": result["staticText"]["objects"],
                      "resolvedUiLocalizationBindings": len(resolved_ui),
                      "missingUiSourceKeyBindings": len(missing_ui),
                      "status": result["status"]}))


if __name__ == "__main__":
    main()
