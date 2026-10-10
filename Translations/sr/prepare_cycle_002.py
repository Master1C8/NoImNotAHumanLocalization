#!/usr/bin/env python3
"""Pin and structurally preflight the author-adjudicated Serbian cycle 002 batch."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SR = ROOT / "Translations/sr"
REVIEW = SR / "independent-review-01"
OUT = SR / "semantic-cycle-002-adjudication.json"
GUIDS = {"UI": "0cbd8a7a4f543344bb95659de87f67a5",
         "Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
         "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import check_value  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def textsha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def idsha(ids):
    return textsha("".join(identifier + "\n" for identifier in ids))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    reviewer = read(REVIEW / "findings.json")
    summary = read(REVIEW / "summary.json")
    verification = read(REVIEW / "verification.json")
    additional = read(SR / "semantic-cycle-002-additional-findings.json")
    risk = read(SR / "semantic-cycle-002-dynamic-risk.json")
    closure = read(SR / "semantic-cycle-001-closure.json")
    manifest = read(ROOT / "Source/preserve-exactly-v4.json")
    canonical = [r["stableId"] for r in manifest["tableRows"] + manifest["staticRows"]]
    rules = {r["stableId"]: r for r in manifest["tableRows"] + manifest["staticRows"]}
    source = {r["stableId"]: r for r in
              (json.loads(line) for line in
               (ROOT / "Source/localization-inventory-v3/strings.jsonl").open())}
    source.update({r["stableId"]: r for r in
                   (json.loads(line) for line in
                    (ROOT / "Source/localization-inventory-v3/static-text.jsonl").open())})
    require(len(canonical) == 16538 and set(canonical) == set(rules), "Canonical scope changed")
    require(sha(SR / "semantic-cycle-001-closure.json") == reviewer["closureSha256"] and
            summary["authoredFileSetSha256"] == closure["currentAuthoredFileSetSha256"] ==
            reviewer["inputAuthoredFileSetSha256"] == risk["baselineAuthoredFileSetSha256"],
            "Independent review baseline changed")
    require(sha(ROOT / "Source/localization-inventory-v3/strings.jsonl") ==
            closure["sourceInventorySha256"] and
            sha(ROOT / "Documentation/glossary-translations/sr/layer.json") ==
            closure["glossaryFingerprint"], "Source or glossary changed")
    targets, paths = {}, {}
    for file in verification["authoredFiles"]:
        path = ROOT / file["path"]
        require(sha(path) == file["sha256"], "Authored baseline changed: " + file["path"])
        batch = read(path)
        for entry in batch["entries"]:
            identifier = entry.get("stableId") or ("string:" + GUIDS[batch["collection"]]
                        + ":" + str(entry["id"]))
            require(identifier not in targets, "Duplicate authored ID")
            targets[identifier], paths[identifier] = entry["target"], file["path"]
    require(set(targets) == set(canonical), "Authored baseline ID coverage changed")
    proposals = reviewer["findings"] + additional["findings"]
    require(len(proposals) == 17 and len({r["stableId"] for r in proposals}) == 17,
            "The complete adjudicated proposal batch changed")
    dismissed = read(REVIEW / "dismissed-candidates.json")
    require(not ({r["stableId"] for r in proposals} &
                 {r["stableId"] for r in dismissed["rows"]}),
            "Dismissed candidate entered correction batch")
    risk_rows = {r["stableId"]: r for r in risk["rows"]}
    entries = []
    for proposal in proposals:
        identifier = proposal["stableId"]
        require(identifier in rules and source[identifier]["source"] == proposal["source"] and
                targets[identifier] == proposal["currentTarget"],
                "Source/current target mismatch: " + identifier)
        require(proposal.get("targetFile", paths[identifier]) == paths[identifier],
                "Target file mismatch: " + identifier)
        if "sourceSha256" in proposal:
            require(proposal["sourceSha256"] == textsha(proposal["source"]),
                    "Reviewer source hash differs")
        if "currentTargetSha256" in proposal:
            require(proposal["currentTargetSha256"] == textsha(proposal["currentTarget"]),
                    "Reviewer current target hash differs")
        if "proposedTargetSha256" in proposal:
            require(proposal["proposedTargetSha256"] == textsha(proposal["proposedTarget"]),
                    "Reviewer proposed target hash differs")
        require(proposal["currentTarget"] != proposal["proposedTarget"],
                "No-op proposal")
        check_value(rules[identifier], proposal["proposedTarget"])
        examples = []
        if identifier in risk_rows:
            raw_labels = {x["target"] for x in risk_rows[identifier]["possibleRawLabels"]
                          if x["target"] is not None}
            examples = [{"rawLabel": label,
                         "assembledTarget": proposal["proposedTarget"].replace("{0}", label)}
                        for label in sorted(raw_labels)]
        entries.append({"findingId": proposal["findingId"], "stableId": identifier,
                        "key": source[identifier].get("key"), "source": proposal["source"],
                        "sourceSha256": textsha(proposal["source"]),
                        "currentTarget": proposal["currentTarget"],
                        "currentTargetSha256": textsha(proposal["currentTarget"]),
                        "acceptedTarget": proposal["proposedTarget"],
                        "acceptedTargetSha256": textsha(proposal["proposedTarget"]),
                        "targetFile": paths[identifier],
                        "objectiveReason": proposal["objectiveReason"],
                        "consumerExamples": examples,
                        "adjudication": "accepted complete unit; protected syntax preflight passed"})
    overlay = dict(targets)
    overlay.update({r["stableId"]: r["acceptedTarget"] for r in entries})
    for identifier in canonical:
        check_value(rules[identifier], overlay[identifier])
    by_id = {r["stableId"]: r for r in entries}
    ordered = [by_id[i] for i in canonical if i in by_id]
    changed = [r["stableId"] for r in ordered]
    result = {"schemaVersion": 1, "locale": "sr", "gameVersion": "1.3.19",
              "cycle": "002", "status": "one accepted author correction batch; preflight only, not yet applied",
              "sourceInventorySha256": closure["sourceInventorySha256"],
              "sourceStaticSha256": closure["sourceStaticSha256"],
              "glossaryFingerprint": closure["glossaryFingerprint"],
              "preserveExactManifestSha256": sha(ROOT / "Source/preserve-exactly-v4.json"),
              "priorAuthoredFileSetSha256": closure["currentAuthoredFileSetSha256"],
              "priorClosureSha256": sha(SR / "semantic-cycle-001-closure.json"),
              "reviewerReportSha256": sha(REVIEW / "report.md"),
              "reviewerFindingsSha256": sha(REVIEW / "findings.json"),
              "reviewerSummarySha256": sha(REVIEW / "summary.json"),
              "reviewerVerificationSha256": sha(REVIEW / "verification.json"),
              "dismissedCandidatesSha256": sha(REVIEW / "dismissed-candidates.json"),
              "additionalFindingsSha256": sha(SR / "semantic-cycle-002-additional-findings.json"),
              "boundedDynamicRiskSha256": sha(SR / "semantic-cycle-002-dynamic-risk.json"),
              "changedIds": changed, "changedIdsCount": len(changed),
              "changedIdsSha256": idsha(changed), "acceptedReviewerFindings": 15,
              "acceptedAdditionalFindings": 2, "dismissedBestsonAndPhoneCandidates": 2,
              "fullCorpusInMemoryProtectedSyntaxPreflight": "passed: 16,538 units",
              "structuralAndSemanticLimits": [
                  "The assembled examples verify literal insertion and expose case/number risks; no game launch or runtime reachability claim is made.",
                  "The 13 unmatched format-slot rows and three unknown same-place UI labels remain separately classified in the bounded risk inventory.",
                  "No independent review of these 17 new target values has occurred."],
              "entries": ordered}
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if OUT.exists():
        require(OUT.read_text() == text, "Immutable adjudication differs")
    else:
        require(args.write, "Adjudication is missing")
        OUT.write_text(text)
    print(json.dumps({"result": "written" if args.write else "verified",
                      "accepted": len(ordered), "changedIdsSha256": idsha(changed),
                      "adjudicationSha256": sha(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
