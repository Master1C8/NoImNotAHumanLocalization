#!/usr/bin/env python3
"""Pin and preflight the six Greek review02 consumer corrections."""

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
REVIEW = HERE / "independent-review-02"
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import check_value  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main():
    findings = json.loads((REVIEW / "findings.json").read_text())["findings"]
    topology = json.loads((REVIEW / "bounded-consumer-topology.json").read_text())
    checks = json.loads((REVIEW / "proposal-and-consumer-checks.json").read_text())
    contract = json.loads((ROOT / "Source/preserve-exactly-v4.json").read_text())
    rules = {row["stableId"]: row for row in contract["tableRows"] + contract["staticRows"]}
    ordinal = {row["stableId"]: i for i, row in enumerate(contract["tableRows"] + contract["staticRows"])}
    consumer = {row["row"]["stableId"]: row for row in topology["consumerRows"]}
    variants = {}
    for row in checks["assembledBribeExamples"]:
        variants.setdefault(row["stableId"], []).append(row)
    assert len(findings) == 6 and len(consumer) == 21 and len(checks["assembledBribeExamples"]) == 126
    rows = []
    for finding in findings:
        sid = finding["stableId"]
        target_file = ROOT / finding["targetFile"]
        authored = HERE / f"dialogue-ordered-{target_file.stem[-3:]}.authored.json"
        if not authored.exists():
            authored = target_file
        assert not finding.get("authoredInput") or ROOT / finding["authoredInput"] == authored
        assert sid in ordinal and sid in consumer
        assert digest(target_file) == finding["targetFileSha256"]
        assert text_digest(finding["source"]) == finding["sourceSha256"]
        assert text_digest(finding["before"]) == finding["beforeSha256"]
        assert text_digest(finding["proposedTarget"]) == finding["proposedTargetSha256"]
        assert consumer[sid]["row"]["currentTarget"] == finding["before"]
        assert consumer[sid]["node"] == finding["compiledOccurrences"][0]["node"]
        assert consumer[sid]["pc"] == finding["compiledOccurrences"][0]["pc"]
        identifier = int(sid.rsplit(":", 1)[1])
        assert next(row["target"] for row in json.loads(target_file.read_text())["entries"]
                    if row["id"] == identifier) == finding["before"]
        assert finding["source"].count("{0}") == finding["proposedTarget"].count("{0}") == 1
        check_value(rules[sid], finding["proposedTarget"])
        assembled = variants[sid]
        assert len(assembled) == 6
        assert all(finding["proposedTarget"].replace("{0}", row["label"]) == row["proposedAssembled"]
                   for row in assembled)
        rows.append({
            "findingId": finding["findingId"], "stableId": sid, "ordinal": ordinal[sid],
            "key": finding["key"], "source": finding["source"],
            "sourceSha256": finding["sourceSha256"],
            "before": finding["before"], "beforeSha256": finding["beforeSha256"],
            "after": finding["proposedTarget"], "afterSha256": finding["proposedTargetSha256"],
            "reason": finding["reason"], "compiledOccurrences": finding["compiledOccurrences"],
            "assembledVariants": [{"item": row["item"], "label": row["label"],
                                   "before": row["currentAssembled"], "after": row["proposedAssembled"]}
                                  for row in assembled],
            "authoredInput": str(authored.relative_to(ROOT)),
            "authoredInputBeforeSha256": digest(authored),
            "targetFile": finding["targetFile"],
            "targetFileBeforeSha256": finding["targetFileSha256"],
            "sourceInvariants": "Preserve speaker, offer/possession, amount/usefulness or acceptability where present, action order and invisibility where present, address and {0}."})
    rows.sort(key=lambda row: row["ordinal"])
    report = {
        "schemaVersion": 1, "locale": "el", "cycle": 3,
        "status": "six complete units adjudicated and protected-syntax/assembled preflight passed; authored application pending",
        "acceptedUnits": 16538,
        "review02EvidenceManifestSha256": digest(REVIEW / "evidence-manifest-v2.json"),
        "review02FindingsSha256": digest(REVIEW / "findings.json"),
        "review02FinalCoverageProofSha256": digest(REVIEW / "final-coverage-and-invalidation-proof.json"),
        "review02ConsumerTopologySha256": digest(REVIEW / "bounded-consumer-topology.json"),
        "review02AssembledChecksSha256": digest(REVIEW / "proposal-and-consumer-checks.json"),
        "sourceInventorySha256": digest(ROOT / "Source/localization-inventory-v3/strings.jsonl"),
        "sourceStaticSha256": digest(ROOT / "Source/localization-inventory-v3/static-text.jsonl"),
        "approvedGlossarySha256": digest(ROOT / "Documentation/glossary-translations/el/layer.json"),
        "priorCycle2ClosureManifestSha256": digest(HERE / "correction-cycle-002-closure-manifest.json"),
        "priorCycle2CheckpointSha256": digest(HERE / "correction-cycle-002-text-checkpoint.json"),
        "previousReview02FreshReads": 252, "previousReview02AcceptedUnchanged": 246,
        "previousReview02Findings": 6, "correctionCount": 6,
        "actualConsumerTemplates": 21, "deficitDomainItems": 6,
        "assembledVariantsPreflight": 36,
        "domainGuard": "Fresh OtherGameData gameplay fields and six deficit keys match pinned evidence; m_Script cached-header mismatch is technical metadata only.",
        "corrections": rows}
    out = HERE / "correction-cycle-003-adjudication.json"
    assert not out.exists(), "Preserve adjudication evidence"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"corrections": len(rows), "assembledVariants": 36,
                      "adjudicationSha256": digest(out)}))


if __name__ == "__main__":
    main()
