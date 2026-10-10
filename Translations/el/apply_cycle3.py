#!/usr/bin/env python3
"""Apply the six pinned Greek consumer corrections as one authored batch."""

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


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main():
    plan_path = HERE / "correction-cycle-003-adjudication.json"
    plan = json.loads(plan_path.read_text())
    assert plan["cycle"] == 3 and plan["correctionCount"] == len(plan["corrections"]) == 6
    pins = {
        "review02EvidenceManifestSha256": HERE / "independent-review-02/evidence-manifest-v2.json",
        "review02FindingsSha256": HERE / "independent-review-02/findings.json",
        "review02FinalCoverageProofSha256": HERE / "independent-review-02/final-coverage-and-invalidation-proof.json",
        "review02ConsumerTopologySha256": HERE / "independent-review-02/bounded-consumer-topology.json",
        "review02AssembledChecksSha256": HERE / "independent-review-02/proposal-and-consumer-checks.json",
        "sourceInventorySha256": ROOT / "Source/localization-inventory-v3/strings.jsonl",
        "sourceStaticSha256": ROOT / "Source/localization-inventory-v3/static-text.jsonl",
        "approvedGlossarySha256": ROOT / "Documentation/glossary-translations/el/layer.json",
        "priorCycle2ClosureManifestSha256": HERE / "correction-cycle-002-closure-manifest.json",
        "priorCycle2CheckpointSha256": HERE / "correction-cycle-002-text-checkpoint.json",
    }
    for key, path in pins.items():
        assert digest(path) == plan[key], (key, path)
    dialogue = [json.loads(line) for line in
                (ROOT / "Source/localization-inventory-v3/strings.jsonl").open()
                if '"collection":"Dialogs"' in line]
    position = {row["stableId"]: index for index, row in enumerate(dialogue)}
    rows_by_map = defaultdict(list)
    rows_by_batch = defaultdict(list)
    for row in plan["corrections"]:
        authored, batch = ROOT / row["authoredInput"], ROOT / row["targetFile"]
        assert authored.parent == batch.parent == HERE
        assert digest(authored) == row["authoredInputBeforeSha256"]
        assert digest(batch) == row["targetFileBeforeSha256"]
        rows_by_map[authored].append(row)
        rows_by_batch[batch].append(row)
    assert len(rows_by_map) == len(rows_by_batch) == 4

    outputs, before = {}, {}
    for authored, rows in rows_by_map.items():
        data = json.loads(authored.read_text())
        changes = {position[row["stableId"]]: row for row in rows}
        assert len(changes) == len(rows)
        seen = set()
        for pair in data["targets"]:
            if pair[0] in changes:
                row = changes[pair[0]]
                assert pair[1] == row["before"]
                pair[1] = row["after"]
                seen.add(pair[0])
        assert seen == set(changes)
        before[authored] = digest(authored)
        outputs[authored] = encoded(data)

    for batch, rows in rows_by_batch.items():
        data = json.loads(batch.read_text())
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
        authored = HERE / f"dialogue-ordered-{batch.stem[-3:]}.authored.json"
        assert authored in outputs
        data["authoredMapSha256"] = hashlib.sha256(outputs[authored]).hexdigest()
        before[batch] = digest(batch)
        outputs[batch] = encoded(data)

    files = [{"path": str(path.relative_to(ROOT)),
              "beforeSha256": before[path],
              "afterSha256": hashlib.sha256(content).hexdigest()}
             for path, content in sorted(outputs.items())]
    applied = {"schemaVersion": 1, "locale": "el", "cycle": 3,
               "status": "six accepted corrections applied in one authored batch; deterministic gates pending",
               "adjudicationPath": str(plan_path.relative_to(ROOT)),
               "adjudicationSha256": digest(plan_path),
               "changedIds": [row["stableId"] for row in plan["corrections"]],
               "changedCount": 6, "files": files,
               "atomicity": "Each file uses os.replace; the eight-file batch is not a filesystem transaction."}
    applied_path = HERE / "correction-cycle-003-applied.json"
    assert not applied_path.exists(), "Preserve application evidence"
    staged = {}
    try:
        for path, content in outputs.items():
            fd, name = tempfile.mkstemp(prefix=".cycle3-", dir=HERE)
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
            staged[path] = Path(name)
        for path in sorted(staged):
            assert digest(path) == before[path]
            os.replace(staged[path], path)
        applied_path.write_bytes(encoded(applied))
    finally:
        for path in staged.values():
            path.unlink(missing_ok=True)
    print(json.dumps({"changedIds": 6, "changedFiles": len(files),
                      "appliedSha256": digest(applied_path)}))


if __name__ == "__main__":
    main()
