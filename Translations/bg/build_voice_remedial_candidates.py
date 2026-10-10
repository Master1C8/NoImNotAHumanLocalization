#!/usr/bin/env python3
"""Reproduce the bounded Bulgarian voice audit from pinned Russian source and draft."""

import hashlib
import json
import re
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BG = ROOT / "Translations/bg"
WORD = re.compile(r"[А-Яа-яЁё]+")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", type=int, choices=(2, 3, 4, 5, 6), default=6)
    args = parser.parse_args()
    spec_path = BG / f"voice-risk-selector-v{args.version}.json"
    out_path = BG / f"voice-remedial-candidates-v{args.version}.json"
    result_path = BG / ("correction-batch-003-result.json" if args.version == 6 else
                        "correction-batch-002-result.json" if args.version == 5 else
                        "correction-batch-001-result.json")
    spec = json.loads(spec_path.read_text())
    assert spec["schemaVersion"] == args.version and spec["locale"] == "bg"
    for name, expected in spec["pinnedInputs"].items():
        assert digest(ROOT / name) == expected, name
    result = json.loads(result_path.read_text())
    plan_path = BG / ("correction-batch-003.json" if args.version == 6 else
                      "correction-batch-002.json" if args.version == 5 else
                      "correction-batch-001.json")
    assert digest(plan_path) == result["planSha256"]
    targets = {}
    paths = {}
    for rec in result["allAuthoredFiles"]:
        path = ROOT / rec["path"]
        assert digest(path) == rec["sha256"], rec["path"]
        batch = json.loads(path.read_text())
        for entry in batch["entries"]:
            if rec["collection"] == "Dialogs":
                sid = "string:444ff14f1967f5a4c8eb9e4cf4c913f1:" + str(entry["id"])
                assert sid not in targets
                targets[sid] = entry["target"]
                paths[sid] = rec["path"]
    assert len(targets) == 16100
    prefixes = tuple(spec["corePrefixes"] + spec["secondaryPrefixes"])
    excluded = set(spec["excludeExactWords"])
    exact_words = set(spec.get("additionalExactWords", []))

    def matches(value):
        return [w for w in WORD.findall(value.lower())
                if w not in excluded and (w in exact_words or w.startswith(prefixes))]

    for word in spec["regressionCases"]["include"]:
        assert matches(word) == [word], ("missed", word)
    for word in spec["regressionCases"]["exclude"]:
        assert not matches(word), ("false positive", word)
    rows = []
    index = -1
    for line in (ROOT / "Source/localization-inventory-v3/strings.jsonl").open():
        row = json.loads(line)
        if row["collection"] != "Dialogs":
            continue
        sid = row["stableId"]
        if sid not in targets:
            continue
        index += 1
        hits = matches(row["source"])
        if hits:
            rows.append({"candidateIndex": len(rows), "dialogueSourceIndex": index,
                         "stableId": sid, "key": row["key"],
                         "sceneNodes": row.get("nodeNames") or [],
                         "speaker": row["source"].split(":", 1)[0],
                         "matchedWords": hits, "source": row["source"],
                         "currentFullTarget": targets[sid], "authoredPath": paths[sid]})
    assert index + 1 == 16100
    report = {"schemaVersion": 1, "locale": "bg", "status": "bounded voice review candidates; not defect findings",
              "selectorPath": str(spec_path.relative_to(ROOT)), "selectorSha256": digest(spec_path),
              "baselineResultPath": str(result_path.relative_to(ROOT)), "baselineResultSha256": digest(result_path),
              "acceptedDialogueUnits": 16100, "candidateCount": len(rows), "candidates": rows}
    payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
    if out_path.exists():
        assert out_path.read_bytes() == payload, "Candidate evidence changed"
    else:
        out_path.write_bytes(payload)
    print(json.dumps({"candidateCount": len(rows), "sha256": digest(out_path),
                      "speakerCount": len(set(r["speaker"] for r in rows))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
