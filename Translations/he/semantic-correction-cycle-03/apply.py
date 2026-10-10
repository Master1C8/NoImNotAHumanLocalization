#!/usr/bin/env python3
"""Apply the fully staged cycle-03 authored batch with restart-safe file checks."""

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CYCLE = Path(__file__).resolve().parent
HE = CYCLE.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    pre = json.loads((CYCLE / "preflight.json").read_text())
    staged = json.loads((CYCLE / "staged-validation-summary.json").read_text())
    consumer = json.loads((CYCLE / "consumer-preflight.json").read_text())
    pins = json.loads((CYCLE / "input-pins.json").read_text())
    baseline = json.loads((CYCLE / "baseline-progress.json").read_text())
    assert pre["status"] == "passed before authored application"
    assert pre["acceptedUnits"] == 16538 and pre["acceptedCorrections"] == 71
    assert staged["status"] == "passed before authored application"
    assert staged["validatedStagedFiles"] == pre["changedAuthoredFiles"] == len(pre["files"])
    assert consumer["branchCount"] == 4 and consumer["assembledVariants"] == 13
    assert sha(CYCLE / "input-pins.json") == pre["inputPinsSha256"]
    assert sha(CYCLE / "adjudications.json") == pre["adjudicationsSha256"]
    assert sha(CYCLE / "changed-ids.txt") == pre["changedIdsSha256"]
    assert sha(ROOT / baseline["sourceInventory"]["stringsPath"]) == pins["sourceInventory"]["stringsSha256"]
    assert sha(ROOT / baseline["sourceInventory"]["staticPath"]) == pins["sourceInventory"]["staticSha256"]
    assert sha(ROOT / baseline["sourceInventory"]["preserveExactPath"]) == pins["sourceInventory"]["preserveExactSha256"]
    assert sha(Path(baseline["glossary"]["path"])) == pins["glossary"]["sha256"]
    assert sha(HE / "progress.json") == pins["priorProgressSha256"]
    assert sha(HE / "semantic-review-progress.json") == pins["priorSemanticProgressSha256"]
    for row in baseline["files"]:
        rel = row["path"]
        now = sha(ROOT / rel)
        expected = pre["files"][rel] if rel in pre["files"] else None
        if expected:
            assert now in (expected["beforeSha256"], expected["afterSha256"]), rel
        else:
            assert now == row["sha256"], rel
    for rel, record in pre["files"].items():
        assert sha(CYCLE / "before-authored" / Path(rel).name) == record["beforeSha256"]
        assert sha(CYCLE / "after-authored" / Path(rel).name) == record["afterSha256"]
    for row in staged["files"]:
        path = ROOT / row["path"]
        assert row["returncode"] == 0 and row["result"] == "passed"
        assert row["batchSha256"] == sha(path)
        assert row["sidecarSha256"] == sha(path.with_suffix(".validation.json"))
    applied = 0
    for rel, record in sorted(pre["files"].items()):
        path = ROOT / rel
        if sha(path) == record["afterSha256"]:
            continue
        temporary = path.with_name(path.name + ".he-cycle03-tmp")
        assert not temporary.exists()
        temporary.write_bytes((CYCLE / "after-authored" / path.name).read_bytes())
        assert sha(temporary) == record["afterSha256"]
        os.replace(temporary, path)
        assert sha(path) == record["afterSha256"]
        applied += 1
    assert all(sha(ROOT / rel) == rec["afterSha256"] for rel, rec in pre["files"].items())
    receipt = {"schemaVersion": 1, "status": "applied", "changedStableIds": 71,
               "changedAuthoredFiles": len(pre["files"]), "appliedThisRun": applied,
               "preflightSha256": sha(CYCLE / "preflight.json"),
               "consumerPreflightSha256": sha(CYCLE / "consumer-preflight.json"),
               "stagedValidationSummarySha256": sha(CYCLE / "staged-validation-summary.json"),
               "files": pre["files"],
               "commitBoundary": "Each authored file was atomically replaced; the multi-file set was not a transaction. All after hashes verified before this receipt."}
    data = (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode()
    target = CYCLE / "application.json"
    if target.exists():
        assert target.read_bytes() == data
    else:
        target.write_bytes(data)
    print(json.dumps({"appliedThisRun": applied, "verifiedFiles": len(pre["files"]),
                      "applicationSha256": sha(target)}))


if __name__ == "__main__":
    main()
