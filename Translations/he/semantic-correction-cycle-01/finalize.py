#!/usr/bin/env python3
"""Bind validated Hebrew corrections and an exact independent-review handoff."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CYCLE = Path(__file__).resolve().parent
HE = CYCLE.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_set(rows):
    data = "".join(x["path"] + "\t" + x["sha256"] + "\n" for x in rows).encode()
    return hashlib.sha256(data).hexdigest()


def write_once(path, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    if path.exists():
        assert path.read_bytes() == data, f"Immutable evidence differs: {path}"
    else:
        path.write_bytes(data)


def main():
    baseline = json.loads((CYCLE / "baseline-semantic-review-progress.json").read_text())
    baseline_progress = json.loads((CYCLE / "baseline-progress.json").read_text())
    preflight = json.loads((CYCLE / "preflight.json").read_text())
    application = json.loads((CYCLE / "application.json").read_text())
    post = json.loads((CYCLE / "post-validation-summary.json").read_text())
    exact = json.loads((CYCLE / "preserve-exact-v4.json").read_text())
    closure = json.loads((CYCLE / "closure-manifest.json").read_text())
    assert baseline["acceptedUnits"] == baseline["reviewedUnits"] == 16538
    assert len(baseline["firstPassFindings"]) == 120
    assert preflight["acceptedFindings"] == application["changedStableIds"] == 120
    assert post["status"] == "passed on applied authored files" and post["validatedFiles"] == 81
    assert exact["exactResult"] == "passed" and exact["checkedRows"] == 16538
    assert closure["changedIds"]["count"] == 120 and closure["closureIds"]["count"] == 2111
    assert sha(HE / "static-text-draft.json") == baseline_progress["files"][next(
        i for i, x in enumerate(baseline_progress["files"]) if x["path"].endswith("static-text-draft.json"))]["sha256"]
    assert sha(HE / "static-text-draft.validation.json") == baseline_progress["validation"]["staticDraftValidationSha256"]
    assert sha(ROOT / baseline_progress["sourceInventory"]["stringsPath"]) == baseline["sourceInventorySha256"]
    assert sha(ROOT / baseline_progress["sourceInventory"]["staticPath"]) == baseline_progress["sourceInventory"]["staticSha256"]
    assert sha(ROOT / baseline_progress["sourceInventory"]["preserveExactPath"]) == baseline["preserveExactSha256"]
    assert sha(Path(baseline_progress["glossary"]["path"])) == baseline["glossarySha256"]
    assert sha(CYCLE / "adjudications.json") == preflight["adjudicationsSha256"]
    assert sha(CYCLE / "changed-ids.txt") == preflight["changedIdsSha256"]
    assert sha(CYCLE / "closure-ids.txt") == closure["closureIds"]["sha256"]
    assert sha(CYCLE / "review-rows.jsonl") == closure["reviewRows"]["sha256"]
    for c in closure["components"].values():
        assert sha(ROOT / c["path"]) == c["sha256"]
    for rel, item in preflight["files"].items():
        assert sha(ROOT / rel) == item["afterSha256"]
    batch_rows = []
    sidecar_rows = []
    for x in exact["inputFiles"]:
        p = ROOT / x["path"]
        assert sha(p) == x["sha256"]
        batch_rows.append(x)
        side = p.with_suffix(".validation.json")
        report = json.loads(side.read_text())
        assert report["structuralResult"] == "passed"
        assert report.get("batchSha256", report.get("draftSha256")) == x["sha256"]
        sidecar_rows.append({"path": str(side.relative_to(ROOT)), "sha256": sha(side)})
    assert len(batch_rows) == len(sidecar_rows) == 337
    assert len({x["path"] for x in batch_rows}) == 337
    assert len({x["path"] for x in sidecar_rows}) == 337
    assert sha(CYCLE / "post-validation-summary.json")
    structural = {"schemaVersion": 1, "status": "passed; structural evidence only",
                  "acceptedUnits": 16538, "authoredUnits": 16538,
                  "currentValidatedFiles": 337, "changedValidatedFiles": 81,
                  "sourceInventorySha256": baseline["sourceInventorySha256"],
                  "glossarySha256": baseline["glossarySha256"],
                  "preserveExactReport": {"path": str((CYCLE / "preserve-exact-v4.json").relative_to(ROOT)),
                                          "sha256": sha(CYCLE / "preserve-exact-v4.json"),
                                          "checkedRows": exact["checkedRows"]},
                  "authoredFileSetSha256": hash_set(batch_rows),
                  "sidecarFileSetSha256": hash_set(sidecar_rows),
                  "authoredFiles": batch_rows, "sidecars": sidecar_rows,
                  "semanticReview": "first pass on baseline; independent correction review pending",
                  "runtime": "not-run per owner instruction"}
    write_once(CYCLE / "full-structural-diff.json", structural)
    first = (CYCLE / "closure-ids.txt").read_text().splitlines()[0]
    handoff = {"schemaVersion": 1, "locale": "he", "gameVersion": "1.3.19",
               "status": "ready for independent dependency-aware language review; no independent verdict",
               "sourceLocale": "ru", "acceptedUnits": 16538,
               "firstSemanticPass": {"reviewedUnits": 16538,
                                     "baselinePath": str((CYCLE / "baseline-semantic-review-progress.json").relative_to(ROOT)),
                                     "baselineSha256": sha(CYCLE / "baseline-semantic-review-progress.json")},
               "sourceInventory": {"path": baseline_progress["sourceInventory"]["stringsPath"],
                                   "sha256": baseline["sourceInventorySha256"]},
               "staticSource": {"path": baseline_progress["sourceInventory"]["staticPath"],
                                "sha256": baseline_progress["sourceInventory"]["staticSha256"]},
               "approvedGlossary": {"path": baseline_progress["glossary"]["path"],
                                    "sha256": baseline["glossarySha256"]},
               "preserveExactManifest": {"path": baseline_progress["sourceInventory"]["preserveExactPath"],
                                         "sha256": baseline["preserveExactSha256"]},
               "adjudications": {"path": str((CYCLE / "adjudications.json").relative_to(ROOT)),
                                 "sha256": sha(CYCLE / "adjudications.json"), "accepted": 120},
               "preflight": {"path": str((CYCLE / "preflight.json").relative_to(ROOT)),
                             "sha256": sha(CYCLE / "preflight.json")},
               "consumerPreflight": {"path": str((CYCLE / "consumer-preflight.json").relative_to(ROOT)),
                                     "sha256": sha(CYCLE / "consumer-preflight.json")},
               "application": {"path": str((CYCLE / "application.json").relative_to(ROOT)),
                               "sha256": sha(CYCLE / "application.json")},
               "postValidation": {"path": str((CYCLE / "post-validation-summary.json").relative_to(ROOT)),
                                  "sha256": sha(CYCLE / "post-validation-summary.json")},
               "fullStructuralDiff": {"path": str((CYCLE / "full-structural-diff.json").relative_to(ROOT)),
                                      "sha256": sha(CYCLE / "full-structural-diff.json")},
               "closureManifest": {"path": str((CYCLE / "closure-manifest.json").relative_to(ROOT)),
                                   "sha256": sha(CYCLE / "closure-manifest.json"),
                                   "changedCount": 120, "closureCount": 2111,
                                   "firstReviewId": first},
               "reviewInstruction": "A distinct language reviewer should compare every current review-rows.jsonl closure row against its pinned source, approved glossary and node/consumer context, plus the mandatory-regressions component. Check accepted corrections, newly selected dependencies and stable branch outputs. Record an independent verdict on unchanged hashes; if corrections follow, use the universal delta rule. Do not credit the structural preflight as language review.",
               "imageTextPlans": "excluded by owner text-only scope; no translated image or texture plan edited",
               "runtime": "not-run per owner instruction", "visual": "not-run",
               "editorialAcceptance": "pending independent review and final gate"}
    write_once(CYCLE / "independent-review-handoff.json", handoff)
    # Update only the two existing locale-specific summaries. The immutable
    # first-pass finding array and reviewed baseline hashes remain unchanged.
    sp = HE / "semantic-review-progress.json"
    gp = HE / "progress.json"
    current_s = json.loads(sp.read_text())
    current_g = json.loads(gp.read_text())
    assert current_s == baseline and current_g == baseline_progress
    current_s["status"] = "first-semantic-pass-complete-on-baseline; corrections applied; independent review pending"
    current_s["firstPassBaseline"] = {"path": str((CYCLE / "baseline-semantic-review-progress.json").relative_to(ROOT)),
                                      "sha256": sha(CYCLE / "baseline-semantic-review-progress.json"),
                                      "reviewedUnits": 16538,
                                      "note": "reviewedFiles hashes pin the pre-correction corpus; they are not current authored hashes"}
    current_s["postCorrection"] = {"cycle": 1,
                                   "handoffPath": str((CYCLE / "independent-review-handoff.json").relative_to(ROOT)),
                                   "handoffSha256": sha(CYCLE / "independent-review-handoff.json"),
                                   "changedIds": 120, "closureIds": 2111,
                                   "currentAuthoredFileSetSha256": structural["authoredFileSetSha256"]}
    current_s["next"] = {"path": str((CYCLE / "closure-ids.txt").relative_to(ROOT)),
                         "firstId": first, "withinFileOffset": 0, "reviewUnits": 2111,
                         "instruction": "Independent dependency-aware language review on the corrected corpus; first-pass findings remain immutable."}
    current_s["correctionBatchStatus"] = "120/120 adjudicated and applied in one cycle; 81 authored files changed; exact and structural checks passed"
    current_s["independentReview"] = "pending; no distinct reviewer verdict"
    current_s["updatedAt"] = datetime.now(timezone.utc).isoformat()
    sp.write_text(json.dumps(current_s, ensure_ascii=False, indent=2) + "\n")
    changed_by_path = preflight["files"]
    for x in current_g["files"]:
        if x["path"] in changed_by_path:
            x["sha256"] = changed_by_path[x["path"]]["afterSha256"]
        assert sha(ROOT / x["path"]) == x["sha256"]
    current_g["validation"]["sourceTargetSemanticAudit"] = "first full 16538-unit semantic pass completed on immutable baseline; 120/120 findings adjudicated and applied; corrected 2111-ID closure awaits distinct independent language review"
    current_g["validation"]["dialogueBatchStructural"] = "passed for all current Hebrew dialogue batches; 81 changed files revalidated with current sidecars"
    current_g["validation"]["preserveExact"] = "passed for all 16538 current authored units against pinned manifest"
    current_g["validation"]["preserveExactReportPath"] = str((CYCLE / "preserve-exact-v4.json").relative_to(ROOT))
    current_g["validation"]["preserveExactReportSha256"] = sha(CYCLE / "preserve-exact-v4.json")
    current_g["validation"]["independentDiffAudit"] = "pending distinct language review; current full structural diff passed"
    current_g["validation"]["independentDiffReportPath"] = str((CYCLE / "full-structural-diff.json").relative_to(ROOT))
    current_g["validation"]["independentDiffReportSha256"] = sha(CYCLE / "full-structural-diff.json")
    current_g["validation"]["semanticReviewProgressSha256"] = sha(sp)
    current_g["validation"]["readinessScan"] = "full 16538/16538 current authored units and 337/337 sidecars validated; no shared-state update"
    current_g["stages"]["editorial"] = "first complete semantic pass and 120-ID correction batch complete; 2111-ID independent closure and editorial acceptance pending"
    current_g["openItems"] = [
        "Complete distinct independent dependency-aware language review of the 2111-ID corrected closure and mandatory regressions; record reviewer identity, verdict and immutable hashes.",
        "If the independent review requests corrections, apply the universal exact delta cycle; then run the final unchanged-hash structural/editorial gate.",
        "Hebrew runtime, visual, font/RTL and package checks remain outside this owner-restricted text-only task."]
    current_g["nextAction"] = ("Hand off " + str((CYCLE / "independent-review-handoff.json").relative_to(ROOT)) +
                               " at SHA-256 " + sha(CYCLE / "independent-review-handoff.json") +
                               "; independent closure starts at " + first + ".")
    current_g["updatedAt"] = current_s["updatedAt"]
    gp.write_text(json.dumps(current_g, ensure_ascii=False, indent=2) + "\n")
    assert sha(sp) == current_g["validation"]["semanticReviewProgressSha256"]
    assert current_s["firstPassFindings"] == baseline["firstPassFindings"]
    print(json.dumps({"structural": "passed", "authoredFiles": 337, "sidecars": 337,
                      "handoffSha256": sha(CYCLE / "independent-review-handoff.json"),
                      "semanticProgressSha256": sha(sp), "progressSha256": sha(gp)}))


if __name__ == "__main__":
    main()
