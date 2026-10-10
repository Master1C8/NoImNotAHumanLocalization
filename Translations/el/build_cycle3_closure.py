#!/usr/bin/env python3
"""Build or verify the Greek cycle-3 consumer closure and independent-review delta."""

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PREFIX = "correction-cycle-003"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("preview", "write", "verify"))
    args = parser.parse_args()
    spec_path = HERE / f"{PREFIX}-selectors.json"
    plan_path = HERE / f"{PREFIX}-adjudication.json"
    applied_path = HERE / f"{PREFIX}-applied.json"
    corpus_path = HERE / f"{PREFIX}-corpus.validation.json"
    previous_path = HERE / "correction-cycle-002-closure-manifest.json"
    review = HERE / "independent-review-02"
    proof_path = review / "final-coverage-and-invalidation-proof.json"
    pins_path = review / "final-input-hashes.json"
    spec = json.loads(spec_path.read_text())
    plan = json.loads(plan_path.read_text())
    applied = json.loads(applied_path.read_text())
    corpus = json.loads(corpus_path.read_text())
    previous = json.loads(previous_path.read_text())
    proof = json.loads(proof_path.read_text())
    assert spec["cycle"] == plan["cycle"] == applied["cycle"] == 3
    assert digest(plan_path) == applied["adjudicationSha256"]
    assert digest(previous_path) == plan["priorCycle2ClosureManifestSha256"]
    assert digest(proof_path) == plan["review02FinalCoverageProofSha256"]
    assert digest(review / "evidence-manifest-v2.json") == plan["review02EvidenceManifestSha256"]
    assert digest(review / "findings.json") == plan["review02FindingsSha256"]
    assert digest(ROOT / "Source/localization-inventory-v3/strings.jsonl") == plan["sourceInventorySha256"]
    assert digest(ROOT / "Source/localization-inventory-v3/static-text.jsonl") == plan["sourceStaticSha256"]
    assert digest(ROOT / "Documentation/glossary-translations/el/layer.json") == plan["approvedGlossarySha256"]
    assert digest(HERE / "correction-cycle-002-text-checkpoint.json") == plan["priorCycle2CheckpointSha256"]
    assert corpus["locale"] == "el" and corpus["rows"] == 16538
    assert corpus["structuralResult"] == corpus["exactResult"] == "passed"
    assert corpus["selectedIdCoverage"] == "16538 unique; no missing/extra"
    assert len(corpus["authoredFiles"]) == 420
    for file in applied["files"]:
        assert digest(ROOT / file["path"]) == file["afterSha256"]
    # Review02's 1,316 pre-application pins are still valid except for this exact
    # eight-file authored/generated application. Its sidecars remain untouched.
    final_pins = json.loads(pins_path.read_text())["pins"]
    changed_paths = {str(ROOT / file["path"]) for file in applied["files"]}
    assert len(final_pins) == 1316 and len(changed_paths) == 8
    for name, expected in final_pins.items():
        path = Path(name)
        if name in changed_paths:
            assert expected == next(file["beforeSha256"] for file in applied["files"]
                                    if str(ROOT / file["path"]) == name)
        else:
            assert digest(path) == expected, name

    source_manifest = json.loads((ROOT / "Source/preserve-exactly-v4.json").read_text())
    accepted_table = {row["stableId"] for row in source_manifest["tableRows"]}
    accepted_static = {row["stableId"] for row in source_manifest["staticRows"]}
    all_dialogue = [json.loads(line) for line in
                    (ROOT / "Source/localization-inventory-v3/strings.jsonl").open()
                    if '"collection":"Dialogs"' in line]
    table = [row for line in (ROOT / "Source/localization-inventory-v3/strings.jsonl").open()
             if (row := json.loads(line))["stableId"] in accepted_table]
    static = [row for line in (ROOT / "Source/localization-inventory-v3/static-text.jsonl").open()
              if (row := json.loads(line))["stableId"] in accepted_static]
    source = table + static
    ids = [row["stableId"] for row in source]
    accepted = set(ids)
    by_id = {row["stableId"]: row for row in source}
    ordinal = {sid: i for i, sid in enumerate(ids)}
    assert len(table) == 16360 and len(static) == 178 and len(accepted) == 16538

    current, current_file = {}, {}
    guids = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
             "UI": "0cbd8a7a4f543344bb95659de87f67a5",
             "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}
    for file in corpus["authoredFiles"]:
        path = ROOT / file["path"]
        assert digest(path) == file["sha256"]
        data = json.loads(path.read_text())
        for entry in data["entries"]:
            sid = (f"string:{guids[data['collection']]}:{entry['id']}"
                   if "collection" in data else entry["stableId"])
            assert sid in accepted and sid not in current
            current[sid] = entry["target"]
            current_file[sid] = file
    assert set(current) == accepted
    changed = {row["stableId"] for row in plan["corrections"]}
    assert len(changed) == 6 and changed == set(applied["changedIds"])
    before = dict(current)
    for row in plan["corrections"]:
        sid = row["stableId"]
        assert row["ordinal"] == ordinal[sid]
        assert row["sourceSha256"] == text_digest(by_id[sid]["source"])
        assert current[sid] == row["after"] and text_digest(current[sid]) == row["afterSha256"]
        before[sid] = row["before"]

    prior_closure = set((HERE / "correction-cycle-002-closure-ids.txt").read_text().splitlines())
    assert len(prior_closure) == previous["closure"]["count"] == 1757
    assert digest(HERE / "correction-cycle-002-closure-ids.txt") == previous["closure"]["sha256"]
    old_decisions = [json.loads(line) for line in
                     (HERE / "independent-review-01/decisions.jsonl").open()]
    reused = proof["remainingReusedDecisions"]
    assert len(reused) == proof["finalClosureReuse"] == 1505
    accepted_review = {}
    for row in reused:
        sid = row["stableId"]
        origin = old_decisions[row["previousDecisionIndex"]]
        assert origin["stableId"] == sid
        assert origin["sourceSha256"] == row["sourceSha256"] == text_digest(by_id[sid]["source"])
        assert origin["currentTargetSha256"] == row["targetSha256"] == text_digest(before[sid])
        assert sid not in accepted_review
        accepted_review[sid] = "review01-reused-by-review02"
    fresh = []
    for name in ("decisions.jsonl", "bounded-additional-decisions.jsonl"):
        fresh.extend(json.loads(line) for line in (review / name).open())
    assert len(fresh) == proof["totalFreshRead"] == 252
    assert len({row["stableId"] for row in fresh}) == 252
    for row in fresh:
        sid = row["stableId"]
        assert row["sourceSha256"] == text_digest(by_id[sid]["source"])
        assert row["currentTargetSha256"] == text_digest(before[sid])
        if row["decision"] == "accepted-current-wording":
            assert sid not in accepted_review
            accepted_review[sid] = "review02-fresh-accepted"
        else:
            assert row["decision"] == "objective-correction-proposed" and sid in changed
    assert len(accepted_review) == 1505 + 246 == 1751
    assert prior_closure == set(accepted_review) | changed
    assert len(set(accepted_review) & changed) == 0
    assert set(proof["newlyInvalidatedPriorAcceptedIds"]) <= changed

    context = set()
    radius = spec["contextNeighborRadius"]
    for sid in changed:
        i = ordinal[sid]
        row = by_id[sid]
        for j in range(max(0, i - radius), min(len(table), i + radius + 1)):
            if source[j]["collection"] == row["collection"]:
                context.add(ids[j])
        nodes = set(row.get("nodeNames", []))
        if nodes:
            context.update(r["stableId"] for r in table
                           if r["collection"] == row["collection"] and
                           nodes.intersection(r.get("nodeNames", [])))
    for prefix in spec["contextNodePrefixes"]:
        matches = {row["stableId"] for row in table
                   if any(node.startswith(prefix) for node in row.get("nodeNames", []))}
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
    assert len(anchors) == 25 and len(callbacks) == 3 and anchors | callbacks <= accepted
    referent.update(anchors | callbacks)

    runtime = set()
    for key in spec["runtimeBinding"]["uiKeys"]:
        matches = {row["stableId"] for row in table if row["collection"] == "UI"
                   and row.get("key") == key}
        assert len(matches) == 1, key
        runtime.update(matches)
    name_pattern = re.compile(spec["runtimeBinding"]["uiKeyRegex"])
    runtime.update(row["stableId"] for row in table if row["collection"] == "UI"
                   and name_pattern.search(row.get("key") or ""))
    for sid in spec["runtimeBinding"]["staticStableIds"]:
        assert sid in accepted_static and "x1" in by_id[sid]["source"]
        runtime.add(sid)
    consumer_spec = spec["actualLocalizeItemConsumerSelector"]
    topology_path = ROOT / consumer_spec["evidencePath"]
    assert digest(topology_path) == consumer_spec["evidenceSha256"]
    topology = json.loads(topology_path.read_text())
    assert topology["completeActualLocalizeItemConsumers"] == consumer_spec["expectedActualConsumerCount"] == 21
    consumers = {row["row"]["stableId"] for row in topology["consumerRows"]}
    assert len(consumers) == 21 and consumers <= accepted
    for row in topology["consumerRows"]:
        sid = row["row"]["stableId"]
        assert row["row"]["key"] == by_id[sid]["key"]
        assert row["row"]["sourceSha256"] == text_digest(by_id[sid]["source"])
        assert row["row"]["currentTargetSha256"] == text_digest(before[sid])
    runtime.update(consumers)
    checks_path = ROOT / consumer_spec["acceptedLabelEvidencePath"]
    assert digest(checks_path) == consumer_spec["acceptedLabelEvidenceSha256"]
    checks = json.loads(checks_path.read_text())
    assert len(checks["acceptedNameKeys"]) == consumer_spec["expectedAcceptedLabelCount"] == 7
    assert len(checks["assembledBribeExamples"]) == consumer_spec["expectedAssembledVariants"] == 126
    assert checks["deficitDomain"] == consumer_spec["expectedDeficitItemEnumNames"]
    assert digest(ROOT / consumer_spec["deficitDomainPath"]) == consumer_spec["deficitDomainSha256"]
    label_ids = {row["stableId"] for row in table if row["collection"] == "UI"
                 and row.get("key") in checks["acceptedNameKeys"]}
    assert len(label_ids) == 7
    runtime.update(label_ids)

    mandatory = set()
    regress = spec["mandatoryRegression"]
    if regress["allAcceptedUI"]:
        mandatory.update(row["stableId"] for row in table if row["collection"] == "UI")
    if regress["allAcceptedStatic"]:
        mandatory.update(accepted_static)
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
    assert len(mandatory) == proof["mandatoryTotal"] == 1269

    components = {"changed": changed, "context": context, "repetition": repetition,
                  "glossary-referent": referent, "runtime-binding": runtime,
                  "mandatory-regression": mandatory}
    assert all(part <= accepted for part in components.values())
    closure = set().union(*components.values())
    assert changed | consumers | label_ids <= closure
    invalidation = defaultdict(list)
    for name, reason in (("context", "changed-scene-context"),
                         ("repetition", "changed-unit-repetition"),
                         ("runtime-binding", "dynamic-consumer-binding")):
        for sid in (components[name] & set(accepted_review)) - changed:
            invalidation[sid].append(reason)
    for sid in consumers & set(accepted_review) - changed:
        invalidation[sid].append("repaired-actual-consumer-selector-class")
    invalidated = set(invalidation)
    new = closure - set(accepted_review)
    delta = changed | new | invalidated
    assert delta == changed | (closure - set(accepted_review)) | invalidated
    assert delta <= closure
    retired = prior_closure - closure
    assert not retired & changed
    assert not retired & mandatory
    assert all(text_digest(current[sid]) == text_digest(before[sid]) for sid in retired)

    outputs, summaries = {}, {}
    for name, part in {**components, "closure": closure, "new": new,
                       "invalidated": invalidated, "delta-review": delta,
                       "retired": retired}.items():
        ordered = [sid for sid in ids if sid in part]
        path = HERE / f"{PREFIX}-{name}-ids.txt"
        data = ("\n".join(ordered) + "\n").encode()
        outputs[path] = data
        summaries[name] = {"path": str(path.relative_to(ROOT)), "count": len(ordered),
                           "sha256": hashlib.sha256(data).hexdigest()}
    consumer_by_id = {row["row"]["stableId"]: row for row in topology["consumerRows"]}
    def review_row(sid):
        consumer = consumer_by_id.get(sid)
        return {"ordinal": ordinal[sid], "stableId": sid,
                "collection": by_id[sid].get("collection", "static"),
                "key": by_id[sid].get("key"),
                "components": [name for name, part in components.items() if sid in part],
                "source": by_id[sid]["source"], "sourceSha256": text_digest(by_id[sid]["source"]),
                "beforeCycle3Target": before[sid],
                "beforeCycle3TargetSha256": text_digest(before[sid]),
                "currentTarget": current[sid], "currentTargetSha256": text_digest(current[sid]),
                "targetFile": current_file[sid]["path"],
                "targetFileSha256": current_file[sid]["sha256"],
                "priorIndependentAcceptance": accepted_review.get(sid),
                "invalidationReasons": invalidation.get(sid, []),
                "actualLocalizeItemConsumer": ({"node": consumer["node"], "pc": consumer["pc"]}
                                               if consumer else None)}
    for name, part in (("closure-review", closure), ("delta-review", delta)):
        path = HERE / f"{PREFIX}-{name}.jsonl"
        data = ("\n".join(json.dumps(review_row(sid), ensure_ascii=False,
                                     separators=(",", ":")) for sid in ids if sid in part) + "\n").encode()
        outputs[path] = data
        summaries[name + "-rows"] = {"path": str(path.relative_to(ROOT)),
                                      "count": len(part), "sha256": hashlib.sha256(data).hexdigest()}
    retired_path = HERE / f"{PREFIX}-retired-evidence.json"
    retired_rows = [{"stableId": sid, "ordinal": ordinal[sid],
                     "reason": "No current-cycle dependency selector matches; source, glossary and target unchanged from the independently read prior value.",
                     "priorIndependentAcceptance": accepted_review.get(sid),
                     "targetSha256": text_digest(current[sid])}
                    for sid in ids if sid in retired]
    outputs[retired_path] = encoded(retired_rows)
    summaries["retired-evidence"] = {"path": str(retired_path.relative_to(ROOT)),
                                     "count": len(retired),
                                     "sha256": hashlib.sha256(outputs[retired_path]).hexdigest()}
    invalidated_path = HERE / f"{PREFIX}-invalidation-evidence.json"
    invalidated_rows = [{"stableId": sid, "ordinal": ordinal[sid],
                         "reasons": invalidation[sid],
                         "priorIndependentAcceptance": accepted_review[sid],
                         "unchangedTargetSha256": text_digest(current[sid])}
                        for sid in ids if sid in invalidated]
    outputs[invalidated_path] = encoded(invalidated_rows)
    summaries["invalidation-evidence"] = {"path": str(invalidated_path.relative_to(ROOT)),
                                          "count": len(invalidated),
                                          "sha256": hashlib.sha256(outputs[invalidated_path]).hexdigest()}
    result = {"schemaVersion": 1, "locale": "el", "cycle": 3,
              "status": "exact post-correction delta ready for distinct reviewer; no author-side independent acceptance",
              "acceptedUnits": 16538, "review02FreshRead": 252,
              "review02FreshAccepted": 246, "review02ReusedAccepted": 1505,
              "verifiedPriorIndependentAcceptedIds": len(accepted_review),
              "sourceInventorySha256": plan["sourceInventorySha256"],
              "sourceStaticSha256": plan["sourceStaticSha256"],
              "approvedGlossarySha256": plan["approvedGlossarySha256"],
              "review02EvidenceManifestSha256": plan["review02EvidenceManifestSha256"],
              "review02FinalCoverageProofSha256": digest(proof_path),
              "review02FinalInputPinsSha256": digest(pins_path),
              "review02FinalInputPinCount": len(final_pins),
              "previousClosureManifestSha256": digest(previous_path),
              "adjudicationSha256": digest(plan_path), "appliedSha256": digest(applied_path),
              "selectorSha256": digest(spec_path), "corpusValidationSha256": digest(corpus_path),
              "components": {name: summaries[name] for name in components},
              "closure": summaries["closure"], "new": summaries["new"],
              "invalidated": summaries["invalidated"],
              "deltaReview": summaries["delta-review"], "retired": summaries["retired"],
              "closureReviewRows": summaries["closure-review-rows"],
              "deltaReviewRows": summaries["delta-review-rows"],
              "retiredEvidence": summaries["retired-evidence"],
              "invalidationEvidence": summaries["invalidation-evidence"],
              "deltaFormula": "corrected ∪ (current closure − verified prior independently read accepted IDs) ∪ explicit invalidation",
              "actualLocalizeItemConsumerCount": len(consumers),
              "actualDeficitItemCount": len(checks["deficitDomain"]),
              "acceptedConsumerLabelCount": len(label_ids),
              "assembledConsumerVariants": len(checks["assembledBribeExamples"]),
              "patternHitCounts": pattern_hits,
              "review02NewlyInvalidatedPriorAcceptedIds": proof["newlyInvalidatedPriorAcceptedIds"],
              "currentTargetFiles": corpus["authoredFiles"],
              "authoredAndGeneratedFiles": applied["files"],
              "unexplainedMissingIds": 0, "unexplainedExtraIds": 0,
              "technicalMetadataNote": "Fresh native m_Script differs from old cached header only; gameplay fields and six deficit keys match. No universal restart.",
              "runtime": "not-run", "editorialAcceptance": "pending"}
    manifest_path = HERE / f"{PREFIX}-closure-manifest.json"
    outputs[manifest_path] = encoded(result)
    if args.mode == "preview":
        print(json.dumps({"counts": {name: summary["count"] for name, summary in summaries.items()},
                          "missingOrExtra": 0}, indent=2))
        return
    for path, content in outputs.items():
        if args.mode == "write":
            assert not path.exists(), path
            path.write_bytes(content)
        else:
            assert path.read_bytes() == content, path
    print(json.dumps({"result": args.mode, "closure": len(closure),
                      "delta": len(delta), "retired": len(retired),
                      "manifestSha256": digest(manifest_path)}))


if __name__ == "__main__":
    main()
