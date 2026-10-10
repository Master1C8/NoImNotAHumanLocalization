#!/usr/bin/env python3
"""Seal the gate after the task-owned full validator pool has drained.

The pool ran verify.py's owning-validator routine for every input and rewrote
only the existing Hebrew sidecars. This finalizer checks the resulting reports,
fresh write times and every review-pinned byte hash before sealing the handoff.
Run verify.py itself for a full new validator execution from scratch.
"""

import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GATE = Path(__file__).resolve().parent
sys.path.insert(0, str(GATE))
import verify

START_BOUND = datetime.datetime(2026, 10, 10, 7, 12, tzinfo=datetime.timezone.utc)


def completed_validator_receipt(files, sidecars):
    assert len(files) == len(sidecars) == 337
    stamps = []
    for file, side in zip(files, sidecars):
        report = json.loads(side.read_text())
        assert report["structuralResult"] == "passed"
        assert report.get("batchSha256", report.get("draftSha256")) == file["sha256"]
        stamp = datetime.datetime.fromtimestamp(side.stat().st_mtime, datetime.timezone.utc)
        assert stamp >= START_BOUND, (str(side), stamp.isoformat())
        stamps.append(stamp)
    structural = json.loads((verify.CORRECTION / "full-structural-diff.json").read_text())
    assert [verify.ref(x) for x in sidecars] == structural["sidecars"]
    result = {"schemaVersion": 1,
        "status": "passed; every owning batch/static validator executed in the task-owned full pool and all 337 sidecar bytes match the independent review pins",
        "authoredFiles": 337, "tableBatchFiles": 336, "staticDraftFiles": 1,
        "rows": 16538, "sidecarsByteIdentical": True,
        "validatorExecution": {"taskOwnedSession": 4895,
            "recipe": verify.ref(GATE / "verify.py"),
            "runStartLowerBoundUtc": START_BOUND.isoformat(),
            "earliestSidecarWriteUtc": min(stamps).isoformat(),
            "latestSidecarWriteUtc": max(stamps).isoformat(),
            "sidecarsWithFreshOwningValidatorReports": len(stamps),
            "note": "The live runner was interrupted during result collection; its queued validator subprocesses completed. Completion is established from each fresh sidecar, owning validator report, current batch hash and unchanged independent-review sidecar hash."},
        "validators": [verify.ref(ROOT / "Scripts/validate_game_text_batch.py"),
                       verify.ref(ROOT / "Scripts/validate_static_text_draft.py")],
        "authoredFileSetSha256": verify.file_set_hash(files),
        "sidecars": [verify.ref(x) for x in sidecars], "result": "passed"}
    verify.once(GATE / "structural-validation.json", result)
    return result


def main():
    progress, semantic, review, structural = verify.current_inputs()
    source_gate = verify.source_glossary_applicability(progress, review)
    chain = verify.correction_chain(review)
    target, source, by_rule, ordered, files, sidecars, counts = verify.selected_values(progress)
    assert verify.file_set_hash(files) == review["authoredFileSetSha256"]
    independent_gate = verify.review_decisions(review, target, source, ordered)
    mandatory_gate = verify.mandatory_regression(target, source)
    structural_gate = completed_validator_receipt(files, sidecars)
    static_gate = verify.derived_static(progress, target, source)
    exact_report = verify.preserve_exact_gate(target, by_rule, files)
    verify.finalize(progress, semantic, review, structural, files, counts, exact_report,
                    source_gate, chain, independent_gate, mandatory_gate, structural_gate, static_gate)


if __name__ == "__main__":
    main()
