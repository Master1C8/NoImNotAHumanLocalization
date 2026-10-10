#!/usr/bin/env python3
"""Reproduce the exact Bulgarian cycle-002 independent review delta."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BG = ROOT / "Translations/bg"
EVIDENCE = BG / "semantic-delta-cycle-002.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload(ids):
    return ("\n".join(ids) + ("\n" if ids else "")).encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preview", "build", "verify"))
    args = parser.parse_args()
    old_path = BG / "semantic-closure-cycle-001.json"
    new_path = BG / "semantic-closure-cycle-002.json"
    review_path = BG / "independent-review-01/review.json"
    result_path = BG / "correction-batch-002-result.json"
    candidate_path = BG / "voice-remedial-candidates-v4.json"
    old, new, review, result = [json.loads(p.read_text()) for p in
                                (old_path, new_path, review_path, result_path)]
    assert review["closureSha256"] == digest(old_path)
    assert review["coverage"]["closurePairsRead"] == 1506
    assert digest(ROOT / review["coverage"]["readIdsPath"]) == review["coverage"]["readIdsSha256"]
    assert (ROOT / review["coverage"]["readIdsPath"]).read_bytes() == (BG / "semantic-cycle-001-closure.ids").read_bytes()
    assert new["correctionResultSha256"] == digest(result_path)
    assert new["components"]["closure"]["count"] == 2686
    assert digest(candidate_path) == new["pinnedInputs"]["Translations/bg/voice-remedial-candidates-v4.json"]
    prior = set(old["components"]["closure"]["ids"])
    current = set(new["components"]["closure"]["ids"])
    corrected = set(result["changedIds"])
    context = set(new["components"]["context"]["ids"])
    repetitions = set(new["components"]["repetitions"]["ids"])
    referents = {name: set(row["ids"]) for name, row in new["glossaryReferentGroups"].items()}
    touched = sorted(name for name, ids in referents.items()
                     if name != "vulgarCharacterVoice" and ids & corrected)
    reasons = {}
    for sid in prior - corrected:
        why = []
        if sid in context:
            why.append("shares a Yarn scene or UI context with a newly corrected unit")
        if sid in repetitions:
            why.append("same exact Russian source as a corrected unit in the cumulative dependency recipe")
        if sid in referents["vulgarCharacterVoice"]:
            why.append("canonical voice selector replaced a five-speaker partial selector after systemic register findings")
        for name in touched:
            if sid in referents[name]:
                why.append("corrected glossary/referent dependency: " + name)
        if why:
            reasons[sid] = why
    invalidated = set(reasons)
    newly_selected = current - prior
    retired = prior - current
    assert not retired, "Prior dependency unexpectedly retired; explain before handoff"
    review_set = corrected | newly_selected | invalidated
    assert review_set <= current
    rank = {row["stableId"]: row["sourceIndex"] for row in new["reviewRows"]}
    assert len(rank) == len(current)
    ordered = lambda values: sorted(values, key=rank.__getitem__)
    outputs = {}
    components = {}
    for name, ids in (("corrected", corrected), ("newClosure", newly_selected),
                      ("invalidatedPrior", invalidated), ("retired", retired),
                      ("review", review_set)):
        relpath = f"Translations/bg/semantic-cycle-002-{name}.ids"
        raw = payload(ordered(ids))
        outputs[relpath] = raw
        components[name] = {"path": relpath, "count": len(ids),
                            "sha256": hashlib.sha256(raw).hexdigest(), "ids": ordered(ids)}
    mandatory = set(new["components"]["mandatoryRegressions"]["ids"])
    old_mandatory = set(old["components"]["mandatoryRegressions"]["ids"])
    assert old_mandatory <= mandatory
    evidence = {
        "schemaVersion": 1, "locale": "bg", "gameVersion": "1.3.19",
        "status": "exact independent cycle-002 delta ready; no independent clean review or editorial acceptance",
        "acceptedUnits": 16538, "firstPassReviewedUnits": 16538,
        "priorReviewPath": str(review_path.relative_to(ROOT)), "priorReviewSha256": digest(review_path),
        "priorReviewedClosurePath": str(old_path.relative_to(ROOT)),
        "priorReviewedClosureSha256": digest(old_path),
        "currentClosurePath": str(new_path.relative_to(ROOT)), "currentClosureSha256": digest(new_path),
        "correctionResultPath": str(result_path.relative_to(ROOT)),
        "correctionResultSha256": digest(result_path),
        "voiceCandidatePath": str(candidate_path.relative_to(ROOT)),
        "voiceCandidateSha256": digest(candidate_path),
        "formula": "corrected IDs union (current closure minus previous independently reviewed closure) union explicitly invalidated prior IDs",
        "components": components,
        "invalidatedPriorReasons": [{"stableId": sid, "reasons": reasons[sid]}
                                    for sid in ordered(invalidated)],
        "touchedReferentRules": touched,
        "retiredDependencyExplanation": "None: the cycle-002 recipe retains all 60 prior corrected IDs, their applicable context/repetition/referent/runtime dependencies, and every prior mandatory regression ID.",
        "mandatoryRegressions": {
            "currentCount": len(mandatory), "priorCount": len(old_mandatory),
            "currentIdsSha256": new["components"]["mandatoryRegressions"]["sha256"],
            "retainedPriorIds": len(old_mandatory),
            "inNextReviewSet": len(mandatory & review_set),
            "groups": {name: {"count": row["count"], "idsSha256": row["idsSha256"]}
                       for name, row in new["mandatoryRegressionGroups"].items()},
        },
        "priorSupplementaryRead": {
            "idsPath": review["coverage"]["supplementaryIdsPath"],
            "idsSha256": review["coverage"]["supplementaryIdsSha256"],
            "count": review["coverage"]["supplementaryPairsRead"],
            "note": "These 50 readings were outside the previous 1506-ID reviewed closure; their IDs remain in the new-closure term when selected."
        },
        "currentAuthoredFiles": result["allAuthoredFiles"],
        "nextReviewRows": [row for row in new["reviewRows"] if row["stableId"] in review_set],
    }
    outputs[str(EVIDENCE.relative_to(ROOT))] = (json.dumps(evidence, ensure_ascii=False, indent=2) + "\n").encode()
    if args.action == "preview":
        print(json.dumps({name: row["count"] for name, row in components.items()}))
        return
    for relpath, raw in outputs.items():
        path = ROOT / relpath
        if args.action == "build":
            assert not path.exists(), "Immutable evidence already exists: " + relpath
            path.write_bytes(raw)
        else:
            assert path.read_bytes() == raw, "Evidence drift: " + relpath
    print(json.dumps({"action": args.action, "reviewIds": len(review_set),
                      "deltaSha256": digest(EVIDENCE), "retired": len(retired)}))


if __name__ == "__main__":
    main()
