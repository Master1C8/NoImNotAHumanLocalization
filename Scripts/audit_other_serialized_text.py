#!/usr/bin/env python3
"""Account for readable non-TMP MonoBehaviour strings in game source files."""

import json
import re
from collections import Counter

import UnityPy

from audit_all_static_text import FILES
from probe_assets import DEFAULT_GAME, EXPECTED_UNITY, ROOT, digest, require
from unity_types import CheckedTypeTreeGenerator, generated_tree


OUTPUT = ROOT / "Documentation/other-serialized-text-scope-v2.json"
TEXT_SCRIPTS = {(1, 2981), (1, 2283), (1, 1205)}
TECHNICAL_LEAVES = {
    "m_TargetAssemblyTypeName", "m_ObjectArgumentAssemblyTypeName", "m_Groups",
    "type", "m_FamilyName", "characterSequence", "m_DefaultControlScheme",
    "m_defaultFontAssetPath", "m_defaultSpriteAssetPath",
    "m_defaultColorGradientPresetsPath", "m_BindingGroup",
}
REVIEW_LEAVES = {"m_Name", "Name", "m_DisplayName", "name", "From", "To"}
CYRILLIC = re.compile("[А-Яа-яЁё]")
RAW_CYRILLIC = re.compile(rb"(?:[\xd0\xd1][\x80-\xbf]){2,}")


def main():
    require(not OUTPUT.exists(), "Preserve previous non-TMP string audit")
    generator = CheckedTypeTreeGenerator(EXPECTED_UNITY)
    generator.load_local_dll_folder(str(DEFAULT_GAME /
        "NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed"))
    candidates, unreadable, source_files = [], [], {}
    raw_cyrillic_hits = []
    for name in FILES:
        path = DEFAULT_GAME / "NoImNotAHuman_Data" / name
        source_files[str(path.relative_to(DEFAULT_GAME))] = digest(path)
        env = UnityPy.load(str(path))
        env.typetree_generator = generator

        def walk(value, owner_id, field):
            if isinstance(value, dict):
                for key, child in value.items():
                    walk(child, owner_id, field + "/" + key)
            elif isinstance(value, (list, tuple)):
                for index, child in enumerate(value):
                    walk(child, owner_id, field + "/" + str(index))
            elif (isinstance(value, str) and
                  (CYRILLIC.search(value) or
                   (len(value) >= 10 and len(value.split()) >= 2))):
                candidates.append({"file": name, "pathId": owner_id,
                                   "field": field, "value": value})

        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            head = obj.parse_monobehaviour_head()
            if (head.m_Script.m_FileID, head.m_Script.m_PathID) in TEXT_SCRIPTS:
                continue
            try:
                tree, _ = generated_tree(obj)
            except (EOFError, ValueError) as error:
                unreadable.append({"file": name, "pathId": obj.path_id,
                                   "error": type(error).__name__})
                for match in RAW_CYRILLIC.finditer(obj.get_raw_data()):
                    raw_cyrillic_hits.append({"file": name, "pathId": obj.path_id,
                                              "byteOffset": match.start()})
                continue
            walk(tree, obj.path_id, "")
    nontechnical = [row for row in candidates
                    if row["field"].rsplit("/", 1)[-1] not in TECHNICAL_LEAVES]
    unique = list({(row["field"].rsplit("/", 1)[-1], row["value"]): row
                   for row in nontechnical}.values())
    print(json.dumps({"candidateFields": len(candidates),
                      "nontechnicalFields": len(nontechnical),
                      "uniqueNontechnicalValues": len(unique)}))
    require(len(candidates) == 338 and len(unique) == 60 and
            not raw_cyrillic_hits and
            all(row["field"].rsplit("/", 1)[-1] in REVIEW_LEAVES
                for row in nontechnical) and
            all(row["field"].rsplit("/", 1)[-1] == "characterSequence"
                for row in candidates if CYRILLIC.search(row["value"])),
            "Non-TMP text candidate scope changed; review new fields")
    result = {"schemaVersion": 2, "gameVersion": "1.3.19",
              "sourceFiles": source_files,
              "candidateFields": len(candidates),
              "technicalFields": len(candidates) - len(nontechnical),
              "nontechnicalFields": len(nontechnical),
              "uniqueNontechnicalValues": len(unique),
              "unreadableComponents": unreadable,
              "rawCyrillicSpansInUnreadable": raw_cyrillic_hits,
              "candidateLeafCounts": dict(Counter(row["field"].rsplit("/", 1)[-1]
                                                for row in candidates)),
              "reviewRows": unique,
              "conclusion": "All readable non-TMP/non-legacy-UI candidate strings are metadata: technical identifiers, font glyph sequences, font/resource names, input scheme names and timeline names. No additional Russian display sentence was found. Unreadable components remain a source-scope limitation."}
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(OUTPUT.relative_to(ROOT)),
                      "candidateFields": len(candidates),
                      "reviewValues": len(unique),
                      "unreadableComponents": len(unreadable)}))


if __name__ == "__main__":
    main()
