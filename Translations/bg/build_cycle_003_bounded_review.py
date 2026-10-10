#!/usr/bin/env python3
"""Freeze complete pre-correction scene, referent, voice and grammar pair scope."""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BG = ROOT / "Translations/bg"


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def node_set(row):
    names = set(row.get("nodeNames") or [])
    match = re.fullmatch(r"line:(.+)_[0-9a-f]{7}", row.get("key") or "")
    if match:
        names.add(match.group(1))
    return names


def main():
    result = load(BG / "correction-batch-002-result.json")
    findings = load(BG / "independent-review-02/findings.json")["findings"]
    read = {r["stableId"] for r in load(BG / "independent-review-02/per-id-read-verdicts.json")}
    targets = {}
    for file in result["allAuthoredFiles"]:
        if file["collection"] != "Dialogs":
            continue
        for row in load(ROOT / file["path"])["entries"]:
            sid = "string:444ff14f1967f5a4c8eb9e4cf4c913f1:" + str(row["id"])
            targets[sid] = (row["target"], file["path"])
    # Reconstruct the pinned pre-correction pairs from the exact full-line plan;
    # the authored draft has already advanced to the corrected final bytes.
    plan = load(BG / "correction-batch-003.json")
    for decision in plan["decisions"]:
        sid = decision["stableId"]
        assert targets[sid] == (decision["acceptedFullTarget"], decision["batchPath"])
        targets[sid] = (decision["currentFullTarget"], decision["batchPath"])
    source = {r["stableId"]: r for r in map(json.loads,
              (ROOT / "Source/localization-inventory-v3/strings.jsonl").open())
              if r["collection"] == "Dialogs" and r["stableId"] in targets}
    finding_ids = {f["stableId"] for f in findings}
    nodes = {node for f in findings for node in f["sceneNodes"]}
    repeat_sources = {source[sid]["source"] for sid in finding_ids}
    groups = {
        "findingSceneNodes": {sid for sid, r in source.items()
                              if node_set(r) & nodes},
        "exactRussianRepetitions": {sid for sid, r in source.items()
                                    if r["source"] in repeat_sources},
        "baldFamilyReferents": {sid for sid, r in source.items()
                                if re.search(r"Bald:.*(ма и ба|мам|баб|отец|пап|бат)", r["source"], re.I)},
        "wheelchairEarSignConsumer": {sid for sid, r in source.items()
                                       if any("Wheelchair_Ears" in n for n in node_set(r))},
        "leperLightExclamation": {sid for sid, r in source.items()
                                   if "Ёбаный свет" in r["source"]},
        "colorVerbReferents": {sid for sid, r in source.items()
                               if "покрасил" in r["source"]},
        "rockImperativeAndMusic": {sid for sid, r in source.items()
                                   if "ЕБАШЬ" in r["source"] or
                                   ("рок" in r["source"].lower() and r["source"].startswith("Rocker:"))},
        "canonicalVoiceSelectorV5": {r["stableId"] for r in
                                      load(BG / "voice-remedial-candidates-v5.json")["candidates"]},
        "bulgarianAgreementAndCoarseNounWatch": {sid for sid, (target, _) in targets.items()
            if re.search(r"\b(?:пълна|дребната|голямата|шибана|шибания|шибаната)\s+"
                         r"(?:шибания|шибан|пълен|ужас|светлина|простотия|беда)\b", target, re.I)},
    }
    assert finding_ids <= set.union(*groups.values())
    affected = set.union(*groups.values())
    order = {sid: i for i, sid in enumerate(source)}
    ordered = lambda ids: sorted(ids, key=order.__getitem__)
    rows = []
    for sid in ordered(affected):
        target, path = targets[sid]
        r = source[sid]
        rows.append({"stableId": sid, "sourceIndexWithinDialogs": order[sid],
                     "sceneNodes": sorted(node_set(r)), "key": r.get("key"),
                     "source": r["source"], "currentFullTarget": target,
                     "authoredPath": path,
                     "groupMembership": [name for name, ids in groups.items() if sid in ids],
                     "independentReview02DeltaRead": sid in read})
    report = {"schemaVersion": 1, "locale": "bg", "gameVersion": "1.3.19",
              "status": "pre-correction bounded full-pair scope; not independent acceptance",
              "sourceSha256": sha(ROOT / "Source/localization-inventory-v3/strings.jsonl"),
              "baselineResultSha256": sha(BG / "correction-batch-002-result.json"),
              "correctionPlanSha256": sha(BG / "correction-batch-003.json"),
              "findingsSha256": sha(BG / "independent-review-02/findings.json"),
              "reviewVerdictsSha256": sha(BG / "independent-review-02/per-id-read-verdicts.json"),
              "voiceSelectorSha256": sha(BG / "voice-risk-selector-v5.json"),
              "voiceCandidatesSha256": sha(BG / "voice-remedial-candidates-v5.json"),
              "groupCounts": {name: len(ids) for name, ids in groups.items()},
              "affectedCount": len(affected), "outsideReview02DeltaCount": len(affected - read),
              "rows": rows}
    path = BG / "correction-cycle-003-bounded-review.json"
    payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
    if path.exists():
        assert path.read_bytes() == payload
    else:
        path.write_bytes(payload)
    print(json.dumps({"affected": len(rows), "outsideReview02Delta": len(affected - read),
                      "groupCounts": report["groupCounts"], "sha256": sha(path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
