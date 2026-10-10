#!/usr/bin/env python3
"""Apply the one final review03 Filipino full-unit finding with exact before evidence."""
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FIL = ROOT / "Translations/fil"
CYCLE = Path(__file__).resolve().parent
REVIEW = FIL / "independent-review-03"
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
    require(not (CYCLE / "plan.json").exists(), "Cycle004 was already applied")
    verification = load(REVIEW / "verification.json")
    inputs = load(REVIEW / "input-verification.json")
    require(sha(REVIEW / "findings.json") ==
            "a6c705bdb93762a49fcee5d9ddbee8110519f2bea82d3b047fb3a357d34756ab",
            "Final findings hash differs")
    require(verification["sourceAndAuthoredPinsUnchanged"] and
            verification["closureUnits"] == 7604 and
            verification["freshPairs"] == 20 and
            verification["objectiveFindings"] == 1 and
            verification["priorExactDecisionsReused"] == 7584 and
            verification["retiredDependenciesVerified"] == 49 and
            verification["fullRestartPredicateObserved"] is False and
            inputs["compiledProgramSha256"] == verification["compiledProgramSha256"] and
            sha(REVIEW / "input-verification.json") == verification["inputVerificationSha256"],
            "Final independent review status differs")
    require(len(inputs["pinChecks"]) == 1111, "Reviewer pin count differs")
    for pin in inputs["pinChecks"]:
        path = ROOT / pin["path"]
        require(path.exists() and sha(path) == pin["expected"] == pin["actual"],
                "Pre-correction pin differs: " + pin["path"])
    findings = load(REVIEW / "findings.json")
    require(len(findings["findings"]) == 1 and
            findings["findings"][0]["acceptedOrdinal"] == 9613 and
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
    instruction = context["nodes"]["Theorist_Asking_3"]["instructions"][27]
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
    review_names = ["REPORT.md", "findings.json", "verification.json",
                    "input-verification.json", "completion-manifest.json",
                    "read-coverage.json", "fresh-decisions.jsonl",
                    "closure-decision-applicability.jsonl",
                    "mandatory-regression-applicability.jsonl",
                    "retired-dependencies.jsonl", "prior-decision-applicability.jsonl",
                    "applied-correction-decisions.json", "recipe-regressions.json",
                    "independent-compiled-context.json", "full-corpus-validation.json"]
    prior = FIL / "semantic-correction-cycle-003"
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
            "row": {"acceptedOrdinal": f["acceptedOrdinal"],
                    "stableId": f["stableId"], "collection": f["collection"],
                    "key": f["key"], "source": f["source"],
                    "sourceSha256": f["sourceSha256"],
                    "currentTarget": f["target"],
                    "currentTargetSha256": f["targetSha256"],
                    "acceptedFullTarget": f["replacement"],
                    "acceptedFullTargetSha256": f["proposedTargetSha256"],
                    "authoredPath": str(path.relative_to(ROOT)),
                    "compiledNode": "Theorist_Asking_3", "compiledInstruction": 27,
                    "decision": "accepted objective full-unit correction",
                    "semanticPreflight": {
                        "facts": "Article describes two sightings; Theorist argues they are one monster and calls the article amusing.",
                        "agency": "Theorist appraises the article after his own interpretation; no event is predicted.",
                        "participants": "Theorist remains speaker, addressing the homeowner as in prior lines.",
                        "timing": "В любом случае concludes the present discussion; Gayunman does not introduce a future contingency.",
                        "informationReveal": "No new monster identity, future event or outcome is asserted.",
                        "register": "Light, sardonic appraisal under SetEmotion Happy.",
                        "compiledBoundary": "Theorist_Asking_3 instruction27 after the one-versus-two-sightings argument at22–25; Stop at34."},
                    "protectedSyntax": "passed pinned v4 check_value"},
            "rejectedPreferenceRewrites": "No other line or already reviewed wording changed; review03 recipeFindings is empty.",
            "fullRestartPredicateObserved": False}
    (CYCLE / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    entry["target"] = f["replacement"]
    raw = (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode()
    temp = path.with_name(path.name + ".cycle004.tmp")
    temp.write_bytes(raw)
    os.replace(temp, path)
    after_path.write_bytes(raw)
    print(json.dumps({"planSha256": sha(CYCLE / "plan.json"),
                      "acceptedOrdinal": 9613,
                      "authoredPath": str(path.relative_to(ROOT)),
                      "beforeSha256": sha(before_path),
                      "afterSha256": sha(after_path)}))


if __name__ == "__main__":
    main()
