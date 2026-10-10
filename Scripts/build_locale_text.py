#!/usr/bin/env python3
"""Build one accepted locale text overlay without editing the original game."""

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import UnityPy

from addressables_catalog import Catalog, update_bundle
from build_locale_probe import LANGUAGES, save_verified
from locale_text_inputs import accepted_inputs
from probe_assets import DEFAULT_GAME, EXPECTED_UNITY, ROOT, UI_ID, digest, require
from unity_types import CheckedTypeTreeGenerator, generated_tree


STRINGS = ROOT / "Source/localization-inventory-v3/strings.jsonl"
STATIC = ROOT / "Source/localization-inventory-v3/static-text.jsonl"
STATIC_SCOPE = ROOT / "Documentation/static-text-scope-v2.json"
MANIFEST = ROOT / "Source/preserve-exactly-v4.json"
COLLECTIONS = {"UI": 259, "Dialogs": 16100, "ChecksDialogs": 1}


def authored_tables(locale):
    source = {}
    for line in STRINGS.open():
        row = json.loads(line)
        source[(row["collection"], int(row["stableId"].rsplit(":", 1)[1]))] = row["source"]
    target = defaultdict(dict)
    files = []
    for path in sorted((ROOT / "Translations" / locale).glob("*batch-*.json")):
        if not re.fullmatch(r"(?:ui|dialogue|checks)-batch-\d{3}\.json", path.name):
            continue
        batch = json.loads(path.read_text())
        collection = batch["collection"]
        require(collection in COLLECTIONS and batch["locale"] == locale and
                batch["sourceInventorySha256"] == digest(STRINGS),
                "Locale batch source identity differs")
        for entry in batch["entries"]:
            key = (collection, entry["id"])
            require(key in source and entry["id"] not in target[collection],
                    "Unknown or duplicate Locale table ID")
            target[collection][entry["id"]] = entry["target"]
        files.append({"path": str(path.relative_to(ROOT)), "sha256": digest(path)})
    require({name: len(values) for name, values in target.items()} == COLLECTIONS,
            "Locale table draft count changed")
    return source, target, files


def build(locale, output, base, acceptance_path, exact_path):
    require(UnityPy.__version__ == "1.25.4", "Unexpected UnityPy serialization version")
    acceptance, exact, pinned_files = accepted_inputs(locale, acceptance_path, exact_path)
    require(output.is_relative_to(ROOT / "outputs") and not output.exists(),
            "Output must be a new directory in canonical outputs")
    require(base.is_relative_to(ROOT / "outputs"), "Base must be in canonical outputs")
    base_report = json.loads((base / "report.json").read_text())
    base_languages = set(base_report["languages"])
    require(base_languages == {locale}, "Native base must add exactly the requested locale")
    for relative, item in base_report["artifacts"].items():
        require(digest(base / relative) == item["sha256"], "Native artifact changed: " + relative)
    for relative, expected in base_report["inputs"].items():
        require(digest(DEFAULT_GAME / relative) == expected, "Original game changed: " + relative)
    static_path = ROOT / "Translations" / locale / "static-text-draft.json"
    source, target, authored_files = authored_tables(locale)
    require({item["path"]: item["sha256"] for item in authored_files +
             [{"path": str(static_path.relative_to(ROOT)), "sha256": digest(static_path)}]} == pinned_files,
            "Acceptance/exact report does not pin the complete current authored file set")
    static_source = {row["stableId"]: row["source"] for row in
                     (json.loads(line) for line in STATIC.open())}
    static_roles = {row["stableId"]: row for row in json.loads(STATIC_SCOPE.read_text())["rows"]}
    static_draft = json.loads(static_path.read_text())
    require(static_draft["staticScopeSha256"] == digest(STATIC_SCOPE),
            "Static source roles changed")
    require(static_draft["coverage"] == "all-nonempty-unbound-v2" and
            len(static_draft["entries"]) == 178, "Static draft coverage changed")
    static_by_file = defaultdict(dict)
    for row in static_draft["entries"]:
        stable_id = row["stableId"]
        require(stable_id in static_source, "Unknown static text source")
        _, name, object_id, field = stable_id.split(":")
        require(field == "m_text" and int(object_id) not in static_by_file[name],
                "Duplicate static text target")
        static_by_file[name][int(object_id)] = (
            static_source[stable_id], row["target"], static_roles[stable_id]["originalText"])

    source_inputs = dict(base_report["inputs"])
    for name in static_by_file:
        relative = str(Path("NoImNotAHuman_Data") / name)
        current = digest(DEFAULT_GAME / relative)
        require(relative not in source_inputs or source_inputs[relative] == current,
                "Original static asset differs from native base")
        source_inputs[relative] = current

    output.mkdir(parents=True)
    artifacts = {}
    table_relative = Path("NoImNotAHuman_Data/StreamingAssets/aa/StandaloneWindows64/"
                          "localization-string-tables-russian(ru)_assets_all.bundle")
    table_source = base / table_relative
    env = UnityPy.load(str(table_source))
    before = {obj.path_id: obj.get_raw_data() for obj in env.objects}
    allowed = set()
    russian = {}
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        tree = obj.read_typetree()
        if tree.get("m_Name", "").endswith("_ru"):
            russian[tree["m_Name"][:-3]] = {
                row["m_Id"]: row["m_Localized"] for row in tree["m_TableData"]}
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        tree = obj.read_typetree()
        name = tree.get("m_Name", "")
        if not name.endswith("_" + locale) or name[:-(len(locale) + 1)] not in target:
            continue
        collection = name[:-(len(locale) + 1)]
        entries = {row["m_Id"]: row for row in tree["m_TableData"]}
        require(set(target[collection]) <= set(entries) and
                set(target[collection]) <= set(russian[collection]),
                "Missing Locale or Russian carrier ID: " + collection)
        for row_id, value in target[collection].items():
            require(russian[collection][row_id] == source[(collection, row_id)],
                    "Original Russian table text differs: " + collection + ":" + str(row_id))
            if entries[row_id]["m_Localized"] != source[(collection, row_id)]:
                require(collection == "UI" and row_id == UI_ID,
                        "Unexpected carrier text: " + collection + ":" + str(row_id))
            entries[row_id]["m_Localized"] = value
        obj.save_typetree(tree)
        allowed.add(obj.path_id)
    require(len(allowed) == 3, "Locale table objects not found")
    table_dest = output / table_relative
    artifacts[str(table_relative)] = save_verified(env, table_dest,
        {"original": before, "allowed": allowed})
    catalog_relative = Path("NoImNotAHuman_Data/StreamingAssets/aa/catalog.bin")
    catalog_source = base / catalog_relative
    new_catalog, catalog_integrity = update_bundle(catalog_source.read_bytes(),
                                                    table_source, table_dest)
    catalog_dest = output / catalog_relative
    catalog_dest.parent.mkdir(parents=True, exist_ok=True)
    catalog_dest.write_bytes(new_catalog)
    require(len(Catalog(new_catalog).bundles()) ==
            len(Catalog(catalog_source.read_bytes()).bundles()),
            "Addressables bundle count changed")
    artifacts[str(catalog_relative)] = {"sha256": digest(catalog_dest),
                                         "bundleIntegrity": catalog_integrity}

    generator = CheckedTypeTreeGenerator(EXPECTED_UNITY)
    generator.load_local_dll_folder(str(DEFAULT_GAME /
        "NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed"))
    static_counts = Counter()
    for name, rows in sorted(static_by_file.items()):
        relative = Path("NoImNotAHuman_Data") / name
        original = base / relative
        if not original.exists():
            original = DEFAULT_GAME / relative
        env = UnityPy.load(str(original))
        env.typetree_generator = generator
        schema_env = None
        if original != DEFAULT_GAME / relative:
            schema_env = UnityPy.load(str(DEFAULT_GAME / relative))
            schema_env.typetree_generator = generator
        before = {obj.path_id: obj.get_raw_data() for obj in env.objects}
        for object_id, (expected, value, original_text) in rows.items():
            obj = env.file.objects.get(object_id)
            require(obj is not None and obj.type.name == "MonoBehaviour",
                    "Static TMP object missing")
            if schema_env is None:
                tree, schema = generated_tree(obj)
            else:
                source_obj = schema_env.file.objects.get(object_id)
                require(source_obj is not None, "Source schema object missing")
                source_tree, schema = generated_tree(source_obj)
                require(source_tree["m_text"] == expected,
                        "Original static text differs from pinned source")
                tree = obj.read_typetree(nodes=schema)
            require(tree["m_text"] == expected,
                    "Static source text differs: " + name + ":" + str(object_id))
            tree["m_text"] = value
            if original_text is not None:
                require(tree.get("originalText") == original_text,
                        "RTL originalText differs: " + name + ":" + str(object_id))
                tree["originalText"] = value
            obj.save_typetree(tree, nodes=schema)
            static_counts[name] += 1
        artifacts[str(relative)] = save_verified(env, output / relative,
            {"original": before, "allowed": set(rows)})
    require(sum(static_counts.values()) == 178, "Static text write count changed")
    accepted_inputs(locale, acceptance_path, exact_path)
    for relative, expected in source_inputs.items():
        require(digest(DEFAULT_GAME / relative) == expected, "Original game changed during overlay build")
    for item in authored_files:
        require(any(row["path"] == item["path"] and row["sha256"] == item["sha256"]
                    for row in exact["inputFiles"]),
                "Authored table batch changed after exact gate")
    report = {"schemaVersion": 1, "status": "isolated accepted locale text overlay; runtime not tested",
              "locale": locale, "builderSha256": digest(Path(__file__)),
              "semanticAcceptancePath": str(acceptance_path.relative_to(ROOT)),
              "exactReportPath": str(exact_path.relative_to(ROOT)),
              "baseReportSha256": digest(base / "report.json"),
              "baseReportPath": str((base / "report.json").relative_to(ROOT)),
              "baseLanguages": sorted(base_languages),
              "exactReportSha256": digest(exact_path),
              "semanticAcceptanceSha256": digest(acceptance_path),
              "sourceInventorySha256": digest(STRINGS),
              "staticInventorySha256": digest(STATIC),
              "staticScopeSha256": digest(STATIC_SCOPE),
              "rtlOriginalTextRows": sum(1 for rows in static_by_file.values()
                                          for _, _, original in rows.values()
                                          if original is not None),
              "authoredFiles": authored_files + [{"path": str(static_path.relative_to(ROOT)),
                                                  "sha256": digest(static_path)}],
              "tableRows": dict(COLLECTIONS), "staticRowsByFile": dict(static_counts),
              "artifacts": artifacts,
              "sourceGameUnchanged": True,
              "sourceGameInputs": source_inputs,
              "runtime": "not-run", "semanticReview": "accepted offline"}
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"report": str((output / "report.json").relative_to(ROOT)),
                      "tableRows": sum(COLLECTIONS.values()),
                      "staticRows": sum(static_counts.values()),
                      "artifacts": len(artifacts)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("locale", choices=sorted(LANGUAGES))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--acceptance", type=Path, required=True)
    parser.add_argument("--exact", type=Path, required=True)
    args = parser.parse_args()
    build(args.locale, args.output.resolve(), args.base.resolve(), args.acceptance.resolve(), args.exact.resolve())
