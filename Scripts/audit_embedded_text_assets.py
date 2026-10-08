#!/usr/bin/env python3
"""Classify embedded TextAssets and flag potential non-table dialogue sources."""

import hashlib
import json
import re
from pathlib import Path

import UnityPy

from audit_all_static_text import FILES
from probe_assets import DEFAULT_GAME, EXPECTED_UNITY, ROOT, digest, require
from unity_types import CheckedTypeTreeGenerator, generated_tree


OUTPUT = ROOT / "Documentation/embedded-text-assets-scope-v2.json"
STRINGS = ROOT / "Source/localization-inventory-v3/strings.jsonl"


def main():
    require(not OUTPUT.exists(), "Preserve the previous TextAsset audit")
    assets, twine_components, source_files = [], [], {}
    for name in FILES:
        path = DEFAULT_GAME / "NoImNotAHuman_Data" / name
        source_files[str(path.relative_to(DEFAULT_GAME))] = digest(path)
        env = UnityPy.load(str(path))
        for obj in env.objects:
            if obj.type.name == "TextAsset":
                tree = obj.read_typetree()
                value = tree["m_Script"]
                assets.append({"file": name, "pathId": obj.path_id,
                               "name": tree["m_Name"], "characters": len(value),
                               "sha256": hashlib.sha256(value.encode()).hexdigest()})
            elif obj.type.name == "MonoBehaviour":
                head = obj.parse_monobehaviour_head()
                if (head.m_Script.m_FileID, head.m_Script.m_PathID) == (1, 1250):
                    twine_components.append({"file": name, "pathId": obj.path_id})
    require(len(assets) == 18 and not twine_components,
            "Embedded TextAsset or Twine component scope changed")
    scripts = [row for row in assets if row["name"] in ("FakePeople_RU", "FakePeople_EN")]
    require(len(scripts) == 2 and all(row["file"] == "resources.assets" for row in scripts),
            "Embedded story source changed")
    env = UnityPy.load(str(DEFAULT_GAME / "NoImNotAHuman_Data/resources.assets"))
    ru_id = next(row["pathId"] for row in scripts if row["name"] == "FakePeople_RU")
    ru = env.file.objects[ru_id].read_typetree()["m_Script"]
    story_ids = {row["pathId"] for row in scripts}
    generator = CheckedTypeTreeGenerator(EXPECTED_UNITY)
    generator.load_local_dll_folder(str(DEFAULT_GAME /
        "NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed"))
    env.typetree_generator = generator
    references, unreadable = [], []

    def walk(value, owner_id, owner_type):
        if isinstance(value, dict):
            if value.get("m_FileID") == 0 and value.get("m_PathID") in story_ids:
                references.append({"ownerPathId": owner_id, "ownerType": owner_type,
                                   "storyPathId": value["m_PathID"]})
            for child in value.values():
                walk(child, owner_id, owner_type)
        elif isinstance(value, (list, tuple)):
            for child in value:
                walk(child, owner_id, owner_type)

    for obj in env.objects:
        if obj.type.name == "TextAsset":
            continue
        try:
            tree = generated_tree(obj)[0] if obj.type.name == "MonoBehaviour" \
                   else obj.read_typetree()
        except (EOFError, ValueError) as error:
            unreadable.append({"pathId": obj.path_id, "type": obj.type.name,
                               "error": type(error).__name__})
            continue
        walk(tree, obj.path_id, obj.type.name)
    require(not references and
            {(row["pathId"], row["type"]) for row in unreadable} ==
            {(1449, "MonoBehaviour"), (1450, "MonoBehaviour")},
            "Embedded story reference or unreadable object scope changed")
    lines = []
    for raw in ru.splitlines():
        line = raw.strip()
        if "@@" in line:
            lines.append(line.split("@@", 1)[1].strip())
        elif "[[" in line and not line.startswith("::"):
            lines.append(re.sub(r"\s*\[\[[^]]+\]\]", "", line).strip())
    lines = [line for line in lines if line]
    table_sources = [json.loads(line)["source"] for line in STRINGS.open()]
    normalized = set(table_sources) | {line.split(": ", 1)[1] for line in table_sources
                                       if ": " in line}
    unmatched = [line for line in lines if line not in normalized]
    metadata_path = (DEFAULT_GAME / "NoImNotAHuman_Data/il2cpp_data/Metadata/"
                     "global-metadata.dat")
    metadata = metadata_path.read_bytes()
    result = {"schemaVersion": 2, "gameVersion": "1.3.19",
              "sourceFiles": source_files, "stringInventorySha256": digest(STRINGS),
              "textAssets": assets, "twineComponentsInSerializedAssets": twine_components,
              "serializedStoryReferencesInResources": references,
              "unreadableResourceObjects": unreadable,
              "russianEmbeddedStory": {"name": "FakePeople_RU", "pathId": ru_id,
                                        "dialogueAndChoiceLines": len(lines),
                                        "linesAbsentFromAnyStringTable": len(unmatched),
                                        "uniqueAbsentLines": len(set(unmatched))},
              "globalMetadataSha256": hashlib.sha256(metadata).hexdigest(),
              "literalFakePeopleNamesInGlobalMetadata": {
                  name: name.encode() in metadata for name in ("FakePeople_RU", "FakePeople_EN")},
              "conclusion": "Embedded Twine story appears to be a legacy source: no serialized DialogueTwine component, no readable serialized resource reference, and no literal story resource names in IL2CPP metadata. Two editor-related MonoBehaviours could not be parsed. Runtime reachability is still unverified; do not count its lines as accepted live-game coverage without a consumer path."}
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(OUTPUT.relative_to(ROOT)), "textAssets": len(assets),
                      "twineComponents": len(twine_components),
                      "storyLinesAbsentFromTables": len(unmatched)}))


if __name__ == "__main__":
    main()
