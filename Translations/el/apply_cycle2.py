#!/usr/bin/env python3
"""Apply the pinned Greek cycle-2 batch to authored inputs and dependent drafts."""

import hashlib
import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main():
    plan_path = HERE / "correction-cycle-002-adjudication.json"
    plan = json.loads(plan_path.read_text())
    assert plan["status"].endswith("authored application pending")
    pins = {
        "sourceInventorySha256": ROOT / "Source/localization-inventory-v3/strings.jsonl",
        "sourceStaticSha256": ROOT / "Source/localization-inventory-v3/static-text.jsonl",
        "approvedGlossarySha256": ROOT / "Documentation/glossary-translations/el/layer.json",
        "firstPassProgressSha256": HERE / "semantic-review-progress.json",
        "review01FindingsSha256": HERE / "independent-review-01/findings-v3.json",
        "review01EvidenceManifestSha256": HERE / "independent-review-01/evidence-manifest-v3.json",
        "review01DecisionsSha256": HERE / "independent-review-01/decisions.jsonl",
        "previousClosureManifestSha256": HERE / "correction-cycle-001-closure-manifest.json",
    }
    for key, path in pins.items():
        assert digest(path) == plan[key], (key, path)
    assert plan["correctionCount"] == len(plan["corrections"]) == 26
    assert sum(row["reviewFindingId"] is not None for row in plan["corrections"]) == 23
    assert len({row["stableId"] for row in plan["corrections"]}) == 26

    # Build all outputs in memory before replacing any current file.
    objects = {}
    before = {}
    def obj(path):
        if path not in objects:
            before[path] = digest(path)
            objects[path] = json.loads(path.read_text())
        return objects[path]

    rows_by_target = defaultdict(list)
    rows_by_authored = defaultdict(list)
    for row in plan["corrections"]:
        target, authored = ROOT / row["targetFile"], ROOT / row["authoredInput"]
        assert digest(target) == row["targetFileBeforeSha256"]
        assert digest(authored) == row["authoredInputBeforeSha256"]
        assert hashlib.sha256(row["before"].encode()).hexdigest() == row["beforeSha256"]
        assert hashlib.sha256(row["after"].encode()).hexdigest() == row["afterSha256"]
        rows_by_target[target].append(row)
        rows_by_authored[authored].append(row)

    dialogue_rows = [json.loads(line) for line in
                     (ROOT / "Source/localization-inventory-v3/strings.jsonl").open()
                     if '"collection":"Dialogs"' in line]
    source_index = {row["stableId"]: index for index, row in enumerate(dialogue_rows)}

    for authored, rows in rows_by_authored.items():
        data = obj(authored)
        if authored.name == "static-lexicon-001.authored.json":
            changes = {}
            for row in rows:
                source = row["source"]
                if source in changes:
                    assert changes[source] == (row["before"], row["after"])
                changes[source] = row["before"], row["after"]
            assert all(sum(item["source"] == source for item in data["lexicon"]) == 1
                       for source in changes)
            for item in data["lexicon"]:
                if item["source"] in changes:
                    old, new = changes[item["source"]]
                    assert item["target"] == old
                    item["target"] = new
        elif "targets" in data:
            changes = {source_index[row["stableId"]]: row for row in rows}
            assert len(changes) == len(rows)
            seen = set()
            for pair in data["targets"]:
                if pair[0] in changes:
                    row = changes[pair[0]]
                    assert pair[1] == row["before"]
                    pair[1] = row["after"]
                    seen.add(pair[0])
            assert seen == set(changes)
        else:
            assert authored in rows_by_target

    for target, rows in rows_by_target.items():
        data = obj(target)
        if target.name == "static-text-draft.json":
            changes = {row["stableId"]: row for row in rows}
            assert len(changes) == len(rows)
            seen = set()
            for entry in data["entries"]:
                sid = entry["stableId"]
                if sid in changes:
                    row = changes[sid]
                    assert entry["target"] == row["before"]
                    entry["target"] = row["after"]
                    seen.add(sid)
            assert seen == set(changes)
            authored = HERE / "static-lexicon-001.authored.json"
            data["authoredMapSha256"] = hashlib.sha256(encoded(objects[authored])).hexdigest()
        else:
            changes = {int(row["stableId"].rsplit(":", 1)[1]): row for row in rows}
            assert len(changes) == len(rows)
            seen = set()
            for entry in data["entries"]:
                if entry["id"] in changes:
                    row = changes[entry["id"]]
                    assert entry["target"] == row["before"]
                    entry["target"] = row["after"]
                    seen.add(entry["id"])
            assert seen == set(changes)
            authored = HERE / f"dialogue-ordered-{target.stem[-3:]}.authored.json"
            if authored.exists():
                data["authoredMapSha256"] = hashlib.sha256(encoded(objects[authored])).hexdigest()

    files = []
    payloads = {}
    for path, data in objects.items():
        payload = encoded(data)
        assert payload != path.read_bytes(), path
        payloads[path] = payload
        files.append({"path": str(path.relative_to(ROOT)), "beforeSha256": before[path],
                      "afterSha256": hashlib.sha256(payload).hexdigest()})
    applied_path = HERE / "correction-cycle-002-applied.json"
    assert not applied_path.exists(), "Preserve immutable application evidence"
    applied = {"schemaVersion": 1, "locale": "el", "cycle": 2,
               "status": "26 accepted corrections applied in one authored batch; deterministic gates pending",
               "adjudicationPath": str(plan_path.relative_to(ROOT)),
               "adjudicationSha256": digest(plan_path),
               "review01FindingsAccepted": 23, "boundedAdditionalCorrections": 3,
               "changedIds": [row["stableId"] for row in plan["corrections"]],
               "changedCount": 26,
               "files": sorted(files, key=lambda item: item["path"]),
               "atomicity": "Each file uses os.replace; this multi-file batch is not a filesystem transaction."}
    # The plan plus before hashes make a mid-write interruption diagnosable.
    staged = {}
    try:
        for path, payload in payloads.items():
            fd, name = tempfile.mkstemp(prefix=".cycle2-", dir=HERE)
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
            staged[path] = Path(name)
        for path in sorted(staged):
            assert digest(path) == before[path]
            os.replace(staged[path], path)
        applied_path.write_bytes(encoded(applied))
    finally:
        for path in staged.values():
            path.unlink(missing_ok=True)
    print(json.dumps({"changedIds": 26, "changedFiles": len(files),
                      "appliedSha256": digest(applied_path)}))


if __name__ == "__main__":
    main()
