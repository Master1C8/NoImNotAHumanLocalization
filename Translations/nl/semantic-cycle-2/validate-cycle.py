#!/usr/bin/env python3
"""Validate Dutch cycle 2 against the unchanged shared validator logic."""

import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path

from importlib.machinery import SourceFileLoader

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def import_shared(filename):
    utility = types.ModuleType("probe_assets")
    utility.ROOT = ROOT
    utility.digest = sha
    def require(condition, message):
        if not condition:
            raise ValueError(message)
    utility.require = require
    previous = sys.modules.get("probe_assets")
    sys.modules["probe_assets"] = utility
    try:
        spec = importlib.util.spec_from_file_location("nl_" + filename, ROOT / "Scripts" / (filename + ".py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if previous is None:
            del sys.modules["probe_assets"]
        else:
            sys.modules["probe_assets"] = previous


def run_main(module, path):
    old = sys.argv
    try:
        sys.argv = [module.__file__, str(path)]
        module.main()
    finally:
        sys.argv = old


def main():
    report_path = HERE / "structural-validation.json"
    exact_path = HERE / "preserve-exact-v4-after.json"
    assert not report_path.exists() and not exact_path.exists()
    adjudication_path = HERE / "adjudicated-corrections-v2.json"
    preflight_path = HERE / "complete-batch-preflight-v2.json"
    adjudication = json.loads(adjudication_path.read_text())
    preflight = json.loads(preflight_path.read_text())
    assert preflight["adjudicationSha256"] == sha(adjudication_path)
    before = [json.loads(line) for line in (HERE / "before-rows.jsonl").open()]
    after = [json.loads(line) for line in (HERE / "after-rows.jsonl").open()]
    assert len(before) == len(after) == len(adjudication["corrections"]) == 38
    assert [x["stableId"] for x in before] == [x["stableId"] for x in after]
    changed = {row["stableId"]: row for row in adjudication["corrections"]}
    paths = [h["path"] for h in adjudication["beforeAuthoredHashes"]]
    # Reconstruct every prior batch byte-for-byte to prove no collateral edits.
    original_hash = {h["path"]: h["sha256"] for h in adjudication["beforeAuthoredHashes"]}
    guids = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
             "UI": "0cbd8a7a4f543344bb95659de87f67a5",
             "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}
    recipe = SourceFileLoader("nl_cycle_recipe", str(ROOT / "Translations/nl/semantic-cycle-1/prepare-and-apply.py")).load_module()
    for rel in paths:
        doc = json.loads((ROOT / rel).read_text())
        for entry in doc["entries"]:
            sid = f"string:{guids[doc['collection']]}:{entry['id']}"
            if sid in changed:
                assert entry["target"] == changed[sid]["after"]
                entry["target"] = changed[sid]["before"]
        style = recipe.original_style(doc, original_hash[rel])
        reconstructed = recipe.serialize_batch(doc, style).encode("utf-8")
        assert hashlib.sha256(reconstructed).hexdigest() == original_hash[rel], rel
    batch_validator = import_shared("validate_game_text_batch")
    batch_reports = []
    for rel in paths:
        path = ROOT / rel
        run_main(batch_validator, path)
        sidecar = path.with_suffix(".validation.json")
        side = json.loads(sidecar.read_text())
        assert side["batchSha256"] == sha(path) and side["structuralResult"] == "passed"
        batch_reports.append({"path": rel, "sha256": sha(path), "validationPath": str(sidecar.relative_to(ROOT)),
                              "validationSha256": sha(sidecar), "rows": side["authoredRows"]})
    # The static draft is unchanged, but rerun its source and credits checks.
    static_path = ROOT / "Translations/nl/static-text-draft.json"
    static_validator = import_shared("validate_static_text_draft")
    run_main(static_validator, static_path)
    static_report = static_path.with_suffix(".validation.json")
    assert json.loads(static_report.read_text())["structuralResult"] == "passed"
    full = import_shared("preserve_exact")
    full.validate("nl", exact_path)
    exact = json.loads(exact_path.read_text())
    assert exact["checkedRows"] == 16538 and exact["exactResult"] == "passed"
    result = {
        "schemaVersion": 1, "locale": "nl", "cycle": 2,
        "adjudicationSha256": sha(adjudication_path),
        "beforeRowsSha256": sha(HERE / "before-rows.jsonl"),
        "afterRowsSha256": sha(HERE / "after-rows.jsonl"),
        "changedAuthoredFileCount": len(paths), "changedUnitCount": 38,
        "priorAuthoredBatchesReconstructedExact": True,
        "changedBatchValidation": batch_reports,
        "staticDraft": {"path": str(static_path.relative_to(ROOT)), "sha256": sha(static_path),
                        "validationPath": str(static_report.relative_to(ROOT)),
                        "validationSha256": sha(static_report), "rows": 178},
        "fullExact": {"path": str(exact_path.relative_to(ROOT)), "sha256": sha(exact_path),
                      "checkedRows": 16538, "result": "passed"},
        "runtime": "not-run", "independentReview": "pending",
        "validatorImportNote": "Unchanged shared validator code; only probe_assets ROOT/digest/require supplied locally to avoid loading unavailable UnityPy and game assets.",
    }
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"Validated {len(paths)} changed batches and all 16538 exact-text units")


if __name__ == "__main__":
    main()
