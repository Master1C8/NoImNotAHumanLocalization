#!/usr/bin/env python3
"""Reproduce the Hebrew offline text gate and root integration handoff.

Writes only immutable evidence in this directory. Owning validators may rewrite
existing Hebrew validation sidecars, but their bytes must remain identical.
No runtime, build, Git, installation, or shared-state operation is performed.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HE = ROOT / "Translations/he"
GATE = Path(__file__).resolve().parent
REVIEW = HE / "independent-review-04"
CORRECTION = HE / "semantic-correction-cycle-04"
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import check_value, validate

GUID = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
        "UI": "0cbd8a7a4f543344bb95659de87f67a5",
        "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(Path(path).read_bytes())


def rel(path):
    return str(path.relative_to(ROOT))


def ref(path, **extra):
    return {"path": rel(path), "sha256": sha(path), **extra}


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def once(path, value):
    data = encoded(value)
    if path.exists():
        assert path.read_bytes() == data, f"immutable gate evidence changed: {path}"
    else:
        path.write_bytes(data)


def file_set_hash(rows):
    return digest("".join(x["path"] + "\t" + x["sha256"] + "\n" for x in rows).encode())


def current_inputs():
    progress = json.loads((HE / "progress.json").read_text())
    semantic = json.loads((HE / "semantic-review-progress.json").read_text())
    review = json.loads((REVIEW / "final-review.json").read_text())
    evidence = json.loads((REVIEW / "final-evidence-manifest.json").read_text())
    final_pins = json.loads((REVIEW / "final-input-verification.json").read_text())
    assert review["locale"] == progress["locale"] == semantic["locale"] == "he"
    assert review["acceptedUnits"] == semantic["acceptedUnits"] == semantic["reviewedUnits"] == 16538
    assert review["independentFromAuthor"] and review["cleanIndependentReview"]
    assert review["findingsCount"] == review["selectorFindingsCount"] == 0
    assert review["fullPairReadUnits"] == review["deltaReviewUnits"] == 72
    assert review["pendingPairReadUnits"] == 0
    assert not review["editorialAcceptance"]  # Root owns whole-locale acceptance.
    assert len(evidence["files"]) == 13 and len(final_pins["hashChecks"]) == 820
    assert all(sha(ROOT / x["path"]) == x["sha256"] for x in evidence["files"])
    assert all(x["passed"] and sha(ROOT / x["path"]) == x["expectedSha256"]
               for x in final_pins["hashChecks"])
    assert sha(REVIEW / "final-review.json") == "583c3016a9d2e9ed0530754b47583048108c01094554feb9a727afa1fdd1c5fe"
    assert sha(REVIEW / "final-findings.json") == "d9e03cdfd8476651eb26962d056332a69c6600a3e4e675f82504c71b0d05f64a"
    findings = json.loads((REVIEW / "final-findings.json").read_text())
    assert findings["findings"] == findings["selectorFindings"] == []
    assert sha(HE / "semantic-review-progress.json") == progress["validation"]["semanticReviewProgressSha256"]
    assert semantic["postCorrection"]["cycle"] == 4
    assert sha(ROOT / semantic["postCorrection"]["handoffPath"]) == semantic["postCorrection"]["handoffSha256"]
    src = progress["sourceInventory"]
    for path_key, hash_key, review_key in (("stringsPath", "stringsSha256", "sourceInventorySha256"),
                                           ("staticPath", "staticSha256", "staticInventorySha256"),
                                           ("preserveExactPath", "preserveExactSha256", "preserveExactSha256")):
        assert sha(ROOT / src[path_key]) == src[hash_key] == review[review_key]
    assert sha(ROOT / progress["glossary"]["path"]) == progress["glossary"]["sha256"] == review["glossarySha256"]
    assert sha(CORRECTION / "closure-manifest.json") == review["closureManifestSha256"]
    assert sha(CORRECTION / "delta-review-rows.jsonl") == review["deltaRowsSha256"]
    structural = json.loads((CORRECTION / "full-structural-diff.json").read_text())
    assert structural["authoredFileSetSha256"] == review["authoredFileSetSha256"]
    assert all(sha(ROOT / x["path"]) == x["sha256"] for x in structural["authoredFiles"])
    assert file_set_hash(structural["authoredFiles"]) == review["authoredFileSetSha256"]
    assert all(sha(ROOT / x["path"]) == x["sha256"] for x in progress["files"])
    return progress, semantic, review, structural


def source_glossary_applicability(progress, review):
    master = Path("/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary-translations.json")
    layer = ROOT / progress["glossary"]["path"]
    master_he = json.loads(master.read_text())["he"]
    local_he = json.loads(layer.read_text())
    assert len(master_he) == len(local_he) == 201 and master_he == local_he
    source_glossary = Path("/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary.json")
    source_entries = json.loads(source_glossary.read_text())
    if isinstance(source_entries, dict):
        source_entries = source_entries["entries"]
    assert len(source_entries) == 201
    result = {"schemaVersion": 1, "status": "current source, preserve-exact and approved glossary pins unchanged",
        "gameVersion": "1.3.19", "sourceLocale": "ru", "locale": "he",
        "sourceInventory": ref(ROOT / progress["sourceInventory"]["stringsPath"]),
        "staticInventory": ref(ROOT / progress["sourceInventory"]["staticPath"]),
        "preserveExactManifest": ref(ROOT / progress["sourceInventory"]["preserveExactPath"]),
        "approvedLocalGlossary": ref(layer, entries=201),
        "masterHebrewLayerParity": {"entries": 201, "idsAndValuesExact": True,
                                    "masterFilePath": str(master), "masterFileSha256AtGate": sha(master)},
        "masterSourceGlossary": {"path": str(source_glossary), "entries": 201,
                                 "rawFileSha256AtGate": sha(source_glossary)},
        "review04SourceSha256": review["sourceInventorySha256"],
        "review04GlossarySha256": review["glossarySha256"],
        "applicability": "No source, accepted inventory, preserve-exact or approved Hebrew glossary change since the clean independent review. Master he layer equals pinned local layer. Master raw file hashes are observation pins, not a shared-file mutation request."}
    once(GATE / "source-glossary-applicability.json", result)
    return result


def correction_chain(review):
    baseline = HE / "semantic-correction-cycle-01/baseline-semantic-review-progress.json"
    first = json.loads(baseline.read_text())
    assert first["reviewedUnits"] == first["acceptedUnits"] == 16538
    assert sha(baseline) == review["baselineSemanticPass"]["sha256"]
    assert len(first["firstPassFindings"]) == 120
    cycles = []
    expected_findings = [31, 7, 14, 0]
    for i in range(1, 5):
        cycle = HE / f"semantic-correction-cycle-{i:02d}"
        independent = HE / f"independent-review-{i:02d}"
        manifest_path = cycle / "closure-manifest.json"
        handoff_path = cycle / "independent-review-handoff.json"
        review_path = independent / "final-review.json"
        findings_path = independent / "final-findings.json"
        manifest = json.loads(manifest_path.read_text())
        verdict = json.loads(review_path.read_text())
        findings = json.loads(findings_path.read_text())
        assert len(findings["findings"]) == expected_findings[i-1]
        for key in ("changedIds", "closureIds", "deltaIds"):
            if key in manifest:
                x = manifest[key]
                assert sha(ROOT / x["path"]) == x["sha256"]
        if "closureManifestSha256" in verdict:
            assert verdict["closureManifestSha256"] == sha(manifest_path)
        if i > 1:
            previous = HE / f"semantic-correction-cycle-{i-1:02d}/closure-manifest.json"
            assert manifest["priorClosureManifestSha256"] == sha(previous)
        cycles.append({"cycle": i, "closure": ref(manifest_path, count=manifest["closureIds"]["count"]),
                       "handoff": ref(handoff_path), "independentReview": ref(review_path),
                       "findings": ref(findings_path, count=len(findings["findings"])),
                       "verdict": verdict.get("verdict")})
    assert cycles[-1]["verdict"] == "clean unchanged-hash independent delta"
    result = {"schemaVersion": 1, "status": "complete 16538-unit first semantic pass and four immutable correction/review cycles verified",
              "firstSemanticPass": ref(baseline, reviewedUnits=16538, findings=120),
              "cycles": cycles,
              "reuseRule": "The first pass remains reusable because source, glossary and accepted ID mapping are unchanged. Each correction cycle has a separate pinned closure; review 04 is the first clean independent delta."}
    once(GATE / "correction-chain.json", result)
    return result


def selected_values(progress):
    rules = json.loads((ROOT / progress["sourceInventory"]["preserveExactPath"]).read_text())
    accepted = rules["tableRows"] + rules["staticRows"]
    ordered = [x["stableId"] for x in accepted]
    assert len(ordered) == len(set(ordered)) == 16538
    by_rule = {x["stableId"]: x for x in accepted}
    source = {x["stableId"]: x for x in map(json.loads, (ROOT / progress["sourceInventory"]["stringsPath"]).open())}
    source.update({x["stableId"]: x for x in map(json.loads, (ROOT / progress["sourceInventory"]["staticPath"]).open())})
    target, files, sidecars = {}, [], []
    counts = Counter()
    for x in progress["files"]:
        path = ROOT / x["path"]
        if re.fullmatch(r"(?:dialogue|ui|checks)-batch-\d{3}\.json", path.name):
            batch = json.loads(path.read_text())
            assert batch["locale"] == "he"
            assert batch["sourceInventorySha256"] == progress["sourceInventory"]["stringsSha256"]
            for entry in batch["entries"]:
                sid = f"string:{GUID[batch['collection']]}:{entry['id']}"
                assert sid not in target
                target[sid] = entry["target"]
                counts[batch["collection"]] += 1
            files.append(ref(path))
            sidecars.append(path.with_suffix(".validation.json"))
    static_path = HE / "static-text-draft.json"
    static = json.loads(static_path.read_text())
    assert static["locale"] == "he"
    for entry in static["entries"]:
        sid = entry["stableId"]
        assert sid not in target
        target[sid] = entry["target"]
        counts["StaticTMP"] += 1
    files.append(ref(static_path))
    sidecars.append(static_path.with_suffix(".validation.json"))
    assert set(target) == set(ordered) == set(source).intersection(set(ordered))
    assert len(target) == 16538
    assert counts == {"Dialogs": 16100, "UI": 259, "ChecksDialogs": 1, "StaticTMP": 178}
    for sid in ordered:
        check_value(by_rule[sid], target[sid])
    assert len(files) == len(sidecars) == 337
    return target, source, by_rule, ordered, files, sidecars, counts


def review_decisions(review, target, source, ordered):
    decision_doc = json.loads((REVIEW / "complete-review-decisions.json").read_text())
    rows = [json.loads(x) for x in (CORRECTION / "delta-review-rows.jsonl").read_text().splitlines()]
    decisions = decision_doc["decisions"]
    assert len(rows) == len(decisions) == 72
    assert [x["stableId"] for x in rows] == [x["stableId"] for x in decisions]
    order = {sid: i for i, sid in enumerate(ordered)}
    assert [x["stableId"] for x in rows] == sorted((x["stableId"] for x in rows), key=order.__getitem__)
    for i, (row, decision) in enumerate(zip(rows, decisions)):
        sid = row["stableId"]
        assert decision["deltaOrdinalZeroBased"] == i and decision["fullPairRead"]
        assert decision["decision"] == "no objective correction found" and decision["findingId"] is None
        assert decision["protectedSyntax"] == "pass"
        assert source[sid]["source"] == row["source"] and target[sid] == row["after"]
        assert digest(row["source"].encode()) == decision["sourceValueSha256"]
        assert digest(row["after"].encode()) == decision["currentTargetValueSha256"]
        if decision.get("location"):
            location = decision["location"]
            assert sha(ROOT / location["path"]) == location["authoredFileSha256"]
    assert review["findingsCount"] == 0
    result = {"schemaVersion": 1,
        "status": "all 72 exact delta pairs retain clean independent decisions on current source and authored values",
        "independentReviewer": review["reviewer"], "fullPairReads": 72,
        "unresolvedObjectiveFindings": 0,
        "review": ref(REVIEW / "final-review.json"),
        "findings": ref(REVIEW / "final-findings.json", count=0),
        "decisions": ref(REVIEW / "complete-review-decisions.json", count=72),
        "deltaRows": ref(CORRECTION / "delta-review-rows.jsonl", count=72),
        "reviewEvidenceManifest": ref(REVIEW / "final-evidence-manifest.json", files=13)}
    once(GATE / "independent-review-applicability.json", result)
    return result


def mandatory_regression(target, source):
    catalog = CORRECTION / "components/mandatory-regressions-ids.txt"
    ids = catalog.read_text().splitlines()
    reuse = json.loads((REVIEW / "regression-reuse.json").read_text())
    assert len(ids) == len(set(ids)) == 549
    assert reuse["catalogSha256"] == sha(catalog)
    assert reuse["catalogCount"] == reuse["reusedCount"] == 549
    assert len(reuse["newReads"]) == 0 and len(reuse["reusedDecisions"]) == 549
    assert set(ids) == {x["stableId"] for x in reuse["reusedDecisions"]}
    prior_cache = {}
    by_path = Counter()
    for x in reuse["reusedDecisions"]:
        sid = x["stableId"]
        assert digest(source[sid]["source"].encode()) == x["sourceValueSha256"]
        assert digest(target[sid].encode()) == x["currentTargetValueSha256"]
        path = ROOT / x["priorDecisionPath"]
        assert sha(path) == x["priorDecisionFileSha256"]
        if path not in prior_cache:
            prior_cache[path] = {d["stableId"]: d for d in json.loads(path.read_text())["decisions"]}
        assert sid in prior_cache[path]
        prior = prior_cache[path][sid]
        assert prior["sourceValueSha256"] == x["sourceValueSha256"]
        assert prior["currentTargetValueSha256"] == x["currentTargetValueSha256"]
        assert prior["findingId"] is None and "no objective correction" in prior["decision"]
        by_path[rel(path)] += 1
    assert sum(by_path.values()) == 549
    result = {"schemaVersion": 1,
        "status": "passed: all 549 catalog IDs have current value hashes and unchanged independent prior decisions",
        "catalog": ref(catalog, count=549), "review04Reuse": ref(REVIEW / "regression-reuse.json"),
        "count": 549, "freshReads": 0, "reusedUnchangedIndependentDecisions": 549,
        "priorDecisionFiles": [ref(ROOT / name, reused=by_path[name]) for name in sorted(by_path)],
        "result": "passed", "semanticReadAtFinalGate": False}
    once(GATE / "mandatory-regression-applicability.json", result)
    return result


def run_structural_validators(files, sidecars):
    existing = []
    for file, side in zip(files, sidecars):
        report = json.loads(side.read_text())
        assert report["structuralResult"] == "passed"
        assert report.get("batchSha256", report.get("draftSha256")) == file["sha256"]
        existing.append(sha(side))
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    def validate_one(index, file, side):
        is_static = Path(file["path"]).name == "static-text-draft.json"
        validator = "validate_static_text_draft.py" if is_static else "validate_game_text_batch.py"
        command = [str(ROOT / ".venv/bin/python"), str(ROOT / "Scripts" / validator), str(ROOT / file["path"])]
        done = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True)
        assert done.returncode == 0, (file["path"], done.stdout, done.stderr)
        report = json.loads(done.stdout)
        assert report["structuralResult"] == "passed"
        assert report.get("batchSha256", report.get("draftSha256")) == file["sha256"]
        assert sha(side) == existing[index-1], (file["path"], "validator changed reviewed sidecar bytes")
        return index
    # Each validator owns one distinct sidecar. Eight subprocesses bound the
    # full rerun while preserving the ordinary owning validator for every file.
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(validate_one, i, file, side)
                   for i, (file, side) in enumerate(zip(files, sidecars), 1)]
        completed = 0
        for future in as_completed(futures):
            future.result()
            completed += 1
            if completed % 50 == 0 or completed == len(files):
                print(f"validated {completed}/{len(files)} authored files", flush=True)
    result = {"schemaVersion": 1, "status": "passed; all owning validators executed and reviewed sidecars stayed byte-identical",
        "authoredFiles": len(files), "tableBatchFiles": len(files)-1,
        "staticDraftFiles": 1, "rows": 16538,
        "sidecarsByteIdentical": True,
        "validators": [ref(ROOT / "Scripts/validate_game_text_batch.py"),
                       ref(ROOT / "Scripts/validate_static_text_draft.py")],
        "authoredFileSetSha256": file_set_hash(files),
        "sidecars": [ref(path) for path in sidecars], "result": "passed"}
    once(GATE / "structural-validation.json", result)
    return result


def derived_static(progress, target, source):
    draft = json.loads((HE / "static-text-draft.json").read_text())
    rows = draft["entries"]
    assert len(rows) == 178 and len({x["stableId"] for x in rows}) == 178
    assert draft["sourceInventoryStaticSha256"] == progress["sourceInventory"]["staticSha256"]
    scope_path = ROOT / "Documentation/static-text-scope-v2.json"
    scope = json.loads(scope_path.read_text())
    assert draft["staticScopeSha256"] == sha(scope_path)
    expected = {x["stableId"] for x in scope["rows"] if x["source"] and
                (not x["localizedStringBindings"] or
                 any(link["sourceStableId"] is None for link in x["localizedStringBindings"]))}
    assert len(expected) == 178 and expected == {x["stableId"] for x in rows}
    credit_sid = "tmp:level5:59:m_text"
    roles_path = HE / "credits-role-map.json"
    role_map = json.loads(roles_path.read_text())
    authored_map = json.loads((HE / "credits-replacements.json").read_text())
    assert role_map["stableId"] == authored_map["stableId"] == credit_sid
    assert role_map["replacements"] == authored_map["replacements"]
    pairs = role_map["replacements"]
    replacements = {x["source"]: x["target"] for x in pairs}
    assert len(pairs) == len(replacements) == 81 and all(replacements.values())
    original = source[credit_sid]["source"]
    pattern = re.compile("|".join(re.escape(x) for x in sorted(replacements, key=len, reverse=True)))
    selected = list(pattern.finditer(original))
    regenerated = pattern.sub(lambda match: replacements[match.group()], original)
    assert len(selected) == 108 and regenerated == target[credit_sid]
    application_path = HE / "credits-application.json"
    application = json.loads(application_path.read_text())
    assert application["sourceSha256"] == digest(original.encode())
    assert application["replacementFileSha256"] == sha(HE / "credits-replacements.json")
    assert application["selectedReplacementSpans"] == 108
    assert application["uniqueReplacementPhrases"] == 81
    assert application["targetSha256"] == digest(regenerated.encode())
    assert application["targetLength"] == len(regenerated)
    assert application["exactPreservation"] == "passed"
    result = {"schemaVersion": 1, "status": "all 178 accepted static IDs and credits span derivation reproducible",
        "rows": 178, "result": "passed",
        "staticDraft": ref(HE / "static-text-draft.json"),
        "staticSidecar": ref(HE / "static-text-draft.validation.json"),
        "staticScope": ref(scope_path, selectedIds=178),
        "creditsRoleMap": ref(roles_path, phrases=81),
        "creditsReplacementDraft": ref(HE / "credits-replacements.json"),
        "creditsApplication": ref(application_path, selectedSpans=108),
        "creditsSourceValueSha256": digest(original.encode()),
        "rederivedCreditsValueSha256": digest(regenerated.encode()),
        "namesAndUnselectedContent": "preserved by longest-first exact source-span substitution"}
    once(GATE / "derived-static.json", result)
    return result


def preserve_exact_gate(target, by_rule, files):
    report_path = GATE / "preserve-exact-v4.json"
    if not report_path.exists():
        validate("he", report_path)
    else:
        for sid, value in target.items():
            check_value(by_rule[sid], value)
    report = json.loads(report_path.read_text())
    assert report["checkedRows"] == 16538 and report["exactResult"] == "passed"
    assert report["manifestSha256"] == sha(ROOT / "Source/preserve-exactly-v4.json")
    assert report["inputFiles"] == files
    return report_path


def finalize(progress, semantic, review, structural, files, counts, exact_report,
             source_gate, chain, independent_gate, mandatory_gate, structural_gate, static_gate):
    scan = subprocess.run([str(ROOT / ".venv/bin/python"), str(ROOT / "Scripts/report_locale_readiness.py"),
                           "--exact", "--compact"], cwd=ROOT,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                          capture_output=True, text=True)
    assert scan.returncode == 0, scan.stderr
    line = next(x for x in scan.stdout.splitlines() if re.match(r"^he\s", x))
    assert "16538/16538 (100.000%)" in line and "problems=0" in line
    assert file_set_hash(files) == review["authoredFileSetSha256"]
    assert sha(HE / "progress.json") == "c871c893961470fe4e4cb9d7bf4bcbb243fe2f610c953595dacf1f473828a07a"
    assert sha(HE / "semantic-review-progress.json") == "e30ea3133f561e4b897710fc15915580ba22feaf33ed3a479929b304d1214941"
    gate = {"schemaVersion": 1, "locale": "he", "gameVersion": "1.3.19", "sourceLocale": "ru",
        "status": "final offline Hebrew text gate passed; root integration and runtime remain separate",
        "acceptedUnits": 16538, "firstSemanticPassUnits": 16538,
        "unresolvedObjectiveFindings": 0, "independentClean": True,
        "independentReviewer": review["reviewer"], "currentHashesUnchanged": True,
        "textCoverage": "16538/16538 accepted visible units (100%)",
        "sourceGlossaryApplicability": ref(GATE / "source-glossary-applicability.json"),
        "correctionChain": ref(GATE / "correction-chain.json"),
        "independentReviewApplicability": ref(GATE / "independent-review-applicability.json"),
        "mandatoryRegression": ref(GATE / "mandatory-regression-applicability.json", count=549,
                                   freshReads=0, reusedUnchangedIndependentDecisions=549),
        "structuralValidation": ref(GATE / "structural-validation.json", rows=16538, files=337),
        "derivedStatic": ref(GATE / "derived-static.json", rows=178),
        "preserveExactReport": ref(exact_report, checkedRows=16538),
        "readinessScan": line,
        "currentAuthoredFileSetSha256": file_set_hash(files),
        "review04": ref(REVIEW / "final-review.json", deltaPairs=72, findings=0),
        "checkpointPreimages": [ref(HE / "progress.json"), ref(HE / "semantic-review-progress.json")],
        "adminCheckpointChange": "none; reviewed operational progress files kept byte-identical",
        "runtime": "not-run per owner instruction", "visual": "not-run",
        "imagesTextures": "outside text-only scope",
        "knownIntegrationLimits": ["characterName_Twins has no exact accepted UI key; runtime fallback remains unverified",
                                   "Hebrew mixed-direction rendering, fonts, wrapping, clipping and dialogue progression require later runtime/visual QA"],
        "editorialAcceptance": "root decision after independent verification; no author self-acceptance"}
    once(GATE / "full-gate-receipt.json", gate)
    # Exact locale-owned path set proposed for integration. The final-gate
    # handoff files themselves are referenced separately to avoid self hashes.
    locale_files = sorted(x for x in HE.rglob("*") if x.is_file()
                          and GATE not in x.parents and "__pycache__" not in x.parts)
    path_set = {"schemaVersion": 1, "scope": "current locale-owned tree outside final-gate/",
                "pathCount": len(locale_files),
                "paths": [ref(x) for x in locale_files],
                "sharedPathsProposed": [], "gitOperation": "none"}
    once(GATE / "integration-path-hashes.json", path_set)
    evidence_paths = [
        REVIEW / "final-review.json", REVIEW / "final-findings.json",
        REVIEW / "complete-review-decisions.json", REVIEW / "regression-reuse.json",
        REVIEW / "final-evidence-manifest.json", REVIEW / "final-input-verification.json",
        CORRECTION / "closure-manifest.json", CORRECTION / "delta-review-rows.jsonl",
        CORRECTION / "selector-regression-spec.json",
        GATE / "source-glossary-applicability.json", GATE / "correction-chain.json",
        GATE / "independent-review-applicability.json",
        GATE / "mandatory-regression-applicability.json",
        GATE / "structural-validation.json", GATE / "derived-static.json",
        exact_report, GATE / "full-gate-receipt.json",
        GATE / "integration-path-hashes.json", GATE / "verify.py"]
    handoff = {"schemaVersion": 1, "locale": "he", "acceptedUnits": 16538,
        "firstSemanticPassUnits": 16538, "unresolvedObjectiveFindings": 0,
        "independentClean": True, "independentReviewer": review["reviewer"],
        "currentHashesUnchanged": True,
        "mandatoryRegression": {"count": 549, "freshReads": 0,
                                "reusedUnchangedIndependentDecisions": 549,
                                "result": "passed"},
        "structural": {"rows": 16538, "result": "passed"},
        "derivedStatic": {"rows": 178, "result": "passed"},
        "preserveExactReport": ref(exact_report),
        "authoredFiles": files,
        "evidenceFiles": [ref(x) for x in evidence_paths],
        "proposedIntegration": {"localePathHashSet": ref(GATE / "integration-path-hashes.json",
                                                       paths=len(locale_files)),
                                "finalGateArtifacts": [ref(x) for x in sorted(GATE.iterdir())
                                                       if x.is_file() and x.name not in
                                                       {"root-handoff.json", "integration-path-hashes.json"}],
                                "rootHandoffSelfPath": rel(GATE / "root-handoff.json"),
                                "sharedPathsProposed": [], "gitOperation": "none"},
        "boundaries": {"textCoverage": "100% accepted authored units",
                       "offlineEditorial": "clean independent exact delta on unchanged hashes",
                       "runtime": "not run", "visualAndRTL": "not run",
                       "integrationAndAcceptance": "root coordinator pending"}}
    once(GATE / "root-handoff.json", handoff)
    print(json.dumps({"status": "passed", "authoredFiles": len(files),
                      "integrationPaths": len(locale_files), "handoffSha256": sha(GATE / "root-handoff.json"),
                      "receiptSha256": sha(GATE / "full-gate-receipt.json")}, ensure_ascii=False))


def main():
    GATE.mkdir(exist_ok=True)
    progress, semantic, review, structural = current_inputs()
    source_gate = source_glossary_applicability(progress, review)
    chain = correction_chain(review)
    target, source, by_rule, ordered, files, sidecars, counts = selected_values(progress)
    assert file_set_hash(files) == review["authoredFileSetSha256"]
    independent_gate = review_decisions(review, target, source, ordered)
    mandatory_gate = mandatory_regression(target, source)
    structural_gate = run_structural_validators(files, sidecars)
    static_gate = derived_static(progress, target, source)
    exact_report = preserve_exact_gate(target, by_rule, files)
    finalize(progress, semantic, review, structural, files, counts, exact_report,
             source_gate, chain, independent_gate, mandatory_gate, structural_gate, static_gate)


if __name__ == "__main__":
    main()
