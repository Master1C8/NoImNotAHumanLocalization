#!/usr/bin/env python3
"""Reproduce the Serbian offline editorial handoff on exact current bytes.

Run with --write once after the owning structural validators and fresh
preserve_exact.validate have passed. Run without --write for read-only replay.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SR = ROOT / "Translations/sr"
OUT = SR / "final-gate"
REVIEW = SR / "independent-review-03"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "Scripts"))
sys.path.insert(0, str(SR))
import preserve_exact  # noqa: E402
import reproduce_static_draft  # noqa: E402

GUIDS = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
         "UI": "0cbd8a7a4f543344bb95659de87f67a5",
         "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def textsha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def relative(path):
    return str(path.relative_to(ROOT))


def pin(path):
    return {"path": relative(path), "sha256": sha(path)}


def emit(path, value, write):
    data = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        require(path.read_text() == data, "Immutable output differs: " + str(path))
    else:
        require(write, "Missing final gate output: " + str(path))
        path.write_text(data)


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    require(OUT.is_dir(), "Missing final-gate directory")
    review_summary = read(REVIEW / "summary.json")
    review_findings = read(REVIEW / "findings.json")
    verification = read(REVIEW / "verification.json")
    review_manifest = read(REVIEW / "artifact-manifest.json")
    require(review_summary["reviewerTask"] == "/root/sr_independent_review_03" and
            review_summary["deltaReviewed"] == review_summary["deltaPassed"] == 4 and
            review_summary["objectiveFindings"] == 0 and
            review_findings["objectiveFindings"] == [] and
            len(verification["pins"]) == 786 and
            verification["result"] == "passed", "Clean review verdict differs")
    require(len(review_manifest["files"]) == 15 and
            all(sha(ROOT / f["path"]) == f["sha256"] and
                (ROOT / f["path"]).stat().st_size == f["bytes"]
                for f in review_manifest["files"]), "Review manifest differs")
    for path, item in verification["pins"].items():
        require(sha(ROOT / path) == item["expectedSha256"] == item["actualSha256"]
                and item["result"] == "passed", "Review input pin changed: " + path)

    pre = read(SR / "semantic-cycle-001-precorrection.json")
    one = read(SR / "semantic-cycle-001-corrections.json")
    regen = read(SR / "semantic-cycle-001-static-regeneration.json")
    two = read(SR / "semantic-cycle-002-corrections.json")
    three = read(SR / "semantic-cycle-003-corrections.json")
    c1 = read(SR / "semantic-cycle-001-closure.json")
    c2 = read(SR / "semantic-cycle-002-closure.json")
    c3 = read(SR / "semantic-cycle-003-closure.json")
    review1 = read(SR / "independent-review-01/summary.json")
    review2 = read(SR / "independent-review-02/summary.json")
    require(pre["acceptedUnits"] == pre["reviewedUnits"] ==
            c1["firstSemanticPassReviewedUnits"] == c2["firstSemanticPassReviewedUnits"] ==
            c3["firstSemanticPassReviewedUnits"] == 16538 and
            pre["reviewedPrefixIdsSha256"] == one["firstSemanticPassReviewedPrefixIdsSha256"] ==
            c1["firstSemanticPassReviewedPrefixIdsSha256"] and
            sha(SR / "semantic-cycle-001-precorrection.json") == one["priorEvidenceSha256"] ==
            c1["precorrectionEvidenceSha256"] and
            sha(SR / "semantic-cycle-001-corrections.json") ==
            regen["previousCorrectionEvidenceSha256"] == c1["correctionEvidenceSha256"] and
            sha(SR / "semantic-cycle-001-static-regeneration.json") ==
            c1["staticRegenerationEvidenceSha256"], "First pass/cycle001 chain differs")
    require(pre["authoredFileSetSha256"] == textsha("".join(
                x["path"] + "\t" + x["sha256"] + "\n"
                for x in sorted(pre["reviewedFileHashes"], key=lambda x: x["path"]))) and
            len(pre["reviewedFileHashes"]) == 341 and
            sum(x["units"] for x in pre["reviewedFileHashes"]) == 16538 and
            one["changedIdCount"] == 26 and
            one["currentAuthoredFileSetSha256"] != pre["authoredFileSetSha256"] and
            regen["currentAuthoredFileSetSha256"] == c1["currentAuthoredFileSetSha256"] ==
            review1["authoredFileSetSha256"], "First pass/cycle001 coverage differs")
    require(sha(SR / "semantic-cycle-001-closure.json") == two["priorClosureSha256"] ==
            c2["priorClosureSha256"] and
            two["changedIdsCount"] == 17 and
            two["currentAuthoredFileSetSha256"] == c2["currentAuthoredFileSetSha256"] ==
            review2["authoredFileSetSha256"] and
            sha(SR / "semantic-cycle-002-closure.json") == three["priorClosureSha256"] ==
            c3["priorClosureSha256"] and
            three["changedIdsCount"] == 1 and
            three["priorAuthoredFileSetSha256"] == two["currentAuthoredFileSetSha256"] and
            three["currentAuthoredFileSetSha256"] == c3["currentAuthoredFileSetSha256"] ==
            review_summary["authoredFileSetSha256"], "Correction/independent chain differs")
    for evidence in (pre, one, two, three):
        for key, name in (("sourceInventorySha256", "Source/localization-inventory-v3/strings.jsonl"),
                          ("sourceStaticSha256", "Source/localization-inventory-v3/static-text.jsonl"),
                          ("glossaryFingerprint", "Documentation/glossary-translations/sr/layer.json")):
            require(evidence[key] == sha(ROOT / name), "Historical source/glossary changed")
    require(sha(ROOT / "Documentation/text-source-acceptance-v1.json") ==
            three["sourceAcceptanceSha256"], "Source acceptance changed")
    glossary = read(REVIEW / "glossary-approval-verification.json")
    require(glossary["entryCount"] == 201 and
            glossary["approvalSha256"] ==
            sha(ROOT / "Documentation/glossary-translations/canonical-reviews/sr.json") ==
            three["canonicalGlossaryReviewSha256"] and
            glossary["layerRawSha256"] == three["glossaryFingerprint"] and
            glossary["masterSourceRawParity"] and glossary["masterSerbianLayerParsedParity"],
            "Canonical glossary approval changed")
    source_glossary = {
        "schemaVersion": 1, "locale": "sr", "acceptedUnits": 16538,
        "sourceInventory": pin(ROOT / "Source/localization-inventory-v3/strings.jsonl"),
        "sourceStatic": pin(ROOT / "Source/localization-inventory-v3/static-text.jsonl"),
        "sourceAcceptance": pin(ROOT / "Documentation/text-source-acceptance-v1.json"),
        "preserveExactManifest": pin(ROOT / "Source/preserve-exactly-v4.json"),
        "glossaryLayer": pin(ROOT / "Documentation/glossary-translations/sr/layer.json"),
        "canonicalGlossaryReview": pin(ROOT / "Documentation/glossary-translations/canonical-reviews/sr.json"),
        "review03GlossaryApplicability": pin(REVIEW / "glossary-approval-verification.json"),
        "firstSemanticPass": pin(SR / "semantic-cycle-001-precorrection.json"),
        "correctionChain": [pin(SR / x) for x in
                            ("semantic-cycle-001-corrections.json",
                             "semantic-cycle-001-static-regeneration.json",
                             "semantic-cycle-002-corrections.json",
                             "semantic-cycle-003-corrections.json")],
        "firstSemanticPassUnits": 16538,
        "changedIdsByCycle": {"001": 26, "002": 17, "003": 1},
        "result": "passed; no universal restart condition changed",
        "scopeLimit": "Glossary CMS parity not rerun; immutable review03 approval/parity evidence reused."}
    emit(OUT / "source-glossary-applicability.json", source_glossary, args.write)

    manifest = read(ROOT / "Source/preserve-exactly-v4.json")
    accepted = [r["stableId"] for r in manifest["tableRows"] + manifest["staticRows"]]
    rules = {r["stableId"]: r for r in manifest["tableRows"] + manifest["staticRows"]}
    require(len(accepted) == len(rules) == 16538, "Accepted inventory differs")
    current, file_counts, sidecars = {}, Counter(), []
    for item in three["currentAuthoredFileHashes"]:
        path = ROOT / item["path"]
        require(sha(path) == item["sha256"], "Current authored file changed")
        data = read(path)
        require(data["locale"] == "sr", "Wrong locale")
        for entry in data["entries"]:
            identifier = entry.get("stableId") or "string:" + GUIDS[data["collection"]] + ":" + str(entry["id"])
            require(identifier not in current, "Duplicate accepted ID")
            current[identifier] = entry["target"]
            file_counts[data.get("collection", "static")] += 1
        side = path.with_suffix(".validation.json")
        report = read(side)
        require(report["structuralResult"] == "passed" and
                report.get("batchSha256", report.get("draftSha256")) == item["sha256"],
                "Stale structural sidecar")
        sidecars.append(pin(side))
    require(len(three["currentAuthoredFileHashes"]) == len(sidecars) == 341 and
            set(current) == set(accepted) and
            file_counts == {"ChecksDialogs": 1, "UI": 259, "Dialogs": 16100, "static": 178},
            "Accepted selected ID coverage differs")
    require(textsha("".join(x["path"] + "\t" + x["sha256"] + "\n"
                           for x in sorted(three["currentAuthoredFileHashes"],
                                           key=lambda x: x["path"]))) ==
            three["currentAuthoredFileSetSha256"], "Authored file-set hash differs")
    for identifier in accepted:
        preserve_exact.check_value(rules[identifier], current[identifier])
    current_static = SR / "static-text-draft.json"
    require(reproduce_static_draft.reproduce() == current_static.read_text() and
            sha(current_static) == three["staticDraftSha256"] and
            sha(SR / "static-authored-map.json") == three["staticAuthoredRecipeSha256"],
            "Static/credits authored derivation differs")
    fresh_exact = OUT / "preserve-exact-current.json"
    old_exact = SR / "preserve-exact-cycle-003.json"
    require(fresh_exact.exists() and sha(fresh_exact) == sha(old_exact) ==
            three["fullPreserveExactReportSha256"] and
            read(fresh_exact)["checkedRows"] == 16538 and
            read(fresh_exact)["exactResult"] == "passed", "Fresh preserve-exact differs")
    structural = {
        "schemaVersion": 1, "locale": "sr", "result": "passed",
        "owningValidators": [".venv/bin/python Scripts/validate_game_text_batch.py <each 340 table batch>",
                             ".venv/bin/python Scripts/validate_static_text_draft.py Translations/sr/static-text-draft.json"],
        "validatedFiles": 341, "validatedRows": 16538,
        "selectedCoverage": {"count": 16538, "idsSha256": textsha("".join(i + "\n" for i in accepted)),
                             "countsByCollection": dict(file_counts), "missing": 0, "extra": 0,
                             "duplicates": 0},
        "authoredFileSetSha256": three["currentAuthoredFileSetSha256"],
        "sidecarHashes": sidecars, "sidecarHashesUnchangedFromReview03": True,
        "derivedStatic": {"rows": 178, "result": "passed", "staticDraft": pin(current_static),
                          "authoredMap": pin(SR / "static-authored-map.json"),
                          "creditsRoleMap": pin(SR / "credits-role-map.json"),
                          "recipe": pin(SR / "reproduce_static_draft.py")},
        "preserveExact": pin(fresh_exact), "preserveExactRows": 16538}
    emit(OUT / "structural.json", structural, args.write)

    result = subprocess.run([str(ROOT / ".venv/bin/python"),
                             str(SR / "build_delta_review_003.py")],
                            cwd=ROOT, capture_output=True, text=True)
    require(result.returncode == 0, "Closure recipe failed: " + result.stderr[:500])
    recipe_result = json.loads(result.stdout)
    require(recipe_result["result"] == "verified" and
            recipe_result["closureSha256"] == review_summary["closureSha256"] and
            recipe_result["deltaRowsSha256"] == review_summary["deltaRowsSha256"],
            "Closure recipe result differs")
    catalog = read(SR / "semantic-cycle-003-regressions.json")["catalog"]
    mandatory = read(REVIEW / "mandatory-regressions.json")
    closure_ids = c3["closureIds"]["ids"]
    delta_ids = c3["deltaReviewIds"]["ids"]
    require(len(closure_ids) == 548 and len(delta_ids) == 4 and
            c3["closureIds"]["idsSha256"] == textsha("".join(i + "\n" for i in closure_ids)) and
            c3["deltaReviewIds"]["idsSha256"] == review_summary["deltaIdsSha256"] and
            len(set().union(*(set(v["ids"]) for v in catalog.values()))) == 548 and
            set().union(*(set(v["ids"]) for v in catalog.values())) == set(closure_ids) and
            mandatory["catalogUnionCount"] == 548 and
            mandatory["freshReadUnits"] == 4 and
            mandatory["exactUnchangedPriorDecisions"] == 544 and
            all(x["result"] == "passed" and
                x["idsSha256"] == catalog[x["name"]]["idsSha256"]
                for x in mandatory["regressions"]), "Mandatory regression catalog differs")
    rows = lines(SR / "semantic-cycle-003-review-rows.jsonl")
    rowmap = {row["stableId"]: row for row in rows}
    require(len(rows) == len(rowmap) == 548 and
            [x["stableId"] for x in rows] == closure_ids, "Closure rows differ")
    fresh = lines(REVIEW / "read-evidence.jsonl")
    reused = lines(REVIEW / "prior-evidence-applicability.jsonl")
    require(len(fresh) == 4 and len(reused) == 544 and
            {x["stableId"] for x in fresh} == set(delta_ids) and
            {x["stableId"] for x in reused} == set(closure_ids) - set(delta_ids),
            "Fresh/reused semantic decision partition differs")
    for item in fresh:
        original = rowmap[item["stableId"]]
        require(item["sourceSha256"] == original["sourceSha256"] and
                item["targetSha256"] == original["targetSha256"] and
                item["source"] == original["source"] and
                item["target"] == original["target"] and
                item["decision"] == "passed within reviewed context" and
                item["findingId"] is None, "Fresh independent decision differs")
    prior_cache = {}
    for item in reused:
        original = rowmap[item["stableId"]]
        path = ROOT / item["priorEvidencePath"]
        require(sha(path) == item["priorEvidenceSha256"] and
                item["sourceSha256"] == original["sourceSha256"] and
                item["targetSha256"] == original["targetSha256"] and
                item["result"].startswith("applicable unchanged independent"),
                "Prior decision applicability differs")
        if path not in prior_cache:
            prior_cache[path] = lines(path)
        prior = prior_cache[path][item["priorReadOrdinal"] - 1]
        require(prior["stableId"] == item["stableId"] and
                prior["sourceSha256"] == item["sourceSha256"] and
                prior["targetSha256"] == item["targetSha256"] and
                prior.get("decision", prior.get("semanticVerdict")) ==
                "passed within reviewed context", "Prior independent row differs")
    require(c3["changedIds"]["count"] == 1 and
            c3["newDependencyIds"]["count"] == 0 and
            c3["explicitlyInvalidatedPriorIds"]["count"] == 3 and
            c3["retiredDependencyIds"]["count"] == 56 and
            set(delta_ids) == set(c3["changedIds"]["ids"]) |
            set(c3["newDependencyIds"]["ids"]) |
            set(c3["explicitlyInvalidatedPriorIds"]["ids"]),
            "Exact delta formula differs")
    closure_proof = {
        "schemaVersion": 1, "locale": "sr", "result": "passed",
        "closure": pin(SR / "semantic-cycle-003-closure.json"),
        "closureRows": pin(SR / "semantic-cycle-003-review-rows.jsonl"),
        "deltaRows": pin(SR / "semantic-cycle-003-delta-review-rows.jsonl"),
        "regressionCatalog": pin(SR / "semantic-cycle-003-regressions.json"),
        "reproductionRecipe": pin(SR / "build_delta_review_003.py"),
        "reproductionResult": recipe_result,
        "currentClosureIds": 548, "changedIds": 1, "newDependencies": 0,
        "explicitlyInvalidatedPriorIds": 3, "retiredDependencies": 56,
        "exactDeltaIds": 4, "freshIndependentDecisions": 4,
        "reusedExactUnchangedIndependentDecisions": 544,
        "mandatoryRegressionCount": 548,
        "priorEvidenceApplicability": pin(REVIEW / "prior-evidence-applicability.jsonl"),
        "freshReadEvidence": pin(REVIEW / "read-evidence.jsonl"),
        "independentSummary": pin(REVIEW / "summary.json"),
        "independentFindings": pin(REVIEW / "findings.json"),
        "unresolvedObjectiveFindings": 0}
    emit(OUT / "closure-proof.json", closure_proof, args.write)

    admin = read(OUT / "administrative-change.json")
    require(admin["scope"] == "operational progress documents only" and
            len(admin["files"]) == 3 and
            all(sha(ROOT / x["path"]) == x["afterSha256"] and
                sha(OUT / x["preimagePath"]) == x["beforeSha256"]
                for x in admin["files"]), "Administrative checkpoint archive differs")
    receipt = {
        "schemaVersion": 1, "locale": "sr", "status": "offline final gate passed; root acceptance pending",
        "acceptedUnits": 16538, "firstSemanticPassUnits": 16538,
        "independentReviewer": review_summary["reviewerTask"],
        "independentClean": True, "unresolvedObjectiveFindings": 0,
        "currentHashesUnchanged": True,
        "authoredFileSetSha256": three["currentAuthoredFileSetSha256"],
        "review03Pins": 786, "review03ManifestFiles": 15,
        "structural": {"rows": 16538, "result": "passed", "evidence": pin(OUT / "structural.json")},
        "derivedStatic": {"rows": 178, "result": "passed"},
        "preserveExactReport": pin(fresh_exact),
        "mandatoryRegression": {"count": 548, "freshReads": 4,
                                "reusedUnchangedIndependentDecisions": 544,
                                "result": "passed", "evidence": pin(OUT / "closure-proof.json")},
        "sourceGlossaryApplicability": pin(OUT / "source-glossary-applicability.json"),
        "administrativeProgressChange": pin(OUT / "administrative-change.json"),
        "limits": ["13 accepted format-slot rows lack a pinned compiled instruction",
                   "Neighbour has no pinned UI display label",
                   "Static consumer/config evidence proves possible inputs, not executed reachability",
                   "Game runtime, Cyrillic glyphs/fonts, layout, build, install, release and integration not tested"],
        "rootNextAction": "Independently verify this exact handoff and integration manifest before editorial acceptance/build."}
    emit(OUT / "gate-receipt.json", receipt, args.write)
    evidence_names = [
        REVIEW / "report.md", REVIEW / "summary.json", REVIEW / "findings.json",
        REVIEW / "verification.json", REVIEW / "artifact-manifest.json",
        REVIEW / "mandatory-regressions.json", REVIEW / "read-evidence.jsonl",
        REVIEW / "prior-evidence-applicability.jsonl",
        REVIEW / "glossary-approval-verification.json",
        SR / "semantic-cycle-001-precorrection.json",
        SR / "semantic-cycle-001-corrections.json",
        SR / "semantic-cycle-001-static-regeneration.json",
        SR / "semantic-cycle-001-closure.json",
        SR / "semantic-cycle-002-corrections.json",
        SR / "semantic-cycle-002-closure.json",
        SR / "semantic-cycle-003-corrections.json",
        SR / "semantic-cycle-003-closure.json",
        OUT / "source-glossary-applicability.json",
        OUT / "structural.json", OUT / "closure-proof.json",
        OUT / "preserve-exact-current.json", OUT / "administrative-change.json",
        OUT / "gate-receipt.json"]
    handoff = {
        "schemaVersion": 1, "locale": "sr", "gameVersion": "1.3.19",
        "acceptedUnits": 16538, "firstSemanticPassUnits": 16538,
        "unresolvedObjectiveFindings": 0, "independentClean": True,
        "independentReviewer": review_summary["reviewerTask"],
        "currentHashesUnchanged": True,
        "mandatoryRegression": {"count": 548, "freshReads": 4,
                                "reusedUnchangedIndependentDecisions": 544,
                                "result": "passed"},
        "structural": {"rows": 16538, "result": "passed"},
        "derivedStatic": {"rows": 178, "result": "passed"},
        "preserveExactReport": pin(fresh_exact),
        "authoredFileSetSha256": three["currentAuthoredFileSetSha256"],
        "authoredFiles": three["currentAuthoredFileHashes"],
        "evidenceFiles": [pin(path) for path in evidence_names],
        "integrationManifest": "Translations/sr/final-gate/integration-manifest.json",
        "integrationManifestSelfHash": "excluded to avoid circular hashing; verify the listed path/hash set and hash the manifest independently",
        "integrationScope": "All current files under Translations/sr, including this handoff; no shared paths or Git staging",
        "editorialAcceptance": "pending root independent verification",
        "runtimeReadiness": "not tested; game launch prohibited",
        "buildReadiness": "not tested; build prohibited",
        "remainingLimits": receipt["limits"],
        "telemetry": {"model": "GPT-6 family exposed; exact served model/effort unknown",
                      "inputTokens": "unknown", "cachedInputTokens": "unknown",
                      "outputTokens": "unknown", "reasoningTokens": "unknown",
                      "totalTokens": "unknown", "reason": "No per-request/session telemetry exposed to this author turn; no estimate substituted."}}
    emit(OUT / "root-handoff.json", handoff, args.write)
    integration_path = OUT / "integration-manifest.json"
    integration_files = sorted(path for path in SR.rglob("*")
                               if path.is_file() and path != integration_path)
    integration = {"schemaVersion": 1, "locale": "sr", "scope": "complete current locale directory",
                   "selfPath": relative(integration_path),
                   "selfHash": "excluded to avoid circular hashing",
                   "fileCountExcludingSelf": len(integration_files),
                   "files": [pin(path) for path in integration_files],
                   "outsideLocalePaths": [], "gitAction": "none; root owns staging and integration"}
    emit(integration_path, integration, args.write)
    print(json.dumps({"result": "written" if args.write else "verified",
                      "authoredFiles": 341, "acceptedRows": 16538,
                      "staticRows": 178, "reviewedDelta": 4,
                      "reusedDecisions": 544, "regressionUnion": 548,
                      "reviewPins": 786, "integrationFilesExcludingManifest": len(integration_files),
                      "rootHandoffSha256": sha(OUT / "root-handoff.json"),
                      "integrationManifestSha256": sha(integration_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
