#!/usr/bin/env python3
"""Bind cycle-02 structural evidence and the exact independent delta handoff."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CYCLE = Path(__file__).resolve().parent
HE = CYCLE.parent
IR = HE / "independent-review-01"
PRIOR = HE / "semantic-correction-cycle-01"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_set(rows):
    data = "".join(x["path"] + "\t" + x["sha256"] + "\n" for x in rows).encode()
    return hashlib.sha256(data).hexdigest()


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
    baseline_g = json.loads((CYCLE / "baseline-progress.json").read_text())
    baseline_s = json.loads((CYCLE / "baseline-semantic-review-progress.json").read_text())
    pre = json.loads((CYCLE / "preflight.json").read_text())
    app = json.loads((CYCLE / "application.json").read_text())
    post = json.loads((CYCLE / "post-validation-summary.json").read_text())
    exact = json.loads((CYCLE / "preserve-exact-v4.json").read_text())
    closure = json.loads((CYCLE / "closure-manifest.json").read_text())
    consumer = json.loads((CYCLE / "consumer-preflight.json").read_text())
    reviewer = json.loads((IR / "final-review.json").read_text())
    assert baseline_s["reviewedUnits"] == baseline_s["acceptedUnits"] == 16538
    assert len(baseline_s["firstPassFindings"]) == 120
    assert pins["priorProgressSha256"] == sha(CYCLE / "baseline-progress.json")
    assert pins["priorSemanticProgressSha256"] == sha(CYCLE / "baseline-semantic-review-progress.json")
    assert sha(IR / "final-review.json") == pins["independentFinalReviewSha256"]
    assert sha(IR / "final-findings.json") == pins["independentFinalFindingsSha256"]
    assert reviewer["verdict"] == "corrections required" and reviewer["editorialAcceptance"] is False
    assert pre["acceptedFindings"] == app["changedStableIds"] == 31
    assert app["status"] == "applied" and post["status"] == "passed on applied authored files"
    assert post["validatedFiles"] == pre["changedAuthoredFiles"] == 24
    assert exact["checkedRows"] == 16538 and exact["exactResult"] == "passed"
    assert closure["changedIds"]["count"] == 31
    assert closure["previousClosureIds"]["count"] == 2111
    assert closure["newClosureIds"]["count"] == 80
    assert closure["explicitlyInvalidatedIds"]["count"] == 83
    assert closure["retiredIds"]["count"] == 0
    assert closure["deltaIds"]["count"] == 194
    for key in ("changedIds", "previousClosureIds", "closureIds", "newClosureIds",
                "explicitlyInvalidatedIds", "retiredIds", "deltaIds", "reviewRows",
                "deltaReviewRows", "runtimeContext"):
        x = closure[key]
        assert sha(ROOT / x["path"]) == x["sha256"]
    for component in closure["components"].values():
        assert sha(ROOT / component["path"]) == component["sha256"]
    assert sha(CYCLE / "build_closure.py") == closure["selectorScriptSha256"]
    assert sha(CYCLE / "consumer-preflight.json") == app["consumerPreflightSha256"]
    assert consumer["correctedFormatRows"] == 15
    assert len(consumer["unresolvedCharacterLabels"]) == 1
    assert consumer["unresolvedCharacterLabels"][0]["character"] == "Twins"
    assert sha(ROOT / pins["sourceInventory"]["stringsPath"]) == pins["sourceInventory"]["stringsSha256"]
    assert sha(ROOT / pins["sourceInventory"]["staticPath"]) == pins["sourceInventory"]["staticSha256"]
    assert sha(ROOT / pins["sourceInventory"]["preserveExactPath"]) == pins["sourceInventory"]["preserveExactSha256"]
    assert sha(Path(pins["glossary"]["path"])) == pins["glossary"]["sha256"]
    for rel, row in pre["files"].items():
        assert sha(ROOT / rel) == row["afterSha256"]
    for x in baseline_g["files"]:
        path = ROOT / x["path"]
        expected = pre["files"][x["path"]]["afterSha256"] if x["path"] in pre["files"] else x["sha256"]
        assert sha(path) == expected
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
    assert len({x["path"] for x in authored}) == 337
    assert len({x["path"] for x in sidecars}) == 337
    runtime = json.loads((CYCLE / "runtime-context.json").read_text())
    for name, record in runtime["derivedMaps"].items():
        assert sha(HE / name) == record["sha256"] and not record["affectedPhrases"]
    assert sha(HE / "static-text-draft.json") == runtime["staticCredits"]["sha256"]
    structural = {"schemaVersion": 1, "status": "passed; structural evidence only",
        "acceptedUnits": 16538, "authoredUnits": 16538, "currentValidatedFiles": 337,
        "changedValidatedFiles": 24,
        "sourceInventorySha256": pins["sourceInventory"]["stringsSha256"],
        "staticInventorySha256": pins["sourceInventory"]["staticSha256"],
        "preserveExactManifestSha256": pins["sourceInventory"]["preserveExactSha256"],
        "glossarySha256": pins["glossary"]["sha256"],
        "preserveExactReport": ref(CYCLE / "preserve-exact-v4.json", checkedRows=16538),
        "postValidation": ref(CYCLE / "post-validation-summary.json", validatedFiles=24),
        "consumerPreflight": ref(CYCLE / "consumer-preflight.json", formatRows=15),
        "authoredFileSetSha256": hash_set(authored),
        "sidecarFileSetSha256": hash_set(sidecars),
        "authoredFiles": authored, "sidecars": sidecars,
        "derivedMapHashes": runtime["derivedMaps"],
        "creditsApplicationSha256": sha(HE / "credits-application.json"),
        "staticCreditsSha256": sha(HE / "static-text-draft.json"),
        "firstSemanticPass": "complete on immutable original baseline",
        "independentReview": "cycle-01 corrections required; cycle-02 exact delta pending",
        "runtime": "not-run per owner instruction"}
    once(CYCLE / "full-structural-diff.json", structural)
    delta_ids = (CYCLE / "delta-ids.txt").read_text().splitlines()
    assert len(delta_ids) == 194
    handoff = {"schemaVersion": 1, "locale": "he", "gameVersion": "1.3.19",
        "sourceLocale": "ru", "acceptedUnits": 16538,
        "status": "ready for independent cycle-02 exact delta review; no cycle-02 verdict",
        "priorIndependentReviewer": reviewer["reviewer"],
        "priorIndependentVerdict": reviewer["verdict"],
        "priorIndependentReview": ref(IR / "final-review.json"),
        "priorIndependentFindings": ref(IR / "final-findings.json", count=31),
        "priorIndependentDecisions": ref(IR / "complete-review-decisions.json", reviewedRows=2111),
        "priorClosure": ref(PRIOR / "closure-manifest.json", count=2111),
        "firstSemanticPass": ref(PRIOR / "baseline-semantic-review-progress.json", reviewedUnits=16538),
        "sourceInventory": {"path": pins["sourceInventory"]["stringsPath"],
                            "sha256": pins["sourceInventory"]["stringsSha256"]},
        "staticSource": {"path": pins["sourceInventory"]["staticPath"],
                         "sha256": pins["sourceInventory"]["staticSha256"]},
        "approvedGlossary": pins["glossary"],
        "preserveExactManifest": {"path": pins["sourceInventory"]["preserveExactPath"],
                                  "sha256": pins["sourceInventory"]["preserveExactSha256"]},
        "adjudications": ref(CYCLE / "adjudications.json", accepted=31),
        "preflight": ref(CYCLE / "preflight.json"),
        "consumerPreflight": ref(CYCLE / "consumer-preflight.json"),
        "application": ref(CYCLE / "application.json"),
        "postValidation": ref(CYCLE / "post-validation-summary.json"),
        "fullStructuralDiff": ref(CYCLE / "full-structural-diff.json"),
        "closureManifest": ref(CYCLE / "closure-manifest.json", closureCount=closure["closureIds"]["count"]),
        "changedIds": closure["changedIds"],
        "newClosureIds": closure["newClosureIds"],
        "explicitlyInvalidatedIds": closure["explicitlyInvalidatedIds"],
        "retiredIds": closure["retiredIds"],
        "deltaIds": closure["deltaIds"],
        "deltaReviewRows": closure["deltaReviewRows"],
        "firstDeltaId": delta_ids[0], "deltaReviewCount": len(delta_ids),
        "reviewInstruction": "A distinct Hebrew reviewer should compare exactly the 194 delta-review-rows.jsonl units to the pinned Russian source, glossary, prior decision context and actual scene/consumer outputs. Check corrected lines, 80 new dependencies and 83 explicitly invalidated prior rows in canonical order, plus the stable mandatory regression catalog on unchanged artifact hashes. Do not reread the other 1997 prior-closure rows automatically. A clean independent verdict is still required before editorial acceptance.",
        "unresolvedConsumer": "characterName_Twins has no exact accepted UI key; static domain evidence does not establish its displayed runtime fallback.",
        "imagesTextures": "excluded by owner text-only scope",
        "runtime": "not-run per owner instruction", "visual": "not-run",
        "editorialAcceptance": False}
    once(CYCLE / "independent-review-handoff.json", handoff)
    sp, gp = HE / "semantic-review-progress.json", HE / "progress.json"
    current_s = json.loads(sp.read_text())
    if current_s.get("postCorrection", {}).get("cycle") == 2:
        assert current_s["postCorrection"]["handoffSha256"] == sha(CYCLE / "independent-review-handoff.json")
        assert current_s["firstPassFindings"] == baseline_s["firstPassFindings"]
    else:
        assert current_s == baseline_s
        current_s["status"] = "first semantic pass complete on immutable baseline; independent cycle-01 review requested changes; cycle-02 corrections applied; exact delta review pending"
        current_s["postCorrection"] = {"cycle": 2,
            "previousCycleHandoffPath": baseline_s["postCorrection"]["handoffPath"],
            "previousCycleHandoffSha256": baseline_s["postCorrection"]["handoffSha256"],
            "priorIndependentReviewPath": str((IR / "final-review.json").relative_to(ROOT)),
            "priorIndependentReviewSha256": sha(IR / "final-review.json"),
            "handoffPath": str((CYCLE / "independent-review-handoff.json").relative_to(ROOT)),
            "handoffSha256": sha(CYCLE / "independent-review-handoff.json"),
            "changedIds": 31, "previousClosureIds": 2111,
            "newClosureIds": 80, "explicitlyInvalidatedIds": 83,
            "retiredIds": 0, "deltaIds": 194,
            "currentAuthoredFileSetSha256": structural["authoredFileSetSha256"]}
        current_s["next"] = {"path": str((CYCLE / "delta-ids.txt").relative_to(ROOT)),
            "firstId": delta_ids[0], "withinFileOffset": 0, "reviewUnits": 194,
            "instruction": "Distinct independent source-to-target delta review; preserve immutable first pass and cycle-01 decisions."}
        current_s["correctionBatchStatus"] = "31/31 objective independent findings adjudicated and applied in cycle 02; 24 authored files changed; all current structural and preserve-exact checks passed"
        current_s["independentReview"] = "cycle-01 complete with corrections required; cycle-02 exact delta pending; no clean verdict"
        current_s["updatedAt"] = datetime.now(timezone.utc).isoformat()
        sp.write_text(json.dumps(current_s, ensure_ascii=False, indent=2) + "\n")
    current_g = json.loads(gp.read_text())
    if current_g["validation"]["semanticReviewProgressSha256"] == sha(sp):
        assert current_g["nextAction"].startswith("Hand off cycle-02")
    else:
        assert current_g == baseline_g
        for row in current_g["files"]:
            if row["path"] in pre["files"]:
                row["sha256"] = pre["files"][row["path"]]["afterSha256"]
            assert sha(ROOT / row["path"]) == row["sha256"]
        v = current_g["validation"]
        v["sourceTargetSemanticAudit"] = "first complete 16538-unit semantic pass preserved on immutable baseline; cycle-01 independent review found 31 objective corrections, adjudicated and applied in cycle 02"
        v["dialogueBatchStructural"] = "passed for all current Hebrew dialogue batches; 24 cycle-02 changed files revalidated with current sidecars"
        v["preserveExact"] = "passed for all 16538 current authored units against pinned manifest"
        v["preserveExactReportPath"] = str((CYCLE / "preserve-exact-v4.json").relative_to(ROOT))
        v["preserveExactReportSha256"] = sha(CYCLE / "preserve-exact-v4.json")
        v["independentDiffAudit"] = "cycle-01 independent review complete with corrections required; cycle-02 194-ID exact delta pending"
        v["independentDiffReportPath"] = str((CYCLE / "full-structural-diff.json").relative_to(ROOT))
        v["independentDiffReportSha256"] = sha(CYCLE / "full-structural-diff.json")
        v["semanticReviewProgressSha256"] = sha(sp)
        v["readinessScan"] = "16538/16538 current authored units and 337/337 sidecars validated; 0 structural problems; no shared-state update"
        current_g["stages"]["editorial"] = "first semantic pass complete; cycle-01 independent review requested changes; 31-ID cycle-02 correction complete; 194-ID delta and clean independent verdict pending"
        current_g["openItems"] = [
            "Distinct independent review of the 194-ID cycle-02 exact delta and mandatory regressions on unchanged hashes; record reviewer identity and verdict.",
            "Verify characterName_Twins runtime fallback if this dynamic variant is exercised; static source contains no exact UI key.",
            "Hebrew runtime, visual, font/RTL and package checks remain outside this owner-restricted text-only task."]
        current_g["nextAction"] = ("Hand off cycle-02 " + str((CYCLE / "independent-review-handoff.json").relative_to(ROOT)) +
                                   " at SHA-256 " + sha(CYCLE / "independent-review-handoff.json") +
                                   "; exact delta starts at " + delta_ids[0] + ".")
        current_g["updatedAt"] = current_s["updatedAt"]
        gp.write_text(json.dumps(current_g, ensure_ascii=False, indent=2) + "\n")
    assert sha(sp) == json.loads(gp.read_text())["validation"]["semanticReviewProgressSha256"]
    assert current_s["firstPassFindings"] == baseline_s["firstPassFindings"]
    print(json.dumps({"authoredUnits": 16538, "sidecars": 337, "deltaIds": 194,
        "handoffSha256": sha(CYCLE / "independent-review-handoff.json"),
        "semanticProgressSha256": sha(sp), "progressSha256": sha(gp)}))


if __name__ == "__main__":
    main()
