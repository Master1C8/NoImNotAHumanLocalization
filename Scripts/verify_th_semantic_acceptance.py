#!/usr/bin/env python3
"""Verify the completed Thai text review and its final authored targets."""

import hashlib
import json
import re
from pathlib import Path

from apply_th_semantic_corrections import authored_entries
from probe_assets import ROOT, require


AUDIT = ROOT / "Documentation/th-semantic-audit-progress-v44.json"
PLAN_1 = ROOT / "Documentation/th-semantic-correction-plan-v2.json"
PLAN_2 = ROOT / "Documentation/th-semantic-correction-plan-v3.json"
RECEIPT_1 = ROOT / "Documentation/th-semantic-correction-application-v1.json"
RECEIPT_2 = ROOT / "Documentation/th-semantic-correction-application-v2.json"
DIFF = ROOT / "Documentation/th-semantic-diff-audit-findings-v1.json"
EXACT = ROOT / "Documentation/th-preserve-exact-v8.json"
PREVIOUS_EXACT = ROOT / "Documentation/th-preserve-exact-v7.json"
PREVIOUS_ACCEPTANCE = ROOT / "Documentation/th-semantic-acceptance-v1.json"
RUNTIME_LOG = ROOT / "outputs/dialogue-th-v5/final-recovery/nohuman-dialogue-evidence.jsonl"
REPORT = ROOT / "Documentation/th-semantic-acceptance-v2.json"
RUNTIME_CORRECTION_ID = "tmp:level1:3904:m_text"
RUNTIME_CORRECTION_BEFORE = " ﻥﺷﺛﻣﻙ"
RUNTIME_CORRECTION_AFTER = " ตัวเลือก"
BATCH = re.compile(r"(?:ui|dialogue|checks)-batch-\d{3}\.json")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    audit, first, second = read(AUDIT), read(PLAN_1), read(PLAN_2)
    receipt_1, receipt_2, diff, exact = (
        read(RECEIPT_1), read(RECEIPT_2), read(DIFF), read(EXACT))
    previous, previous_exact = read(PREVIOUS_ACCEPTANCE), read(PREVIOUS_EXACT)
    require(previous["unresolvedObjectiveFindings"] == 0 and
            previous["inputSha256"][str(PREVIOUS_EXACT.relative_to(ROOT))] ==
            digest(PREVIOUS_EXACT), "Previous Thai acceptance changed")
    previous_files = {row["path"]: row["sha256"] for row in previous_exact["inputFiles"]}
    current_files = {row["path"]: row["sha256"] for row in exact["inputFiles"]}
    require(previous_files.keys() == current_files.keys() and
            {path for path in previous_files if previous_files[path] != current_files[path]} ==
            {"Translations/th/static-text-draft.json"},
            "Runtime correction changed more than the one static draft")
    events = [json.loads(line) for line in RUNTIME_LOG.open()]
    require(any(row["kind"] == "answer-panel" and
                row["data"].get("text") == RUNTIME_CORRECTION_BEFORE
                for row in events), "Missing runtime evidence for the placeholder")
    require(audit["reviewedRows"] == audit["totalRows"] == 16538 and
            len(audit["findings"]) == 145,
            "First full source-to-target read differs")
    require(receipt_1["planSha256"] == digest(PLAN_1) and
            receipt_2["planSha256"] == digest(PLAN_2) and
            second["inputReceiptSha256"] == digest(RECEIPT_1),
            "Correction chain changed")
    require(second["diffAuditFindingsSha256"] == digest(DIFF) and
            diff["reviewedUniqueTriplets"] == 186 and
            diff["reviewedChangedRows"] == 450 and
            len(diff["findings"]) == 7,
            "Independent diff audit differs")
    require(exact["exactResult"] == "passed" and exact["checkedRows"] == 16538,
            "Final exact-text gate did not pass")
    require(first["pairedSha256"] == audit["pairedSha256"] ==
            digest(ROOT / first["pairedPath"]),
            "Source/target audit input changed")
    paired = [json.loads(line) for line in (ROOT / first["pairedPath"]).open()]
    require(len(paired) == 16538 and
            [row["ordinal"] for row in paired] == list(range(1, 16539)),
            "Audit ordinals are incomplete")
    expected = {row["stableId"]: row["target"] for row in paired}
    require(len(expected) == 16538, "Duplicate accepted stable ID")
    first_ids = set()
    for change in first["changes"]:
        key = change["stableId"]
        require(key not in first_ids and expected[key] == change["currentTarget"],
                "First correction predecessor differs")
        first_ids.add(key)
        expected[key] = change["proposedTarget"]
    require(len(first_ids) == 450, "First correction row count differs")
    second_ids = set()
    for change in second["changes"]:
        key = change["stableId"]
        require(key not in second_ids and expected[key] == change["currentTarget"],
                "Diff correction predecessor differs")
        second_ids.add(key)
        expected[key] = change["proposedTarget"]
    require(len(second_ids) == 7, "Diff correction row count differs")
    waived = {row["ordinal"] for row in first["findingsNoChangeAfterContext"]}
    require(waived == {484}, "Editorial waiver changed")
    require(all(f["stableId"] in first_ids or f["ordinal"] in waived
                for f in audit["findings"]), "First-pass finding lacks resolution")

    _, authored = authored_entries()
    require(set(authored) == set(expected), "Authored stable-ID coverage changed")
    require(expected[RUNTIME_CORRECTION_ID] == RUNTIME_CORRECTION_BEFORE,
            "Previous placeholder target changed")
    expected[RUNTIME_CORRECTION_ID] = RUNTIME_CORRECTION_AFTER
    for key, value in expected.items():
        require(authored[key][1]["target"] == value,
                "Final authored target differs: " + key)
    residual_signals = [row["ordinal"] for row in paired
                        if "признак" in row["source"].lower() and
                        "สัญญาณ" in authored[row["stableId"]][1]["target"]]
    require(residual_signals == [8152, 14289],
            "Guest trait terminology closure changed")
    wrong_dismissals = [row["ordinal"] for row in paired
                        if re.search(r"на ?хуй|нахер", row["source"], re.I) and
                        "ไปตาย" in authored[row["stableId"]][1]["target"]]
    require(not wrong_dismissals, "Dismissal still rendered as a death wish")

    final_receipts = {item["path"]: item["sha256After"] for item in
                      receipt_1["files"] + receipt_2["files"]}
    require(len(final_receipts) == 117, "Changed-file closure changed")
    for name, sha in final_receipts.items():
        actual = (previous_files[name] if name == "Translations/th/static-text-draft.json"
                  else digest(ROOT / name))
        require(actual == sha,
                "Final translation file differs from correction receipt: " + name)
    for item in exact["inputFiles"]:
        require(digest(ROOT / item["path"]) == item["sha256"],
                "Final exact report has a stale input file")
    validation_files = 0
    for path in sorted((ROOT / "Translations/th").glob("*batch-*.json")):
        if not BATCH.fullmatch(path.name):
            continue
        sidecar = path.with_suffix(".validation.json")
        require(sidecar.exists() and
                read(sidecar)["batchSha256"] == digest(path) and
                read(sidecar)["structuralResult"] == "passed",
                "Stale batch validation: " + str(path))
        validation_files += 1
    static = ROOT / "Translations/th/static-text-draft.json"
    static_validation = read(static.with_suffix(".validation.json"))
    require(static_validation["draftSha256"] == digest(static) and
            static_validation["structuralResult"] == "passed",
            "Stale static validation")
    require(validation_files == 334, "Authored batch count changed")

    require(not REPORT.exists(), "Preserve previous acceptance report")
    report = {"schemaVersion": 1, "locale": "th", "gameVersion": "1.3.19",
              "status": "Thai text editorially accepted offline; runtime and visual QA pending",
              "acceptedSourceRows": len(paired), "firstSemanticPassRows": 16538,
              "firstPassFindings": 145, "contextualWaivers": 1,
              "firstCorrectionRows": 450, "independentDiffTripletsReviewed": 186,
              "independentDiffRowsReviewed": 450, "diffRevisions": 7,
              "finalExactRows": exact["checkedRows"],
              "finalBatchValidations": validation_files,
              "finalStaticValidationRows": static_validation["rows"],
              "unresolvedObjectiveFindings": 0,
              "runtimeCorrection": {"stableId": RUNTIME_CORRECTION_ID,
                                    "before": RUNTIME_CORRECTION_BEFORE,
                                    "after": RUNTIME_CORRECTION_AFTER,
                                    "reason": "The serialized answer-panel placeholder appeared during Thai dialogue and produced missing-glyph boxes.",
                                    "previousAcceptanceSha256": digest(PREVIOUS_ACCEPTANCE),
                                    "runtimeEvidenceSha256": digest(RUNTIME_LOG)},
              "inputSha256": {str(path.relative_to(ROOT)): digest(path)
                              for path in (AUDIT, PLAN_1, PLAN_2, RECEIPT_1,
                                           RECEIPT_2, DIFF, EXACT)},
              "runtime": "not-run", "visualQa": "not-run"}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"report": str(REPORT.relative_to(ROOT)),
                      "acceptedSourceRows": len(paired),
                      "unresolvedObjectiveFindings": 0}))


if __name__ == "__main__":
    main()
