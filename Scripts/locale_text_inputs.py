"""Read-only acceptance and exact-ID gates shared by locale delivery tools."""

import json
import re
from collections import defaultdict
from pathlib import Path

from preserve_exact import MANIFEST, SCOPE, STATIC_SCOPE, check_value
from probe_assets import ROOT, digest, require
from report_locale_readiness import BATCH, selected_ids


def read(path):
    return json.loads(path.read_text())


def project_path(value):
    path = (ROOT / value).resolve()
    require(path.is_relative_to(ROOT), "Input escaped canonical checkout: " + value)
    return path


def checked_files(rows):
    result = {}
    for row in rows:
        path = project_path(row["path"])
        relative = str(path.relative_to(ROOT))
        require(relative not in result and digest(path) == row["sha256"],
                "Duplicate or stale pinned input: " + relative)
        result[relative] = row["sha256"]
    return result


def current_text(locale, require_sidecars=True, directory=None):
    selected, strings_hash, static_hash = selected_ids()
    manifest = read(MANIFEST)
    require(manifest["sourceInventorySha256"] == strings_hash and
            manifest["staticInventorySha256"] == static_hash and
            manifest["sourceScopeReportSha256"] == digest(SCOPE) and
            manifest["staticScopeSha256"] == digest(STATIC_SCOPE), "Exact source contract changed")
    rules = {(r.get("collection", "static"), r["stableId"] if "collection" not in r
              else int(r["stableId"].rsplit(":", 1)[1])): r
             for r in manifest["tableRows"] + manifest["staticRows"]}
    require(set(rules) == {(c, key) for c, keys in selected.items() for key in keys},
            "Exact contract differs from accepted ID scope")
    state = read(ROOT / "Documentation/localization-state.json")
    roster = next(r for r in state["localeRows"] if r["locale"] == locale)
    source = [json.loads(line) for line in (ROOT / "Source/localization-inventory-v3/strings.jsonl").open()]
    positions = defaultdict(dict)
    for row in source:
        collection = row["collection"]
        positions[collection][int(row["stableId"].rsplit(":", 1)[1])] = len(positions[collection])
    directory = ROOT / "Translations" / locale if directory is None else directory.resolve()
    require(directory.is_relative_to(ROOT), "Text corpus escaped canonical checkout")
    paths = sorted(p for p in directory.glob("*.json") if BATCH.fullmatch(p.name))
    paths.append(directory / "static-text-draft.json")
    values, files = {}, []
    for path in paths:
        data = read(path)
        collection = "static" if path.name == "static-text-draft.json" else data["collection"]
        require(data["schemaVersion"] == 1 and data["locale"] == locale and
                data["gameVersion"] == state["gameVersion"] and data["sourceLocale"] == state["sourceLocale"] and
                data["glossaryFingerprint"] == roster["glossaryFingerprint"], "Authored identity differs: " + str(path))
        field = "sourceInventoryStaticSha256" if collection == "static" else "sourceInventorySha256"
        require(data[field] == (static_hash if collection == "static" else strings_hash), "Authored source changed")
        require(collection in selected, "Unknown collection")
        order = []
        for entry in data["entries"]:
            key = entry["stableId"] if collection == "static" else entry["id"]
            if collection != "static":
                require(type(key) is int, "Noninteger table ID")
                order.append(positions[collection].get(key, -1))
            identity = (collection, key)
            require(key in selected[collection] and identity not in values, "Unknown or duplicate accepted ID")
            check_value(rules[identity], entry["target"])
            values[identity] = entry["target"]
        require(order == sorted(order), "Authored entries out of source order")
        if collection == "static":
            require(data["coverage"] == "all-nonempty-unbound-v2" and
                    data["staticScopeSha256"] == digest(STATIC_SCOPE), "Static scope incomplete or stale")
        file_hash = digest(path)
        if require_sidecars:
            receipt = read(path.with_suffix(".validation.json"))
            require(receipt["locale"] == locale and receipt["structuralResult"] == "passed" and
                    receipt.get("batchSha256", receipt.get("draftSha256")) == file_hash and
                    receipt.get("authoredRows", receipt.get("rows")) == len(data["entries"]),
                    "Current structural receipt missing: " + str(path))
        files.append({"path": str(path.relative_to(ROOT)), "sha256": file_hash})
    require(set(values) == set(rules) and len(values) == 16538, "Incomplete accepted target coverage")
    # Credits derive from authored roles rather than a separately edited full block.
    credits = read(directory / "credits-role-map.json")
    require(credits["schemaVersion"] == 1 and credits["stableId"] == "tmp:level5:59:m_text" and
            credits["sourceInventoryStaticSha256"] == static_hash, "Credits source identity differs")
    pairs = credits["replacements"]
    replacements = {row["source"]: row["target"] for row in pairs}
    require(len(replacements) == len(pairs) and all(replacements) and all(replacements.values()), "Invalid credits roles")
    original = next(json.loads(line)["source"] for line in
                    (ROOT / "Source/localization-inventory-v3/static-text.jsonl").open()
                    if json.loads(line)["stableId"] == credits["stableId"])
    require(all(phrase in original for phrase in replacements), "Credits phrase absent from source")
    pattern = re.compile("|".join(re.escape(s) for s in sorted(replacements, key=len, reverse=True)))
    require(pattern.sub(lambda m: replacements[m.group()], original) == values[("static", credits["stableId"])],
            "Credits derivation differs from final target")
    from localization_mechanics import verify
    mechanics_files = verify(locale, values, directory)
    files.extend({"path": str(path.relative_to(ROOT)), "sha256": digest(path)} for path in mechanics_files)
    return values, files


def accepted_inputs(locale, acceptance_path, exact_path):
    require(acceptance_path.is_relative_to(ROOT) and exact_path.is_relative_to(ROOT), "Evidence escaped canonical checkout")
    acceptance, exact = read(acceptance_path), read(exact_path)
    require(exact["locale"] == locale and exact["exactResult"] == "passed" and exact["checkedRows"] == 16538 and
            exact["manifestSha256"] == digest(MANIFEST), "Exact report missing or stale")
    if locale == "th":
        require(acceptance_path == ROOT / "Documentation/th-semantic-acceptance-v2.json" and
                acceptance["status"] == "Thai text editorially accepted offline; runtime and visual QA pending" and
                acceptance["acceptedSourceRows"] == acceptance["firstSemanticPassRows"] == 16538,
                "Pinned Thai acceptance differs")
    else:
        require(acceptance["locale"] == locale and acceptance["status"] == "text editorially accepted offline" and
                acceptance["acceptedUnits"] == acceptance["firstSemanticPassUnits"] == 16538 and
                acceptance["independentClean"] is True and acceptance["structuralRows"] == 16538 and
                acceptance["derivedStaticRows"] == 178 and acceptance["mandatoryRegression"]["result"] == "passed",
                "Locale editorial acceptance incomplete")
        regression = acceptance["mandatoryRegression"]
        require(regression["count"] == regression["freshReads"] + regression["reusedUnchangedIndependentDecisions"],
                "Mandatory independent regression coverage incomplete")
    require(acceptance["unresolvedObjectiveFindings"] == 0 and
            acceptance["inputSha256"][str(exact_path.relative_to(ROOT))] == digest(exact_path), "Semantic/exact pin differs")
    for relative, expected in acceptance["inputSha256"].items():
        require(digest(project_path(relative)) == expected, "Acceptance evidence changed: " + relative)
    _, current_files = current_text(locale)
    pinned = checked_files(exact["inputFiles"])
    require({r["path"]: r["sha256"] for r in current_files} == pinned,
            "Authored input set changed after exact/semantic gate")
    for field, relative in (("sourceInventorySha256", "Source/localization-inventory-v3/strings.jsonl"),
                            ("staticInventorySha256", "Source/localization-inventory-v3/static-text.jsonl")):
        require(exact[field] == digest(ROOT / relative), "Exact inventory pin differs")
    return acceptance, exact, pinned
