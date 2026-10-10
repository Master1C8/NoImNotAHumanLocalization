#!/usr/bin/env python3
"""Build or verify immutable Hungarian correction-closure evidence.

The selector specification, canonical inventories, first-pass segments and
current authored files are the only inputs. This script never generates
translation wording and never reviews semantics on behalf of a reviewer.
"""

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
LOCALE = ROOT / "Translations/hu"
OUT = HERE / "evidence"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def data(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def jsonl(values):
    return "".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n"
                   for x in values).encode()


def id_bytes(ids):
    return "".join(x + "\n" for x in ids).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def rel(path):
    return str(path.relative_to(ROOT))


def batch_files():
    pattern = re.compile(r"(?:dialogue|ui|checks)-batch-\d{3}\.json$")
    return sorted(p for p in LOCALE.glob("*-batch-*.json") if pattern.fullmatch(p.name))


def stable_id(batch, entry):
    guid = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
            "UI": "0cbd8a7a4f543344bb95659de87f67a5",
            "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}[batch["collection"]]
    return "string:" + guid + ":" + str(entry["id"])


def corpus():
    plan = json.loads((HERE / "adjudicated-plan.json").read_text())
    first = json.loads((LOCALE / "semantic-review-progress.json").read_text())
    spec = json.loads((HERE / "closure-selector-spec.json").read_text())
    preserve = json.loads((ROOT / "Source/preserve-exactly-v4.json").read_text())
    accepted = preserve["tableRows"] + preserve["staticRows"]
    order = [row["stableId"] for row in accepted]
    require(len(order) == len(set(order)) == 16538, "Accepted ID set differs")
    accepted_set = set(order)
    require(plan["firstPassProgressSha256"] == digest(LOCALE / "semantic-review-progress.json") and
            plan["preserveExactManifestSha256"] == digest(ROOT / "Source/preserve-exactly-v4.json") and
            plan["sourceInventorySha256"] == digest(ROOT / "Source/localization-inventory-v3/strings.jsonl") and
            plan["staticInventorySha256"] == digest(ROOT / "Source/localization-inventory-v3/static-text.jsonl") and
            plan["approvedGlossaryLayerSha256"] == digest(ROOT / "Documentation/glossary-translations/hu/layer.json") and
            plan["canonicalGlossarySha256"] == digest(Path("/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary.json")),
            "Pinned source/glossary/first-pass inputs changed")
    source = {x["stableId"]: x for path in
              (ROOT / "Source/localization-inventory-v3/strings.jsonl",
               ROOT / "Source/localization-inventory-v3/static-text.jsonl")
              for x in (json.loads(line) for line in path.open()) if x["stableId"] in accepted_set}
    before = {}
    ordinal = 0
    for segment_ref in first["segments"]:
        segment_path = ROOT / segment_ref["path"]
        require(digest(segment_path) == segment_ref["sha256"], "First-pass segment changed")
        segment = json.loads(segment_path.read_text())
        require(segment["firstOrdinal"] == ordinal and
                segment["reviewedUnits"] == len(segment["rows"]), "First-pass ordinal gap")
        for row in segment["rows"]:
            sid = row["stableId"]
            require(sid == order[ordinal] and row["ordinal"] == ordinal and
                    row["source"] == source[sid]["source"], "First-pass row alignment changed")
            before[sid] = row["target"]
            ordinal += 1
    require(ordinal == 16538 and len(before) == 16538, "First-pass review incomplete")
    after = {}
    files = {}
    for path in batch_files():
        batch = json.loads(path.read_text())
        files[rel(path)] = digest(path)
        sidecar = path.with_suffix(".validation.json")
        check = json.loads(sidecar.read_text())
        require(check["batchSha256"] == files[rel(path)] and
                check["structuralResult"] == "passed", "Current batch validation stale: " + rel(path))
        for entry in batch["entries"]:
            sid = stable_id(batch, entry)
            require(sid not in after, "Current duplicate ID: " + sid)
            after[sid] = {"target": entry["target"], "authoredFile": rel(path)}
    static_path = LOCALE / "static-text-draft.json"
    static = json.loads(static_path.read_text())
    files[rel(static_path)] = digest(static_path)
    for entry in static["entries"]:
        sid = entry["stableId"]
        require(sid not in after, "Current duplicate static ID: " + sid)
        after[sid] = {"target": entry["target"], "authoredFile": rel(static_path)}
    require(set(after) == set(order), "Current accepted ID set differs")
    changed = [sid for sid in order if before[sid] != after[sid]["target"]]
    planned = [row["stableId"] for row in plan["rows"]]
    require(changed == planned and len(changed) == 118, "Actual correction delta differs")
    for row in plan["rows"]:
        sid = row["stableId"]
        require(row["currentTarget"] == before[sid] and
                row["finalTarget"] == after[sid]["target"] and
                row["source"] == source[sid]["source"], "Before/after values differ: " + sid)
    return plan, first, spec, preserve, order, source, before, after, files


def evidence():
    plan, first, spec, preserve, order, source, before, after, files = corpus()
    ordinal = {sid: i for i, sid in enumerate(order)}
    changed = {row["stableId"] for row in plan["rows"]}
    rules = {row["stableId"]: row for row in preserve["tableRows"] + preserve["staticRows"]}
    nodes = {node for row in plan["rows"] for node in row["nodeNames"]}
    groups = defaultdict(set)
    scene = set()
    for sid in order:
        src = source[sid]
        key = src.get("key") or ""
        row_nodes = set(src.get("nodeNames") or [])
        for node in sorted(nodes & row_nodes):
            groups["node:" + node].add(sid)
            scene.add(sid)
        for family in spec["sceneSelection"]["fallbackChangedKeyFamilies"]:
            if key.startswith("line:" + family + "_"):
                groups["fallback:" + family].add(sid)
                scene.add(sid)
        for family in spec["sceneSelection"]["uiKeyFamilies"]:
            if key.startswith(family):
                groups["ui:" + family].add(sid)
                scene.add(sid)
        for family in spec["sceneSelection"]["relatedBranchPrefixes"]:
            if any(n.startswith(family) for n in row_nodes) or key.startswith("line:" + family):
                groups["branch:" + family].add(sid)
                scene.add(sid)
    # A changed row can have incomplete Yarn metadata; the source-key fallback
    # above supplies its branch. Every changed ID must belong to a context group.
    require(changed <= scene, "A corrected ID lacks containing scene/UI context")
    source_values = {source[sid]["source"] for sid in changed}
    old_values = {before[sid] for sid in changed}
    new_values = {after[sid]["target"] for sid in changed}
    repetitions = {sid for sid in order if source[sid]["source"] in source_values or
                   before[sid] in old_values or after[sid]["target"] in new_values}
    selectors = {}
    terms = set()
    for item in spec["glossaryAndReferentSelectors"]:
        sr = re.compile(item["sourceRegex"], re.I)
        tr = re.compile(item["targetRegex"], re.I)
        ids = {sid for sid in order if sr.search(source[sid]["source"]) or
               tr.search(before[sid]) or tr.search(after[sid]["target"])}
        require(ids, "Empty term selector: " + item["id"])
        selectors[item["id"]] = ids
        terms |= ids
    runtime_templates = [sid for sid in order if rules[sid]["formatSlots"] and sid in scene]
    name_domain = [sid for sid in order if (source[sid].get("key") or "").startswith("characterName_")]
    item_pattern = re.compile(r"(?:FridgeItem_[A-Za-z]+_Name|consumable_[a-z]+_name)$")
    item_domain = [sid for sid in order if item_pattern.fullmatch(source[sid].get("key") or "")]
    require(len(runtime_templates) == 8 and len(name_domain) == 57 and len(item_domain) == 10,
            "Dynamic consumer topology or candidate domain changed")
    runtime = set(runtime_templates + name_domain + item_domain)
    regressions = {}
    regressions["ui-menu-hud-title-locale-save-input-environment"] = {
        sid for sid in order if rules[sid].get("collection") == "UI"}
    regressions["accepted-checks"] = {
        sid for sid in order if rules[sid].get("collection") == "ChecksDialogs"}
    regressions["static-tmp-credits-environment"] = {
        sid for sid in order if sid.startswith("tmp:")}
    technical = spec["mandatoryRegressionCatalog"]["technicalManifestFields"]
    regressions["placeholders-markup-numbers-linebreak-exact-symbols"] = {
        sid for sid in order if any(rules[sid][field] for field in technical)}
    kinship = re.compile(spec["mandatoryRegressionCatalog"]["kinshipSourceRegex"], re.I)
    profession = re.compile(spec["mandatoryRegressionCatalog"]["professionTitleSourceRegex"], re.I)
    regressions["gender-kinship-address"] = {
        sid for sid in order if kinship.search(source[sid]["source"]) or
        profession.search(source[sid]["source"])}
    prefixes = {}
    for sid in order:
        prefix = rules[sid]["speakerPrefix"]
        if prefix and prefix not in prefixes:
            prefixes[prefix] = sid
    regressions["speaker-label-representatives"] = set(prefixes.values())
    mandatory = set().union(*regressions.values())
    components = {"changed": changed, "sceneContext": scene,
                  "repetitions": repetitions, "glossaryReferents": terms,
                  "runtimeBinding": runtime, "mandatoryRegression": mandatory}
    closure = set().union(*components.values())

    result = {}
    for name, members in components.items():
        result[name + "-ids.txt"] = id_bytes(sid for sid in order if sid in members)
    result["closure-ids.txt"] = id_bytes(sid for sid in order if sid in closure)
    group_rows = []
    for name, members in sorted(groups.items()):
        ids = [sid for sid in order if sid in members]
        group_rows.append({"group": name, "count": len(ids), "idListSha256": sha(id_bytes(ids)), "ids": ids})
    result["scene-groups.json"] = data({"schemaVersion": 1, "locale": "hu",
                                       "groups": group_rows})
    selector_rows = []
    for item in spec["glossaryAndReferentSelectors"]:
        ids = [sid for sid in order if sid in selectors[item["id"]]]
        selector_rows.append({**item, "count": len(ids), "idListSha256": sha(id_bytes(ids)), "ids": ids})
    result["glossary-referent-selectors.json"] = data({"schemaVersion": 1, "locale": "hu",
                                                     "selectors": selector_rows})
    regression_rows = []
    for name, members in regressions.items():
        ids = [sid for sid in order if sid in members]
        regression_rows.append({"category": name, "count": len(ids),
                                "idListSha256": sha(id_bytes(ids)), "ids": ids,
                                "reviewStatus": "pending independent semantic review"})
    result["mandatory-regression-catalog.json"] = data({
        "schemaVersion": 1, "locale": "hu", "scope": spec["mandatoryRegressionCatalog"],
        "categories": regression_rows, "unionCount": len(mandatory),
        "unionIdListSha256": sha(result["mandatoryRegression-ids.txt"])})

    domain = [{"stableId": sid, "key": source[sid]["key"],
               "source": source[sid]["source"], "target": after[sid]["target"]}
              for sid in name_domain]
    result["resident-name-domain.json"] = data({"schemaVersion": 1, "locale": "hu",
                                                "count": len(domain), "entries": domain,
                                                "domainStatus": "conservative source-defined UI label superset; occupancy restrictions not verified"})
    items = [{"stableId": sid, "key": source[sid]["key"],
              "source": source[sid]["source"], "target": after[sid]["target"]}
             for sid in item_domain]
    result["item-name-domain.json"] = data({"schemaVersion": 1, "locale": "hu",
                                            "count": len(items), "entries": items,
                                            "domainStatus": "conservative source-defined item-label superset; actual Bribe slot restrictions not verified"})
    assembled = []
    templates = []
    for sid in runtime_templates:
        slots = rules[sid]["formatSlots"]
        unique = sorted(set(slots))
        require(unique in (["{0}"], ["{0}", "{1}"]), "Unexpected dynamic slot set")
        src_template = source[sid]["source"]
        dst_template = after[sid]["target"]
        key = source[sid].get("key") or ""
        is_bribe = "_Bribe_" in key
        require(is_bribe or "Occupied" in key, "Unclassified dynamic consumer")
        candidates = items if is_bribe else domain
        templates.append({"stableId": sid, "source": src_template,
                          "target": dst_template, "nodeNames": source[sid].get("nodeNames") or [],
                          "formatSlots": slots,
                          "candidateDomain": "item-name-domain.json" if is_bribe else "resident-name-domain.json"})
        if len(unique) == 1:
            combinations = ((a,) for a in candidates)
        else:
            require(not is_bribe, "Unexpected two-item Bribe slot")
            combinations = ((a, b) for a in candidates for b in candidates
                            if a["stableId"] != b["stableId"])
        for values in combinations:
            original, translated = src_template, dst_template
            for index, value in enumerate(values):
                original = original.replace("{" + str(index) + "}", value["source"])
                translated = translated.replace("{" + str(index) + "}", value["target"])
            require("{0}" not in original + translated and "{1}" not in original + translated,
                    "Assembled dynamic value retains a slot")
            assembled.append({"templateStableId": sid,
                              "candidateStableIds": [value["stableId"] for value in values],
                              "sourceAssembled": original, "targetAssembled": translated})
    result["assembled-consumer-context.jsonl"] = jsonl(assembled)
    result["runtime-consumer-context.json"] = data({
        "schemaVersion": 1, "locale": "hu", "templates": templates,
        "residentNameDomainPath": "resident-name-domain.json", "residentDomainCount": 57,
        "itemNameDomainPath": "item-name-domain.json", "itemDomainCount": 10,
        "assemblyCount": len(assembled),
        "assemblySha256": sha(result["assembled-consumer-context.jsonl"]),
        "bindingInterpretation": "Occupied branches use resident-name candidates; Bribe branches use item-name candidates. These source-defined domains are conservative supersets.",
        "runtimeLimit": "Static assembly verifies grammar and preserved slot semantics, not exact item/occupancy restrictions, renderer layout or game runtime.",
        "nontranslatableProtectedFragments": [{"stableId": sid,
             "speakerPrefix": rules[sid]["speakerPrefix"],
             "formatSlots": rules[sid]["formatSlots"],
             "tmpTags": rules[sid]["tmpTags"]} for sid in runtime_templates]})

    delta = [{"ordinal": ordinal[sid], "stableId": sid,
              "source": source[sid]["source"], "before": before[sid],
              "after": after[sid]["target"], "authoredFile": after[sid]["authoredFile"],
              "beforeAuthoredFileSha256": next(row["authoredFileSha256"] for row in plan["rows"] if row["stableId"] == sid),
              "afterAuthoredFileSha256": files[after[sid]["authoredFile"]]}
             for sid in order if sid in changed]
    result["changed-delta.jsonl"] = jsonl(delta)
    review_rows = []
    for sid in order:
        if sid not in closure:
            continue
        tags = [name for name, members in components.items() if sid in members]
        review_rows.append({"ordinal": ordinal[sid], "stableId": sid,
                            "collection": rules[sid].get("collection", "Static TMP"),
                            "key": source[sid].get("key") or sid,
                            "nodeNames": list(dict.fromkeys(source[sid].get("nodeNames") or [])),
                            "source": source[sid]["source"], "before": before[sid],
                            "after": after[sid]["target"],
                            "authoredFile": after[sid]["authoredFile"],
                            "afterAuthoredFileSha256": files[after[sid]["authoredFile"]],
                            "components": tags,
                            "independentReview": "pending"})
    result["closure-review-rows.jsonl"] = jsonl(review_rows)
    result["after-authored-files.json"] = data({"schemaVersion": 1, "locale": "hu",
                                                "files": [{"path": f, "sha256": h}
                                                          for f, h in sorted(files.items())],
                                                "fileCount": len(files)})
    closure_rows = [{"component": name, "count": len(members),
                     "idListSha256": sha(result[name + "-ids.txt"]),
                     "path": name + "-ids.txt"} for name, members in components.items()]
    manifest = {"schemaVersion": 1, "locale": "hu", "gameVersion": "1.3.19",
                "auditKind": "author correction dependency closure; independent review pending",
                "acceptedUnits": 16538,
                "sourceInventorySha256": plan["sourceInventorySha256"],
                "staticInventorySha256": plan["staticInventorySha256"],
                "preserveExactManifestSha256": plan["preserveExactManifestSha256"],
                "approvedGlossaryLayerSha256": plan["approvedGlossaryLayerSha256"],
                "canonicalGlossarySha256": plan["canonicalGlossarySha256"],
                "firstPassProgressSha256": plan["firstPassProgressSha256"],
                "firstPassErrataSha256": plan["firstPassErrataSha256"],
                "adjudicatedPlanSha256": digest(HERE / "adjudicated-plan.json"),
                "selectorSpecSha256": digest(HERE / "closure-selector-spec.json"),
                "preflightSha256": digest(HERE / "preflight.json"),
                "changedCount": len(changed),
                "changedIdListSha256": sha(result["changed-ids.txt"]),
                "closureCount": len(closure),
                "closureIdListSha256": sha(result["closure-ids.txt"]),
                "components": closure_rows,
                "sceneGroupCount": len(group_rows),
                "runtimeTemplateCount": len(runtime_templates),
                "runtimeAssemblyCount": len(assembled),
                "mandatoryRegressionCount": len(mandatory),
                "files": [{"path": name, "sha256": sha(payload), "bytes": len(payload)}
                          for name, payload in sorted(result.items())],
                "reviewerStatus": "not assigned in this author chat",
                "independentDiffAudit": "not-started",
                "editorialAcceptance": "pending",
                "runtimeAcceptance": "not-run"}
    result["closure-manifest.json"] = data(manifest)
    return result, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    mode = parser.parse_args().mode
    result, manifest = evidence()
    if mode == "build":
        require(not OUT.exists(), "Immutable closure already exists")
        OUT.mkdir()
        for name, payload in result.items():
            (OUT / name).write_bytes(payload)
    else:
        require(OUT.exists() and {p.name for p in OUT.iterdir()} == set(result),
                "Closure file set differs")
        for name, payload in result.items():
            require((OUT / name).read_bytes() == payload, "Closure output differs: " + name)
    print(json.dumps({"mode": mode, "closureCount": manifest["closureCount"],
                      "changedCount": manifest["changedCount"],
                      "components": {x["component"]: x["count"] for x in manifest["components"]},
                      "sceneGroups": manifest["sceneGroupCount"],
                      "runtimeAssemblies": manifest["runtimeAssemblyCount"],
                      "manifestSha256": digest(OUT / "closure-manifest.json")}))


if __name__ == "__main__":
    main()
