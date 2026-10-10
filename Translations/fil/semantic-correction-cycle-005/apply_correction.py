#!/usr/bin/env python3
"""Apply the one final review04 Filipino full-unit finding with exact before evidence."""
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FIL = ROOT / "Translations/fil"
CYCLE = Path(__file__).resolve().parent
REVIEW = FIL / "independent-review-04"
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import check_value  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def th(value):
    return hashlib.sha256(value.encode()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def main():
    require(not (CYCLE / "plan.json").exists(), "Cycle005 was already applied")
    require(sha(REVIEW / "completion-manifest.json") == "dea36a5b9f34c3b207fc97bcd88e29c03592fd21767ec3112918da6ad339915b", "Review04 seal differs")
    for pin in load(REVIEW / "completion-manifest.json")["files"]:
        require(sha(ROOT / pin["path"]) == pin["sha256"], "Sealed review evidence changed")
    verification = load(REVIEW / "verification.json")
    inputs = load(REVIEW / "input-verification.json")
    require(sha(REVIEW / "findings.json") ==
            "56e39c86c3d72928ba6349b537dbbf5a9e3cea822c347f1f801a9573f84322c6",
            "Final findings hash differs")
    require(verification["sourceAndAuthoredPinsUnchanged"] and
            verification["closureUnits"] == 7612 and
            verification["freshPairs"] == 26 and
            verification["objectiveFindings"] == 1 and
            verification["priorExactDecisionsReused"] == 7586 and
            verification["retiredNew"] == 5 and verification["retiredPrior"] == 49 and
            verification["fullRestartPredicateObserved"] is False and
            inputs["compiledProgramSha256"] == verification["compiledProgramSha256"] and
            sha(REVIEW / "input-verification.json") == verification["inputVerificationSha256"],
            "Final independent review status differs")
    require(len(inputs["pinChecks"]) == 1627, "Reviewer pin count differs")
    for pin in inputs["pinChecks"]:
        path = ROOT / pin["path"]
        require(path.exists() and sha(path) == pin["sha256"],
                "Pre-correction pin differs: " + pin["path"])
    findings = load(REVIEW / "findings.json")
    require(len(findings["findings"]) == 1 and
            findings["findings"][0]["acceptedOrdinal"] == 9614 and
            findings["recipeFindings"] == [], "Unexpected final proposal list")
    f = findings["findings"][0]
    source = next(row for row in
                  (json.loads(line) for line in
                   (ROOT / "Source/localization-inventory-v3/strings.jsonl").open())
                  if row["stableId"] == f["stableId"])
    rule = next(row for row in load(ROOT / "Source/preserve-exactly-v4.json")["tableRows"]
                if row["stableId"] == f["stableId"])
    require(source["source"] == f["source"] and source["key"] == f["key"] and
            th(source["source"]) == f["sourceSha256"] and
            f["replacement"] == f["proposedFullTarget"] and
            th(f["replacement"]) == f["proposedTargetSha256"],
            "Source or complete proposed target differs")
    check_value(rule, f["replacement"])
    context_path = REVIEW / "independent-compiled-context.json"
    context = load(context_path)
    require(context["compiledProgramSha256"] == verification["compiledProgramSha256"],
            "Compiled source program differs")
    instruction = context["nodes"]["Theorist_Asking_3"]["instructions"][25]
    require(instruction["op"] == "RunLine" and
            instruction["sourceStableId"] == f["stableId"] and
            instruction["source"] == f["source"] and
            instruction["target"] == f["target"],
            "Compiled scene-bound line differs")
    path = FIL / "dialogue-batch-250.json"
    doc = load(path)
    entry = next(e for e in doc["entries"]
                 if str(e["id"]) == f["stableId"].rsplit(":", 1)[1])
    require(entry["target"] == f["target"] and th(entry["target"]) == f["targetSha256"],
            "Current authored target differs")
    before_path = CYCLE / "before-authored-files" / path.name
    after_path = CYCLE / "after-authored-files" / path.name
    before_path.parent.mkdir()
    after_path.parent.mkdir()
    before_path.write_bytes(path.read_bytes())
    sidecar = path.with_suffix(".validation.json")
    sidecar_snapshot = CYCLE / "before-validation-files" / sidecar.name
    sidecar_snapshot.parent.mkdir()
    sidecar_snapshot.write_bytes(sidecar.read_bytes())
    review_names = ["REPORT.md", "findings.json", "verification.json",
                    "input-verification.json", "completion-manifest.json",
                    "read-coverage.json", "fresh-decisions.jsonl",
                    "closure-decision-applicability.jsonl",
                    "mandatory-regression-applicability.jsonl",
                    "retired-dependencies.jsonl", "prior-decision-applicability.jsonl",
                    "applied-correction-decisions.json", "recipe-regressions.json",
                    "independent-compiled-context.json", "full-corpus-validation.json"]
    prior = FIL / "semantic-correction-cycle-004"
    prior_plan = load(prior / "plan.json")
    plan = {"schemaVersion": 1, "locale": "fil", "gameVersion": "1.3.19",
            "sourceLocale": "ru",
            "status": "one complete objective adjudication and preflight before bounded application",
            "sourceAndGlossaryFingerprints": prior_plan["sourceAndGlossaryFingerprints"],
            "preserveExactManifestSha256": prior_plan["preserveExactManifestSha256"],
            "compiledProgramSha256": context["compiledProgramSha256"],
            "compiledContextPath": str(context_path.relative_to(ROOT)),
            "compiledContextSha256": sha(context_path),
            "previousClosurePath": str((prior / "closure.json").relative_to(ROOT)),
            "previousClosureSha256": sha(prior / "closure.json"),
            "previousPairedSha256": sha(prior / "closure-paired.jsonl"),
            "finalReviewEvidenceSha256": {name: sha(REVIEW / name) for name in review_names},
            "verifiedPreCorrectionPins": len(inputs["pinChecks"]),
            "beforeAuthoredPath": str(before_path.relative_to(ROOT)),
            "beforeAuthoredSha256": sha(before_path),
            "beforeValidationPath": str(path.with_suffix(".validation.json").relative_to(ROOT)),
            "beforeValidationSha256": sha(path.with_suffix(".validation.json")),
            "beforeValidationSnapshotPath": str(sidecar_snapshot.relative_to(ROOT)),
            "beforeValidationSnapshotSha256": sha(sidecar_snapshot),
            "boundedAuthorReviewPath": str((CYCLE / "bounded-author-review.json").relative_to(ROOT)),
            "boundedAuthorReviewSha256": sha(CYCLE / "bounded-author-review.json"),
            "boundedCompiledContextPath": str((CYCLE / "bounded-compiled-context.json").relative_to(ROOT)),
            "boundedCompiledContextSha256": sha(CYCLE / "bounded-compiled-context.json"),
            "row": {"acceptedOrdinal": f["acceptedOrdinal"],
                    "stableId": f["stableId"], "collection": f["collection"],
                    "key": f["key"], "source": f["source"],
                    "sourceSha256": f["sourceSha256"],
                    "currentTarget": f["target"],
                    "currentTargetSha256": f["targetSha256"],
                    "acceptedFullTarget": f["replacement"],
                    "acceptedFullTargetSha256": f["proposedTargetSha256"],
                    "authoredPath": str(path.relative_to(ROOT)),
                    "compiledNode": "Theorist_Asking_3", "compiledInstruction": 25,
                    "decision": "accepted objective full-unit correction",
                    "semanticPreflight": {
                        "facts": "Article author reported TWO frightening pale men, one in windows and another at the doorstep; Theorist argues they are the same monster and hypothesizes a mistaken perception due to the window-distorted face.",
                        "agency": "Article author, not Theorist or the monster, is the mistaken perceiver; Theorist offers the conjecture.",
                        "participants": "Speaker remains Theorist; niya follows the article author from preceding instructions; halimaw disambiguates face owner already established at24.",
                        "timing": "Past belief (inakala) versus generic window appearance (kapag tinitingnan); no future contingency.",
                        "informationReveal": "Monster term occurs at24 before25, no early disclosure.",
                        "modality": "Sa palagay ko retains tentative hypothesis, not a proven cause; dahil restores causal explanation.",
                        "register": "Analytical conjecture under Sad, then Happy at26 before conclusion27; no additional profanity or preference rewrite.",
                        "compiledBoundary": "Theorist_Asking_3 instruction25 after14–24, no intervening branch; visiting guard precedes14; stop34."
},
                    "protectedSyntax": "passed pinned v4 check_value"},
            "rejectedPreferenceRewrites": "83 bounded family pairs and seven actual compiled nodes adjudicated; no additional objective same-mechanism defect. No unrelated target changed; review04 recipeFindings is empty.",
            "fullRestartPredicateObserved": False}
    (CYCLE / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    entry["target"] = f["replacement"]
    raw = (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode()
    temp = path.with_name(path.name + ".cycle005.tmp")
    temp.write_bytes(raw)
    os.replace(temp, path)
    after_path.write_bytes(raw)
    print(json.dumps({"planSha256": sha(CYCLE / "plan.json"),
                      "acceptedOrdinal": 9614,
                      "authoredPath": str(path.relative_to(ROOT)),
                      "beforeSha256": sha(before_path),
                      "afterSha256": sha(after_path)}))


if __name__ == "__main__":
    main()
