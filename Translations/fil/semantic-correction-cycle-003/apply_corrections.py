#!/usr/bin/env python3
"""Apply the two independently proposed Filipino full-unit corrections once."""
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FIL = ROOT / "Translations/fil"
CYCLE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import check_value  # noqa: E402


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_text())


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    require(not (CYCLE / "plan.json").exists(), "Cycle 003 already applied")
    review = FIL / "independent-review-02"
    verification = read(review / "verification.json")
    require(verification["sourceAndAuthoredPinsUnchanged"] and
            verification["objectiveFindings"] == 2 and
            verification["fullRestartPredicateObserved"] is False,
            "Final independent review status differs")
    for pin in verification["pinChecks"]:
        path = ROOT / pin["path"]
        require(path.exists() and sha(path.read_bytes()) == pin["expected"] == pin["actual"],
                "Pre-correction pin differs: " + pin["path"])
    findings = read(review / "findings.json")["findings"]
    require([r["acceptedOrdinal"] for r in findings] == [943, 10326],
            "Unexpected final proposal list")
    source = {r["stableId"]: r for r in
              (json.loads(line) for line in
               (ROOT / "Source/localization-inventory-v3/strings.jsonl").open())}
    rules = {r["stableId"]: r for r in
             read(ROOT / "Source/preserve-exactly-v4.json")["tableRows"]}
    context = read(review / "additional-compiled-context.json")
    require(context["compiledProgramSha256"] == verification["compiledProgramSha256"],
            "Compiled program pin differs")
    paths = {}
    for file in sorted(FIL.glob("dialogue-batch-*.json")):
        if not file.stem.rsplit("-", 1)[-1].isdigit():
            continue
        doc = read(file)
        for entry in doc["entries"]:
            sid = "string:444ff14f1967f5a4c8eb9e4cf4c913f1:" + str(entry["id"])
            if sid in {row["stableId"] for row in findings}:
                require(sid not in paths, "Duplicate corrected ID")
                paths[sid] = file
    require(len(paths) == 2, "Corrected batch mapping differs")
    semantic = {
        943: {
            "facts": "All nearby houses are destroyed; the player's house alone remains.",
            "agency": "Any next calamity is predicted to fall on the player, not on another house.",
            "participants": "Window addresses the player in the second person.",
            "timing": "Что бы ни случилось is an open future contingency; mangyari preserves it.",
            "informationReveal": "No specific next event is disclosed or asserted to have happened.",
            "register": "Neutral descriptive Window voice.",
            "compiledBoundary": "window_12_1 instruction 3 after three uninterrupted scene facts; Stop at 4."
        },
        10326: {
            "facts": "Everyone says they solve problems; in reality absolutely nothing happens.",
            "agency": "The indefinite people claim problem solving; Esenin denies observable progress.",
            "participants": "Esenin speaks to the homeowner; no new actor is introduced.",
            "timing": "Present ongoing claim and present absence of progress.",
            "informationReveal": "The following lines predict later catastrophe; this line reveals none.",
            "register": "Vulgar complaint retained with putangina as an expletive, not a thing.",
            "compiledBoundary": "Esenin_Asking_3_1 instruction 5 after profane line 4, before prediction at 7–9."
        }
    }
    rows = []
    for f in findings:
        sid = f["stableId"]
        src = source[sid]
        require(src["source"] == f["source"] and src["key"] == f["key"] and
                sha(src["source"].encode()) == f["sourceSha256"], "Source mapping differs")
        file = paths[sid]
        entry = next(e for e in read(file)["entries"] if str(e["id"]) == sid.rsplit(":", 1)[1])
        require(entry["target"] == f["target"] and
                sha(entry["target"].encode()) == f["targetSha256"], "Current target differs")
        require(f["replacement"] == f["proposedFullTarget"] and
                sha(f["replacement"].encode()) == f["proposedTargetSha256"],
                "Complete proposal differs")
        check_value(rules[sid], f["replacement"])
        node = f["nodeNames"][0]
        matches = [i for i in context["nodes"][node]["instructions"]
                   if i.get("sourceStableId") == sid]
        require(len(matches) == 1 and matches[0]["source"] == f["source"] and
                matches[0]["target"] == f["target"], "Compiled scene differs")
        rows.append({"acceptedOrdinal": f["acceptedOrdinal"], "stableId": sid,
                     "collection": f["collection"], "key": f["key"],
                     "source": f["source"], "sourceSha256": f["sourceSha256"],
                     "currentTarget": f["target"], "currentTargetSha256": f["targetSha256"],
                     "acceptedFullTarget": f["replacement"],
                     "acceptedFullTargetSha256": f["proposedTargetSha256"],
                     "authoredPath": str(file.relative_to(ROOT)),
                     "compiledNode": node, "compiledInstruction": matches[0]["index"],
                     "decision": "accepted objective full-unit correction",
                     "semanticPreflight": semantic[f["acceptedOrdinal"]],
                     "protectedSyntax": "passed pinned v4 check_value"})
    before = []
    (CYCLE / "before-authored-files").mkdir()
    (CYCLE / "after-authored-files").mkdir()
    for file in sorted(set(paths.values())):
        raw = file.read_bytes()
        snapshot = CYCLE / "before-authored-files" / file.name
        snapshot.write_bytes(raw)
        before.append({"authoredPath": str(file.relative_to(ROOT)),
                       "snapshotPath": str(snapshot.relative_to(ROOT)),
                       "sha256": sha(raw),
                       "validationPath": str(file.with_suffix(".validation.json").relative_to(ROOT)),
                       "validationSha256": sha(file.with_suffix(".validation.json").read_bytes())})
    plan = {"schemaVersion": 1, "locale": "fil", "gameVersion": "1.3.19",
            "sourceLocale": "ru", "status": "complete adjudication and preflight before one bounded application",
            "finalReviewFindingsPath": str((review / "findings.json").relative_to(ROOT)),
            "finalReviewFindingsSha256": sha((review / "findings.json").read_bytes()),
            "finalReviewVerificationSha256": sha((review / "verification.json").read_bytes()),
            "finalReviewReportSha256": sha((review / "REPORT.md").read_bytes()),
            "previousClosurePath": "Translations/fil/semantic-correction-cycle-002/closure.json",
            "previousClosureSha256": sha((FIL / "semantic-correction-cycle-002/closure.json").read_bytes()),
            "previousPairedSha256": sha((FIL / "semantic-correction-cycle-002/closure-paired.jsonl").read_bytes()),
            "compiledContextPath": str((review / "additional-compiled-context.json").relative_to(ROOT)),
            "compiledContextSha256": sha((review / "additional-compiled-context.json").read_bytes()),
            "compiledProgramSha256": context["compiledProgramSha256"],
            "preserveExactManifestSha256": sha((ROOT / "Source/preserve-exactly-v4.json").read_bytes()),
            "sourceAndGlossaryFingerprints": read(FIL / "semantic-correction-cycle-002/plan.json")["sourceAndGlossaryFingerprints"],
            "verifiedPreCorrectionPins": len(verification["pinChecks"]),
            "acceptedFindings": 2, "rejectedFinalFindings": 0,
            "withdrawnPriorCandidates": read(review / "findings.json")["withdrawnPriorCandidatesStillWithdrawn"],
            "beforeAuthoredFiles": before, "rows": rows,
            "dependentRecipeDecision": "No corrected Russian source equals a common-option or static source phrase; regenerate and compare the unchanged derived option/static/credits recipes after application.",
            "fullRestartPredicateObserved": False}
    (CYCLE / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    for file in sorted(set(paths.values())):
        doc = read(file)
        targets = {r["stableId"].rsplit(":", 1)[1]: r["acceptedFullTarget"]
                   for r in rows if r["authoredPath"] == str(file.relative_to(ROOT))}
        for entry in doc["entries"]:
            replacement = targets.get(str(entry["id"]))
            if replacement is not None:
                entry["target"] = replacement
        raw = (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode()
        temp = file.with_name(file.name + ".cycle003.tmp")
        temp.write_bytes(raw)
        os.replace(temp, file)
        (CYCLE / "after-authored-files" / file.name).write_bytes(raw)
    print(json.dumps({"planSha256": sha((CYCLE / "plan.json").read_bytes()),
                      "appliedIds": [r["acceptedOrdinal"] for r in rows],
                      "authoredFiles": len(before)}))


if __name__ == "__main__":
    main()
