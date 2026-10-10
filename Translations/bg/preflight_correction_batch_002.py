#!/usr/bin/env python3
"""Pin and preflight the single Bulgarian correction cycle after independent review."""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BG = ROOT / "Translations/bg"
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import check_value  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def main():
    reviewer = BG / "independent-review-01-author-adjudication.json"
    parts = [BG / f"voice-remedial-author-proposals-part-{n:03}.json" for n in (1, 2, 3)]
    selector = BG / "voice-risk-selector-v4.json"
    candidates = BG / "voice-remedial-candidates-v4.json"
    baseline = BG / "correction-batch-001-result.json"
    previous = BG / "semantic-closure-cycle-001.json"
    plan_path = BG / "correction-batch-002.json"
    previous_review = BG / "independent-review-01/review.json"
    for path, expected in load(selector)["pinnedInputs"].items():
        assert digest(ROOT / path) == expected, path
    assert load(candidates)["selectorSha256"] == digest(selector)
    assert load(reviewer)["voiceCandidateSha256"] == digest(BG / "voice-remedial-candidates-v2.json")
    assert load(previous_review)["closureSha256"] == digest(previous) or load(previous_review).get("closureEvidenceSha256") == digest(previous)

    receipt = load(baseline)
    targets = {}
    for rec in receipt["allAuthoredFiles"]:
        path = ROOT / rec["path"]
        assert digest(path) == rec["sha256"], rec["path"]
        batch = load(path)
        for entry in batch["entries"]:
            if rec["collection"] == "StaticTMP":
                sid = entry["stableId"]
            else:
                guid = {"UI": "0cbd8a7a4f543344bb95659de87f67a5",
                        "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6",
                        "Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1"}[rec["collection"]]
                sid = f"string:{guid}:{entry['id']}"
            assert sid not in targets, sid
            targets[sid] = (entry["target"], rec["path"], rec["collection"])
    assert len(targets) == 16538
    sources = {}
    for relpath in ("Source/localization-inventory-v3/strings.jsonl",
                    "Source/localization-inventory-v3/static-text.jsonl"):
        for line in (ROOT / relpath).open():
            row = json.loads(line)
            if row["stableId"] in targets:
                sources[row["stableId"]] = row["source"]
    assert len(sources) == len(targets)
    manifest = load(ROOT / "Source/preserve-exactly-v4.json")
    rules = {r["stableId"]: r for r in manifest["tableRows"] + manifest["staticRows"]}
    assert len(rules) == len(targets)
    inputs = [{"path": str(path.relative_to(ROOT)), "sha256": digest(path)}
              for path in [reviewer, *parts, selector, candidates, baseline, previous, previous_review]]
    raw = []
    for item in load(reviewer)["decisions"]:
        raw.append((item["stableId"], item["source"], item["currentFullTarget"],
                    item["acceptedFullTarget"], item["findingId"], item["decision"]))
    for path in parts:
        for item in load(path)["proposals"]:
            raw.append((item["stableId"], item["source"], item["currentFullTarget"],
                        item["proposedFullTarget"], path.name + ":" +
                        str(item.get("candidateIndex", item.get("candidateV3Index"))), "accept"))
    assert len(raw) == 147
    decisions = []
    seen = set()
    for sid, source, current, accepted, basis, status in raw:
        assert sid not in seen, sid
        seen.add(sid)
        actual, path, collection = targets[sid]
        assert source == sources[sid], sid + " source"
        assert current == actual, sid + " target"
        assert current != accepted, sid + " unchanged"
        check_value(rules[sid], accepted)
        decisions.append({"stableId": sid, "collection": collection, "batchPath": path,
                          "source": source, "currentFullTarget": current,
                          "acceptedFullTarget": accepted, "basis": basis,
                          "authorDecision": status})
    plan = {"schemaVersion": 1, "locale": "bg", "gameVersion": "1.3.19",
            "status": "preflight passed; one consolidated 147-ID correction batch ready to apply",
            "acceptedUnits": 16538, "decisionCount": len(decisions),
            "reviewerDecisionCount": 51, "additionalVoiceDecisionCount": 96,
            "pinnedInputs": inputs,
            "sourceSha256": digest(ROOT / "Source/localization-inventory-v3/strings.jsonl"),
            "staticSourceSha256": digest(ROOT / "Source/localization-inventory-v3/static-text.jsonl"),
            "preserveExactlySha256": digest(ROOT / "Source/preserve-exactly-v4.json"),
            "bgGlossarySha256": digest(ROOT / "Documentation/glossary-translations/canonical-reviews/artifacts/bg/layer.json"),
            "sourceGlossarySha256": digest(Path("/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary.json")),
            "baselineAuthoredFiles": receipt["allAuthoredFiles"],
            "decisions": decisions}
    payload = (json.dumps(plan, ensure_ascii=False, indent=2) + "\n").encode()
    if plan_path.exists():
        assert plan_path.read_bytes() == payload, "Correction plan drift"
    else:
        plan_path.write_bytes(payload)
    print(json.dumps({"decisions": len(decisions), "planSha256": digest(plan_path),
                      "affectedFiles": len({d["batchPath"] for d in decisions})}, ensure_ascii=False))


if __name__ == "__main__":
    main()
