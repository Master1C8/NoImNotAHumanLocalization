"""Read back original objects and the exact additions in a single-locale base."""

import copy
import json

import UnityPy

from addressables_catalog import Catalog
from build_locale_probe import LANGUAGES, identity
from probe_assets import DEFAULT_GAME, EXPECTED_UNITY, ROOT, SAMPLES, UI_ID, digest, require
from unity_types import CheckedTypeTreeGenerator, generated_tree


def verify_native(base, locale):
    report = json.loads((base / "report.json").read_text())
    require(set(report["languages"]) == {locale} and report["sourceUnchanged"] is True, "Not an isolated native base")
    english, endonym = LANGUAGES[locale]
    key_id = identity("ui-key/language_" + locale)
    require(report["languageKeyIds"] == {locale: key_id}, "Unexpected locale key identity")
    generator = CheckedTypeTreeGenerator(EXPECTED_UNITY)
    generator.load_local_dll_folder(str(DEFAULT_GAME / "NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed"))
    count = new_count = 0
    added_names = set()
    for relative, item in report["artifacts"].items():
        require(digest(base / relative) == item["sha256"] and digest(DEFAULT_GAME / relative) == report["inputs"][relative],
                "Native/source artifact pin changed")
        if relative.endswith("catalog.bin"):
            continue
        before, after = UnityPy.load(str(DEFAULT_GAME / relative)), UnityPy.load(str(base / relative))
        old = {o.path_id: o for o in before.objects}
        new = {o.path_id: o for o in after.objects}
        require(set(old) <= set(new) and len(new) - len(old) == item["newObjects"], "Native object coverage differs")
        allowed = set(item["changedOriginalObjects"])
        filename = relative.rsplit("/", 1)[1]
        is_font = filename in ("sharedassets0.assets", "resources.assets")
        if is_font:
            before.typetree_generator = generator
        for object_id, obj in old.items():
            actual_obj = new[object_id]
            if object_id not in allowed:
                require(obj.get_raw_data() == actual_obj.get_raw_data(), "Original native object changed")
            elif is_font:
                expected, schema = generated_tree(obj)
                expected = copy.deepcopy(expected)
                role = {"th": 2611, "fa": 2605, "hi": 2614, "he": 900000}.get(locale, 2614)
                expected["<Fonts>k__BackingField"]["_serializedList"].append(
                    {"Key": locale, "Value": {"m_FileID": 0 if filename == "sharedassets0.assets" else 2, "m_PathID": role}})
                require(actual_obj.read_typetree(nodes=schema) == expected, "Original font-role fields changed beyond requested binding")
            else:
                expected = copy.deepcopy(obj.read_typetree())
                actual = actual_obj.read_typetree()
                if obj.type.name == "AssetBundle":
                    containers = dict(actual["m_Container"])
                    require(all(containers.get(name) == value for name, value in expected["m_Container"]), "Original bundle containers changed")
                    require(actual["m_PreloadTable"][:len(expected["m_PreloadTable"])] == expected["m_PreloadTable"], "Original bundle preloads changed")
                    for name, value in actual["m_Container"]:
                        if name not in dict(expected["m_Container"]):
                            clone_name = name.rsplit("/", 1)[1].removesuffix(".asset")
                            require(clone_name == f"{english} ({locale})" or clone_name.endswith("_" + locale), "Unexpected new locale container")
                            require(value["asset"] == {"m_FileID": 0, "m_PathID": identity(clone_name)}, "New container identity differs")
                    for field in ("m_Container", "m_PreloadTable"):
                        expected[field] = actual[field]
                elif expected.get("m_Name") == "UI Shared Data":
                    expected["m_Entries"].append({"m_Id": key_id, "m_Key": "language_" + locale, "m_Metadata": {"m_Items": []}})
                elif expected.get("m_Name", "").startswith("UI_"):
                    expected["m_TableData"].append({"m_Id": key_id, "m_Localized": endonym, "m_Metadata": {"m_Items": []}})
                else:
                    require(False, "Unexpected modified original native object")
                require(actual == expected, "Original native fields changed beyond permitted additions")
            count += 1
        expected_ids = set()
        if filename == "localization-locales_assets_all.bundle":
            sources = [o for o in old.values() if o.type.name == "MonoBehaviour" and o.peek_name() == "Russian (ru)"]
        elif filename == "localization-string-tables-russian(ru)_assets_all.bundle":
            sources = [o for o in old.values() if o.type.name == "MonoBehaviour"]
        elif filename == "localization-asset-tables-russian(ru)_assets_all.bundle":
            sources = [o for o in old.values() if o.type.name == "MonoBehaviour"]
        else:
            sources = []
        for obj in sources:
            expected = copy.deepcopy(obj.read_typetree())
            source_name = expected["m_Name"]
            if filename == "localization-locales_assets_all.bundle":
                name = f"{english} ({locale})"
                expected.update(m_Name=name, m_LocaleName=name, m_SortOrder=100)
                expected["m_Identifier"]["m_Code"] = locale
            else:
                name = source_name[:-2] + locale
                expected["m_Name"] = name
                expected["m_LocaleId"]["m_Code"] = locale
                if source_name == "UI_ru":
                    expected["m_TableData"].append({"m_Id": key_id, "m_Localized": endonym, "m_Metadata": {"m_Items": []}})
                    next(row for row in expected["m_TableData"] if row["m_Id"] == UI_ID)["m_Localized"] = SAMPLES[locale]
            path_id = identity(name)
            require(path_id in new and new[path_id].read_typetree() == expected, "New carrier differs from its exact Russian template")
            expected_ids.add(path_id)
            added_names.add(name)
        if locale == "he" and filename == "sharedassets0.assets":
            # Validate the separate font/atlas/material clone without changing originals.
            font, schema = generated_tree(old[2614])
            liberation, _ = generated_tree(old[2604])
            font = copy.deepcopy(font)
            font.update(m_Name="VN Probe LiberationSans Dynamic", m_FaceInfo=liberation["m_FaceInfo"],
                        m_SourceFontFile={"m_FileID": 0, "m_PathID": 1172}, m_SourceFontFileGUID=liberation["m_SourceFontFileGUID"])
            font["m_CreationSettings"]["sourceFontFileGUID"] = liberation["m_SourceFontFileGUID"]
            font["m_CreationSettings"]["pointSize"] = 86
            font["m_FontFeatureTable"] = {key: [] for key in font["m_FontFeatureTable"]}
            material_id = font["m_Material"]["m_PathID"]
            texture_id = font["m_AtlasTextures"][0]["m_PathID"]
            texture = old[texture_id].read_typetree()
            texture["m_Name"] = "VN Probe Hebrew Atlas"
            material = old[material_id].read_typetree()
            material["m_Name"] = "VN Probe Hebrew Material"
            for _, value in material["m_SavedProperties"]["m_TexEnvs"]:
                if value["m_Texture"] == {"m_FileID": 0, "m_PathID": texture_id}:
                    value["m_Texture"]["m_PathID"] = 900002
            font["m_Material"]["m_PathID"] = 900001
            font["m_AtlasTextures"][0]["m_PathID"] = 900002
            require(new[900000].read_typetree(nodes=schema) == font and new[900001].read_typetree() == material and
                    new[900002].read_typetree() == texture, "Hebrew font clone differs")
            expected_ids |= {900000, 900001, 900002}
        require(set(new) - set(old) == expected_ids, "Unexpected native new object IDs")
        new_count += len(expected_ids)
    catalog_relative = "NoImNotAHuman_Data/StreamingAssets/aa/catalog.bin"
    source_catalog = Catalog((DEFAULT_GAME / catalog_relative).read_bytes())
    target_catalog = Catalog((base / catalog_relative).read_bytes())
    source_keys, target_keys = source_catalog.keys(), target_catalog.keys()
    require(set(target_keys) - set(source_keys) == added_names | {"Locale-" + locale}, "Unexpected locale catalog keys")
    for key, details in source_keys.items():
        require(target_keys[key]["locations"][:len(details["locations"])] == details["locations"], "Original catalog locations changed")
    require(len(target_keys["Locale"]["locations"]) == len(source_keys["Locale"]["locations"]) + 1 and
            len(target_catalog.bundles()) == len(source_catalog.bundles()), "Catalog is not a single-locale extension")
    return {"originalNativeObjectsCompared": count, "newNativeObjectsCompared": new_count,
            "newLocale": locale, "newUiKey": "language_" + locale, "fontRolesCompared": 3,
            "catalogBoundary": "single locale; original location prefixes preserved", "result": "passed"}
