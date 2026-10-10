"""Verify all final translated values and all other serialized overlay fields."""

import argparse
import copy
import json
from collections import Counter, defaultdict
from pathlib import Path

import UnityPy

from addressables_catalog import update_bundle
from build_locale_text import authored_tables
from locale_text_inputs import accepted_inputs, project_path
from probe_assets import DEFAULT_GAME, EXPECTED_UNITY, ROOT, digest, require
from unity_types import CheckedTypeTreeGenerator, generated_tree


def verify(build, artifact_root=None, write=True):
    require(build.is_relative_to(ROOT / "outputs"), "Overlay escaped canonical outputs")
    artifact_root = build if artifact_root is None else artifact_root
    require(artifact_root.is_relative_to(ROOT / "outputs"), "Delivered artifacts escaped canonical outputs")
    report_path = build / "report.json"
    report = json.loads(report_path.read_text())
    locale = report["locale"]
    accepted_inputs(locale, project_path(report["semanticAcceptancePath"]), project_path(report["exactReportPath"]))
    require(report["semanticAcceptanceSha256"] == digest(project_path(report["semanticAcceptancePath"])) and
            report["exactReportSha256"] == digest(project_path(report["exactReportPath"])), "Overlay acceptance stale")
    base_report_path = project_path(report["baseReportPath"])
    base = base_report_path.parent
    require(digest(base_report_path) == report["baseReportSha256"], "Overlay base changed")
    _, targets, files = authored_tables(locale)
    static_path = ROOT / "Translations" / locale / "static-text-draft.json"
    require(files + [{"path": str(static_path.relative_to(ROOT)), "sha256": digest(static_path)}] == report["authoredFiles"],
            "Overlay authored pins changed")
    by_file = defaultdict(dict)
    for row in json.loads(static_path.read_text())["entries"]:
        _, name, object_id, field = row["stableId"].split(":")
        require(field == "m_text", "Unknown static field")
        by_file[name][int(object_id)] = row["target"]
    generator = CheckedTypeTreeGenerator(EXPECTED_UNITY)
    generator.load_local_dll_folder(str(DEFAULT_GAME / "NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed"))
    table_counts, static_counts = Counter(), Counter()
    unchanged_objects = original_text = changed_objects = 0
    for relative, details in report["artifacts"].items():
        delivered = artifact_root / relative
        require(delivered.resolve().is_relative_to(artifact_root) and digest(delivered) == details["sha256"], "Overlay hash differs")
        if relative.endswith("catalog.bin"):
            table_relative = next(r for r in report["artifacts"] if r.endswith("localization-string-tables-russian(ru)_assets_all.bundle"))
            expected, _ = update_bundle((base / relative).read_bytes(), base / table_relative, artifact_root / table_relative)
            require(delivered.read_bytes() == expected, "Overlay catalog edits exceed target bundle integrity")
            continue
        carrier = base / relative
        if not carrier.exists():
            carrier = DEFAULT_GAME / relative
        before, after = UnityPy.load(str(carrier)), UnityPy.load(str(delivered))
        old = {o.path_id: o for o in before.objects}
        new = {o.path_id: o for o in after.objects}
        require(set(old) == set(new), "Text overlay changed object IDs")
        filename = Path(relative).name
        if filename in by_file:
            schema_env = UnityPy.load(str(DEFAULT_GAME / relative))
            schema_env.typetree_generator = generator
        for object_id, original in old.items():
            target = new[object_id]
            require(original.type == target.type, "Object type changed")
            if filename in by_file and object_id in by_file[filename]:
                source_tree, schema = generated_tree(schema_env.file.objects[object_id])
                expected = copy.deepcopy(original.read_typetree(nodes=schema))
                expected["m_text"] = by_file[filename][object_id]
                if source_tree.get("originalText") is not None:
                    expected["originalText"] = by_file[filename][object_id]
                    original_text += 1
                require(target.read_typetree(nodes=schema) == expected, "Static object differs beyond selected text fields")
                static_counts[filename] += 1
                changed_objects += 1
            elif filename.endswith("localization-string-tables-russian(ru)_assets_all.bundle") and original.type.name == "MonoBehaviour" and original.peek_name() in {c + "_" + locale for c in targets}:
                expected = copy.deepcopy(original.read_typetree())
                collection = expected["m_Name"][:-(len(locale) + 1)]
                rows = {row["m_Id"]: row for row in expected["m_TableData"]}
                require(len(rows) == len(expected["m_TableData"]), "Duplicate carrier table IDs")
                for row_id, value in targets[collection].items():
                    rows[row_id]["m_Localized"] = value
                    table_counts[collection] += 1
                require(target.read_typetree() == expected, "Locale table differs beyond selected values")
                changed_objects += 1
            else:
                require(original.get_raw_data() == target.get_raw_data(), "Unselected original object changed: " + relative + ":" + str(object_id))
                unchanged_objects += 1
    require(dict(table_counts) == report["tableRows"] and sum(table_counts.values()) == 16360 and
            dict(static_counts) == report["staticRowsByFile"] and sum(static_counts.values()) == 178 and
            original_text == report["rtlOriginalTextRows"] == 165 and len(report["artifacts"]) == 10,
            "Serialized text coverage differs")
    result = {"schemaVersion": 1, "locale": locale, "reportSha256": digest(report_path),
              "verifierSha256": digest(Path(__file__)), "tableRowsCompared": 16360,
              "staticRowsCompared": 178, "rtlOriginalTextRowsCompared": 165,
              "artifactHashesCompared": 10, "unchangedObjectsCompared": unchanged_objects,
              "selectedObjectsAllOtherFieldsCompared": changed_objects,
              "catalogChange": "only translated carrier bundle integrity",
              "serializedValuesResult": "passed", "allOtherOverlayFieldsResult": "passed",
              "semanticReview": "accepted offline", "runtime": "not-run"}
    if write:
        output = build / "verification.json"
        require(not output.exists(), "Preserve previous overlay verification")
        output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    verify(parser.parse_args().build.resolve())
