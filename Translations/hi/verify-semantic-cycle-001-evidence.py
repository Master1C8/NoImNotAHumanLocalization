#!/usr/bin/env python3
"""Verify Hindi correction evidence; optionally write its immutable receipt."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HI = ROOT / "Translations/hi"
OUT = HI / "semantic-cycle-001-applied-evidence.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    plan = read(HI / "semantic-cycle-001-application-plan.json")
    adjudication = read(HI / "semantic-cycle-001-adjudication.json")
    gate = read(HI / "semantic-cycle-001-structural-gate.json")
    assert sha(HI / "semantic-cycle-001-adjudication.json") == plan["adjudicationSha256"]
    assert len(plan["files"]) == plan["fileCount"] == 72
    assert len(plan["changedIds"]) == plan["changedCount"] == 94
    changes = {item["stableId"]: item for item in adjudication["items"]}
    assert set(changes) == set(plan["changedIds"])
    post_gate = {file["path"]: file for file in gate["files"]}
    receipts = []
    for file in plan["files"]:
        path = Path(file["path"])
        before = HI / "semantic-cycle-001-before-files" / path.name
        after = HI / "semantic-cycle-001-after-files" / path.name
        live = ROOT / path
        assert sha(before) == file["beforeSha256"], before
        assert sha(after) == sha(live) == file["afterSha256"] == post_gate[file["path"]]["sha256"], live
        old = read(before)
        new = read(after)
        assert old.keys() == new.keys() and old["entries"] != new["entries"]
        assert {k: old[k] for k in old if k != "entries"} == {k: new[k] for k in new if k != "entries"}
        old_entries = {str(row["id"]): row for row in old["entries"]}
        new_entries = {str(row["id"]): row for row in new["entries"]}
        assert old_entries.keys() == new_entries.keys()
        changed_numeric = set()
        for number in old_entries:
            before_row, after_row = old_entries[number], new_entries[number]
            assert before_row.keys() == after_row.keys()
            assert {k: before_row[k] for k in before_row if k != "target"} == {k: after_row[k] for k in after_row if k != "target"}
            if before_row["target"] != after_row["target"]:
                changed_numeric.add(number)
        assert changed_numeric == {sid.rsplit(":", 1)[1] for sid in file["changedIds"]}
        for sid in file["changedIds"]:
            number = sid.rsplit(":", 1)[1]
            assert old_entries[number]["target"] == changes[sid]["before"]
            assert new_entries[number]["target"] == changes[sid]["acceptedFullTarget"]
        vpath = Path(file["beforeValidationPath"])
        before_validation = HI / "semantic-cycle-001-before-files" / vpath.name
        after_validation = HI / "semantic-cycle-001-after-files" / vpath.name
        assert sha(before_validation) == file["beforeValidationSha256"]
        assert sha(after_validation) == sha(ROOT / vpath) == post_gate[file["path"]]["validationSha256"]
        receipt = dict(file)
        receipt["afterValidationSha256"] = sha(after_validation)
        receipt["changedCount"] = len(changed_numeric)
        receipts.append(receipt)
    result = {
        "schemaVersion": 1,
        "locale": "hi",
        "gameVersion": "1.3.19",
        "status": "before/after evidence verified; full semantic and independent acceptance pending",
        "applicationPlanSha256": sha(HI / "semantic-cycle-001-application-plan.json"),
        "adjudicationSha256": sha(HI / "semantic-cycle-001-adjudication.json"),
        "structuralGateSha256": sha(HI / "semantic-cycle-001-structural-gate.json"),
        "changedIds": len(changes),
        "changedFiles": len(receipts),
        "unexpectedEntryOrMetadataChanges": 0,
        "evidenceFiles": receipts,
        "writeBoundary": plan["writeBoundary"],
    }
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.verify:
        assert OUT.read_text(encoding="utf-8") == text
        print("verified 94 corrections in 72 files, including before/after sidecars")
    else:
        OUT.write_text(text, encoding="utf-8")
        print("wrote verified 94-correction evidence receipt")


if __name__ == "__main__":
    main()
