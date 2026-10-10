#!/usr/bin/env python3
"""Read-only Czech final-gate verifier; it never accepts or builds a locale."""

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "Scripts"))
from locale_text_inputs import current_text  # noqa: E402


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read(relative):
    return json.loads((ROOT / relative).read_text())


def check_refs(rows):
    seen = set()
    for row in rows:
        relative = row["path"]
        path = (ROOT / relative).resolve()
        need(path.is_relative_to(ROOT), "Evidence escaped checkout: " + relative)
        need(relative not in seen, "Duplicate evidence path: " + relative)
        seen.add(relative)
        need(digest(path) == row["sha256"], "Changed evidence: " + relative)
    return seen


def main():
    handoff = read("Translations/cs/final-gate/root-handoff.json")
    need(set(handoff) == {"locale", "acceptedUnits", "firstSemanticPassUnits",
                            "unresolvedObjectiveFindings", "independentClean",
                            "independentReviewer", "currentHashesUnchanged",
                            "mandatoryRegression", "structural", "derivedStatic",
                            "preserveExactReport", "authoredFiles", "evidenceFiles",
                            "remainingLimits"}, "Handoff schema differs")
    need(handoff["locale"] == "cs", "Wrong locale")
    need(handoff["acceptedUnits"] == handoff["firstSemanticPassUnits"] == 16538,
         "First-pass coverage differs")
    need(handoff["unresolvedObjectiveFindings"] == 0 and
         handoff["independentClean"] is True and
         handoff["independentReviewer"] == "/root/cs_independent_review_04" and
         handoff["currentHashesUnchanged"] is True, "Independent verdict differs")
    need(handoff["structural"] == {"rows": 16538, "result": "passed"} and
         handoff["derivedStatic"] == {"rows": 178, "result": "passed"},
         "Structural or static result differs")
    mandatory = handoff["mandatoryRegression"]
    need(mandatory == {"count": 178, "freshReads": 0,
                       "reusedUnchangedIndependentDecisions": 178,
                       "result": "passed"}, "Mandatory independent accounting differs")
    check_refs(handoff["evidenceFiles"])
    check_refs(handoff["authoredFiles"])
    plan = read("Translations/cs/final-gate/integration-plan.json")
    need(plan["authoredFileCount"] == len(plan["authoredFiles"]) == 411 and
         plan["evidenceFileCount"] == len(handoff["evidenceFiles"]) and
         plan["authoredFiles"] == handoff["authoredFiles"] and
         plan["evidenceFiles"] == [r for r in handoff["evidenceFiles"] if
                                   r["path"] != "Translations/cs/final-gate/integration-plan.json"],
         "Proposed integration path/hash set differs")

    values, files = current_text("cs", require_sidecars=False)
    need(len(values) == 16538 and files == handoff["authoredFiles"],
         "Current Czech text differs from handoff")
    exact_ref = handoff["preserveExactReport"]
    exact = read(exact_ref["path"])
    need(digest(ROOT / exact_ref["path"]) == exact_ref["sha256"] and
         exact["locale"] == "cs" and exact["checkedRows"] == 16538 and
         exact["exactResult"] == "passed" and exact["inputFiles"] == files and
         exact["manifestSha256"] == digest(ROOT / "Source/preserve-exactly-v4.json"),
         "Canonical preserve-exact receipt is stale")
    corpus = read("Translations/cs/semantic-correction-cycle-008-full-corpus-receipt.json")
    need(corpus["rows"] == 16538 and corpus["exactResult"] ==
         corpus["structuralResult"] == "passed" and corpus["authoredFiles"] == files,
         "Fresh locale-only corpus receipt is stale")
    for script, expected in corpus["owningValidators"].items():
        need(digest(ROOT / "Scripts" / script) == expected,
             "Owning validator changed: " + script)
    need(digest(ROOT / "Scripts/validate_locale_corpus.py") ==
         corpus["validatorSha256"], "Corpus validator changed")
    need(digest(ROOT / "Scripts/locale_text_inputs.py") ==
         corpus["inputLoaderSha256"], "Input loader changed")

    source = [json.loads(line) for line in
              (ROOT / "Source/localization-inventory-v3/strings.jsonl").open()]
    static_source = {r["stableId"]: r for r in
                     (json.loads(line) for line in
                      (ROOT / "Source/localization-inventory-v3/static-text.jsonl").open())}
    static_draft = read("Translations/cs/static-text-draft.json")
    need(len(static_draft["entries"]) == 178, "Static count differs")
    selected = ([r for r in source if r["collection"] == "UI"] +
                [r for r in source if r["collection"] == "ChecksDialogs" and
                 r["stableId"].endswith(":21377524158749")] +
                [r for r in source if r["collection"] == "Dialogs"] +
                [static_source[e["stableId"]] for e in static_draft["entries"]])
    accepted_ids = [r["stableId"] for r in selected]
    need(len(accepted_ids) == len(set(accepted_ids)) == 16538,
         "Accepted source scope differs")
    by_id = {r["stableId"]: r for r in selected}

    frozen = read("Translations/cs/semantic-review-first-pass-frozen.json")
    first = read("Translations/cs/final-gate/first-pass-coverage.json")
    need(frozen["reviewedUnits"] == first["acceptedReviewedUnits"] == 16538 and
         text_digest("".join(s + "\n" for s in accepted_ids)) ==
         frozen["reviewedPrefixIdsSha256"], "First-pass accepted-ID pin differs")
    historical = []
    for part in frozen["semanticEvidence"]:
        need(digest(ROOT / part["meta"]) == part["metaSha256"] and
             digest(ROOT / part["rows"]) == part["rowsSha256"],
             "First-pass evidence changed")
        historical.extend(json.loads(line) for line in (ROOT / part["rows"]).open())
    obsolete = frozen["obsoleteEvidence"]
    need(digest(ROOT / obsolete["path"]) == obsolete["sha256"] and
         len(historical) == 16539 and
         sum(r["stableId"] == obsolete["obsoleteStableId"] for r in historical) == 1,
         "Obsolete ChecksDialogs evidence differs")
    reviewed = [r for r in historical if r["stableId"] != obsolete["obsoleteStableId"]]
    need(len(reviewed) == 16538 and {r["stableId"] for r in reviewed} ==
         set(accepted_ids), "First-pass reviewed set differs")
    need(Counter(r["status"] for r in reviewed) ==
         {"reviewed-pass": 16457, "reviewed-finding": 70, "needs-context": 11},
         "First-pass status accounting differs")
    for row in reviewed:
        need(row["source"] == by_id[row["stableId"]]["source"] and
             text_digest(row["source"]) == row["sourceSha256"] and
             text_digest(row["target"]) == row["targetSha256"],
             "First-pass row changed: " + row["stableId"])

    chain = read("Translations/cs/final-gate/correction-chain.json")
    check_refs(chain["allCorrectionFilesAndRecipes"])
    need([s["appliedFullUnits"] for s in chain["stages"]] ==
         [76, 7, 7, 1, 4, 15, 1], "Correction sequence differs")
    closure = read("Translations/cs/semantic-correction-cycle-008-closure.json")
    need(len(closure["closureIds"]) == closure["closureCount"] == 1131 and
         not closure["topologyGaps"] and not closure["missingAcceptedIds"] and
         not closure["extraIds"], "Current closure is incomplete")
    need(closure["nextDeltaIds"] == closure["correctedIds"] and
         len(closure["correctedIds"]) == 1 and
         not closure["newDependencyIds"] and not closure["retiredDependencyIds"] and
         not closure["explicitInvalidatedPriorIds"], "Exact final delta differs")
    closure_rows = {r["stableId"]: r for r in closure["reviewRows"]}
    need(set(closure_rows) == set(closure["closureIds"]), "Closure rows differ")
    for sid, row in closure_rows.items():
        key = (row["collection"], sid) if row["collection"] == "StaticTMP" else \
              (row["collection"], int(sid.rsplit(":", 1)[1]))
        if row["collection"] == "StaticTMP":
            key = ("static", sid)
        need(text_digest(by_id[sid]["source"]) == row["sourceSha256"] and
             values[key] == row["target"] and
             text_digest(values[key]) == row["targetSha256"],
             "Current closure row changed: " + sid)

    review_dir = ROOT / "Translations/cs/independent-review-04"
    pins = json.loads((review_dir / "input-pins.json").read_text())
    for path, expected in pins["refs"].items():
        need(digest(ROOT / path) == expected, "Review04 context pin changed: " + path)
    need({r["path"]: r["sha256"] for r in files} == pins["authoredFiles"],
         "Review04 authored files changed")
    sealed = json.loads((review_dir / "evidence-manifest.json").read_text())
    check_refs(sealed["files"])
    verdict = json.loads((review_dir / "final-verdict.json").read_text())
    need(digest(review_dir / "final-verdict.json") ==
         "a70303bf5a86387c3d7461bc44f72d718f9c0cde8b85baae753f6830c8e3117b" and
         digest(review_dir / "evidence-manifest.json") ==
         "d167b63666638801e41feec6ccfe0a08a899109d072b8773174f99e6124efd83" and
         verdict["objectiveFindings"] == 0 and
         verdict["closureSha256"] == digest(ROOT / "Translations/cs/semantic-correction-cycle-008-closure.json"),
         "Review04 clean verdict is inapplicable")
    fresh = [json.loads(line) for line in (review_dir / "reviewed-rows.jsonl").open()]
    retained = json.loads((review_dir / "prior-decision-applicability.json").read_text())["retainedDecisionRows"]
    need(len(fresh) == 1 and len(retained) == 1130 and
         {r["stableId"] for r in fresh + retained} == set(closure_rows),
         "Independent closure decision coverage differs")
    for row in fresh + retained:
        target = closure_rows[row["stableId"]]
        need(row["sourceSha256"] == target["sourceSha256"] and
             row["targetSha256"] == target["targetSha256"],
             "Independent row no longer matches: " + row["stableId"])
    regression = json.loads((review_dir / "regression-result.json").read_text())
    ids = regression["ids"]
    need(len(ids) == len(set(ids)) == len(regression["decisionRows"]) == 178 and
         set(ids) == {r["stableId"] for r in regression["decisionRows"]} and
         len(regression["groups"]) == 12 and regression["freshSemanticRereads"] == 0,
         "Mandatory catalog accounting differs")
    for row in regression["decisionRows"]:
        current = closure_rows[row["stableId"]]
        need((row["sourceSha256"], row["targetSha256"]) ==
             (current["sourceSha256"], current["targetSha256"]),
             "Mandatory row changed: " + row["stableId"])

    derived = read("Translations/cs/final-gate/derived-text.json")
    need(derived["staticRows"] == 178 and derived["creditsRoleCells"] == 93 and
         derived["commonOptionPhrases"] == 26 and
         derived["commonOptionExpandedRows"] == 2763 and
         derived["correctionClosureRepetitionIds"] == 111,
         "Static or repetition derivation differs")
    phrases = read("Translations/cs/common-options-001.authored.json")["phrases"]
    dialogs = [r for r in source if r["collection"] == "Dialogs"]
    need(len(phrases) == 26, "Common option recipe differs")
    for phrase in phrases:
        matches = [r for r in dialogs if r["source"] == phrase["source"]]
        need(len(matches) == phrase["expectedRows"], "Option repetition count differs")
        for row in matches:
            key = ("Dialogs", int(row["stableId"].rsplit(":", 1)[1]))
            need(values[key] == phrase["target"], "Option expansion changed")

    boundary = read("Translations/cs/final-gate/integration-boundary.json")
    sidecar = read(boundary["staleSidecarPath"])
    need(sidecar["batchSha256"] == boundary["sidecarBatchSha256"] and
         digest(ROOT / boundary["currentBatchPath"]) ==
         boundary["currentBatchSha256"], "Recorded acceptance boundary changed")
    print(json.dumps({"locale": "cs", "finalGate": "passed",
                      "acceptedTextUnits": 16538, "currentAuthoredFiles": 411,
                      "firstSemanticUnits": 16538, "closureRows": 1131,
                      "independentFresh": 1, "independentPrior": 1130,
                      "mandatoryUniqueIds": 178,
                      "canonicalPreserveExact": "passed",
                      "rootAcceptance": "pending shared sidecar-boundary resolution"}))


if __name__ == "__main__":
    main()
