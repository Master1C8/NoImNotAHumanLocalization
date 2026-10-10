#!/usr/bin/env python3
"""Update only the Persian current checkpoint after cycle-3 immutable evidence."""

import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[3]
FA = ROOT / "Translations/fa"
CYCLE = pathlib.Path(__file__).resolve().parent
PROGRESS = FA / "semantic-review-progress.json"
DOC = ROOT / "Documentation/fa-text-progress-v1.json"
REVIEW = FA / "independent-review-02"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    if path.read_bytes() != data:
        path.write_bytes(data)


def main():
    closure = read(CYCLE / "closure.json")
    hashes = closure["componentHashes"]
    assert hashes["closure"]["count"] == 946 and hashes["nextReviewDelta"]["count"] == 18
    p = read(PROGRESS)
    d = read(DOC)
    assert p["acceptedUnits"] == p["reviewedUnits"] == d["coverage"]["denominator"] == 16538
    assert p["firstPassEvidence"]["sha256"] == sha(FA / "audit-cycle-001/first-pass.snapshot.json")
    assert p["cycle2Evidence"]["closureSha256"] == sha(FA / "audit-cycle-002/closure.json")
    assert p["pins"]["sourceStringsSha256"] == sha(ROOT / "Source/localization-inventory-v3/strings.jsonl")
    assert p["pins"]["sourceStaticSha256"] == sha(ROOT / "Source/localization-inventory-v3/static-text.jsonl")
    assert p["pins"]["persianGlossaryLayerSha256"] == sha(ROOT / "Documentation/glossary-translations/fa/layer.json")
    batches = sorted(x for x in FA.glob("*batch-*.json") if
                     re.fullmatch(r"(?:ui|dialogue|checks)-batch-\d{3}\.json", x.name))
    batchset = hashlib.sha256("".join(
        str(x.relative_to(ROOT)) + "\t" + sha(x) + "\n" for x in batches).encode()).hexdigest()
    assert len(batches) == 418
    p["stage"] = "correction-cycle-003-applied; independent-review-03-pending"
    p["postIndependentCorrectionUnits"] = 6
    p["independentReview02"] = {
        "verdictPath": "Translations/fa/independent-review-02/review-verdict.json",
        "verdictSha256": sha(REVIEW / "review-verdict.json"),
        "findingsSha256": sha(REVIEW / "findings.json"),
        "evidenceIndexSha256": sha(REVIEW / "evidence-index.json"),
        "reviewedDeltaFullUnits": 1408,
        "previousClosureUnits": 2701,
        "cycle2CorrectionsPassed": 5,
        "objectiveProposalsAccepted": 1,
        "cleanIndependentGate": False,
    }
    if "cycle1Evidence" not in p:
        p["cycle1Evidence"] = p["currentEvidence"]
    p["currentEvidence"] = {
        "cycle": 3,
        "sourceManifestSha256": sha(ROOT / "Source/preserve-exactly-v4.json"),
        "sourceStringsSha256": sha(ROOT / "Source/localization-inventory-v3/strings.jsonl"),
        "sourceStaticSha256": sha(ROOT / "Source/localization-inventory-v3/static-text.jsonl"),
        "glossaryLayerSha256": sha(ROOT / "Documentation/glossary-translations/fa/layer.json"),
        "batchSetSha256": batchset,
        "staticDraftSha256": sha(FA / "static-text-draft.json"),
        "correctionPlanSha256": sha(CYCLE / "correction-plan.json"),
        "closurePath": "Translations/fa/audit-cycle-003/closure.json",
        "closureSha256": sha(CYCLE / "closure.json"),
        "closureIdsSha256": sha(CYCLE / "closure-ids.txt"),
        "nextReviewDeltaPath": "Translations/fa/audit-cycle-003/next-review-delta.json",
        "nextReviewDeltaSha256": sha(CYCLE / "next-review-delta.json"),
        "nextReviewDeltaIdsSha256": sha(CYCLE / "nextReviewDelta-ids.txt"),
        "deterministicGateSha256": sha(CYCLE / "deterministic-gate.json"),
        "structuralSidecarGateSha256": sha(CYCLE / "structural-sidecar-gate.json"),
    }
    p["cycle3Evidence"] = {
        "phase": "one author correction applied; independent delta review pending",
        "preflightSha256": sha(CYCLE / "preflight.json"),
        "selectorSpecSha256": sha(CYCLE / "selector-spec.json"),
        "auntEnumerationSha256": sha(CYCLE / "aunt-enumeration.json"),
        "fileDeltaManifestSha256": sha(CYCLE / "file-delta-manifest.json"),
        "diffAuditSha256": sha(CYCLE / "diff-audit.json"),
        "closureSha256": sha(CYCLE / "closure.json"),
        "closureUnits": 946,
        "closureIdsSha256": hashes["closure"]["sha256"],
        "nextReviewDeltaSha256": sha(CYCLE / "next-review-delta.json"),
        "nextReviewDeltaUnits": 18,
        "nextReviewDeltaIdsSha256": hashes["nextReviewDelta"]["sha256"],
        "newlySelectedUnits": 2,
        "invalidatedPriorUnits": 16,
        "retiredPriorUnits": 1757,
        "mandatoryRegressionUnits": 544,
        "missingAcceptedIds": 0,
        "extraUnacceptedIds": 0,
        "reviewerHandoffSha256": sha(CYCLE / "reviewer-handoff.md"),
        "runtime": "not-run",
    }
    if (CYCLE / "evidence-index.json").exists():
        p["cycle3Evidence"]["evidenceIndexSha256"] = sha(CYCLE / "evidence-index.json")
    p["pinsScope"] = "The pins and reviewedSegments retain the historical first-pass source/glossary and before-correction authored evidence; current authored hashes and delta evidence are in currentEvidence and cycle3Evidence."
    p["nextAction"] = "Distinct reviewer: reproduce cycle-3 946-ID closure, read exact 18-ID next delta (one corrected, two newly selected Scammer_Death rows, 16 prior reviewed rows invalidated by batch-348 file hash), and check the 544-ID mandatory catalog. Independent clean acceptance and authorized runtime/visual checks remain pending."
    write(PROGRESS, p)
    d["authoredArtifacts"]["batchSetSha256"] = batchset
    d["authoredArtifacts"]["staticDraftSha256"] = sha(FA / "static-text-draft.json")
    d["authoredArtifacts"]["semanticReviewProgressSha256"] = sha(PROGRESS)
    d["authoredArtifacts"]["correctionCycle3"] = "Translations/fa/audit-cycle-003/"
    d["authoredArtifacts"]["correctionCycle3ClosureSha256"] = sha(CYCLE / "closure.json")
    d["authoredArtifacts"]["correctionCycle3GateSha256"] = sha(CYCLE / "deterministic-gate.json")
    d["authoredArtifacts"]["independentReview02VerdictSha256"] = sha(REVIEW / "review-verdict.json")
    d["checks"]["batchStructure"] = "All 418 current batch sidecars match current authored hashes and pass; cycle-3 batch 348 was revalidated after its one full-unit correction."
    d["checks"]["protectedValues"] = "Cycle-3 full deterministic gate checked all 16,538 accepted IDs against Source/preserve-exactly-v4.json; full .venv readiness --exact reported fa 16,538/16,538 validated, observed 16,538, problems 0."
    d["checks"]["semanticReview"] = "Complete first pass remains 16,538/16,538 on unchanged source/glossary. Review02 read the exact 1,408-ID cycle-2 delta; all five prior corrections passed and one new aunt-side finding was applied by the author in cycle 3. Author validation is not independent acceptance."
    d["checks"]["independentDiffReview"] = "Review02 verdict: one objective finding, clean gate failed. Cycle-3 closure 946; exact 18-ID delta awaiting a distinct reviewer. No final editorial acceptance."
    d["nextAction"] = p["nextAction"]
    write(DOC, d)
    print(json.dumps({"batchSetSha256": batchset, "progressSha256": sha(PROGRESS),
                      "documentationSha256": sha(DOC), "nextDelta": 18}))


if __name__ == "__main__":
    main()
