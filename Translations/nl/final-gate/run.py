#!/usr/bin/env python3
"""Final Dutch static text gate on the reviewed, unchanged authored inputs.

Run with the canonical checkout's .venv/bin/python. This reads shared inputs,
updates only Dutch validation sidecars, and writes immutable Dutch gate receipts.
"""

import contextlib
import hashlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
NL = ROOT / "Translations/nl"
REVIEW = NL / "independent-review-03"
MANIFEST = NL / "semantic-cycle-3/closure-v2/closure-manifest.json"
CHECKPOINT = NL / "semantic-cycle-3/checkpoint-v2.json"
REPORT = HERE / "structural-and-exact.json"
EXACT = HERE / "preserve-exact-v4.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def text_sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def lines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_cli_main(module, path):
    prior = sys.argv
    try:
        sys.argv = [str(module.__file__), str(path)]
        with contextlib.redirect_stdout(io.StringIO()):
            module.main()
    finally:
        sys.argv = prior


def verify_review_and_inputs():
    assert not REPORT.exists() and not EXACT.exists(), "Preserve existing final gate reports"
    manifest = load(MANIFEST)
    checkpoint = load(CHECKPOINT)
    evidence = load(REVIEW / "evidence-manifest.json")
    final = load(REVIEW / "final-input-recheck.json")
    assert sha(MANIFEST) == checkpoint["cycle3"]["closureManifestSha256"] == evidence["currentClosureManifestSha256"]
    assert sha(ROOT / manifest["deltaReviewRowsPath"]) == evidence["currentDeltaRowsSha256"]
    assert evidence["reviewer"] == "/root/nl_independent_review_03"
    assert evidence["reviewedPairs"] == 40 and evidence["objectiveTextFindings"] == 0
    assert evidence["finalInputHashesUnchanged"] is True and final["status"] == "passed"
    for item in evidence["artifacts"]:
        assert sha(ROOT / item["path"]) == item["sha256"], item["path"]
    assert len(final["verifiedHashes"]) == 400
    for item in final["verifiedHashes"]:
        assert sha(item["path"]) == item["sha256"], item["path"]
    assert sha(ROOT / checkpoint["currentProgressPath"]) == checkpoint["currentProgressSha256"]
    assert sha(ROOT / checkpoint["handoffPath"]) == checkpoint["handoffSha256"]
    assert final["authoredSetSha256"] == manifest["manual"]["authoredSetSha256"] == checkpoint["currentAuthoredBatchSetSha256"]
    for item in manifest["pins"].values():
        path = Path(item["path"])
        assert sha(path if path.is_absolute() else ROOT / path) == item["sha256"], item["path"]
    for item in manifest["manual"]["authoredBatches"]:
        assert sha(ROOT / item["path"]) == item["sha256"], item["path"]
    authored_set = text_sha("".join(item["path"] + " " + item["sha256"] + "\n"
                                  for item in manifest["manual"]["authoredBatches"]))
    assert authored_set == manifest["manual"]["authoredSetSha256"]
    assert len(manifest["manual"]["authoredBatches"]) == 334
    assert sha(NL / "static-text-map.json") == manifest["manual"]["staticMapSha256"]
    assert sha(NL / "credits-role-map.json") == manifest["manual"]["creditsRoleMapSha256"]
    assert sha(NL / "static-text-draft.json") == manifest["derived"]["staticDraftSha256"]
    first = load(NL / "semantic-review-progress.json")
    assert first["acceptedUnits"] == first["reviewedUnits"] == 16538 and first["nextId"] is None
    assert sha(NL / "semantic-review-rows-pass1.jsonl") == manifest["pass1ReviewRowsSha256"]
    decisions = lines(REVIEW / "review-decisions.jsonl")
    delta = lines(ROOT / manifest["deltaReviewRowsPath"])
    assert len(decisions) == len(delta) == 40
    for decision, row in zip(decisions, delta):
        assert decision["reviewer"] == evidence["reviewer"]
        assert decision["fullUnitRead"] is True and decision["allUnchangedFactsChecked"] is True
        assert decision["decision"] == "no-objective-text-finding-in-independent-read"
        assert (decision["stableId"], decision["sourceSha256"], decision["targetSha256"]) == (
            row["stableId"], row["sourceSha256"], row["targetSha256"])
    assert sha(REVIEW / "review-decisions.jsonl") == next(item["sha256"] for item in evidence["artifacts"]
                                                    if item["path"].endswith("/review-decisions.jsonl"))
    findings = load(REVIEW / "findings.json")
    assert findings["objectiveTextFindings"] == 0 and findings["findings"] == []
    regression = load(REVIEW / "regression-result.json")
    mandatory = (ROOT / manifest["components"]["mandatory-regressions"]["path"]).read_text().splitlines()
    delta_ids = (ROOT / manifest["components"]["delta"]["path"]).read_text().splitlines()
    assert len(mandatory) == regression["mandatoryIds"] == 569
    assert len(delta_ids) == regression["freshFullUnitReads"] == 40
    assert set(delta_ids) <= set(mandatory)
    assert regression["reusedUnchangedIndependentReads"] == 529
    assert regression["status"].startswith("passed")
    assert len(final["reusedUnchangedDecisions"]) == 724
    reused = {item["stableId"] for item in final["reusedUnchangedDecisions"]}
    assert len(reused & set(mandatory)) == 529
    assert len(set(mandatory) - (reused | set(delta_ids))) == 0
    return manifest, evidence, regression, first


def main():
    manifest, evidence, regression, first = verify_review_and_inputs()
    state = ROOT / "Documentation/localization-state.json"
    state_before = sha(state)
    authored_before = {item["path"]: item["sha256"] for item in manifest["manual"]["authoredBatches"]}
    static_before = sha(NL / "static-text-draft.json")
    scripts = ROOT / "Scripts"
    sys.path.insert(0, str(scripts))
    batch_validator = import_file("nl_final_batch_validator", scripts / "validate_game_text_batch.py")
    static_validator = import_file("nl_final_static_validator", scripts / "validate_static_text_draft.py")
    exact_validator = import_file("nl_final_exact_validator", scripts / "preserve_exact.py")
    readiness = import_file("nl_final_readiness", scripts / "report_locale_readiness.py")
    builder = import_file("nl_static_builder", NL / "build-static-draft.py")
    script_hashes = {str(path.relative_to(ROOT)): sha(path) for path in
                     (scripts / "validate_game_text_batch.py", scripts / "validate_static_text_draft.py",
                      scripts / "preserve_exact.py", scripts / "report_locale_readiness.py",
                      NL / "build-static-draft.py")}
    batch_receipts = []
    for item in manifest["manual"]["authoredBatches"]:
        path = ROOT / item["path"]
        run_cli_main(batch_validator, path)
        sidecar = path.with_suffix(".validation.json")
        result = load(sidecar)
        assert result["batchSha256"] == item["sha256"] and result["structuralResult"] == "passed"
        batch_receipts.append({"path": item["path"], "sha256": item["sha256"],
                               "rows": result["authoredRows"], "sidecarPath": str(sidecar.relative_to(ROOT)),
                               "sidecarSha256": sha(sidecar)})
    assert sum(item["rows"] for item in batch_receipts) == 16360
    with tempfile.TemporaryDirectory(prefix="nl-static-repro-", dir=HERE) as temporary:
        builder.HERE = Path(temporary)
        for name in ("static-text-map.json", "credits-role-map.json"):
            shutil.copyfile(NL / name, Path(temporary) / name)
        with contextlib.redirect_stdout(io.StringIO()):
            builder.main()
        generated = Path(temporary) / "static-text-draft.json"
        assert generated.read_bytes() == (NL / "static-text-draft.json").read_bytes()
        reproduced_static_sha = sha(generated)
    assert reproduced_static_sha == static_before == manifest["derived"]["staticDraftSha256"]
    run_cli_main(static_validator, NL / "static-text-draft.json")
    static_sidecar = NL / "static-text-draft.validation.json"
    static_report = load(static_sidecar)
    assert static_report["rows"] == 178 and static_report["structuralResult"] == "passed"
    assert static_report["draftSha256"] == static_before
    with contextlib.redirect_stdout(io.StringIO()):
        exact_validator.validate("nl", EXACT)
    exact_result = load(EXACT)
    assert exact_result["checkedRows"] == 16538 and exact_result["exactResult"] == "passed"
    snapshot = readiness.snapshot(exact=True)
    nl = next(row for row in snapshot["locales"] if row["locale"] == "nl")
    assert nl["authoredRows"] == nl["observedInScopeRows"] == nl["structurallyValidatedRows"] == 16538
    assert nl["problems"] == [] and len(nl["files"]) == 335
    assert sha(state) == state_before, "Shared locale state changed during final gate"
    for rel, expected in authored_before.items():
        assert sha(ROOT / rel) == expected, rel
    assert sha(NL / "static-text-draft.json") == static_before
    for item in manifest["pins"].values():
        path = Path(item["path"])
        assert sha(path if path.is_absolute() else ROOT / path) == item["sha256"]
    for rel, expected in script_hashes.items():
        assert sha(ROOT / rel) == expected, rel
    output = {
        "schemaVersion": 1, "locale": "nl", "gameVersion": "1.3.19", "sourceLocale": "ru",
        "status": "passed static structural, exact, mandatory-catalog and derived-artifact gate on unchanged authored hashes",
        "reviewer": evidence["reviewer"], "reviewEvidenceManifestSha256": sha(REVIEW / "evidence-manifest.json"),
        "reviewDecisionsSha256": sha(REVIEW / "review-decisions.jsonl"),
        "firstSemanticPassReviewedUnits": first["reviewedUnits"],
        "independentCleanDeltaUnits": len((ROOT / manifest["components"]["delta"]["path"]).read_text().splitlines()),
        "mandatoryRegressionCatalog": {"count": regression["mandatoryIds"],
                                       "freshFullUnitReads": regression["freshFullUnitReads"],
                                       "reusedUnchangedHashBoundDecisions": regression["reusedUnchangedIndependentReads"],
                                       "evidenceSha256": sha(REVIEW / "regression-result.json")},
        "acceptedTextUnits": 16538, "authoredBatchCount": len(batch_receipts),
        "authoredTableRows": sum(item["rows"] for item in batch_receipts),
        "staticRows": static_report["rows"], "currentStructuralRows": nl["structurallyValidatedRows"],
        "authoredBatchSetSha256": manifest["manual"]["authoredSetSha256"],
        "closureManifestSha256": sha(MANIFEST),
        "sourceAndGlossaryPins": manifest["pins"], "validatorAndBuilderHashes": script_hashes,
        "sharedStateSha256Unchanged": state_before,
        "batchValidation": batch_receipts,
        "staticDraft": {"path": "Translations/nl/static-text-draft.json", "sha256": static_before,
                        "reproducedByteForByte": True, "validationPath": str(static_sidecar.relative_to(ROOT)),
                        "validationSha256": sha(static_sidecar)},
        "fullPreserveExact": {"path": str(EXACT.relative_to(ROOT)), "sha256": sha(EXACT),
                              "checkedRows": exact_result["checkedRows"], "result": exact_result["exactResult"]},
        "readiness": {"observedRows": nl["observedInScopeRows"], "authoredRows": nl["authoredRows"],
                      "structurallyValidatedRows": nl["structurallyValidatedRows"], "problems": nl["problems"]},
        "sourceRuntimeLimits": {
            "uncompiledAcceptedKeys": ["line:Twins_Entrance_Occupied_0880fa9",
                                       "line:Anger_Entrance_Occupied_076f124"],
            "missingExactUiLabelFallbackKeys": ["characterName_Neighbour", "characterName_Alkonost",
                                                "characterName_Twins"],
            "classification": "baseline source/runtime reachability questions; no demonstrated reachable Dutch text defect",
        },
        "staticLayoutSchema": "passed selected text structure and protected markup; rendered layout not tested",
        "runtimeLayoutFontPackage": "not-run/not-accepted",
        "imageTextures": "excluded by owner",
        "completedAt": datetime.now(timezone.utc).isoformat(),
    }
    REPORT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(f"Dutch final gate passed: {len(batch_receipts)} batches, 16,538 structural and exact rows; "
          f"review 40 clean; mandatory 569 accounted; report {sha(REPORT)}")


if __name__ == "__main__":
    main()
