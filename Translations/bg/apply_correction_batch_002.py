#!/usr/bin/env python3
"""Apply or verify pinned Bulgarian cycle-002 full-line corrections, resumably."""

import argparse
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BG = ROOT / "Translations/bg"
PLAN = BG / "correction-batch-002.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def compact_entries(data):
    header = {key: value for key, value in data.items() if key != "entries"}
    text = json.dumps(header, ensure_ascii=False, indent=2)
    text = text[:-2] + ',\n  "entries": [\n'
    text += ',\n'.join('    ' + json.dumps(row, ensure_ascii=False)
                       for row in data["entries"])
    return (text + '\n  ]\n}\n').encode("utf-8")


def expanded(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preview", "apply", "verify"))
    args = parser.parse_args()
    plan = json.loads(PLAN.read_text())
    assert len(plan["decisions"]) == plan["decisionCount"] == 147
    for record in plan["pinnedInputs"]:
        assert digest((ROOT / record["path"]).read_bytes()) == record["sha256"], record["path"]
    grouped = defaultdict(list)
    for item in plan["decisions"]:
        grouped[item["batchPath"]].append(item)
    baseline = {r["path"]: r for r in plan["baselineAuthoredFiles"]}
    assert set(grouped) <= set(baseline)
    updates = {}
    for relpath, decisions in grouped.items():
        path = ROOT / relpath
        data = json.loads(path.read_text())
        entries = {e["stableId"] if relpath.endswith("static-text-draft.json") else
                   int(e["id"]): e for e in data["entries"]}
        for d in decisions:
            key = d["stableId"] if relpath.endswith("static-text-draft.json") else int(d["stableId"].rsplit(":", 1)[1])
            assert entries[key]["target"] in (d["currentFullTarget"], d["acceptedFullTarget"]), d["stableId"]
            entries[key]["target"] = d["currentFullTarget"]
        baseline_bytes = expanded(data)
        style = expanded
        if digest(baseline_bytes) != baseline[relpath]["sha256"]:
            baseline_bytes = compact_entries(data)
            style = compact_entries
        assert digest(baseline_bytes) == baseline[relpath]["sha256"], relpath + " baseline"
        for d in decisions:
            key = d["stableId"] if relpath.endswith("static-text-draft.json") else int(d["stableId"].rsplit(":", 1)[1])
            entries[key]["target"] = d["acceptedFullTarget"]
        new_bytes = style(data)
        current = path.read_bytes()
        assert current in (baseline_bytes, new_bytes), relpath + " unexpected content"
        updates[relpath] = (baseline_bytes, new_bytes, path)
    if args.action == "preview":
        print(json.dumps({"changedIds": len(plan["decisions"]), "changedFiles": len(updates),
                          "alreadyAppliedFiles": sum(path.read_bytes() == new for old, new, path in updates.values())}))
        return
    if args.action == "apply":
        for relpath, (old, new, path) in updates.items():
            if path.read_bytes() == new:
                continue
            temporary = path.with_suffix(path.suffix + ".cycle002-tmp")
            assert not temporary.exists(), str(temporary)
            with temporary.open("xb") as stream:
                stream.write(new)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
    assert all(path.read_bytes() == new for old, new, path in updates.values())
    print(json.dumps({"action": args.action, "changedIds": len(plan["decisions"]),
                      "changedFiles": len(updates), "allExpectedTargetHashes": True}))


if __name__ == "__main__":
    main()
