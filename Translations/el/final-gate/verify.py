#!/usr/bin/env python3
"""Read-only verification of the sealed Greek text handoff.

This checks evidence applicability and deterministic gates. It does not perform
semantic review, accept the locale, modify sidecars, or launch the game.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
EL = ROOT / "Translations/el"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "Scripts"))
from locale_text_inputs import current_text  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pinned(relative, expected):
    path = (ROOT / relative).resolve()
    assert path.is_relative_to(ROOT), relative
    assert sha(path) == expected, relative
    return path


def lines(path):
    raw = path.read_bytes()
    assert raw.endswith(b"\n") and b"\r" not in raw, str(path)
    return [json.loads(line) for line in raw.splitlines()]


def check():
    handoff = read(HERE / "root-handoff.json")
    gate = read(HERE / "gate-evidence.json")
    assert handoff["locale"] == "el"
    assert handoff["acceptedUnits"] == handoff["firstSemanticPassUnits"] == 16538
    assert handoff["unresolvedObjectiveFindings"] == 0
    assert handoff["independentClean"] is True
    assert handoff["independentReviewer"] == "/root/el_independent_review_03"
    assert handoff["currentHashesUnchanged"] is True
    assert handoff["mandatoryRegression"] == {
        "count": 1269, "freshReads": 39,
        "reusedUnchangedIndependentDecisions": 1230, "result": "passed"}
    assert handoff["structural"] == {"rows": 16538, "result": "passed"}
    assert handoff["derivedStatic"] == {"rows": 178, "result": "passed"}
    assert len({r["path"] for r in handoff["evidenceFiles"]}) == len(handoff["evidenceFiles"])
    for row in handoff["evidenceFiles"]:
        pinned(row["path"], row["sha256"])

    manifest = pinned("Translations/el/independent-review-03/evidence-manifest.json",
                      "b79ebcb47a2a12e6664ae4a6b38690df6cd0ab07fa5c0174c63a7a8ba0501b17")
    review = read(manifest)
    assert review["reviewer"] == handoff["independentReviewer"]
    assert review["verdict"] == "clean-on-pinned-unchanged-hashes"
    assert len(review["evidencePins"]) == 13
    for path, expected in review["evidencePins"].items():
        pinned(path, expected)
    original_pins = read(EL / "independent-review-03/input-pins.json")["pins"]
    assert len(original_pins) == 1365
    refresh = read(HERE / "administrative-refresh.json")
    assert len(refresh["refreshed"]) == 4
    admin = {str(ROOT / row["path"]): row for row in refresh["refreshed"]}
    assert {Path(p).name for p in admin} == {
        "dialogue-batch-019.validation.json", "dialogue-batch-024.validation.json",
        "dialogue-batch-026.validation.json", "dialogue-batch-029.validation.json"}
    for path, expected in original_pins.items():
        if path in admin:
            row = admin[path]
            assert row["previousSha256"] == expected
            pinned(row["archivedPreimagePath"], expected)
            assert sha(Path(path)) == row["currentSha256"]
        else:
            assert sha(Path(path)) == expected, path
    findings = read(EL / "independent-review-03/findings.json")
    assert findings["verdict"] == review["verdict"]
    assert findings["fullUnitObjectiveFindings"] == findings["selectorDefects"] == []

    first = read(EL / "semantic-review-progress.json")
    assert first["acceptedUnits"] == first["reviewedUnits"] == 16538
    assert sha(EL / "semantic-review-progress.json") == gate["firstSemanticProgressSha256"]
    first_rows = []
    end = 0
    for segment in first["reviewedSegments"]:
        assert segment["startOrdinal"] == end
        end = segment["endOrdinalExclusive"]
        assert segment["rows"] == end - segment["startOrdinal"]
        path = pinned(segment["evidencePath"], segment["evidenceSha256"])
        rows = lines(path)
        assert len(rows) == segment["rows"]
        assert [r["ordinal"] for r in rows] == list(range(segment["startOrdinal"], end))
        assert rows[0]["stableId"] == segment["firstStableId"]
        assert rows[-1]["stableId"] == segment["lastStableId"]
        first_rows.extend(rows)
    assert end == len(first_rows) == 16538
    assert len({r["stableId"] for r in first_rows}) == 16538
    source_manifest = read(ROOT / "Source/preserve-exactly-v4.json")
    assert [r["stableId"] for r in first_rows] == [r["stableId"] for r in
           source_manifest["tableRows"] + source_manifest["staticRows"]]
    assert sha(ROOT / "Source/preserve-exactly-v4.json") == gate["preserveManifestSha256"]

    c1, c2, c3 = [read(EL / f"correction-cycle-00{n}-closure-manifest.json") for n in (1, 2, 3)]
    assert c1["firstPassProgressSha256"] == c2["firstPassProgressSha256"] == gate["firstSemanticProgressSha256"]
    assert c2["previousClosureManifestSha256"] == sha(EL / "correction-cycle-001-closure-manifest.json")
    assert c3["previousClosureManifestSha256"] == sha(EL / "correction-cycle-002-closure-manifest.json")
    for n, cycle in ((1, c1), (2, c2), (3, c3)):
        assert cycle["acceptedUnits"] == 16538
        assert cycle["sourceInventorySha256"] == gate["sourceInventorySha256"]
        assert cycle["sourceStaticSha256"] == gate["sourceStaticSha256"]
        assert cycle["approvedGlossarySha256"] == gate["approvedGlossarySha256"]
        assert sha(EL / f"correction-cycle-00{n}-adjudication.json") == cycle["adjudicationSha256"]
        assert sha(EL / f"correction-cycle-00{n}-applied.json") == cycle["appliedSha256"]
        for component in cycle["components"].values():
            path = pinned(component["path"], component["sha256"])
            if path.suffix == ".txt":
                assert len(path.read_text().splitlines()) == component["count"]
        for name in ("closure", "new", "invalidated", "deltaReview", "retired"):
            component = cycle.get(name)
            if component:
                path = pinned(component["path"], component["sha256"])
                assert len(path.read_text().splitlines()) == component["count"]
    assert c2["review01EvidenceManifestSha256"] == sha(EL / "independent-review-01/evidence-manifest-v3.json")
    assert c3["review02EvidenceManifestSha256"] == sha(EL / "independent-review-02/evidence-manifest-v2.json")
    assert review["closureManifestSha256"] == sha(EL / "correction-cycle-003-closure-manifest.json")
    assert c3["unexplainedMissingIds"] == c3["unexplainedExtraIds"] == 0

    delta = lines(EL / "independent-review-03/decisions.jsonl")
    closure = lines(EL / "correction-cycle-003-closure-review.jsonl")
    reuse = read(EL / "independent-review-03/applicability-proof.json")["reusedCurrentClosureDecisions"]
    assert len(delta) == 138 and len(reuse) == 1566 and len(closure) == 1704
    assert all(r["decision"] == "accepted-current-wording" and
               r["fullSourceAndCurrentTargetRead"] for r in delta)
    assert [r["stableId"] for r in delta] == (EL / "correction-cycle-003-delta-review-ids.txt").read_text().splitlines()
    assert len({r["stableId"] for r in delta} | {r["stableId"] for r in reuse}) == 1704
    mandatory = (EL / "correction-cycle-003-mandatory-regression-ids.txt").read_text().splitlines()
    assert len(mandatory) == len(set(mandatory)) == 1269
    fresh_ids = {r["stableId"] for r in delta}
    reused_ids = {r["stableId"] for r in reuse}
    assert len(set(mandatory) & fresh_ids) == 39
    assert len(set(mandatory) & reused_ids) == 1230
    assert set(mandatory) <= fresh_ids | reused_ids
    assert len((EL / "correction-cycle-003-retired-ids.txt").read_text().splitlines()) == 71

    exact = read(pinned(handoff["preserveExactReport"]["path"], handoff["preserveExactReport"]["sha256"]))
    assert exact["locale"] == "el" and exact["checkedRows"] == 16538
    assert exact["exactResult"] == "passed" and exact["manifestSha256"] == gate["preserveManifestSha256"]
    assert exact["sourceInventorySha256"] == gate["sourceInventorySha256"]
    assert exact["staticInventorySha256"] == gate["sourceStaticSha256"]
    _, current_files = current_text("el")
    assert current_files == handoff["authoredFiles"] == exact["inputFiles"]
    corpus = read(EL / "independent-review-03/corpus.validation.json")
    assert corpus["authoredFiles"] == current_files
    assert corpus["rows"] == 16538 and corpus["structuralResult"] == corpus["exactResult"] == "passed"
    assert corpus["validatorSha256"] == sha(ROOT / "Scripts/validate_locale_corpus.py")
    derived = read(EL / "correction-cycle-003-derived.validation.json")
    assert derived["result"] == "passed" and derived["static"]["rows"] == 178
    assert derived["repeated"]["rows"] == 2831
    for row in derived["orderedMaps"]:
        pinned(row["map"], row["mapSha256"])
        pinned(row["batch"], row["batchSha256"])
    pinned("Translations/el/static-lexicon-001.authored.json", derived["static"]["lexiconSha256"])
    pinned("Translations/el/static-text-draft.json", derived["static"]["draftSha256"])
    pinned("Translations/el/dialogue-repeats-001.authored.json", derived["repeated"]["authoredMapSha256"])
    pinned("Translations/el/dialogue-batch-006.json", derived["repeated"]["batchSha256"])
    consumer = read(EL / "correction-cycle-003-consumers.validation.json")
    assert consumer["result"] == "passed"
    assert gate["consumerCounts"] == {"actualConsumers": 21, "correctedAssemblies": 36,
                                       "citationControls": 90, "itemHintControls": 14}
    assert gate["remainingLimits"] == handoff["remainingLimits"]

    plan = read(HERE / "integration-plan.json")
    assert plan["proposedAcceptanceOutput"] == "Documentation/el-text-acceptance-v1.json"
    assert plan["outputMustNotExistBeforeAcceptance"] is True
    assert not (ROOT / plan["proposedAcceptanceOutput"]).exists()
    for row in plan["currentInputs"]:
        pinned(row["path"], row["sha256"])
    assert plan["authoredFileCount"] == len(handoff["authoredFiles"])
    assert plan["evidenceFileCount"] == len(handoff["evidenceFiles"])
    assert plan["authoredPathHashSetSha256"] == hashlib.sha256(json.dumps(
        handoff["authoredFiles"], ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    assert plan["evidencePathHashSetSha256"] == hashlib.sha256(json.dumps(
        handoff["evidenceFiles"], ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()

    # The original closure builder passed before the four administrative sidecar
    # refreshes. Its exact old sidecar bytes are checked above in the archive.
    # Re-running it against refreshed sidecars would reject administrative pins,
    # although all reviewed text and dependency inputs remain unchanged.
    subprocess.run((sys.executable, str(EL / "verify_cycle3_consumers.py"), "--verify"),
                   cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    return {"result": "passed", "acceptedUnits": 16538, "closure": 1704,
            "fresh": 138, "reused": 1566, "mandatory": 1269,
            "review03InputPins": 1365, "archivedAdministrativePreimages": 4,
            "authoredFiles": len(current_files)}


if __name__ == "__main__":
    print(json.dumps(check()))
