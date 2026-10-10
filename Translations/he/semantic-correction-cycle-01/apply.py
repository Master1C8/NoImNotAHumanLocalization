#!/usr/bin/env python3
"""Apply the preflighted Hebrew correction cycle with per-file restart checks."""

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
    preflight = json.loads((CYCLE / "preflight.json").read_text())
    assert preflight["status"] == "passed before authored application"
    assert preflight["acceptedUnits"] == 16538
    assert preflight["acceptedFindings"] == 120
    assert preflight["changedAuthoredFiles"] == 81
    assert sha(CYCLE / "changed-ids.txt") == preflight["changedIdsSha256"]
    assert sha(CYCLE / "adjudications.json") == preflight["adjudicationsSha256"]
    assert json.loads((CYCLE / "consumer-preflight.json").read_text())["fullDisplayCellRows"] == 17
    assert json.loads((CYCLE / "staged-validation-summary.json").read_text())["validatedStagedFiles"] == 81
    baseline = json.loads((CYCLE / "baseline-semantic-review-progress.json").read_text())
    progress = json.loads((CYCLE / "baseline-progress.json").read_text())
    assert sha(ROOT / progress["sourceInventory"]["stringsPath"]) == baseline["sourceInventorySha256"]
    assert sha(ROOT / progress["sourceInventory"]["preserveExactPath"]) == baseline["preserveExactSha256"]
    assert sha(Path(progress["glossary"]["path"])) == baseline["glossarySha256"]
    assert len(preflight["files"]) == 81
    # Establish the complete input state before any replacement. A resumed run may
    # see files already at the exact staged hash, and will never revert them.
    for rel, record in preflight["files"].items():
        current = sha(ROOT / rel)
        assert current in (record["beforeSha256"], record["afterSha256"]), rel
        assert sha(CYCLE / "before-authored" / Path(rel).name) == record["beforeSha256"]
        assert sha(CYCLE / "after-authored" / Path(rel).name) == record["afterSha256"]
    changed = 0
    for rel, record in sorted(preflight["files"].items()):
        path = ROOT / rel
        if sha(path) == record["afterSha256"]:
            continue
        temporary = path.with_name(path.name + ".he-cycle01-tmp")
        assert not temporary.exists(), temporary
        temporary.write_bytes((CYCLE / "after-authored" / path.name).read_bytes())
        assert sha(temporary) == record["afterSha256"]
        os.replace(temporary, path)
        assert sha(path) == record["afterSha256"]
        changed += 1
    assert all(sha(ROOT / rel) == record["afterSha256"]
               for rel, record in preflight["files"].items())
    receipt = CYCLE / "application.json"
    payload = {"schemaVersion": 1, "status": "applied",
               "preflightSha256": sha(CYCLE / "preflight.json"),
               "consumerPreflightSha256": sha(CYCLE / "consumer-preflight.json"),
               "stagedValidationSummarySha256": sha(CYCLE / "staged-validation-summary.json"),
               "changedStableIds": 120, "changedAuthoredFiles": 81,
               "files": preflight["files"],
               "commitBoundary": "Each authored file was replaced atomically; the 81-file set was not a transaction. All after hashes verified before this receipt."}
    data = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()
    if receipt.exists():
        assert receipt.read_bytes() == data
    else:
        receipt.write_bytes(data)
    print(json.dumps({"appliedNow": changed, "verifiedFiles": 81,
                      "applicationSha256": sha(receipt)}))


if __name__ == "__main__":
    main()
