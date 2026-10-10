#!/usr/bin/env python3
"""Freeze exact corrected Bulgarian authored files and validation receipts."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BG = ROOT / "Translations/bg"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def main():
    plan_path = BG / "correction-batch-003.json"
    plan = load(plan_path)
    assert plan["decisionCount"] == 41
    baseline_path = BG / "correction-batch-002-result.json"
    baseline = load(baseline_path)
    corpus_path = BG / "locale-corpus-cycle-003.json"
    corpus = load(corpus_path)
    preserve_path = BG / "preserve-exact-cycle-003.json"
    preserve = load(preserve_path)
    assert corpus["rows"] == preserve["checkedRows"] == 16538
    assert corpus["structuralResult"] == corpus["exactResult"] == preserve["exactResult"] == "passed"
    affected = {d["batchPath"] for d in plan["decisions"]}
    files = []
    for original in baseline["allAuthoredFiles"]:
        record = dict(original)
        path = ROOT / record["path"]
        sidecar = ROOT / record["validationPath"]
        record["sha256"] = sha(path)
        record["validationSha256"] = sha(sidecar)
        if record["path"] not in affected:
            assert record == original, record["path"]
        else:
            check = load(sidecar)
            assert check["batchSha256"] == record["sha256"] and check["structuralResult"] == "passed"
        files.append(record)
    assert len(files) == baseline["allAuthoredFileCount"] == 411
    assert {f["path"] for f in files} == {f["path"] for f in corpus["authoredFiles"]}
    assert all(f["sha256"] == next(c["sha256"] for c in corpus["authoredFiles"]
                                     if c["path"] == f["path"]) for f in files)
    assert {f["path"] for f in preserve["inputFiles"]} == {f["path"] for f in files}
    assert all(f["sha256"] == next(c["sha256"] for c in preserve["inputFiles"]
                                     if c["path"] == f["path"]) for f in files)
    changed = [f for f in files if f["path"] in affected]
    result = {"schemaVersion": 1, "locale": "bg", "gameVersion": "1.3.19",
              "status": "41 full-unit corrections applied; 35 affected batches validated; full 16538-unit structural and exact corpus passed; independent delta pending",
              "planPath": str(plan_path.relative_to(ROOT)), "planSha256": sha(plan_path),
              "baselineResultPath": str(baseline_path.relative_to(ROOT)),
              "baselineResultSha256": sha(baseline_path),
              "changedIds": [d["stableId"] for d in plan["decisions"]],
              "changedIdCount": len(plan["decisions"]),
              "changedFiles": changed, "changedFileCount": len(changed),
              "allAuthoredFiles": files, "allAuthoredFileCount": len(files),
              "localeCorpus": {"path": str(corpus_path.relative_to(ROOT)), "sha256": sha(corpus_path),
                                "rows": corpus["rows"], "result": "passed"},
              "preserveExactly": {"path": str(preserve_path.relative_to(ROOT)),
                                  "sha256": sha(preserve_path), "checkedRows": 16538,
                                  "result": "passed"},
              "independentDiffReview": "pending separate reviewer; no editorial acceptance"}
    path = BG / "correction-batch-003-result.json"
    payload = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode()
    if path.exists():
        assert path.read_bytes() == payload
    else:
        path.write_bytes(payload)
    print(json.dumps({"changedIds": len(result["changedIds"]), "changedFiles": len(changed),
                      "allFiles": len(files), "resultSha256": sha(path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
