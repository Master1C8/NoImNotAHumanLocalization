#!/usr/bin/env python3
"""Verify correction batch 001 changed only its 60 authored target fields."""

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BG = ROOT / "Translations/bg"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def compact_entries(data):
    header = {key: value for key, value in data.items() if key != "entries"}
    text = json.dumps(header, ensure_ascii=False, indent=2)
    text = text[:-2] + ',\n  "entries": [\n'
    text += ',\n'.join('    ' + json.dumps(row, ensure_ascii=False)
                       for row in data["entries"])
    return (text + '\n  ]\n}\n').encode("utf-8")


def main():
    plan = json.loads((BG / "correction-batch-001.json").read_text())
    first = json.loads((BG / "semantic-first-pass-cycle-000.json").read_text())
    result = json.loads((BG / "correction-batch-001-result.json").read_text())
    assert plan["firstPassEvidenceSha256"] == sha((BG / "semantic-first-pass-cycle-000.json").read_bytes())
    assert result["planSha256"] == sha((BG / "correction-batch-001.json").read_bytes())
    assert len(plan["decisions"]) == 60
    before = {row["path"]: row["sha256"] for row in first["reviewedFiles"]}
    after = {row["path"]: row["sha256"] for row in result["allAuthoredFiles"]}
    assert len(before) == len(after) == 411 and set(before) == set(after)
    grouped = defaultdict(list)
    for decision in plan["decisions"]:
        grouped[decision["batchPath"]].append(decision)
    assert set(grouped) == {row["path"] for row in result["changedFiles"]}
    assert all(before[path] == after[path] for path in before if path not in grouped)
    styles = Counter()
    for path, decisions in grouped.items():
        current_bytes = (ROOT / path).read_bytes()
        assert sha(current_bytes) == after[path]
        data = json.loads(current_bytes)
        entries = {row["id"]: row for row in data["entries"]}
        for decision in decisions:
            entry = entries[int(decision["stableId"].rsplit(":", 1)[1])]
            assert entry["target"] == decision["acceptedFullTarget"]
            entry["target"] = decision["currentTarget"]
        expanded = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        compact = compact_entries(data)
        if sha(expanded) == before[path]:
            styles["expanded"] += 1
        elif sha(compact) == before[path]:
            styles["compactEntries"] += 1
        else:
            raise AssertionError("Unexplained pre-correction byte difference: " + path)
    print(json.dumps({"result": "exact 60 target-field edits only",
                      "changedIds": len(plan["decisions"]),
                      "changedFiles": len(grouped),
                      "unchangedFiles": len(before) - len(grouped),
                      "preCorrectionSerialization": dict(styles)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
