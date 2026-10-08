#!/usr/bin/env python3
"""Verify every translated value in the serialized Thai draft artifacts."""

import argparse
import json
from collections import Counter
from pathlib import Path

import UnityPy

from build_th_text_draft import DEFAULT_OUTPUT, authored_tables
from probe_assets import DEFAULT_GAME, EXPECTED_UNITY, ROOT, digest, require
from unity_types import CheckedTypeTreeGenerator, generated_tree


def main(build):
    require(build.is_relative_to(ROOT / "outputs"), "Build must be in canonical outputs")
    report_path = build / "report.json"
    report = json.loads(report_path.read_text())
    require(report["status"].startswith("isolated Thai text draft"),
            "Not a Thai draft build")
    require(report["semanticReview"] == "accepted offline" and
            report["semanticAcceptanceSha256"] == digest(
                ROOT / "Documentation/th-semantic-acceptance-v2.json"),
            "Build is not pinned to accepted Thai text")
    for relative, row in report["artifacts"].items():
        require(digest(build / relative) == row["sha256"],
                "Delivered artifact hash changed: " + relative)
    _, target, _ = authored_tables()
    table_path = next(build / relative for relative in report["artifacts"]
                      if relative.endswith("localization-string-tables-russian(ru)_assets_all.bundle"))
    env = UnityPy.load(str(table_path))
    found = Counter()
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        tree = obj.read_typetree()
        name = tree.get("m_Name", "")
        if not name.endswith("_th") or name[:-3] not in target:
            continue
        collection = name[:-3]
        actual = {row["m_Id"]: row["m_Localized"] for row in tree["m_TableData"]}
        for row_id, value in target[collection].items():
            require(actual.get(row_id) == value,
                    "Delivered Thai table value differs: " + collection + ":" + str(row_id))
            found[collection] += 1
    require(dict(found) == report["tableRows"], "Delivered table coverage changed")

    generator = CheckedTypeTreeGenerator(EXPECTED_UNITY)
    generator.load_local_dll_folder(str(DEFAULT_GAME /
        "NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed"))
    static = json.loads((ROOT / "Translations/th/static-text-draft.json").read_text())
    by_file = {}
    for row in static["entries"]:
        _, name, object_id, field = row["stableId"].split(":")
        require(field == "m_text", "Unexpected static field")
        by_file.setdefault(name, {})[int(object_id)] = row["target"]
    static_found = Counter()
    rtl_found = 0
    for name, expected in sorted(by_file.items()):
        env = UnityPy.load(str(build / "NoImNotAHuman_Data" / name))
        env.typetree_generator = generator
        source_env = UnityPy.load(str(DEFAULT_GAME / "NoImNotAHuman_Data" / name))
        source_env.typetree_generator = generator
        for object_id, value in expected.items():
            source_tree, schema = generated_tree(source_env.file.objects[object_id])
            tree = env.file.objects[object_id].read_typetree(nodes=schema)
            require(tree["m_text"] == value,
                    "Delivered Thai static value differs: " + name + ":" + str(object_id))
            if source_tree.get("originalText") is not None:
                require(tree.get("originalText") == value,
                        "Delivered Thai RTL originalText differs: " + name + ":" + str(object_id))
                rtl_found += 1
            static_found[name] += 1
    require(dict(static_found) == report["staticRowsByFile"],
            "Delivered static coverage changed")
    require(rtl_found == report["rtlOriginalTextRows"],
            "Delivered RTL originalText coverage changed")
    result = {"schemaVersion": 1, "reportSha256": digest(report_path),
              "verifierSha256": digest(Path(__file__)),
              "tableRowsCompared": sum(found.values()),
              "staticRowsCompared": sum(static_found.values()),
              "rtlOriginalTextRowsCompared": rtl_found,
              "artifactHashesCompared": len(report["artifacts"]),
              "serializedValuesResult": "passed",
              "semanticReview": "accepted offline", "runtime": "not-run"}
    output = build / "verification.json"
    require(not output.exists(), "Preserve previous artifact verification")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    main(args.build.resolve())
