#!/usr/bin/env python3
"""Bind cycle-03 structural evidence and its exact independent delta handoff."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CYCLE = Path(__file__).resolve().parent
HE = CYCLE.parent
PRIOR = HE / "semantic-correction-cycle-02"
IR = HE / "independent-review-02"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_set(rows):
    return hashlib.sha256("".join(x["path"] + "\t" + x["sha256"] + "\n" for x in rows).encode()).hexdigest()


def once(path, obj):
    data = (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode()
    if path.exists():
        assert path.read_bytes() == data, f"immutable evidence differs: {path}"
    else:
        path.write_bytes(data)


def ref(path, **extra):
    return {"path": str(path.relative_to(ROOT)), "sha256": sha(path), **extra}


def main():
    pins = json.loads((CYCLE / "input-pins.json").read_text())
    g0 = json.loads((CYCLE / "baseline-progress.json").read_text())
    s0 = json.loads((CYCLE / "baseline-semantic-review-progress.json").read_text())
    pre = json.loads((CYCLE / "preflight.json").read_text())
    app = json.loads((CYCLE / "application.json").read_text())
    post = json.loads((CYCLE / "post-validation-summary.json").read_text())
    exact = json.loads((CYCLE / "preserve-exact-v4.json").read_text())
    closure = json.loads((CYCLE / "closure-manifest.json").read_text())
    consumer = json.loads((CYCLE / "consumer-preflight.json").read_text())
    scope = json.loads((CYCLE / "remedial-scope.json").read_text())
    review = json.loads((IR / "final-review.json").read_text())
    assert s0["acceptedUnits"] == s0["reviewedUnits"] == 16538
    assert len(s0["firstPassFindings"]) == 120
    assert sha(CYCLE / "baseline-progress.json") == pins["priorProgressSha256"]
    assert sha(CYCLE / "baseline-semantic-review-progress.json") == pins["priorSemanticProgressSha256"]
    assert sha(IR / "final-review.json") == pins["independentFinalReviewSha256"]
    assert sha(IR / "final-findings.json") == pins["independentFinalFindingsSha256"]
    assert sha(IR / "complete-review-decisions.json") == pins["independentDecisionsSha256"]
    assert review["verdict"] == "corrections required" and review["editorialAcceptance"] is False
    assert sha(CYCLE / "authored_wording.py") == pins["authoredWordingSha256"]
    assert pre["acceptedCorrections"] == app["changedStableIds"] == 71
    assert app["status"] == "applied" and post["status"] == "passed on applied authored files"
    assert pre["changedAuthoredFiles"] == post["validatedFiles"] == 9
    assert exact["checkedRows"] == 16538 and exact["exactResult"] == "passed"
    assert closure["changedIds"]["count"] == 71
    assert closure["previousClosureIds"]["count"] == 2191
    assert closure["closureIds"]["count"] == 2382
    assert closure["newClosureIds"]["count"] == 191
    assert closure["explicitlyInvalidatedIds"]["count"] == 66
    assert closure["retiredIds"]["count"] == 0
    assert closure["deltaIds"]["count"] == 269
    for key in ("changedIds", "previousClosureIds", "closureIds", "newClosureIds",
                "explicitlyInvalidatedIds", "retiredIds", "deltaIds", "reviewRows",
                "deltaReviewRows", "runtimeContext"):
        assert sha(ROOT / closure[key]["path"]) == closure[key]["sha256"]
    for item in closure["components"].values():
        assert sha(ROOT / item["path"]) == item["sha256"]
    assert sha(CYCLE / "build_closure.py") == closure["selectorScriptSha256"]
    assert consumer["branchCount"] == 4 and consumer["assembledVariants"] == 13
    assert scope["Nun"]["scopedRows"] == 142 and scope["Nun"]["correctedRows"] == 63
    assert scope["Bald"]["scopedProfanityRows"] == 30
    assert sha(ROOT / pins["sourceInventory"]["stringsPath"]) == pins["sourceInventory"]["stringsSha256"]
    assert sha(ROOT / pins["sourceInventory"]["staticPath"]) == pins["sourceInventory"]["staticSha256"]
    assert sha(ROOT / pins["sourceInventory"]["preserveExactPath"]) == pins["sourceInventory"]["preserveExactSha256"]
    assert sha(Path(pins["glossary"]["path"])) == pins["glossary"]["sha256"]
    for rel, x in pre["files"].items():
        assert sha(ROOT / rel) == x["afterSha256"]
    for x in g0["files"]:
        expected = pre["files"][x["path"]]["afterSha256"] if x["path"] in pre["files"] else x["sha256"]
        assert sha(ROOT / x["path"]) == expected
    authored, sidecars = [], []
    for x in exact["inputFiles"]:
        path = ROOT / x["path"]
        assert sha(path) == x["sha256"]
        authored.append(x)
        side = path.with_suffix(".validation.json")
        report = json.loads(side.read_text())
        assert report["structuralResult"] == "passed"
        assert report.get("batchSha256", report.get("draftSha256")) == x["sha256"]
        sidecars.append({"path": str(side.relative_to(ROOT)), "sha256": sha(side)})
    assert len(authored) == len(sidecars) == 337
    assert len({x["path"] for x in authored}) == len({x["path"] for x in sidecars}) == 337
    context = json.loads((CYCLE / "runtime-context.json").read_text())
    for name, record in context["derivedMaps"].items():
        assert sha(HE / name) == record["sha256"] and not record["affectedPhrases"]
    assert sha(HE / "static-text-draft.json") == context["staticCredits"]["sha256"]
    structural = {"schemaVersion": 1, "status": "passed; structural evidence only",
        "acceptedUnits": 16538, "authoredUnits": 16538, "currentValidatedFiles": 337,
        "changedValidatedFiles": 9,
        "sourceInventorySha256": pins["sourceInventory"]["stringsSha256"],
        "staticInventorySha256": pins["sourceInventory"]["staticSha256"],
        "preserveExactManifestSha256": pins["sourceInventory"]["preserveExactSha256"],
        "glossarySha256": pins["glossary"]["sha256"],
        "preserveExactReport": ref(CYCLE / "preserve-exact-v4.json", checkedRows=16538),
        "postValidation": ref(CYCLE / "post-validation-summary.json", validatedFiles=9),
        "consumerPreflight": ref(CYCLE / "consumer-preflight.json", branches=4, variants=13),
        "remedialScope": ref(CYCLE / "remedial-scope.json", nunRows=142, baldProfanityRows=30),
        "authoredFileSetSha256": hash_set(authored), "sidecarFileSetSha256": hash_set(sidecars),
        "authoredFiles": authored, "sidecars": sidecars,
        "derivedMapHashes": context["derivedMaps"],
        "creditsApplicationSha256": sha(HE / "credits-application.json"),
        "staticCreditsSha256": sha(HE / "static-text-draft.json"),
        "semanticReview": "original complete first pass preserved; independent cycle-02 corrections applied; cycle-03 delta pending",
        "runtime": "not-run per owner instruction"}
    once(CYCLE / "full-structural-diff.json", structural)
    delta_ids = (CYCLE / "delta-ids.txt").read_text().splitlines()
    assert len(delta_ids) == 269
    handoff = {"schemaVersion": 1, "locale": "he", "gameVersion": "1.3.19",
        "sourceLocale": "ru", "acceptedUnits": 16538,
        "status": "ready for independent cycle-03 exact delta review; no cycle-03 verdict",
        "priorIndependentReviewer": review["reviewer"],
        "priorIndependentVerdict": review["verdict"],
        "priorIndependentReview": ref(IR / "final-review.json"),
        "priorIndependentFindings": ref(IR / "final-findings.json", count=7),
        "priorIndependentDecisions": ref(IR / "complete-review-decisions.json", reviewedRows=194),
        "priorClosure": ref(PRIOR / "closure-manifest.json", count=2191),
        "firstSemanticPass": ref(HE / "semantic-correction-cycle-01" / "baseline-semantic-review-progress.json", reviewedUnits=16538),
        "sourceInventory": {"path": pins["sourceInventory"]["stringsPath"], "sha256": pins["sourceInventory"]["stringsSha256"]},
        "staticSource": {"path": pins["sourceInventory"]["staticPath"], "sha256": pins["sourceInventory"]["staticSha256"]},
        "approvedGlossary": pins["glossary"],
        "preserveExactManifest": {"path": pins["sourceInventory"]["preserveExactPath"], "sha256": pins["sourceInventory"]["preserveExactSha256"]},
        "reviewerDecisionReconciliation": ref(CYCLE / "reviewer-decision-reconciliation.json", rows=194),
        "adjudications": ref(CYCLE / "adjudications.json", accepted=71),
        "remedialScope": ref(CYCLE / "remedial-scope.json", nunRows=142, baldProfanityRows=30),
        "preflight": ref(CYCLE / "preflight.json"),
        "consumerPreflight": ref(CYCLE / "consumer-preflight.json"),
        "application": ref(CYCLE / "application.json"),
        "postValidation": ref(CYCLE / "post-validation-summary.json"),
        "fullStructuralDiff": ref(CYCLE / "full-structural-diff.json"),
        "closureManifest": ref(CYCLE / "closure-manifest.json", closureCount=2382),
        "changedIds": closure["changedIds"], "newClosureIds": closure["newClosureIds"],
        "explicitlyInvalidatedIds": closure["explicitlyInvalidatedIds"],
        "retiredIds": closure["retiredIds"], "deltaIds": closure["deltaIds"],
        "deltaReviewRows": closure["deltaReviewRows"],
        "firstDeltaId": delta_ids[0], "deltaReviewCount": 269,
        "reviewInstruction": "A distinct Hebrew reviewer should compare exactly the 269 delta-review-rows.jsonl units against the pinned full Russian units, approved glossary, compiled scene and resident domains. The set is 71 corrected IDs plus 191 new closure IDs plus 66 explicitly invalidated prior IDs, with 59 corrected IDs also new. Check all 549 mandatory regression catalog IDs on unchanged current hashes, reusing valid prior decisions and reading affected ones. Do not automatically reread the unchanged prior closure. A clean independent verdict remains required before editorial acceptance.",
        "sourceDomainConflict": "Fan/Luka fixed Russian masculine conflicts with configured female resident alternatives; neutral Hebrew does not infer canonical gender.",
        "unresolvedConsumer": "characterName_Twins still lacks an exact accepted UI key; its runtime display fallback remains unverified.",
        "imagesTextures": "excluded by owner text-only scope",
        "runtime": "not-run per owner instruction", "visual": "not-run", "editorialAcceptance": False}
    once(CYCLE / "independent-review-handoff.json", handoff)
    sp, gp = HE / "semantic-review-progress.json", HE / "progress.json"
    current_s = json.loads(sp.read_text())
    if current_s.get("postCorrection", {}).get("cycle") == 3:
        assert current_s["postCorrection"]["handoffSha256"] == sha(CYCLE / "independent-review-handoff.json")
        assert current_s["firstPassFindings"] == s0["firstPassFindings"]
    else:
        assert current_s == s0
        current_s["status"] = "first semantic pass preserved; independent cycles 01 and 02 requested changes; consolidated cycle-03 corrections applied; exact delta review pending"
        current_s["postCorrection"] = {"cycle": 3,
            "previousCycleHandoffPath": s0["postCorrection"]["handoffPath"],
            "previousCycleHandoffSha256": s0["postCorrection"]["handoffSha256"],
            "priorIndependentReviewPath": str((IR / "final-review.json").relative_to(ROOT)),
            "priorIndependentReviewSha256": sha(IR / "final-review.json"),
            "handoffPath": str((CYCLE / "independent-review-handoff.json").relative_to(ROOT)),
            "handoffSha256": sha(CYCLE / "independent-review-handoff.json"),
            "changedIds": 71, "previousClosureIds": 2191, "closureIds": 2382,
            "newClosureIds": 191, "explicitlyInvalidatedIds": 66,
            "retiredIds": 0, "deltaIds": 269,
            "currentAuthoredFileSetSha256": structural["authoredFileSetSha256"]}
        current_s["next"] = {"path": str((CYCLE / "delta-ids.txt").relative_to(ROOT)),
            "firstId": delta_ids[0], "withinFileOffset": 0, "reviewUnits": 269,
            "instruction": "Distinct independent source-to-target delta review; preserve immutable original first pass and prior review decisions."}
        current_s["correctionBatchStatus"] = "71/71 objective cycle-03 corrections adjudicated and applied together; 9 authored files changed; complete current structure and preserve-exact checks passed"
        current_s["independentReview"] = "cycle-02 complete with seven consolidated findings; cycle-03 exact delta pending; no clean verdict"
        current_s["updatedAt"] = datetime.now(timezone.utc).isoformat()
        sp.write_text(json.dumps(current_s, ensure_ascii=False, indent=2) + "\n")
    current_g = json.loads(gp.read_text())
    if current_g["validation"]["semanticReviewProgressSha256"] == sha(sp):
        assert current_g["nextAction"].startswith("Hand off cycle-03")
    else:
        assert current_g == g0
        for x in current_g["files"]:
            if x["path"] in pre["files"]:
                x["sha256"] = pre["files"][x["path"]]["afterSha256"]
            assert sha(ROOT / x["path"]) == x["sha256"]
        v = current_g["validation"]
        v["sourceTargetSemanticAudit"] = "first complete 16538-unit semantic pass preserved; seven independent cycle-02 findings plus 64 bounded Nun/Bald findings adjudicated and applied in one cycle-03 batch"
        v["dialogueBatchStructural"] = "passed for all current Hebrew dialogue batches; 9 cycle-03 changed files revalidated with current sidecars"
        v["preserveExact"] = "passed for all 16538 current authored units against pinned manifest"
        v["preserveExactReportPath"] = str((CYCLE / "preserve-exact-v4.json").relative_to(ROOT))
        v["preserveExactReportSha256"] = sha(CYCLE / "preserve-exact-v4.json")
        v["independentDiffAudit"] = "cycle-02 independent review complete with corrections required; cycle-03 269-ID exact delta pending"
        v["independentDiffReportPath"] = str((CYCLE / "full-structural-diff.json").relative_to(ROOT))
        v["independentDiffReportSha256"] = sha(CYCLE / "full-structural-diff.json")
        v["semanticReviewProgressSha256"] = sha(sp)
        v["readinessScan"] = "16538/16538 current authored units and 337/337 sidecars validated; 0 structural problems; no shared-state update"
        current_g["stages"]["editorial"] = "first semantic pass complete; independent cycle-02 requested changes; 71-ID consolidated cycle-03 correction complete; 269-ID delta and clean independent verdict pending"
        current_g["openItems"] = [
            "Distinct independent review of the 269-ID cycle-03 exact delta and mandatory regressions on unchanged hashes; record reviewer identity and verdict.",
            "Verify characterName_Twins runtime fallback if that dynamic variant is exercised; static source contains no exact UI key.",
            "Hebrew runtime, visual, font/RTL and package checks remain outside this owner-restricted text-only task."]
        current_g["nextAction"] = ("Hand off cycle-03 " + str((CYCLE / "independent-review-handoff.json").relative_to(ROOT)) +
                                   " at SHA-256 " + sha(CYCLE / "independent-review-handoff.json") +
                                   "; exact delta starts at " + delta_ids[0] + ".")
        current_g["updatedAt"] = current_s["updatedAt"]
        gp.write_text(json.dumps(current_g, ensure_ascii=False, indent=2) + "\n")
    assert sha(sp) == json.loads(gp.read_text())["validation"]["semanticReviewProgressSha256"]
    assert current_s["firstPassFindings"] == s0["firstPassFindings"]
    print(json.dumps({"authoredUnits": 16538, "sidecars": 337, "deltaIds": 269,
        "handoffSha256": sha(CYCLE / "independent-review-handoff.json"),
        "semanticProgressSha256": sha(sp), "progressSha256": sha(gp)}))


if __name__ == "__main__":
    main()
