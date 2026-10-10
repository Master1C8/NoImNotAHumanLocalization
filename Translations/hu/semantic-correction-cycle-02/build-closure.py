#!/usr/bin/env python3
"""Build or verify immutable Hungarian correction-cycle-02 review evidence."""

import argparse
import hashlib
import json
import re
from collections import defaultdict
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
HU = ROOT / "Translations/hu"
PREV = HU / "semantic-correction-cycle-01/evidence"
REVIEW = HU / "independent-review-01"
OUT = HERE / "evidence"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    return sha(path.read_bytes())


def data(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def jsonl(values):
    return "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
                   for row in values).encode()


def id_data(ids):
    return "".join(sid + "\n" for sid in ids).encode()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def relative(path):
    return str(path.relative_to(ROOT))


def parse_ids(path):
    return path.read_text().splitlines()


def sid(batch, entry):
    guid = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
            "UI": "0cbd8a7a4f543344bb95659de87f67a5",
            "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}[batch["collection"]]
    return f"string:{guid}:{entry['id']}"


def corpus():
    plan = json.loads((HERE / "adjudicated-plan.json").read_text())
    spec = json.loads((HERE / "closure-selector-spec.json").read_text())
    remedial = json.loads((HERE / "bounded-remedial-read.json").read_text())
    prior = json.loads((PREV / "closure-manifest.json").read_text())
    review = json.loads((REVIEW / "review-verdict.json").read_text())
    pins = {"sourceInventorySha256": ROOT / "Source/localization-inventory-v3/strings.jsonl",
            "staticInventorySha256": ROOT / "Source/localization-inventory-v3/static-text.jsonl",
            "preserveExactManifestSha256": ROOT / "Source/preserve-exactly-v4.json",
            "approvedGlossaryLayerSha256": ROOT / "Documentation/glossary-translations/hu/layer.json",
            "canonicalGlossarySha256": Path("/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary.json"),
            "firstPassProgressSha256": HU / "semantic-review-progress.json",
            "reviewVerdictSha256": REVIEW / "review-verdict.json",
            "reviewProposalSha256": REVIEW / "consolidated-proposals-v2.json",
            "reviewArtifactManifestSha256": REVIEW / "artifact-manifest.json",
            "previousClosureManifestSha256": PREV / "closure-manifest.json",
            "previousReviewedRowsSha256": REVIEW / "full-pair-read-evidence.jsonl"}
    for key, path in pins.items():
        require(plan[key] == digest(path), "Input pin changed: " + key)
    require(prior["closureCount"] == review["reviewRows"] == 2902 and
            review["status"] == "corrections-required", "Previous review differs")
    artifact = json.loads((REVIEW / "artifact-manifest.json").read_text())
    for item in artifact["artifacts"]:
        require(digest(ROOT / item["path"]) == item["sha256"],
                "Independent evidence changed: " + item["path"])
    for item in prior["files"]:
        require(digest(PREV / item["path"]) == item["sha256"],
                "Previous closure changed: " + item["path"])
    preserve = json.loads((ROOT / "Source/preserve-exactly-v4.json").read_text())
    ordered_rows = preserve["tableRows"] + preserve["staticRows"]
    order = [row["stableId"] for row in ordered_rows]
    require(len(order) == len(set(order)) == 16538, "Accepted ID order changed")
    rules = {row["stableId"]: row for row in ordered_rows}
    source = {row["stableId"]: row for name in ("strings", "static-text")
              for row in (json.loads(line) for line in
                          (ROOT / f"Source/localization-inventory-v3/{name}.jsonl").open())
              if row["stableId"] in rules}
    require(set(source) == set(order), "Source coverage changed")
    pattern = re.compile(r"(?:dialogue|ui|checks)-batch-\d{3}\.json$")
    files = sorted(path for path in HU.glob("*-batch-*.json") if pattern.fullmatch(path.name))
    files.append(HU / "static-text-draft.json")
    after, ownership, hashes = {}, {}, {}
    for path in files:
        doc = json.loads(path.read_text())
        hashes[relative(path)] = digest(path)
        check = json.loads(path.with_suffix(".validation.json").read_text())
        require(check.get("batchSha256", check.get("draftSha256")) == hashes[relative(path)] and
                check["structuralResult"] == "passed", "Validation stale: " + relative(path))
        for entry in doc["entries"]:
            key = entry["stableId"] if path.name == "static-text-draft.json" else sid(doc, entry)
            require(key not in after, "Duplicate authored ID")
            after[key] = entry["target"]
            ownership[key] = relative(path)
    require(set(after) == set(order) and len(files) == 474, "Authored file set changed")
    previous_hashes = {x["path"]: x["sha256"] for x in
                       json.loads((PREV / "after-authored-files.json").read_text())["files"]}
    changed = {row["stableId"]: row for row in plan["rows"]}
    require(len(changed) == 14, "Correction count changed")
    for key, row in changed.items():
        require(source[key]["source"] == row["source"] and after[key] == row["finalTarget"] and
                ownership[key] == row["authoredFile"] and
                previous_hashes[ownership[key]] == row["beforeAuthoredFileSha256"],
                "Correction application differs: " + key)
    for path, old_hash in previous_hashes.items():
        if path not in {r["authoredFile"] for r in plan["rows"]}:
            require(hashes[path] == old_hash, "Unplanned authored change: " + path)
    require([r["stableId"] for r in remedial["rows"]] ==
            json.loads((REVIEW / "proposed-dependency-selectors.json").read_text())["riskCatalogExtensionIds"] and
            remedial["candidateCount"] == 196, "Remedial candidate set differs")
    for row in remedial["rows"]:
        key = row["stableId"]
        require(source[key]["source"] == row["source"] and after[key] == row["currentTarget"] and
                ownership[key] == row["authoredFile"] and
                previous_hashes[ownership[key]] == row["authoredFileSha256"],
                "Remedial read no longer bound: " + key)
    return plan, spec, prior, review, preserve, order, rules, source, after, ownership, hashes, changed, remedial


def generate():
    (plan, spec, prior, review, preserve, order, rules, source, after,
     ownership, hashes, changed, remedial) = corpus()
    position = {key: i for i, key in enumerate(order)}
    previous = parse_ids(PREV / "closure-ids.txt")
    require(len(previous) == len(set(previous)) == 2902 and
            sha(id_data(previous)) == prior["closureIdListSha256"], "Previous closure ID list changed")
    previous_set = set(previous)
    old_components = {item["component"]: set(parse_ids(PREV / item["path"]))
                      for item in prior["components"]}
    groups = defaultdict(set)
    changed_nodes = {node for key in changed for node in source[key].get("nodeNames", [])}
    changed_families = {source[key].get("key", "").rsplit("_", 1)[0] + "_"
                        for key in changed if source[key].get("key", "").startswith("line:")}
    scene = set(old_components["sceneContext"])
    for key in order:
        record = source[key]
        nodes = record.get("nodeNames", [])
        for node in set(nodes) & changed_nodes:
            groups["node:" + node].add(key)
            scene.add(key)
        source_key = record.get("key") or ""
        for family in changed_families:
            if source_key.startswith(family):
                groups["key-family:" + family].add(key)
                scene.add(key)
        if any(node.startswith(("Twins_Entrance", "Couple_Entrance")) for node in nodes):
            groups["related-entrance-branch"].add(key)
            scene.add(key)
    source_values = {row["source"] for row in changed.values()}
    before_values = {row["currentTarget"] for row in changed.values()}
    after_values = {row["finalTarget"] for row in changed.values()}
    repetitions = set(old_components["repetitions"]) | {
        key for key in order if source[key]["source"] in source_values or
        after[key] in before_values or after[key] in after_values}
    selectors = {}
    terms = set(old_components["glossaryReferents"])
    for row in spec["glossaryAndReferentSelectors"]:
        src_re = re.compile(row["sourceRegex"], re.I)
        dst_re = re.compile(row["targetRegex"], re.I)
        found = {key for key in order if src_re.search(source[key]["source"]) or
                 dst_re.search(after[key])}
        require(found, "Empty selector: " + row["id"])
        selectors[row["id"]] = found
        terms |= found
    slots = {key for key in order if rules[key]["formatSlots"]}
    names = [key for key in order if (source[key].get("key") or "").startswith("characterName_")]
    consumables = [key for key in order if re.fullmatch(r"consumable_[a-z]+_name",
                    source[key].get("key") or "")]
    require(len(slots) == 111 and len(names) == 57 and len(consumables) == 7,
            "Actual dynamic consumer domain changed")
    runtime = slots | set(names) | set(consumables)
    risk = {row["stableId"] for row in remedial["rows"]}
    mandatory = set(old_components["mandatoryRegression"]) | risk
    components = {"changed": set(changed), "sceneContext": scene,
                  "repetitions": repetitions, "glossaryReferents": terms,
                  "runtimeBinding": runtime, "mandatoryRegression": mandatory,
                  "previouslyReviewedContext": previous_set}
    closure = set().union(*components.values())
    result = {name + "-ids.txt": id_data(key for key in order if key in members)
              for name, members in components.items()}
    result["closure-ids.txt"] = id_data(key for key in order if key in closure)
    result["scene-groups.json"] = data({"schemaVersion": 2, "locale": "hu",
                                        "groups": [{"group": name, "count": len(members),
                                                    "ids": [key for key in order if key in members]}
                                                   for name, members in sorted(groups.items())]})
    result["glossary-referent-selectors.json"] = data({
        "schemaVersion": 2, "locale": "hu", "selectors":
        [{**row, "count": len(selectors[row["id"]]),
          "ids": [key for key in order if key in selectors[row["id"]]]}
         for row in spec["glossaryAndReferentSelectors"]]})
    result["mandatory-regression-catalog.json"] = data({
        "schemaVersion": 2, "locale": "hu", "scope": spec["mandatoryRegressionCatalog"],
        "previousCount": len(old_components["mandatoryRegression"]),
        "candidateExtensionCount": len(risk), "currentCount": len(mandatory),
        "applicability": [{"stableId": row["stableId"], "catalogGroups": row["catalogGroups"],
                           "classification": row["classification"]} for row in remedial["rows"]],
        "currentIdListSha256": sha(result["mandatoryRegression-ids.txt"])})
    def label(key):
        return {"stableId": key, "key": source[key]["key"],
                "source": source[key]["source"], "target": after[key]}
    name_entries = [label(key) for key in names]
    item_entries = [label(key) for key in consumables]
    require(next(e["target"] for e in item_entries if e["key"] == "consumable_bobeer_name") == "Sör",
            "Bobeer consumer output changed")
    result["resident-name-domain.json"] = data({"schemaVersion": 2, "locale": "hu",
                                                "count": 57, "entries": name_entries,
                                                "domainStatus": "conservative source-defined UI label superset"})
    result["item-name-domain.json"] = data({"schemaVersion": 2, "locale": "hu",
                                            "count": 7, "entries": item_entries,
                                            "binding": "LocalizeItem supplies consumable_<enum lowercase>_name",
                                            "consumerEvidenceSha256": digest(REVIEW / "consumer-il.json")})
    old_items = json.loads((PREV / "item-name-domain.json").read_text())["entries"]
    removed = [item for item in old_items if item["stableId"] not in consumables]
    require(len(removed) == 3 and all(e["key"].startswith("FridgeItem_") for e in removed),
            "Fridge item retirement differs")
    prior_runtime = json.loads((PREV / "runtime-consumer-context.json").read_text())
    templates = []
    assembled = []
    compiled = json.loads((REVIEW / "compiled-context.json").read_text())["nodes"]
    compiled_lines = {str(operand) for node in compiled if node["compiled"]
                      for inst in node["instructions"] if inst["opcode"] == 2
                      for operand in inst["operands"] if isinstance(operand, str)}
    bribe_keys = []
    for item in prior_runtime["templates"]:
        key = item["stableId"]
        consumer = "item" if "item-name" in item["candidateDomain"] else "resident"
        choices = item_entries if consumer == "item" else name_entries
        if consumer == "item":
            bribe_keys.append(key)
        src_text, dst_text = source[key]["source"], after[key]
        require(src_text == item["source"] and set(re.findall(r"\{\d+\}", src_text)) ==
                set(re.findall(r"\{\d+\}", dst_text)), "Template slot changed")
        line_key = source[key].get("key")
        templates.append({"stableId": key, "key": line_key, "source": src_text,
                          "target": dst_text, "formatSlots": rules[key]["formatSlots"],
                          "candidateDomain": "item-name-domain.json" if consumer == "item"
                                             else "resident-name-domain.json",
                          "compiledOccurrence": line_key in compiled_lines,
                          "protectedFragments": {"speakerPrefix": rules[key]["speakerPrefix"],
                                                 "formatSlots": rules[key]["formatSlots"],
                                                 "tmpTags": rules[key]["tmpTags"]}})
        pairs = ((a, b) for a, b in product(choices, repeat=2) if a["stableId"] != b["stableId"]) \
                if "{1}" in src_text else ((a,) for a in choices)
        for pair in pairs:
            src_value, dst_value = src_text, dst_text
            for index, candidate in enumerate(pair):
                slot = "{" + str(index) + "}"
                src_value = src_value.replace(slot, candidate["source"])
                dst_value = dst_value.replace(slot, candidate["target"])
            require(not re.search(r"\{[01]\}", src_value + dst_value), "Unassembled template")
            if key in changed and "Occupied" in (line_key or ""):
                require(" van" in dst_value, "Hungarian occupied copula missing")
            assembled.append({"templateStableId": key,
                              "candidateStableIds": [x["stableId"] for x in pair],
                              "sourceAssembled": src_value, "targetAssembled": dst_value})
    require(len(templates) == 8 and len(assembled) == 3491 and len(bribe_keys) == 2,
            "Consumer assembly topology differs")
    result["assembled-consumer-context.jsonl"] = jsonl(assembled)
    result["runtime-consumer-context.json"] = data({
        "schemaVersion": 2, "locale": "hu", "templates": templates,
        "residentDomainCount": 57, "itemDomainCount": 7,
        "allAcceptedFormatSlotCount": 111, "assemblyCount": len(assembled),
        "assemblySha256": sha(result["assembled-consumer-context.jsonl"]),
        "compiledProgramSha256": digest(REVIEW / "compiled-context.json"),
        "retiredConsumerCandidates": [{**item, "reason": "FridgeItem label is not supplied by LocalizeItem"}
                                      for item in removed],
        "nontranslatableProtectedFragments": [t["protectedFragments"] for t in templates],
        "runtimeLimit": "Static assembly only; actual deficit and occupancy restrictions unverified"})
    invalidated = set(bribe_keys) | {item["stableId"] for item in old_items}
    require(len(invalidated) == 12 and invalidated <= previous_set,
            "Invalidated prior consumer context differs")
    new_only = closure - previous_set
    next_delta = set(changed) | new_only | invalidated
    result["newly-selected-ids.txt"] = id_data(key for key in order if key in new_only)
    result["explicitly-invalidated-prior-ids.txt"] = id_data(key for key in order if key in invalidated)
    result["next-review-delta-ids.txt"] = id_data(key for key in order if key in next_delta)
    result["retirement.json"] = data({
        "schemaVersion": 2, "locale": "hu", "totalClosureRetiredIds": [],
        "reason": "Prior reviewed closure retained as a regression component",
        "runtimeComponentRetiredIds": [item["stableId"] for item in removed],
        "runtimeComponentReason": "FridgeItem labels are valid UI units but not LocalizeItem consumer outputs",
        "retainedStandaloneUiByMandatoryCatalog": all(item["stableId"] in mandatory for item in removed)})
    delta_rows = [{"ordinal": position[key], "stableId": key,
                   "source": source[key]["source"], "before": changed[key]["currentTarget"],
                   "after": after[key], "authoredFile": ownership[key],
                   "beforeAuthoredFileSha256": changed[key]["beforeAuthoredFileSha256"],
                   "afterAuthoredFileSha256": hashes[ownership[key]]}
                  for key in order if key in changed]
    result["changed-delta.jsonl"] = jsonl(delta_rows)
    review_rows = [{"ordinal": position[key], "stableId": key,
                    "collection": rules[key].get("collection", "Static TMP"),
                    "key": source[key].get("key") or key,
                    "nodeNames": source[key].get("nodeNames", []),
                    "source": source[key]["source"],
                    "before": changed[key]["currentTarget"] if key in changed else after[key],
                    "after": after[key], "authoredFile": ownership[key],
                    "afterAuthoredFileSha256": hashes[ownership[key]],
                    "components": [name for name, members in components.items() if key in members],
                    "nextDeltaReasons": (["corrected"] if key in changed else []) +
                                        (["newly-selected"] if key in new_only else []) +
                                        (["invalidated-prior-consumer-context"] if key in invalidated else [])}
                   for key in order if key in closure]
    result["closure-review-rows.jsonl"] = jsonl(review_rows)
    result["next-review-delta.jsonl"] = jsonl(row for row in review_rows if row["stableId"] in next_delta)
    result["after-authored-files.json"] = data({"schemaVersion": 2, "locale": "hu",
                                                "fileCount": len(hashes),
                                                "files": [{"path": k, "sha256": v}
                                                          for k, v in sorted(hashes.items())]})
    components_meta = [{"component": name, "count": len(members),
                        "path": name + "-ids.txt", "sha256": sha(result[name + "-ids.txt"])}
                       for name, members in components.items()]
    prior_meta = [{"component": item["component"], "count": item["count"],
                   "sha256": item["idListSha256"]} for item in prior["components"]]
    manifest = {"schemaVersion": 2, "locale": "hu", "gameVersion": "1.3.19",
                "status": "author correction closure; independent review pending",
                "acceptedUnits": 16538, "sourceInventorySha256": plan["sourceInventorySha256"],
                "staticInventorySha256": plan["staticInventorySha256"],
                "approvedGlossaryLayerSha256": plan["approvedGlossaryLayerSha256"],
                "canonicalGlossarySha256": plan["canonicalGlossarySha256"],
                "preserveExactManifestSha256": plan["preserveExactManifestSha256"],
                "firstPassProgressSha256": plan["firstPassProgressSha256"],
                "reviewVerdictSha256": plan["reviewVerdictSha256"],
                "previousClosureManifestSha256": plan["previousClosureManifestSha256"],
                "previousReviewedRowsSha256": plan["previousReviewedRowsSha256"],
                "planSha256": digest(HERE / "adjudicated-plan.json"),
                "remedialReadSha256": digest(HERE / "bounded-remedial-read.json"),
                "selectorSpecSha256": digest(HERE / "closure-selector-spec.json"),
                "preflightSha256": digest(HERE / "preflight.json"),
                "previousClosureCount": len(previous_set), "closureCount": len(closure),
                "correctedCount": len(changed), "newlySelectedCount": len(new_only),
                "explicitlyInvalidatedPriorCount": len(invalidated),
                "nextReviewDeltaCount": len(next_delta),
                "nextReviewFormula": "corrected IDs union (current closure minus previous independently reviewed closure) union explicitly invalidated prior IDs",
                "currentComponents": components_meta, "previousComponents": prior_meta,
                "sceneGroupCount": len(groups), "runtimeTemplateCount": len(templates),
                "runtimeAssemblyCount": len(assembled),
                "mandatoryCatalogCount": len(mandatory),
                "closureIdListSha256": sha(result["closure-ids.txt"]),
                "nextReviewDeltaIdListSha256": sha(result["next-review-delta-ids.txt"]),
                "files": [{"path": name, "sha256": sha(payload), "bytes": len(payload)}
                          for name, payload in sorted(result.items())],
                "reviewerStatus": "distinct reviewer not yet assigned",
                "editorialAcceptance": "pending", "runtimeAcceptance": "not-run"}
    result["closure-manifest.json"] = data(manifest)
    return result, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    mode = parser.parse_args().mode
    result, manifest = generate()
    if mode == "build":
        require(not OUT.exists(), "Immutable output already exists")
        OUT.mkdir()
        for name, payload in result.items():
            (OUT / name).write_bytes(payload)
    else:
        require(OUT.exists() and {p.name for p in OUT.iterdir()} == set(result),
                "Output file set changed")
        for name, payload in result.items():
            require((OUT / name).read_bytes() == payload, "Output differs: " + name)
    print(json.dumps({"mode": mode, "closure": manifest["closureCount"],
                      "nextDelta": manifest["nextReviewDeltaCount"],
                      "new": manifest["newlySelectedCount"],
                      "assemblies": manifest["runtimeAssemblyCount"],
                      "manifestSha256": digest(OUT / "closure-manifest.json")}))


if __name__ == "__main__":
    main()
