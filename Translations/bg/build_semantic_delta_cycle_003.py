#!/usr/bin/env python3
"""Reproduce the exact Bulgarian independent review delta after correction003."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BG = ROOT / "Translations/bg"
EVIDENCE = BG / "semantic-delta-cycle-003.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def id_bytes(ids):
    return ("\n".join(ids) + ("\n" if ids else "")).encode()


def same_pair_consumer(a, b):
    return all(a.get(key) == b.get(key) for key in
               ("source", "target", "key", "sceneNodes", "collection"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preview", "build", "verify"))
    args = parser.parse_args()
    old_path = BG / "semantic-closure-cycle-002.json"
    new_path = BG / "semantic-closure-cycle-003.json"
    old, new = load(old_path), load(new_path)
    result_path = BG / "correction-batch-003-result.json"
    result = load(result_path)
    assert new["correctionResultSha256"] == sha(result_path)
    old_rows = {r["stableId"]: r for r in old["reviewRows"]}
    new_rows = {r["stableId"]: r for r in new["reviewRows"]}
    old_ids, current = set(old_rows), set(new_rows)
    assert len(old_ids) == 2686 and len(current) == 2839

    review01_path = BG / "independent-review-01/review.json"
    review02_path = BG / "independent-review-02/review.json"
    review01, review02 = load(review01_path), load(review02_path)
    closure01_path = BG / "semantic-closure-cycle-001.json"
    assert review01["closureSha256"] == sha(closure01_path)
    assert review02["closureSha256"] == sha(old_path)
    review01_ids = set((BG / "independent-review-01/read.ids").read_text().splitlines())
    review02_ids = set((BG / "independent-review-02/read.ids").read_text().splitlines())
    assert len(review01_ids) == 1506 and len(review02_ids) == 2110
    assert review01_ids | review02_ids == old_ids
    read01_rows = {r["stableId"]: r for r in load(closure01_path)["reviewRows"]}
    assert review01_ids == set(read01_rows)
    verdict_path = BG / "independent-review-02/per-id-read-verdicts.json"
    verdicts = load(verdict_path)
    assert len(verdicts) == 2110 and {v["stableId"] for v in verdicts} == review02_ids
    for v in verdicts:
        r = old_rows[v["stableId"]]
        assert v["fullPairRead"] and v["sourceSha256"] == text_sha(r["source"])
        assert v["targetSha256"] == text_sha(r["target"])
    # Review01-only rows are reusable only with the exact source, target and
    # compiled consumer identity from its sealed read; Review02 rows use cycle002.
    prior_applicable = set()
    prior_sources = defaultdict(int)
    for sid in review02_ids:
        if sid in new_rows and same_pair_consumer(old_rows[sid], new_rows[sid]):
            prior_applicable.add(sid)
            prior_sources["review02Exact"] += 1
    for sid in review01_ids - review02_ids:
        if sid in new_rows and same_pair_consumer(read01_rows[sid], new_rows[sid]):
            prior_applicable.add(sid)
            prior_sources["review01Exact"] += 1
    supplementary_path = BG / "independent-review-02/selector-supplementary-rows.json"
    supplementary = [r for r in load(supplementary_path) if not r["inDelta"]]
    assert len(supplementary) == 4
    supplemental_reused, supplemental_changed = [], []
    for r in supplementary:
        sid = r["stableId"]
        current_row = new_rows[sid]
        if (current_row["source"], current_row["target"], current_row["key"]) == (
                r["source"], r["target"], r["key"]):
            prior_applicable.add(sid)
            supplemental_reused.append(sid)
        else:
            assert sid in result["changedIds"] and current_row["source"] == r["source"]
            supplemental_changed.append(sid)
    assert len(supplemental_reused) == 3 and len(supplemental_changed) == 1
    assert prior_applicable <= current

    corrected = set(result["changedIds"])
    plan = load(BG / "correction-batch-003.json")
    assert corrected == {d["stableId"] for d in plan["decisions"]} and len(corrected) == 41
    changed_nodes = {n for sid in corrected for n in new_rows[sid]["sceneNodes"]}
    changed_sources = {new_rows[sid]["source"] for sid in corrected}
    affected = load(BG / "correction-cycle-003-bounded-review.json")
    group_ids = defaultdict(set)
    for row in affected["rows"]:
        for group in row["groupMembership"]:
            group_ids[group].add(row["stableId"])
    direct_concepts = ("baldFamilyReferents", "wheelchairEarSignConsumer",
                       "leperLightExclamation", "colorVerbReferents",
                       "rockImperativeAndMusic")
    reasons = {}
    for sid in prior_applicable:
        row = new_rows[sid]
        why = []
        if set(row["sceneNodes"]) & changed_nodes:
            why.append("same compiled Yarn node as a correction003 full-unit replacement")
        if row["source"] in changed_sources:
            why.append("exact Russian repetition of a correction003 unit")
        for group in direct_concepts:
            if sid in group_ids[group] and group_ids[group] & corrected:
                why.append("direct affected referent or consumer: " + group)
        if why:
            reasons[sid] = why
    invalidated = set(reasons)
    newly_selected = current - prior_applicable
    retired = old_ids - current
    assert not retired, "Retired dependencies need an explanation before handoff"
    review_set = corrected | newly_selected | invalidated
    assert review_set <= current and corrected <= review_set
    rank = {row["stableId"]: row["sourceIndex"] for row in new["reviewRows"]}
    ordered = lambda ids: sorted(ids, key=rank.__getitem__)
    outputs, components = {}, {}
    for name, ids in (("corrected", corrected), ("newClosure", newly_selected),
                      ("invalidatedPrior", invalidated), ("retired", retired),
                      ("review", review_set), ("priorApplicable", prior_applicable)):
        rel = f"Translations/bg/semantic-cycle-003-{name}.ids"
        raw = id_bytes(ordered(ids))
        outputs[rel] = raw
        components[name] = {"path": rel, "count": len(ids),
                            "sha256": hashlib.sha256(raw).hexdigest(), "ids": ordered(ids)}
    mandatory = set(new["components"]["mandatoryRegressions"]["ids"])
    old_mandatory = set(old["components"]["mandatoryRegressions"]["ids"])
    assert len(mandatory) == len(old_mandatory) == 908 and mandatory == old_mandatory
    evidence = {
        "schemaVersion": 1, "locale": "bg", "gameVersion": "1.3.19",
        "status": "exact correction003 independent delta ready; independent clean, editorial and runtime gates pending",
        "acceptedUnits": 16538, "firstPassReviewedUnits": 16538,
        "priorReview01Path": str(review01_path.relative_to(ROOT)),
        "priorReview01Sha256": sha(review01_path),
        "priorReview02Path": str(review02_path.relative_to(ROOT)),
        "priorReview02Sha256": sha(review02_path),
        "priorVerdictsPath": str(verdict_path.relative_to(ROOT)),
        "priorVerdictsSha256": sha(verdict_path),
        "priorClosurePath": str(old_path.relative_to(ROOT)), "priorClosureSha256": sha(old_path),
        "currentClosurePath": str(new_path.relative_to(ROOT)), "currentClosureSha256": sha(new_path),
        "correctionResultPath": str(result_path.relative_to(ROOT)),
        "correctionResultSha256": sha(result_path),
        "supplementaryRowsPath": str(supplementary_path.relative_to(ROOT)),
        "supplementaryRowsSha256": sha(supplementary_path),
        "boundedAffectedReviewPath": "Translations/bg/correction-cycle-003-bounded-review.json",
        "boundedAffectedReviewSha256": sha(BG / "correction-cycle-003-bounded-review.json"),
        "formula": "corrected IDs union (current closure minus exact verified prior independently read IDs) union explicitly invalidated prior IDs",
        "components": components,
        "priorReadingApplicability": {"review02ExactCount": prior_sources["review02Exact"],
                                       "review01OnlyExactCount": prior_sources["review01Exact"],
                                       "review02SupplementalExactReused": supplemental_reused,
                                       "review02SupplementalChanged": supplemental_changed,
                                       "priorClosureFullyReadIds": len(old_ids)},
        "invalidatedPriorReasons": [{"stableId": sid, "reasons": reasons[sid]}
                                    for sid in ordered(invalidated)],
        "retiredDependencyExplanation": "None: all 2686 prior closure IDs remain in the current closure; cumulative changed, context, repetition, referent, runtime and mandatory groups are retained.",
        "mandatoryRegressions": {"currentCount": len(mandatory),
                                 "retainedPriorIds": len(old_mandatory),
                                 "inNextReviewSet": len(mandatory & review_set),
                                 "groups": {name: {"count": row["count"], "idsSha256": row["idsSha256"]}
                                            for name, row in new["mandatoryRegressionGroups"].items()}},
        "currentAuthoredFiles": result["allAuthoredFiles"],
        "nextReviewRows": [r for r in new["reviewRows"] if r["stableId"] in review_set],
    }
    outputs[str(EVIDENCE.relative_to(ROOT))] = (json.dumps(evidence, ensure_ascii=False, indent=2) + "\n").encode()
    if args.action == "preview":
        print(json.dumps({name: row["count"] for name, row in components.items()}))
        return
    for rel, raw in outputs.items():
        path = ROOT / rel
        if args.action == "build":
            assert not path.exists(), "Immutable evidence already exists: " + rel
            path.write_bytes(raw)
        else:
            assert path.read_bytes() == raw, "Evidence drift: " + rel
    print(json.dumps({"action": args.action, "reviewIds": len(review_set),
                      "deltaSha256": sha(EVIDENCE), "retired": len(retired)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
