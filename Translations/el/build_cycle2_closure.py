#!/usr/bin/env python3
"""Reproduce the Greek cycle-2 closure and distinct-reviewer delta from pinned evidence."""

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PREFIX = "correction-cycle-002"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def encoded(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("preview", "write", "verify"))
    args = parser.parse_args()
    spec_path = HERE / f"{PREFIX}-selectors.json"
    plan_path = HERE / f"{PREFIX}-adjudication.json"
    errata_path = HERE / f"{PREFIX}-adjudication-errata.json"
    applied_path = HERE / f"{PREFIX}-applied.json"
    exact_path = HERE / f"{PREFIX}-preserve-exact.validation.json"
    full_path = HERE / f"{PREFIX}-full-structural.validation.json"
    previous_path = HERE / "correction-cycle-001-closure-manifest.json"
    decisions_path = HERE / "independent-review-01/decisions.jsonl"
    spec, plan = json.loads(spec_path.read_text()), json.loads(plan_path.read_text())
    errata, applied = json.loads(errata_path.read_text()), json.loads(applied_path.read_text())
    exact, full = json.loads(exact_path.read_text()), json.loads(full_path.read_text())
    previous = json.loads(previous_path.read_text())
    assert spec["locale"] == plan["locale"] == applied["locale"] == "el"
    assert spec["cycle"] == plan["cycle"] == applied["cycle"] == 2
    assert digest(plan_path) == applied["adjudicationSha256"] == errata["adjudicationSha256"]
    assert digest(previous_path) == plan["previousClosureManifestSha256"]
    assert digest(decisions_path) == plan["review01DecisionsSha256"]
    assert digest(HERE / "semantic-review-progress.json") == plan["firstPassProgressSha256"]
    assert digest(ROOT / "Source/localization-inventory-v3/strings.jsonl") == plan["sourceInventorySha256"]
    assert digest(ROOT / "Source/localization-inventory-v3/static-text.jsonl") == plan["sourceStaticSha256"]
    assert digest(ROOT / "Documentation/glossary-translations/el/layer.json") == plan["approvedGlossarySha256"]
    assert exact["checkedRows"] == full["acceptedUnits"] == 16538
    assert exact["exactResult"] == full["result"] == "passed"
    assert full["preserveExactSha256"] == digest(exact_path)
    for file in applied["files"]:
        assert digest(ROOT / file["path"]) == file["afterSha256"]

    source_manifest = json.loads((ROOT / "Source/preserve-exactly-v4.json").read_text())
    table_set = {row["stableId"] for row in source_manifest["tableRows"]}
    static_set = {row["stableId"] for row in source_manifest["staticRows"]}
    all_dialogue = [json.loads(line) for line in
                    (ROOT / "Source/localization-inventory-v3/strings.jsonl").open()
                    if '"collection":"Dialogs"' in line]
    table = [row for line in (ROOT / "Source/localization-inventory-v3/strings.jsonl").open()
             if (row := json.loads(line))["stableId"] in table_set]
    static = [row for line in (ROOT / "Source/localization-inventory-v3/static-text.jsonl").open()
              if (row := json.loads(line))["stableId"] in static_set]
    source = table + static
    ids = [row["stableId"] for row in source]
    accepted = set(ids)
    by_id = {row["stableId"]: row for row in source}
    ordinal = {sid: i for i, sid in enumerate(ids)}
    assert len(table) == 16360 and len(static) == 178 and len(accepted) == len(ids) == 16538

    current, current_file = {}, {}
    guids = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
             "UI": "0cbd8a7a4f543344bb95659de87f67a5",
             "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}
    for file in exact["inputFiles"]:
        path = ROOT / file["path"]
        assert digest(path) == file["sha256"]
        obj = json.loads(path.read_text())
        for entry in obj["entries"]:
            sid = (f"string:{guids[obj['collection']]}:{entry['id']}"
                   if "collection" in obj else entry["stableId"])
            assert sid in accepted and sid not in current
            current[sid] = entry["target"]
            current_file[sid] = file
    assert set(current) == accepted

    changed = {row["stableId"] for row in plan["corrections"]}
    assert changed == set(applied["changedIds"]) and len(changed) == 26
    before = dict(current)
    for row in plan["corrections"]:
        sid = row["stableId"]
        assert sid in accepted and row["ordinal"] == ordinal[sid]
        assert row["source"] == by_id[sid]["source"] and current[sid] == row["after"]
        before[sid] = row["before"]
    assert all(text_digest(before[sid]) == row["beforeSha256"]
               for row in plan["corrections"] for sid in [row["stableId"]])

    prior_ids = (HERE / "correction-cycle-001-closure-ids.txt").read_text().splitlines()
    assert len(prior_ids) == 1816 and len(set(prior_ids)) == 1816
    assert digest(HERE / "correction-cycle-001-closure-ids.txt") == previous["components"]["closure"]["sha256"]
    decisions = [json.loads(line) for line in decisions_path.open()]
    assert [row["stableId"] for row in decisions] == prior_ids
    previous_file_hashes = {file["path"]: file["sha256"] for file in previous["currentTargetFiles"]}
    reviewed = set(prior_ids)
    for row in decisions:
        sid = row["stableId"]
        assert row["targetFileSha256"] == previous_file_hashes[row["targetFile"]]
        assert row["sourceSha256"] == text_digest(by_id[sid]["source"])
        assert row["glossaryFingerprint"] == plan["approvedGlossarySha256"]
        assert row["currentTargetSha256"] == text_digest(before[sid])

    context = set()
    radius = spec["contextNeighborRadius"]
    for sid in changed:
        i = ordinal[sid]
        row = by_id[sid]
        if sid in static_set:
            continue
        for j in range(max(0, i - radius), min(len(table), i + radius + 1)):
            if source[j]["collection"] == row["collection"]:
                context.add(ids[j])
        nodes = set(row.get("nodeNames", []))
        if nodes:
            context.update(r["stableId"] for r in table
                           if r["collection"] == row["collection"] and
                           nodes.intersection(r.get("nodeNames", [])))
    for prefix in spec["contextNodePrefixes"]:
        matches = {r["stableId"] for r in table
                   if any(node.startswith(prefix) for node in r.get("nodeNames", []))}
        assert matches, prefix
        context.update(matches)

    changed_source = {by_id[sid]["source"] for sid in changed}
    changed_before = {before[sid] for sid in changed}
    changed_after = {current[sid] for sid in changed}
    repetition = {sid for sid in ids if by_id[sid]["source"] in changed_source or
                  current[sid] in changed_before | changed_after or
                  before[sid] in changed_before}

    referent = set()
    pattern_hits = {}
    for selector in spec["glossaryReferentSelectors"]:
        source_pattern = re.compile(selector["sourceRegex"], re.IGNORECASE)
        target_pattern = re.compile(selector["targetRegex"], re.IGNORECASE)
        hits = {sid for sid in ids if source_pattern.search(by_id[sid]["source"]) or
                target_pattern.search(current[sid]) or target_pattern.search(before[sid])}
        assert hits, selector["name"]
        pattern_hits[selector["name"]] = len(hits)
        referent.update(hits)
    anchors = set(spec["canonicalUnknownRoleStableIds"])
    callbacks = set(spec["kilotonCallbackStableIds"])
    assert len(anchors) == 25 and len(callbacks) == 3
    assert anchors | callbacks <= accepted
    assert callbacks <= referent, "Source-root callback selector missed a canonical instance"
    referent.update(anchors | callbacks)

    runtime = set()
    for key in spec["runtimeBinding"]["uiKeys"]:
        matches = {row["stableId"] for row in table if row.get("collection") == "UI"
                   and row.get("key") == key}
        assert len(matches) == 1, key
        runtime.update(matches)
    name_pattern = re.compile(spec["runtimeBinding"]["uiKeyRegex"])
    runtime.update(row["stableId"] for row in table if row.get("collection") == "UI"
                   and name_pattern.search(row.get("key") or ""))
    for sid in spec["runtimeBinding"]["staticStableIds"]:
        assert sid in static_set and "x1" in by_id[sid]["source"]
        runtime.add(sid)

    mandatory = set()
    regress = spec["mandatoryRegression"]
    if regress["allAcceptedUI"]:
        mandatory.update(row["stableId"] for row in table if row["collection"] == "UI")
    if regress["allAcceptedStatic"]:
        mandatory.update(static_set)
    for row in source_manifest["tableRows"]:
        if ((regress["protectedFormatSlots"] and row["formatSlots"]) or
                (regress["protectedTmpTags"] and row["tmpTags"]) or
                (regress["protectedExactTexts"] and row["wholeTextExact"]) or
                (regress["protectedNumbers"] and row["numbers"])):
            mandatory.add(row["stableId"])
    kinship = re.compile(regress["kinshipSourceRegex"], re.IGNORECASE)
    mandatory.update(row["stableId"] for row in table if kinship.search(row["source"]))
    for start, end in regress["foreignerDialogueSourceIndexRanges"]:
        assert 0 <= start < end <= len(all_dialogue)
        mandatory.update(row["stableId"] for row in all_dialogue[start:end]
                         if row["stableId"] in accepted)

    components = {"changed": changed, "context": context, "repetition": repetition,
                  "glossary-referent": referent, "runtime-binding": runtime,
                  "mandatory-regression": mandatory}
    assert all(part <= accepted for part in components.values())
    closure = set().union(*components.values())
    assert changed <= closure and anchors | callbacks <= closure
    invalidation = defaultdict(list)
    policies = {"context": "changed-scene-context", "repetition": "changed-line-repetition",
                "runtime-binding": "dynamic-consumer-binding"}
    for name, reason in policies.items():
        for sid in components[name] & reviewed - changed:
            invalidation[sid].append(reason)
    for sid in (anchors | callbacks) & reviewed - changed:
        invalidation[sid].append("repaired-canonical-selector-class")
    invalidated = set(invalidation)
    new = closure - reviewed
    delta = changed | new | invalidated
    assert delta == changed | (closure - reviewed) | invalidated
    assert delta <= closure
    retired = reviewed - closure
    assert not (retired & changed) and not (retired & invalidated)
    assert all(text_digest(current[sid]) == next(row["currentTargetSha256"]
               for row in decisions if row["stableId"] == sid) for sid in retired)

    outputs = {}
    summaries = {}
    for name, part in {**components, "closure": closure, "new": new,
                       "invalidated": invalidated, "delta-review": delta,
                       "retired": retired}.items():
        ordered = [sid for sid in ids if sid in part]
        path = HERE / f"{PREFIX}-{name}-ids.txt"
        data = ("\n".join(ordered) + "\n").encode("utf-8")
        outputs[path] = data
        summaries[name] = {"path": str(path.relative_to(ROOT)), "count": len(ordered),
                           "sha256": hashlib.sha256(data).hexdigest(),
                           "newline": "LF, terminal newline"}

    def review_row(sid):
        return {"ordinal": ordinal[sid], "stableId": sid,
                "collection": by_id[sid].get("collection", "static"),
                "key": by_id[sid].get("key"),
                "components": [name for name, part in components.items() if sid in part],
                "source": by_id[sid]["source"], "sourceSha256": text_digest(by_id[sid]["source"]),
                "beforeCycle2Target": before[sid],
                "beforeCycle2TargetSha256": text_digest(before[sid]),
                "currentTarget": current[sid], "currentTargetSha256": text_digest(current[sid]),
                "targetFile": current_file[sid]["path"],
                "targetFileSha256": current_file[sid]["sha256"],
                "review01Read": sid in reviewed,
                "cycle2InvalidationReasons": invalidation.get(sid, [])}

    for name, part in (("closure-review", closure), ("delta-review", delta)):
        path = HERE / f"{PREFIX}-{name}.jsonl"
        data = ("\n".join(json.dumps(review_row(sid), ensure_ascii=False,
                                     separators=(",", ":")) for sid in ids if sid in part) + "\n").encode()
        outputs[path] = data
        summaries[name + "-rows"] = {"path": str(path.relative_to(ROOT)),
                                      "count": len(part), "sha256": hashlib.sha256(data).hexdigest()}
    retired_rows = [{"stableId": sid, "ordinal": ordinal[sid],
                     "previousComponents": next(row["components"] for row in decisions
                                                if row["stableId"] == sid),
                     "reason": "No current-cycle dependency selector matches; source, glossary and target are unchanged from reviewed evidence.",
                     "currentTargetSha256": text_digest(current[sid])}
                    for sid in ids if sid in retired]
    retired_path = HERE / f"{PREFIX}-retired-evidence.json"
    outputs[retired_path] = encoded(retired_rows)
    summaries["retired-evidence"] = {"path": str(retired_path.relative_to(ROOT)),
                                     "count": len(retired),
                                     "sha256": hashlib.sha256(outputs[retired_path]).hexdigest()}
    manifest = {
        "schemaVersion": 1, "locale": "el", "cycle": 2,
        "status": "exact delta handoff for a distinct reviewer; author self-read is not independent acceptance",
        "acceptedUnits": 16538, "firstPassReviewedUnits": 16538,
        "review01ReadUnits": len(reviewed), "review01ReadDecisionsSha256": digest(decisions_path),
        "sourceInventorySha256": plan["sourceInventorySha256"],
        "sourceStaticSha256": plan["sourceStaticSha256"],
        "approvedGlossarySha256": plan["approvedGlossarySha256"],
        "firstPassProgressSha256": plan["firstPassProgressSha256"],
        "review01EvidenceManifestSha256": plan["review01EvidenceManifestSha256"],
        "previousClosureManifestSha256": digest(previous_path),
        "adjudicationSha256": digest(plan_path), "adjudicationErrataSha256": digest(errata_path),
        "appliedSha256": digest(applied_path), "selectorSha256": digest(spec_path),
        "preserveExactValidationSha256": digest(exact_path),
        "fullStructuralValidationSha256": digest(full_path),
        "components": {name: summaries[name] for name in components},
        "closure": summaries["closure"], "new": summaries["new"],
        "invalidated": summaries["invalidated"], "deltaReview": summaries["delta-review"],
        "retired": summaries["retired"], "retiredEvidence": summaries["retired-evidence"],
        "closureReviewRows": summaries["closure-review-rows"],
        "deltaReviewRows": summaries["delta-review-rows"],
        "deltaFormula": "changed ∪ (current closure − review01 independently read closure) ∪ explicitly invalidated prior IDs",
        "invalidationPolicy": spec["reviewInvalidationPolicy"],
        "patternHitCounts": pattern_hits,
        "canonicalUnknownRoleAnchorCount": len(anchors),
        "priorMissingUnknownRoleAnchorCount": 20,
        "kilotonCallbackCount": len(callbacks),
        "currentTargetFiles": exact["inputFiles"],
        "authoredAndGeneratedFiles": applied["files"],
        "unexplainedMissingIds": 0, "unexplainedExtraIds": 0,
        "runtime": "not-run by owner instruction", "editorialAcceptance": "pending"}
    manifest_path = HERE / f"{PREFIX}-closure-manifest.json"
    outputs[manifest_path] = encoded(manifest)
    if args.mode == "preview":
        print(json.dumps({"counts": {name: part["count"] for name, part in summaries.items()},
                          "patternHits": pattern_hits, "missingOrExtra": 0}, indent=2))
        return
    for path, content in outputs.items():
        if args.mode == "write":
            assert not path.exists(), path
            path.write_bytes(content)
        else:
            assert path.read_bytes() == content, path
    print(json.dumps({"result": args.mode, "closure": len(closure), "delta": len(delta),
                      "retired": len(retired), "manifestSha256": digest(manifest_path)}))


if __name__ == "__main__":
    main()
