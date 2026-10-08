#!/usr/bin/env python3
"""Verify the delivered Thai-only data, including the added locale boundaries."""

import argparse
import json
from pathlib import Path

import UnityPy

from addressables_catalog import Catalog
from probe_assets import DEFAULT_GAME, ROOT, digest, require
from unity_types import CheckedTypeTreeGenerator, generated_tree


def named_mono_objects(path):
    env = UnityPy.load(str(path))
    return {obj.peek_name(): obj for obj in env.objects
            if obj.type.name == "MonoBehaviour"}


def verify(package):
    require(package.is_relative_to(ROOT / "outputs"), "Package escaped outputs")
    report_path = package / "report.json"
    report = json.loads(report_path.read_text())
    require(report["locale"] == "th" and report["newLocaleCount"] == 1 and
            report["translatedTextValues"] == 16538 and
            report["rtlOriginalTextValues"] == 165 and
            len(report["artifacts"]) == 31, "Unexpected Thai package report")
    for relative, row in report["artifacts"].items():
        target = package / relative
        require(target.resolve().is_relative_to(package.resolve()) and
                digest(target) == row["sha256"], "Package hash mismatch: " + relative)
    prefix = "NoImNotAHuman_Data/StreamingAssets/aa/StandaloneWindows64/"
    locale_file = prefix + "localization-locales_assets_all.bundle"
    source_locales = set(named_mono_objects(DEFAULT_GAME / locale_file))
    target_locales = set(named_mono_objects(package / locale_file))
    require(target_locales - source_locales == {"Thai (th)"} and
            source_locales <= target_locales,
            "The delivered locale bundle adds more than Thai")
    shared_file = prefix + "localization-assets-shared_assets_all.bundle"
    source_ui = named_mono_objects(DEFAULT_GAME / shared_file)["UI Shared Data"].read_typetree()
    target_ui = named_mono_objects(package / shared_file)["UI Shared Data"].read_typetree()
    source_keys = {row["m_Key"] for row in source_ui["m_Entries"]}
    target_keys = {row["m_Key"] for row in target_ui["m_Entries"]}
    require(target_keys - source_keys == {"language_th"} and source_keys <= target_keys,
            "The delivered UI key set adds more than Thai")
    original_catalog = Catalog((DEFAULT_GAME / "NoImNotAHuman_Data/StreamingAssets/aa/catalog.bin").read_bytes())
    target_catalog = Catalog((package / "NoImNotAHuman_Data/StreamingAssets/aa/catalog.bin").read_bytes())
    require(len(target_catalog.keys()["Locale"]["locations"]) ==
            len(original_catalog.keys()["Locale"]["locations"]) + 1,
            "The delivered catalog added an unexpected locale count")
    generator = CheckedTypeTreeGenerator("6000.3.10f1")
    generator.load_local_dll_folder(str(DEFAULT_GAME /
        "NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed"))
    role_count = 0
    for name, objects in (("sharedassets0.assets", (2601,)),
                          ("resources.assets", (1453, 1454))):
        target = UnityPy.load(str(package / "NoImNotAHuman_Data" / name))
        source = UnityPy.load(str(DEFAULT_GAME / "NoImNotAHuman_Data" / name))
        target.typetree_generator = source.typetree_generator = generator
        for object_id in objects:
            original_tree, schema = generated_tree(source.file.objects[object_id])
            target_tree = target.file.objects[object_id].read_typetree(nodes=schema)
            original_roles = {row["Key"] for row in original_tree["<Fonts>k__BackingField"]["_serializedList"]}
            target_roles = {row["Key"] for row in target_tree["<Fonts>k__BackingField"]["_serializedList"]}
            require(target_roles - original_roles == {"th"} and
                    original_roles <= target_roles,
                    "A delivered font role adds more than Thai")
            role_count += 1
    result = {"schemaVersion": 1, "reportSha256": digest(report_path),
              "artifactHashesCompared": 31, "translatedTextValuesComparedByTextBuild": 16538,
              "newLocales": ["th"], "newUiKeys": ["language_th"],
              "fontRolesCompared": role_count, "result": "passed",
              "runtime": "separate fixture check required"}
    output = package / "verification.json"
    require(not output.exists(), "Preserve prior package verification")
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    args = parser.parse_args()
    verify(args.package.resolve())
