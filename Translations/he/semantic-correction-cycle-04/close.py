#!/usr/bin/env python3
"""Build the cycle-04 closure, immutable structural evidence, and handoff."""

import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CYCLE = Path(__file__).resolve().parent
HE = CYCLE.parent
PRIOR = HE / "semantic-correction-cycle-03"
IR = HE / "independent-review-03"
sys.path.insert(0, str(CYCLE))
from workflow import GUID, digest, sha, encoded, once, lines, ref


def hash_set(rows):
    return digest("".join(x["path"] + "\t" + x["sha256"] + "\n" for x in rows).encode())


def refs_inside(obj, ids, sources, old_targets):
    """Find exact and ID references without guessing a derived map's schema."""
    exact = set(sources) | set(old_targets) | set(ids)
    numbers = {int(sid.rsplit(":", 1)[1]) for sid in ids if sid.startswith("string:")}
    hits = []
    def visit(value, route=""):
        if isinstance(value, dict):
            for key, item in value.items():
                visit(item, route + "/" + str(key))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                visit(item, route + "/" + str(i))
        elif value in exact if isinstance(value, str) else value in numbers if isinstance(value, int) else False:
            hits.append(route)
    visit(obj)
    return hits


def main():
    pins = json.loads((CYCLE / "input-pins.json").read_text())
    pre = json.loads((CYCLE / "preflight.json").read_text())
    app = json.loads((CYCLE / "application.json").read_text())
    post = json.loads((CYCLE / "post-validation-summary.json").read_text())
    exact = json.loads((CYCLE / "preserve-exact-v4.json").read_text())
    consumer = json.loads((CYCLE / "compiled-consumer-preflight.json").read_text())
    ledger = json.loads((CYCLE / "bald-voice-roster-ledger.json").read_text())
    adj = json.loads((CYCLE / "adjudications.json").read_text())["records"]
    baseline = json.loads((CYCLE / "baseline-progress.json").read_text())
    prior_semantic = json.loads((CYCLE / "baseline-semantic-review-progress.json").read_text())
    assert sha(CYCLE / "baseline-progress.json") == pins["priorProgressSha256"]
    assert sha(CYCLE / "baseline-semantic-review-progress.json") == pins["priorSemanticProgressSha256"]
    assert sha(PRIOR / "closure-manifest.json") == pins["priorClosureManifestSha256"]
    assert sha(PRIOR / "closure-ids.txt") == pins["priorClosureIdsSha256"]
    assert sha(PRIOR / "delta-review-rows.jsonl") == pins["priorDeltaRowsSha256"]
    assert sha(IR / "final-review.json") == pins["review03Sha256"]
    assert sha(IR / "final-findings.json") == pins["review03FindingsSha256"]
    assert sha(IR / "complete-review-decisions.json") == pins["review03DecisionsSha256"]
    assert app["status"] == "applied" and app["changedStableIds"] == 14
    assert post["status"] == "passed on applied authored files" and post["validatedFiles"] == 5
    assert exact["checkedRows"] == 16538 and exact["exactResult"] == "passed"
    assert consumer["changedCompiledUnits"] == 14 and len(ledger["rows"]) == 132
    assert sha(CYCLE / "preflight.json") == app["preflightSha256"]
    srcpaths = pins["sourceInventory"]
    assert sha(ROOT / srcpaths["stringsPath"]) == srcpaths["stringsSha256"]
    assert sha(ROOT / srcpaths["staticPath"]) == srcpaths["staticSha256"]
    assert sha(ROOT / srcpaths["preserveExactPath"]) == srcpaths["preserveExactSha256"]
    assert sha(ROOT / pins["glossary"]["path"]) == pins["glossary"]["sha256"]
    rules = json.loads((ROOT / srcpaths["preserveExactPath"]).read_text())
    accepted = rules["tableRows"] + rules["staticRows"]
    ordered = [x["stableId"] for x in accepted]
    order = {sid: i for i, sid in enumerate(ordered)}
    assert len(order) == len(ordered) == 16538
    source = {x["stableId"]: x for x in map(json.loads, (ROOT / srcpaths["stringsPath"]).open())}
    source.update({x["stableId"]: x for x in map(json.loads, (ROOT / srcpaths["staticPath"]).open())})
    assert set(order) <= set(source)
    prior_ids = (PRIOR / "closure-ids.txt").read_text().splitlines()
    assert len(prior_ids) == 2382 and prior_ids == sorted(prior_ids, key=order.__getitem__)
    old = set(prior_ids)
    before, after = {}, {}
    for f in baseline["files"]:
        rel = f["path"]
        current = ROOT / rel
        expected = pre["files"][rel]["afterSha256"] if rel in pre["files"] else f["sha256"]
        assert sha(current) == expected, rel
        if not re.search(r"(?:dialogue|ui|checks)-batch-\d{3}\.json$", rel):
            continue
        former = CYCLE / "before-authored" / current.name if rel in pre["files"] else current
        a, b = json.loads(former.read_text()), json.loads(current.read_text())
        assert a["collection"] == b["collection"] and len(a["entries"]) == len(b["entries"])
        for x, y in zip(a["entries"], b["entries"]):
            assert x["id"] == y["id"]
            sid = f"string:{GUID[b['collection']]}:{y['id']}"
            assert sid in order and sid not in after
            before[sid], after[sid] = x["target"], y["target"]
    for x in json.loads((HE / "static-text-draft.json").read_text())["entries"]:
        sid = x["stableId"]
        assert sid in order and sid not in after
        before[sid] = after[sid] = x["target"]
    assert set(before) == set(after) == set(order)
    changed = {sid for sid in order if before[sid] != after[sid]}
    assert len(changed) == 14 and changed == {x["stableId"] for x in adj}
    assert (CYCLE / "changed-ids.txt").read_bytes() == lines(changed, order)
    for row in ledger["rows"]:
        sid = row["stableId"]
        assert source[sid]["source"] == row["source"] and before[sid] == row["targetBefore"]
        assert digest(row["source"].encode()) == row["sourceSha256"]
        assert digest(row["targetBefore"].encode()) == row["targetBeforeSha256"]
    coarse = {x["stableId"] for x in ledger["rows"] if x["dependencySelected"]}
    controls = {x["stableId"] for x in ledger["rows"] if x["review03Control"]}
    assert len(coarse) == 39 and len(controls) == 8 and controls <= coarse
    reviewer_controls = json.loads((IR / "selector-controls.json").read_text())["rows"]
    assert controls == {x["stableId"] for x in reviewer_controls}
    review_findings = json.loads((IR / "final-findings.json").read_text())["findings"]
    assert {x["stableId"] for x in review_findings} == changed

    components = defaultdict(set)
    components["changed"].update(changed)
    components["retained-prior-closure"].update(old)
    components["bald-source-voice-risk"].update(coarse)
    affected_nodes = {node for x in adj for node in x["nodeNames"]}
    assert "Nun_Entrance_1" in affected_nodes and "Nun_Entrance_2" in affected_nodes
    # The profanity option's actual callback complaints are shared by both
    # entrance choices. These are dependency nodes, not all Nun dialogue.
    affected_nodes.update({"Nun_Entrance_4"})
    for sid in ordered:
        if affected_nodes.intersection(source[sid].get("nodeNames", [])):
            components["compiled-scene-neighbors-and-callback"].add(sid)
    source_exact = {x["source"] for x in adj}
    old_exact = {x["before"] for x in adj}
    new_exact = {x["after"] for x in adj}
    for sid in ordered:
        if source[sid]["source"] in source_exact or before[sid] in old_exact or after[sid] in new_exact:
            components["exact-repetitions-and-wording"].add(sid)
    # The changed eye/hand lines share contiguous compiled branches; their
    # prompts and exposed outcomes are selected through actual affected nodes.
    for rule in accepted:
        sid = rule["stableId"]
        if (sid.startswith("tmp:") or rule.get("collection") in ("UI", "ChecksDialogs")
                or rule["formatSlots"] or rule["tmpTags"] or rule["wholeTextExact"]):
            components["mandatory-regressions"].add(sid)
    first = json.loads((HE / "semantic-correction-cycle-01" / "baseline-semantic-review-progress.json").read_text())
    for note in first["knownEditorialFollowups"]:
        for number in re.findall(r"\b\d{15,18}\b", note):
            components["mandatory-regressions"].update(sid for sid in order if sid.endswith(":" + number))
    old_mandatory = set((PRIOR / "components/mandatory-regressions-ids.txt").read_text().splitlines())
    assert components["mandatory-regressions"] == old_mandatory and len(old_mandatory) == 549
    # The source selector is proven against every pinned Bald speaker row,
    # including all eight reviewer controls. It does not invalidate every
    # previously reviewed coarse line merely because this ledger now exists.
    components["selector-regression-controls"].update(controls)
    closure = set().union(*components.values())
    new = closure - old
    retired = old - closure
    assert not retired
    # Review-03 retained 110504457400295426 without explicitly invalidating
    # it. Its correction and compiled neighbors now invalidate that evidence.
    affected = (components["compiled-scene-neighbors-and-callback"] |
                components["exact-repetitions-and-wording"])
    invalidated = (affected & old) - changed
    retained_control = next(x["stableId"] for x in reviewer_controls if x["stableId"].endswith(":110504457400295426"))
    assert retained_control in old and retained_control in changed
    # It is already present as a corrected ID; record the explicit historical
    # invalidation reason without adding a duplicate to the set formula.
    historical_invalidations = {retained_control: "Review-03 retained this row without explicit invalidation; cycle-04 replacement invalidates its old decision and corrected-ID coverage includes it."}
    delta = changed | new | invalidated
    assert delta <= closure
    for name, ids in components.items():
        once(CYCLE / "components" / (name + "-ids.txt"), lines(ids, order))
    for name, ids in (("closure", closure), ("new-closure", new), ("retired", retired),
                      ("explicitly-invalidated", invalidated), ("delta", delta)):
        once(CYCLE / (name + "-ids.txt"), lines(ids, order))
    causes = {sid: sorted(name for name, ids in components.items() if sid in ids) for sid in closure}
    def row(sid):
        x = source[sid]
        return {"stableId": sid, "collection": x.get("collection", "StaticTMP"),
                "key": x.get("key"), "nodeNames": x.get("nodeNames", []),
                "source": x["source"], "before": before[sid], "after": after[sid],
                "components": causes[sid], "reviewDelta": sid in delta,
                "deltaReasons": [label for label, yes in (("corrected", sid in changed),
                    ("new-closure", sid in new), ("explicitly-invalidated", sid in invalidated)) if yes]}
    rows = [row(sid) for sid in sorted(closure, key=order.__getitem__)]
    def render(values):
        return ("\n".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) for x in values) + "\n").encode()
    once(CYCLE / "review-rows.jsonl", render(rows))
    delta_rows = [x for x in rows if x["reviewDelta"]]
    once(CYCLE / "delta-review-rows.jsonl", render(delta_rows))
    map_status = {}
    for name in ("action-label-map.json", "visitor-choice-map.json", "repeated-choices-map.json",
                 "repeated-ambient-map.json", "credits-replacements.json", "credits-role-map.json",
                 "credits-application.json", "static-text-draft.json"):
        path = HE / name
        hits = refs_inside(json.loads(path.read_text()), changed, source_exact, old_exact)
        assert not hits, (name, hits)
        map_status[name] = {"path": str(path.relative_to(ROOT)), "sha256": sha(path),
                            "affectedReferences": 0, "result": "current; no changed source, old-target, stable-ID or numeric-ID reference"}
    once(CYCLE / "derived-artifact-reconciliation.json", encoded({"schemaVersion": 1,
        "status": "all locale-owned derived maps and static credits current; no recipe input affected",
        "changedIdsSha256": sha(CYCLE / "changed-ids.txt"), "artifacts": map_status}))
    context = {"schemaVersion": 1, "status": "hashed compiled context; not additional translation units",
               "compiledConsumerPreflight": ref(CYCLE / "compiled-consumer-preflight.json", changedLines=14),
               "baldRosterLedger": ref(CYCLE / "bald-voice-roster-ledger.json", rows=132, selected=39),
               "affectedCompiledNodes": sorted(affected_nodes),
               "selectorControls": ref(IR / "selector-controls.json", controls=8, losses=5, retained=3),
               "historicalInvalidation": historical_invalidations,
               "derivedArtifacts": ref(CYCLE / "derived-artifact-reconciliation.json"),
               "retiredDependencies": [],
               "retentionReason": "The 2,382-ID previous closure remains the unresolved reviewed dependency baseline. Unchanged prior Bald/Nun reads remain reusable except actual changed-node and exact-wording invalidations."}
    once(CYCLE / "runtime-context.json", encoded(context))
    stats = {name: ref(CYCLE / "components" / (name + "-ids.txt"), count=len(ids))
             for name, ids in sorted(components.items())}
    manifest = {"schemaVersion": 1,
        "status": "cycle-04 applied; exact independent delta ready; no cycle-04 verdict",
        "canonicalOrder": "preserve-exactly-v4 tableRows then staticRows; UTF-8, one ID per line, final LF for nonempty files",
        "selectorScriptSha256": sha(Path(__file__)), "workflowScriptSha256": sha(CYCLE / "workflow.py"),
        "inputPinsSha256": sha(CYCLE / "input-pins.json"),
        "sourceInventorySha256": srcpaths["stringsSha256"],
        "staticInventorySha256": srcpaths["staticSha256"],
        "preserveExactSha256": srcpaths["preserveExactSha256"],
        "glossarySha256": pins["glossary"]["sha256"],
        "priorClosureManifestSha256": pins["priorClosureManifestSha256"],
        "independentReviewSha256": pins["review03Sha256"],
        "independentFindingsSha256": pins["review03FindingsSha256"],
        "changedIds": ref(CYCLE / "changed-ids.txt", count=len(changed)),
        "previousClosureIds": ref(PRIOR / "closure-ids.txt", count=len(old)),
        "closureIds": ref(CYCLE / "closure-ids.txt", count=len(closure)),
        "newClosureIds": ref(CYCLE / "new-closure-ids.txt", count=len(new)),
        "explicitlyInvalidatedIds": ref(CYCLE / "explicitly-invalidated-ids.txt", count=len(invalidated)),
        "retiredIds": ref(CYCLE / "retired-ids.txt", count=len(retired)),
        "deltaIds": ref(CYCLE / "delta-ids.txt", count=len(delta)),
        "components": stats,
        "reviewRows": ref(CYCLE / "review-rows.jsonl", count=len(rows)),
        "deltaReviewRows": ref(CYCLE / "delta-review-rows.jsonl", count=len(delta_rows)),
        "runtimeContext": ref(CYCLE / "runtime-context.json", nodes=len(affected_nodes)),
        "repairedSelectors": ["Complete 132-row Bald speaker roster with explicit per-row voice classification and eight pinned missed-variant controls",
                              "Actual compiled affected nodes and Nun profanity-option callback",
                              "Exact source and old/new target repetitions", "549-ID mandatory regression catalog"],
        "baldRosterRows": 132, "baldRiskRows": 39, "selectorControlRows": 8,
        "deltaFormula": "corrected IDs union current-minus-previous closure union explicitly invalidated previously reviewed IDs",
        "retiredDependencyReason": "none; all prior closure dependencies retained as applicable baseline",
        "historicalInvalidation": historical_invalidations,
        "editorialAcceptance": False}
    once(CYCLE / "closure-manifest.json", encoded(manifest))
    authored, sidecars = [], []
    for x in exact["inputFiles"]:
        path = ROOT / x["path"]
        assert sha(path) == x["sha256"]
        side = path.with_suffix(".validation.json")
        report = json.loads(side.read_text())
        assert report["structuralResult"] == "passed"
        assert report.get("batchSha256", report.get("draftSha256")) == x["sha256"]
        authored.append(x)
        sidecars.append(ref(side))
    assert len(authored) == len(sidecars) == 337
    structural = {"schemaVersion": 1, "status": "passed; structural evidence only",
        "acceptedUnits": 16538, "authoredUnits": 16538, "validatedCurrentFiles": 337,
        "changedValidatedFiles": 5,
        "sourceInventorySha256": srcpaths["stringsSha256"],
        "staticInventorySha256": srcpaths["staticSha256"],
        "preserveExactManifestSha256": srcpaths["preserveExactSha256"],
        "glossarySha256": pins["glossary"]["sha256"],
        "preserveExactReport": ref(CYCLE / "preserve-exact-v4.json", checkedRows=16538),
        "postValidation": ref(CYCLE / "post-validation-summary.json", files=5),
        "compiledConsumerPreflight": ref(CYCLE / "compiled-consumer-preflight.json", units=14),
        "derivedArtifacts": ref(CYCLE / "derived-artifact-reconciliation.json"),
        "authoredFileSetSha256": hash_set(authored),
        "sidecarFileSetSha256": hash_set(sidecars),
        "authoredFiles": authored, "sidecars": sidecars,
        "semanticReview": "original complete first pass preserved; independent cycle-03 findings corrected; cycle-04 exact delta pending",
        "runtime": "not-run per owner instruction"}
    once(CYCLE / "full-structural-diff.json", encoded(structural))
    handoff = {"schemaVersion": 1, "locale": "he", "gameVersion": "1.3.19",
        "sourceLocale": "ru", "acceptedUnits": 16538,
        "status": "ready for independent cycle-04 exact delta review; no cycle-04 verdict",
        "priorIndependentReviewer": json.loads((IR / "final-review.json").read_text())["reviewer"],
        "priorIndependentVerdict": "corrections required",
        "priorIndependentReview": ref(IR / "final-review.json"),
        "priorIndependentFindings": ref(IR / "final-findings.json", count=14),
        "priorIndependentDecisions": ref(IR / "complete-review-decisions.json", reviewedRows=269),
        "priorSelectorControls": ref(IR / "selector-controls.json", readPairs=8),
        "priorClosure": ref(PRIOR / "closure-manifest.json", count=2382),
        "firstSemanticPass": ref(HE / "semantic-correction-cycle-01/baseline-semantic-review-progress.json", reviewedUnits=16538),
        "sourceInventory": {"path": srcpaths["stringsPath"], "sha256": srcpaths["stringsSha256"]},
        "staticSource": {"path": srcpaths["staticPath"], "sha256": srcpaths["staticSha256"]},
        "approvedGlossary": pins["glossary"],
        "preserveExactManifest": {"path": srcpaths["preserveExactPath"], "sha256": srcpaths["preserveExactSha256"]},
        "reviewerDecisionReconciliation": ref(CYCLE / "reviewer-decision-reconciliation.json", rows=269),
        "adjudications": ref(CYCLE / "adjudications.json", accepted=14),
        "baldVoiceRoster": ref(CYCLE / "bald-voice-roster-ledger.json", rows=132, selected=39),
        "preflight": ref(CYCLE / "preflight.json"),
        "compiledConsumerPreflight": ref(CYCLE / "compiled-consumer-preflight.json", units=14),
        "application": ref(CYCLE / "application.json"),
        "postValidation": ref(CYCLE / "post-validation-summary.json"),
        "derivedArtifacts": ref(CYCLE / "derived-artifact-reconciliation.json"),
        "fullStructuralDiff": ref(CYCLE / "full-structural-diff.json"),
        "closureManifest": ref(CYCLE / "closure-manifest.json", closureCount=len(closure)),
        "changedIds": manifest["changedIds"], "newClosureIds": manifest["newClosureIds"],
        "explicitlyInvalidatedIds": manifest["explicitlyInvalidatedIds"],
        "retiredIds": manifest["retiredIds"], "deltaIds": manifest["deltaIds"],
        "deltaReviewRows": manifest["deltaReviewRows"],
        "firstDeltaId": (CYCLE / "delta-ids.txt").read_text().splitlines()[0],
        "deltaReviewCount": len(delta),
        "reviewInstruction": "Distinct reviewer: compare exactly the hash-bound cycle-04 delta-review-rows.jsonl full Russian/Hebrew units, compiled scenes and approved glossary. Recheck 549 mandatory regression IDs on unchanged hashes, reusing unaffected review-03 and earlier decisions. Verify 14 corrected units and all newly exposed Bald voice-variant dependencies. Do not reread unchanged prior closure by default. Record an independent verdict; this handoff is not acceptance.",
        "sourceDomainConflict": "Fan/Luka configured resident alternatives conflict with fixed Russian masculine; prior neutral Hebrew remains unchanged and no gender is guessed.",
        "unresolvedConsumer": "characterName_Twins lacks an exact accepted UI key; runtime fallback remains unverified.",
        "imagesTextures": "excluded by owner text-only scope",
        "runtime": "not-run per owner instruction", "visual": "not-run", "editorialAcceptance": False}
    once(CYCLE / "independent-review-handoff.json", encoded(handoff))
    print(json.dumps({"changed": len(changed), "previous": len(old), "closure": len(closure),
                      "new": len(new), "invalidated": len(invalidated), "retired": len(retired),
                      "delta": len(delta), "manifestSha256": sha(CYCLE / "closure-manifest.json"),
                      "handoffSha256": sha(CYCLE / "independent-review-handoff.json")}))


if __name__ == "__main__":
    main()
