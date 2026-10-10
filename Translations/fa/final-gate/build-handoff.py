#!/usr/bin/env python3
"""Seal the Persian offline text gate for root integration without touching shared state."""

import hashlib
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[3]
FA = ROOT / "Translations/fa"
GATE = pathlib.Path(__file__).resolve().parent
REVIEW = FA / "independent-review-03"
CYCLE = FA / "audit-cycle-003"
PROGRESS = FA / "semantic-review-progress.json"
DOC = ROOT / "Documentation/fa-text-progress-v1.json"
MASTER = pathlib.Path("/Users/antonkrutov/Desktop/SiteForMods")
MASTER_SOURCE = MASTER / "data/games/no-im-not-a-human/glossary.json"
MASTER_LAYERS = MASTER / "data/games/no-im-not-a-human/glossary-translations.json"
LOCAL_SOURCE = ROOT / "Documentation/glossary-research/final-v1/glossary.json"
LOCAL_LAYER = ROOT / "Documentation/glossary-translations/fa/layer.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def once(path, raw):
    if path.exists():
        assert path.read_bytes() == raw, f"sealed evidence differs: {path}"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)


def rel(path):
    return str(path.relative_to(ROOT))


def verify_review():
    verdict_path = REVIEW / "review-verdict.json"
    index_path = REVIEW / "evidence-index.json"
    assert sha(verdict_path) == "8d1210986d0847f163505ab94334c873060cf643ac4051af84d42a6a960f8e31"
    assert sha(index_path) == "15f16d86863af0530dca02379d03f358a00cede56d73a7674b40f8041df9e432"
    verdict, index = read(verdict_path), read(index_path)
    assert len(index["files"]) == 17 and len(verdict["pins"]) == 539
    for name, expected in index["files"].items():
        assert sha(REVIEW / name) == expected, name
    for name, expected in verdict["pins"].items():
        assert sha(ROOT / name) == expected, name
    assert verdict["verdict"].startswith("clean independent cycle003")
    assert verdict["objectiveProposals"] == 0 and verdict["reviewedDeltaFullUnits"] == 18
    assert verdict["mandatoryRegressionCount"] == 544
    assert verdict["mandatoryCurrentDeltaReads"] == 0
    assert verdict["mandatoryExactUnchangedIndependentDecisions"] == 544
    assert verdict["mandatoryLogicalResult"] == "clean"
    assert verdict["retiredPriorRowsAccounted"] == 1757
    assert verdict["sourceAndGlossaryUnchanged"] and verdict["firstSemanticPassReusable"] == 16538
    findings = read(REVIEW / "findings.json")
    assert findings["objectiveProposals"] == 0 and findings["rows"] == []
    return verdict, index


def source_and_master():
    local_source, local_fa = read(LOCAL_SOURCE), read(LOCAL_LAYER)
    master_source, master_fa = read(MASTER_SOURCE), read(MASTER_LAYERS)["fa"]
    assert local_source == master_source and local_fa == master_fa
    assert len(local_source["entries"]) == len(local_fa) == 201
    assert local_source["sourceLocale"] == "ru"
    return {"sourceEntries": 201, "localeEntries": 201, "sourceEqual": True,
            "persianLayerEqual": True,
            "masterSourcePath": str(MASTER_SOURCE), "masterSourceSha256": sha(MASTER_SOURCE),
            "localSourcePath": rel(LOCAL_SOURCE), "localSourceSha256": sha(LOCAL_SOURCE),
            "masterLayersPath": str(MASTER_LAYERS), "masterLayersSha256": sha(MASTER_LAYERS),
            "localLayerPath": rel(LOCAL_LAYER), "localLayerSha256": sha(LOCAL_LAYER),
            "cli": "./vnrevival glossary guide; ./vnrevival glossary work no-im-not-a-human fa: 201/201, ID/order match, zero missing/extra"}


def derived(receipt, verdict):
    source = {}
    for name in ("strings.jsonl", "static-text.jsonl"):
        for line in (ROOT / "Source/localization-inventory-v3" / name).open():
            row = json.loads(line)
            assert row["stableId"] not in source
            source[row["stableId"]] = row
    values = {}
    for item in receipt["authoredFiles"]:
        path = ROOT / item["path"]
        assert sha(path) == item["sha256"]
        batch = read(path)
        if path.name == "static-text-draft.json":
            for row in batch["entries"]:
                sid = row["stableId"]
                assert sid not in values
                values[sid] = row["target"]
        else:
            guid = {"UI": "0cbd8a7a4f543344bb95659de87f67a5",
                    "Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
                    "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}[batch["collection"]]
            for row in batch["entries"]:
                sid = f"string:{guid}:{row['id']}"
                assert sid not in values
                values[sid] = row["target"]
    assert len(values) == 16538
    static = read(FA / "static-text-draft.json")["entries"]
    phrases = read(FA / "static-phrase-map.json")["phrases"]
    mapping = {row["source"]: row["target"] for row in phrases}
    assert len(mapping) == len(phrases)
    mapped = [row for row in static if source[row["stableId"]]["source"] in mapping]
    assert len(static) == 178 and len(mapped) == 177
    assert all(row["target"] == mapping[source[row["stableId"]]["source"]] for row in mapped)
    credits = read(FA / "credits-role-map.json")["replacements"]
    cm = {row["source"]: row["target"] for row in credits}
    assert len(cm) == len(credits) == 81
    pattern = re.compile("|".join(re.escape(s) for s in sorted(cm, key=len, reverse=True)))
    credit_id = "tmp:level5:59:m_text"
    assert pattern.sub(lambda m: cm[m.group()], source[credit_id]["source"]) == values[credit_id]
    common = read(FA / "common-options-001.authored.json")["phrases"]
    selected = []
    for row in common:
        matches = [sid for sid, src in source.items() if src.get("collection") == "Dialogs" and src["source"] == row["source"]]
        assert len(matches) == row["expectedRows"]
        assert all(values[sid] == row["target"] for sid in matches)
        selected.extend(matches)
    assert len(selected) == len(set(selected)) == 2841
    command = [str(ROOT / ".venv/bin/python"), "Scripts/expand_exact_text_batch.py", "--verify",
               "Translations/fa/common-options-001.authored.json", "Translations/fa/dialogue-batch-001.json"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    expansion = json.loads(result.stdout)
    assert expansion["result"] == "verified" and expansion["rows"] == 2841
    catalog = read(REVIEW / "catalog-reuse.json")
    assert catalog["count"] == 544 and catalog["admittedDynamicOutputs"] == 6
    assert verdict["derivedApplicability"].startswith("177 static map rows exact;81 credits roles exact regeneration;2841 common options rows exact")
    evidence = {"schemaVersion": 1, "locale": "fa", "result": "passed",
                "staticRows": 178, "staticPhraseMapRows": 177, "creditsRoles": 81,
                "commonOptionsRows": 2841, "commonOptionsDistinctIds": 2841,
                "admittedDynamicConsumerOutputsFromSealedReview03": 6,
                "expansionVerifyCommand": ".venv/bin/python " + " ".join(command[1:]),
                "expansionVerifyResult": expansion["result"],
                "sourceStringsSha256": sha(ROOT / "Source/localization-inventory-v3/strings.jsonl"),
                "sourceStaticSha256": sha(ROOT / "Source/localization-inventory-v3/static-text.jsonl"),
                "recipeHashes": {rel(p): sha(p) for p in
                                (FA / "static-phrase-map.json", FA / "credits-role-map.json",
                                 FA / "common-options-001.authored.json", ROOT / "Scripts/expand_exact_text_batch.py")},
                "review03CatalogSha256": sha(REVIEW / "catalog-reuse.json")}
    once(GATE / "derived-check.json", encode(evidence))
    return evidence


def update_progress(receipt, verdict):
    pre_dir = GATE / "preimages"
    pre_dir.mkdir(exist_ok=True)
    for path in (PROGRESS, DOC):
        pre = pre_dir / path.name
        if not pre.exists():
            pre.write_bytes(path.read_bytes())
    p_before = read(pre_dir / PROGRESS.name)
    d_before = read(pre_dir / DOC.name)
    assert p_before["acceptedUnits"] == p_before["reviewedUnits"] == 16538
    assert p_before["cycle3Evidence"]["closureSha256"] == sha(CYCLE / "closure.json")
    assert d_before["coverage"]["authoredAndStructurallyValid"] == 16538
    p = read(PROGRESS)
    p["stage"] = "offline-text-gate-passed; root-integration-pending"
    p["independentReview03"] = {
        "verdictPath": rel(REVIEW / "review-verdict.json"),
        "verdictSha256": sha(REVIEW / "review-verdict.json"),
        "evidenceIndexSha256": sha(REVIEW / "evidence-index.json"),
        "reviewedDeltaFullUnits": 18, "objectiveFindings": 0,
        "mandatoryRegressionCount": 544,
        "mandatoryFreshReads": 0,
        "mandatoryReusedUnchangedIndependentDecisions": 544,
        "result": "clean independent text delta",
    }
    p["finalOfflineGate"] = {
        "freshCorpusPath": rel(GATE / "fresh-full-corpus.json"),
        "freshCorpusSha256": sha(GATE / "fresh-full-corpus.json"),
        "derivedCheckPath": rel(GATE / "derived-check.json"),
        "derivedCheckSha256": sha(GATE / "derived-check.json"),
        "acceptedUnits": 16538, "firstSemanticPassUnits": 16538,
        "structural": "passed", "preserveExact": "passed",
        "independentClean": True,
        "runtimeVisual": "not-run",
        "rootIntegration": "pending",
    }
    p["nextAction"] = "Root independently verify Translations/fa/final-gate/root-handoff.json, acceptance/build integration and canonical Git commit. Persian runtime shaping, bidi, fonts and layout remain untested; no game launch in this text task."
    PROGRESS.write_bytes(encode(p))
    d = read(DOC)
    d["stage"] = "offline-text-gate-passed; root-integration-pending"
    d["authoredArtifacts"]["semanticReviewProgressSha256"] = sha(PROGRESS)
    d["authoredArtifacts"]["independentReview03VerdictSha256"] = sha(REVIEW / "review-verdict.json")
    d["authoredArtifacts"]["finalFullCorpusSha256"] = sha(GATE / "fresh-full-corpus.json")
    d["checks"]["independentDiffReview"] = "Review03 clean on exact 18-ID delta; all 544 mandatory catalog decisions are unchanged and independently supported. Root owns final acceptance/integration."
    d["checks"]["protectedValues"] = "Fresh fa-only full-corpus validator passed 16,538/16,538 selected IDs, exact spans, original grammar and metadata/order guards; no historical sidecars rewritten."
    d["checks"]["offlineFinalGate"] = "passed structural/exact/derived checks; root independently verifies final acceptance and build. Runtime and visual not-run."
    d["nextAction"] = p["nextAction"]
    DOC.write_bytes(encode(d))
    assert p["pins"] == p_before["pins"] and p["reviewedSegments"] == p_before["reviewedSegments"]
    assert p["reviewedUnits"] == p_before["reviewedUnits"] == 16538
    assert p["cycle3Evidence"] == p_before["cycle3Evidence"]
    assert d["coverage"] == d_before["coverage"]
    assert d["inputs"] == d_before["inputs"]
    assert d["authoredArtifacts"]["batchSetSha256"] == d_before["authoredArtifacts"]["batchSetSha256"]
    return {"progressBeforeSha256": sha(pre_dir / PROGRESS.name),
            "progressAfterSha256": sha(PROGRESS),
            "documentationBeforeSha256": sha(pre_dir / DOC.name),
            "documentationAfterSha256": sha(DOC),
            "semanticAndArtifactInputsUnchanged": True}


def main():
    verdict, index = verify_review()
    receipt_path = GATE / "fresh-full-corpus.json"
    receipt = read(receipt_path)
    assert receipt["locale"] == "fa" and receipt["rows"] == 16538
    assert receipt["structuralResult"] == receipt["exactResult"] == "passed"
    assert receipt["selectedIdCoverage"] == "16538 unique; no missing/extra"
    assert len(receipt["authoredFiles"]) == 419
    for item in receipt["authoredFiles"]:
        assert sha(ROOT / item["path"]) == item["sha256"]
    assert sha(ROOT / "Scripts/validate_locale_corpus.py") == receipt["validatorSha256"]
    assert sha(ROOT / "Scripts/locale_text_inputs.py") == receipt["inputLoaderSha256"]
    for name, pin in receipt["owningValidators"].items():
        assert sha(ROOT / "Scripts" / name) == pin
    master = source_and_master()
    derived(receipt, verdict)
    operational = update_progress(receipt, verdict)
    # Operational checkpoint edits are outside the sealed reviewer inputs.
    verify_review()
    assert all(sha(ROOT / row["path"]) == row["sha256"] for row in receipt["authoredFiles"])
    once(GATE / "operational-change.json", encode({"schemaVersion": 1, "locale": "fa", **operational,
         "review03VerdictSha256Unchanged": sha(REVIEW / "review-verdict.json"),
         "review03IndexSha256Unchanged": sha(REVIEW / "evidence-index.json"),
         "authoredFileCountUnchanged": 419,
         "sourceGlossaryAndRecipePinsUnchanged": True}))
    evidence_paths = [
        GATE / "fresh-full-corpus.json", GATE / "derived-check.json", GATE / "operational-change.json",
        GATE / "preimages/semantic-review-progress.json", GATE / "preimages/fa-text-progress-v1.json",
        PROGRESS, DOC,
        REVIEW / "review-verdict.json", REVIEW / "evidence-index.json", REVIEW / "findings.json",
        REVIEW / "per-id-review.json", REVIEW / "catalog-reuse.json", REVIEW / "first-pass-reuse.json",
        REVIEW / "verification.json", REVIEW / "retired-accounting.json",
        FA / "audit-cycle-001/first-pass.snapshot.json",
        FA / "audit-cycle-002/closure.json", CYCLE / "closure.json", CYCLE / "closure-ids.txt",
        CYCLE / "next-review-delta.json", CYCLE / "nextReviewDelta-ids.txt",
        CYCLE / "mandatoryRegression-ids.txt", CYCLE / "evidence-index.json",
        ROOT / "Documentation/localization-source-inventory-v3.json",
        ROOT / "Documentation/text-source-acceptance-v1.json",
        ROOT / "Source/localization-inventory-v3/strings.jsonl",
        ROOT / "Source/localization-inventory-v3/static-text.jsonl",
        ROOT / "Source/preserve-exactly-v4.json", LOCAL_SOURCE, LOCAL_LAYER,
    ]
    assert len({str(p) for p in evidence_paths}) == len(evidence_paths)
    report = {"schemaVersion": 1, "locale": "fa", "gameVersion": "1.3.19", "sourceLocale": "ru",
              "scope": "text-only; images and textures excluded",
              "status": "offline Persian text gate passed; root integration pending",
              "acceptedUnits": 16538, "firstSemanticPassUnits": 16538,
              "unresolvedObjectiveFindings": 0,
              "independentClean": True,
              "independentReviewer": verdict["reviewer"],
              "currentHashesUnchanged": True,
              "mandatoryRegression": {"count": 544, "freshReads": 0,
                                      "reusedUnchangedIndependentDecisions": 544, "result": "passed"},
              "structural": {"rows": 16538, "result": "passed", "tableBatches": 418,
                             "tableRows": 16360, "staticRows": 178},
              "derivedStatic": {"rows": 178, "result": "passed", "mappedPhraseRows": 177,
                                "creditsRoleReplacements": 81},
              "commonOptions": {"rows": 2841, "result": "passed"},
              "preserveExactReport": {"path": rel(receipt_path), "sha256": sha(receipt_path)},
              "authoredFiles": receipt["authoredFiles"],
              "evidenceFiles": [{"path": rel(path), "sha256": sha(path)} for path in evidence_paths],
              "sharedRecipes": [{"path": rel(path), "sha256": sha(path)} for path in
                                (ROOT / "Scripts/validate_locale_corpus.py",
                                 ROOT / "Scripts/locale_text_inputs.py",
                                 ROOT / "Scripts/validate_game_text_batch.py",
                                 ROOT / "Scripts/validate_static_text_draft.py",
                                 ROOT / "Scripts/preserve_exact.py",
                                 ROOT / "Scripts/expand_exact_text_batch.py")],
              "masterGlossaryParity": master,
              "operationalProgress": operational,
              "independentReview": {"deltaFullPairs": 18, "cycle003Closure": 946,
                                    "retiredPriorRows": 1757,
                                    "admittedDynamicConsumerOutputs": 6,
                                    "verdictSha256": sha(REVIEW / "review-verdict.json"),
                                    "evidenceIndexSha256": sha(REVIEW / "evidence-index.json")},
              "unresolvedSourceContext": read(CYCLE / "closure.json")["unresolvedQuestions"],
              "runtime": "not-run; Persian joining, ZWNJ, bidi, fonts, layout and game progression unverified",
              "visual": "not-run", "build": "not-run by fa author",
              "integration": "root owns independent acceptance/build verification and Git commit",
              "modelUsage": {"inputTokens": None, "cachedInputTokens": None,
                             "outputTokens": None, "reasoningTokens": None, "totalTokens": None,
                             "status": "unknown; per-request telemetry not exposed to this author turn"}}
    once(GATE / "root-handoff.json", encode(report))
    print(json.dumps({"acceptedUnits": 16538, "authoredFiles": 419,
                      "evidenceFiles": len(report["evidenceFiles"]), "reportSha256": sha(GATE / "root-handoff.json"),
                      "freshCorpusSha256": sha(receipt_path), "operationalProgress": operational}))


if __name__ == "__main__":
    main()
