#!/usr/bin/env python3
"""Reproduce the Hungarian offline final gate without rereading unchanged prose.

`build` writes immutable locale-only gate reports once. `verify` recomputes
their bytes from current inputs. Structural validator commands are recorded in
validate-all.py; this recipe verifies their current, byte-identical sidecars.
"""

import argparse
import hashlib
import json
import re
import runpy
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HU = ROOT / "Translations/hu"
HERE = Path(__file__).resolve().parent
REVIEW1 = HU / "independent-review-01"
REVIEW2 = HU / "independent-review-02"
CYCLE1 = HU / "semantic-correction-cycle-01"
CYCLE2 = HU / "semantic-correction-cycle-02"
CYCLE3 = HU / "semantic-correction-cycle-03"
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import check_value  # noqa: E402
from report_locale_readiness import selected_ids  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def load(path):
    return json.loads(path.read_text())


def rows(path):
    return [json.loads(line) for line in path.open()]


def require(test, message):
    if not test:
        raise ValueError(message)


def rel(path):
    return str(path.relative_to(ROOT))


def artifact_manifest(directory):
    manifest = load(directory / "artifact-manifest.json")
    for item in manifest["artifacts"]:
        path = ROOT / item["path"]
        require(digest(path) == item["sha256"] and path.stat().st_size == item["bytes"],
                "Immutable review artifact changed: " + item["path"])
    return len(manifest["artifacts"])


def authored_corpus(input_verification, structural):
    expected = input_verification["authoredFiles"]
    require(len(expected) == 474 and structural["tableBatchCount"] == 473 and
            structural["tableRows"] == 16360 and structural["staticRows"] == 178 and
            structural["totalRows"] == 16538 and structural["result"] == "passed",
            "Structural report count changed")
    batch_name = re.compile(r"(?:dialogue|ui|checks)-batch-\d{3}\.json$")
    paths = sorted(p for p in HU.glob("*-batch-*.json") if batch_name.fullmatch(p.name))
    paths.append(HU / "static-text-draft.json")
    require(len(paths) == 474 and {rel(path) for path in paths} == set(expected),
            "Authored file set changed")
    structural_files = {item["path"]: item for item in
                        structural["tableBatches"] + [structural["staticDraft"]]}
    require(set(structural_files) == set(expected), "Structural file set changed")
    target, owner = {}, {}
    for path in paths:
        name = rel(path)
        require(digest(path) == expected[name] == structural_files[name]["sha256"],
                "Reviewed authored hash changed: " + name)
        sidecar = path.with_suffix(".validation.json")
        require(digest(sidecar) == structural_files[name]["sidecarSha256"],
                "Structural sidecar changed: " + name)
        doc = load(path)
        require(doc["locale"] == "hu" and doc["gameVersion"] == "1.3.19" and
                doc["sourceLocale"] == "ru", "Authored identity changed")
        if path.name == "static-text-draft.json":
            require(len(doc["entries"]) == 178, "Static row count changed")
            entries = ((entry["stableId"], entry["target"]) for entry in doc["entries"])
        else:
            guid = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
                    "UI": "0cbd8a7a4f543344bb95659de87f67a5",
                    "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}[doc["collection"]]
            entries = ((f"string:{guid}:{entry['id']}", entry["target"])
                       for entry in doc["entries"])
        count = 0
        for key, value in entries:
            require(key not in target, "Duplicate accepted ID: " + key)
            target[key], owner[key] = value, name
            count += 1
        require(count == structural_files[name]["rows"], "Structural row count differs: " + name)
    require(len(target) == 16538, "Accepted target count differs")
    return paths, target, owner


def source_and_first_pass(source, order):
    first_path = HU / "semantic-review-progress.json"
    first = load(first_path)
    require(first["acceptedUnits"] == first["reviewedUnits"] == 16538 and
            first["nextOrdinal"] == 16538 and first["nextStableId"] is None and
            first["reviewedThroughOrdinal"] == 16537 and len(first["segments"]) == 133,
            "First semantic pass incomplete")
    pins = {"sourceInventorySha256": ROOT / "Source/localization-inventory-v3/strings.jsonl",
            "staticInventorySha256": ROOT / "Source/localization-inventory-v3/static-text.jsonl",
            "acceptedScopeSha256": ROOT / "Documentation/text-source-acceptance-v1.json",
            "preserveExactManifestSha256": ROOT / "Source/preserve-exactly-v4.json",
            "approvedGlossaryLayerSha256": ROOT / "Documentation/glossary-translations/hu/layer.json",
            "canonicalGlossarySha256": Path("/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary.json")}
    for key, path in pins.items():
        require(first[key] == digest(path), "First pass pin changed: " + key)
    require(first["fullTextPreflightSha256"] == digest(HU / "full-text-preflight-v1.json") and
            first["evidenceErrata"]["sha256"] == digest(ROOT / first["evidenceErrata"]["path"]) and
            first["pendingCorrectionBatch"]["sha256"] == digest(ROOT / first["pendingCorrectionBatch"]["path"]),
            "First-pass evidence changed")
    ordinal = 0
    for segment_ref in first["segments"]:
        path = ROOT / segment_ref["path"]
        require(digest(path) == segment_ref["sha256"], "First-pass segment changed")
        segment = load(path)
        require(segment["firstOrdinal"] == ordinal and
                segment["reviewedUnits"] == len(segment["rows"]), "First-pass segment gap")
        for row in segment["rows"]:
            key = row["stableId"]
            require(row["ordinal"] == ordinal and key == order[ordinal] and
                    row["source"] == source[key]["source"], "First-pass row mismatch")
            ordinal += 1
    require(ordinal == 16538, "First-pass unit count differs")
    return first, first_path


def static_derivation(source, target):
    phrase_path = HU / "static-phrase-map.json"
    credit_path = HU / "credits-role-map.json"
    phrase = load(phrase_path)
    credit = load(credit_path)
    inventory = ROOT / "Source/localization-inventory-v3/static-text.jsonl"
    require(phrase["locale"] == "hu" and
            phrase["sourceInventoryStaticSha256"] == digest(inventory) and
            credit["sourceInventoryStaticSha256"] == digest(inventory),
            "Static recipe source pin changed")
    mapping = {row["source"]: row["target"] for row in phrase["entries"]}
    require(len(mapping) == len(phrase["entries"]) == 75, "Static phrase map differs")
    credit_id = "tmp:level5:59:m_text"
    used = set()
    for key in (key for key in target if key.startswith("tmp:")):
        if key == credit_id:
            continue
        original = source[key]["source"]
        require(original in mapping and target[key] == mapping[original],
                "Static phrase derivation mismatch: " + key)
        used.add(original)
    require(used == set(mapping), "Unused or missing static phrase map entry")
    require(credit["stableId"] == credit_id and len(credit["replacements"]) == 81,
            "Credits recipe differs")
    replacements = {row["source"]: row["target"] for row in credit["replacements"]}
    require(len(replacements) == 81 and all(replacements.values()),
            "Credits role map duplicate or empty")
    original = source[credit_id]["source"]
    require(all(original.count(phrase) for phrase in replacements),
            "Credits source phrase absent")
    pattern = re.compile("|".join(re.escape(phrase)
                                  for phrase in sorted(replacements, key=len, reverse=True)))
    derived = pattern.sub(lambda match: replacements[match.group()], original)
    require(derived == target[credit_id], "Credits derivation differs")
    static_ids = {key for key in target if key.startswith("tmp:")}
    require(len(static_ids) == 178, "Static accepted ID count differs")
    return {"schemaVersion": 1, "locale": "hu", "rows": 178,
            "phraseMapEntries": 75, "nonCreditRows": 177,
            "creditsRoleReplacements": 81, "result": "passed",
            "phraseMapPath": rel(phrase_path), "phraseMapSha256": digest(phrase_path),
            "creditsRoleMapPath": rel(credit_path), "creditsRoleMapSha256": digest(credit_path),
            "staticDraftPath": "Translations/hu/static-text-draft.json",
            "staticDraftSha256": digest(HU / "static-text-draft.json"),
            "creditStableId": credit_id, "creditTargetSha256": text_sha(target[credit_id])}


def review_decisions(target, owner, closure, review_verdict):
    current = CYCLE3 / "evidence"
    previous = CYCLE1 / "evidence"
    delta = (current / "next-review-delta-ids.txt").read_text().splitlines()
    mandatory = (current / "mandatoryRegression-ids.txt").read_text().splitlines()
    old_ids = (previous / "closure-ids.txt").read_text().splitlines()
    require(len(delta) == 264 and len(set(delta)) == 264 and
            len(mandatory) == 1697 and len(set(mandatory)) == 1697 and
            len(old_ids) == 2902, "Review ID lists changed")
    full = rows(REVIEW2 / "full-unit-decisions.jsonl")
    require(len(full) == 264 and {r["stableId"] for r in full} == set(delta) and
            all(r["reader"] == review_verdict["reviewer"] and r["fullUnitRead"] and
                r["sourceSha256"] == text_sha(r["source"]) and
                r["targetSha256"] == text_sha(target[r["stableId"]]) and
                r["afterAuthoredFileSha256"] == digest(ROOT / owner[r["stableId"]])
                for r in full), "Fresh independent decisions not current")
    prior = load(REVIEW2 / "prior-applicability.json")
    require(len(prior["rows"]) == 2902 and
            {r["stableId"] for r in prior["rows"]} == set(old_ids) and
            all(r["sourceHashVerified"] and
                r["currentAuthoredFileSha256"] == digest(ROOT / owner[r["stableId"]])
                for r in prior["rows"]), "Prior independent applicability changed")
    catalog = rows(REVIEW2 / "mandatory-catalog-decisions.jsonl")
    require(len(catalog) == 1697 and {r["stableId"] for r in catalog} == set(mandatory),
            "Mandatory catalog decision IDs changed")
    fresh = reused = 0
    for row in catalog:
        key = row["stableId"]
        require(row["decision"] == "passed-static-editorial" and
                row["currentTargetSha256"] == text_sha(target[key]),
                "Mandatory catalog decision stale: " + key)
        if row["previousEvidenceReusable"]:
            reused += 1
            require(key in old_ids and key not in delta and
                    row["reader"] == "/root/hu_independent_review_01" and
                    row["basis"] == "verified-independent-review-01/full-pair-read-evidence.jsonl",
                    "Prior catalog reuse inapplicable: " + key)
        else:
            fresh += 1
            require(key in delta and row["reader"] == review_verdict["reviewer"] and
                    row["basis"] == "independent-review-02/full-unit-decisions.jsonl",
                    "Fresh catalog decision inapplicable: " + key)
    require((fresh, reused) == (218, 1479), "Catalog fresh/reused split changed")
    objective = load(REVIEW2 / "objective-findings.json")
    require(objective["completeForAssignedDelta"] and
            objective["reviewedFullDeltaUnits"] == 264 and
            not objective["objectiveFindings"] and not objective["proposedCorrections"],
            "Unresolved objective finding")
    return {"schemaVersion": 1, "locale": "hu", "count": 1697,
            "freshReads": fresh, "reusedUnchangedIndependentDecisions": reused,
            "result": "passed", "freshDecisionPath": rel(REVIEW2 / "full-unit-decisions.jsonl"),
            "freshDecisionSha256": digest(REVIEW2 / "full-unit-decisions.jsonl"),
            "catalogDecisionPath": rel(REVIEW2 / "mandatory-catalog-decisions.jsonl"),
            "catalogDecisionSha256": digest(REVIEW2 / "mandatory-catalog-decisions.jsonl"),
            "priorApplicabilityPath": rel(REVIEW2 / "prior-applicability.json"),
            "priorApplicabilitySha256": digest(REVIEW2 / "prior-applicability.json")}


def generate():
    review1_count = artifact_manifest(REVIEW1)
    review2_count = artifact_manifest(REVIEW2)
    verdict = load(REVIEW2 / "review-verdict.json")
    input_check = load(REVIEW2 / "input-verification.json")
    structural_path = HERE / "structural-validators.json"
    structural = load(structural_path)
    require(verdict["status"] == "clean-independent-delta-static-editorial" and
            verdict["objectiveFindings"] == 0 and verdict["reviewedFullUnits"] == 264 and
            verdict["unchangedAtFinalCheck"] and input_check["allByteIdentical"],
            "Independent clean review changed")
    paths, target, owner = authored_corpus(input_check, structural)
    source = {r["stableId"]: r for name in ("strings", "static-text")
              for r in rows(ROOT / f"Source/localization-inventory-v3/{name}.jsonl")}
    preserve_path = ROOT / "Source/preserve-exactly-v4.json"
    preserve = load(preserve_path)
    accepted = preserve["tableRows"] + preserve["staticRows"]
    order = [row["stableId"] for row in accepted]
    require(len(order) == len(set(order)) == 16538 and set(order) == set(target),
            "Selected accepted ID coverage changed")
    selected, source_hash, static_hash = selected_ids()
    selected_full = {f"string:{guid}:{value}" for collection, guid in
                     (("UI", "0cbd8a7a4f543344bb95659de87f67a5"),
                      ("Dialogs", "444ff14f1967f5a4c8eb9e4cf4c913f1"),
                      ("ChecksDialogs", "389c6d80595013c41b85a7197838c4b6"))
                     for value in selected[collection]} | selected["static"]
    require(set(order) == selected_full and source_hash == input_check["sourceInventorySha256"] and
            static_hash == input_check["staticInventorySha256"], "Selected source scope changed")
    for rule in accepted:
        check_value(rule, target[rule["stableId"]])
    first, first_path = source_and_first_pass(source, order)
    plan1, plan2, plan3 = [load(path / "adjudicated-plan.json")
                           for path in (CYCLE1, CYCLE2, CYCLE3)]
    require((len(plan1["rows"]), len(plan2["rows"]), len(plan3["rows"])) == (118, 14, 15) and
            plan3["rows"][:14] == plan2["rows"] and
            plan3["supersedesPlanSha256"] == digest(CYCLE2 / "adjudicated-plan.json") and
            plan3["firstPassProgressSha256"] == digest(first_path),
            "Correction chain changed")
    closure_path = CYCLE3 / "evidence/closure-manifest.json"
    require(digest(closure_path) == verdict["closureManifestSha256"] ==
            input_check["closureManifestSha256"], "Current closure changed")
    recipe = runpy.run_path(str(CYCLE3 / "build-closure.py"))
    payloads, closure = recipe["generate"]()
    require(len(payloads) == input_check["reproducedOutputs"] == 24 and
            all((CYCLE3 / "evidence" / name).read_bytes() == value
                for name, value in payloads.items()), "Closure reproduction differs")
    require(closure["closureCount"] == 3140 and closure["nextReviewDeltaCount"] == 264 and
            closure["mandatoryCatalogCount"] == 1697, "Closure scope changed")
    require(verdict["deltaIdListSha256"] == digest(CYCLE3 / "evidence/next-review-delta-ids.txt") and
            verdict["deltaReviewRowsSha256"] == digest(CYCLE3 / "evidence/next-review-delta.jsonl"),
            "Reviewed delta changed")
    mandatory = review_decisions(target, owner, closure, verdict)
    derived = static_derivation(source, target)
    pins = {"sourceInventorySha256": source_hash,
            "staticInventorySha256": static_hash,
            "acceptedScopeSha256": digest(ROOT / "Documentation/text-source-acceptance-v1.json"),
            "preserveExactManifestSha256": digest(preserve_path),
            "approvedGlossaryLayerSha256": digest(ROOT / "Documentation/glossary-translations/hu/layer.json"),
            "canonicalGlossarySha256": digest(Path("/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary.json"))}
    for key, value in pins.items():
        require(value == input_check.get({"approvedGlossaryLayerSha256": "glossaryLayerSha256",
                                          "canonicalGlossarySha256": "canonicalGlossarySha256",
                                          "preserveExactManifestSha256": "preserveManifestSha256"}.get(key, key), value) and
                value == first[key], "Source or glossary applicability changed: " + key)
    source_report = {"schemaVersion": 1, "locale": "hu", "result": "passed",
                     "gameVersion": "1.3.19", "acceptedUnits": 16538,
                     "firstSemanticPassUnits": 16538, "firstSemanticPassProgressPath": rel(first_path),
                     "firstSemanticPassProgressSha256": digest(first_path),
                     "firstSemanticPassSegments": len(first["segments"]),
                     "correctionChain": [{"path": rel(path / "adjudicated-plan.json"),
                                          "sha256": digest(path / "adjudicated-plan.json"),
                                          "rows": len(plan["rows"])}
                                         for path, plan in ((CYCLE1, plan1), (CYCLE2, plan2), (CYCLE3, plan3))],
                     "review01VerdictSha256": digest(REVIEW1 / "review-verdict.json"),
                     "review02VerdictSha256": digest(REVIEW2 / "review-verdict.json"),
                     "review01ArtifactsChecked": review1_count,
                     "review02ArtifactsChecked": review2_count,
                     "currentClosureManifestSha256": digest(closure_path),
                     "currentHashesUnchanged": True, **pins}
    authored = [{"path": rel(path), "sha256": digest(path)} for path in paths]
    exact_report = {"schemaVersion": 1, "locale": "hu", "gameVersion": "1.3.19",
                    "checkedRows": 16538, "selectedAcceptedIdCoverage": 16538,
                    "result": "passed", "problems": [],
                    "manifestPath": rel(preserve_path), "manifestSha256": digest(preserve_path),
                    "validatorPath": "Scripts/preserve_exact.py",
                    "validatorSha256": digest(ROOT / "Scripts/preserve_exact.py"),
                    "authoredFiles": authored,
                    "boundary": "Source/target IDs and preserve-exact grammar; no serialized build or runtime"}
    result = {"source-glossary-applicability.json": encode(source_report),
              "derived-static.json": encode(derived),
              "mandatory-regression.json": encode(mandatory),
              "preserve-exact-report.json": encode(exact_report)}
    receipt = {"schemaVersion": 1, "locale": "hu", "gameVersion": "1.3.19",
               "result": "passed-offline-final-gate", "acceptedUnits": 16538,
               "firstSemanticPassUnits": 16538, "unresolvedObjectiveFindings": 0,
               "independentClean": True, "independentReviewer": verdict["reviewer"],
               "currentHashesUnchanged": True,
               "mandatoryRegression": {"count": 1697, "freshReads": 218,
                                       "reusedUnchangedIndependentDecisions": 1479,
                                       "result": "passed"},
               "structural": {"rows": 16538, "tableBatches": 473,
                              "staticRows": 178, "result": "passed"},
               "derivedStatic": {"rows": 178, "result": "passed"},
               "preserveExact": {"rows": 16538, "result": "passed"},
               "reviewVerdictPath": rel(REVIEW2 / "review-verdict.json"),
               "reviewVerdictSha256": digest(REVIEW2 / "review-verdict.json"),
               "structuralReportPath": rel(structural_path),
               "structuralReportSha256": digest(structural_path),
               "evidence": [{"path": rel(HERE / name), "sha256": digest_bytes}
                            for name, digest_bytes in
                            ((name, hashlib.sha256(payload).hexdigest()) for name, payload in sorted(result.items()))],
               "scopeLimit": "Offline static text/editorial gate only; no font, layout, package, install or runtime acceptance"}
    result["full-gate-receipt.json"] = encode(receipt)
    return result, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    mode = parser.parse_args().mode
    result, receipt = generate()
    if mode == "build":
        for name in result:
            require(not (HERE / name).exists(), "Immutable gate file already exists: " + name)
        for name, payload in result.items():
            (HERE / name).write_bytes(payload)
    else:
        for name, payload in result.items():
            require((HERE / name).read_bytes() == payload, "Gate output differs: " + name)
    print(json.dumps({"mode": mode, "result": receipt["result"],
                      "acceptedUnits": 16538, "reviewedDelta": 264,
                      "receiptSha256": digest(HERE / "full-gate-receipt.json")}))


if __name__ == "__main__":
    main()
