"""Prepare the root's final Filipino handoff after exact independent acceptance."""
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import MANIFEST
from verify_final_inputs import verify


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    path = HERE / name
    assert not path.exists(), path
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    return {"path": str(path.relative_to(ROOT)), "sha256": sha(path)}


def main():
    for name in ("root-review.json", "preserve-exact.json", "root-handoff.json"):
        assert not (HERE / name).exists(), name
    proof = verify(7, 7)
    author_directory = ROOT / "Translations/fil/semantic-correction-cycle-007"
    review_directory = ROOT / "Translations/fil/independent-review-07"
    receipt = json.loads((author_directory / "full-corpus-validation.json").read_bytes())
    assert receipt["locale"] == "fil" and receipt["rows"] == 16538
    assert receipt["structuralResult"] == receipt["exactResult"] == "passed"
    current = {r["path"]: r["sha256"] for r in proof["authoredFiles"]}
    assert current == {r["path"]: r["sha256"] for r in receipt["authoredFiles"]}
    # verify() freshly executes current_text's exact, scope and credits guards.
    # Preserve the original author/reviewer schemas and use a new adapter.
    root_review = write("root-review.json", proof)
    exact = write("preserve-exact.json", {
        "locale": "fil", "exactResult": "passed", "checkedRows": 16538,
        "manifestSha256": sha(MANIFEST),
        "sourceInventorySha256": receipt["sourceInventorySha256"],
        "staticInventorySha256": receipt["staticInventorySha256"],
        "inputFiles": proof["authoredFiles"],
        "boundary": "Fresh current_text exact selected-ID/metadata/grammar/nesting and credits check, reconciled to the fresh complete author corpus receipt; no gameplay or semantic reading.",
        "rootReview": root_review,
        "authorCorpusReceipt": {"path": str((author_directory / "full-corpus-validation.json").relative_to(ROOT)),
                                "sha256": sha(author_directory / "full-corpus-validation.json")},
        "runtime": "not-run"})
    manifest_path = review_directory / "completion-manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    evidence = {}
    external = {r["path"]: r["sha256"] for r in proof["verifiedExternalInputPins"]}

    def include(record):
        relative = record["path"]
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT):
            assert external.get(str(path)) == record["sha256"] and sha(path) == record["sha256"]
            # Root's canonical review and the immutable independent manifest
            # bind these read-only original-game/workflow inputs. The delivery
            # acceptance tool intentionally accepts project paths only.
            return
        assert sha(path) == record["sha256"], relative
        assert relative not in evidence or evidence[relative] == record["sha256"]
        evidence[relative] = record["sha256"]

    for record in manifest["files"] + manifest["currentInputPins"]:
        include(record)
    for record in proof["decisionAncestry"]["evidenceFiles"]:
        include(record)
    for record in (root_review, exact):
        include(record)
    for path in [manifest_path, ROOT / "Translations/fil/semantic-review-progress.json",
                 ROOT / "Translations/fil/credits-role-map.json",
                 HERE / "verify_author_chain.py", HERE / "verify_decision_chain.py",
                 HERE / "verify_final_inputs.py", Path(__file__).resolve()]:
        include({"path": str(path.relative_to(ROOT)), "sha256": sha(path)})
    for record in proof["authoredFiles"]:
        path = (ROOT / record["path"]).with_suffix(".validation.json")
        include({"path": str(path.relative_to(ROOT)), "sha256": sha(path)})
    regression = proof["mandatoryRegression"]
    handoff = {
        "locale": "fil", "acceptedUnits": 16538, "firstSemanticPassUnits": 16538,
        "unresolvedObjectiveFindings": 0, "independentClean": True,
        "independentReviewer": "/root/fil_independent_review_07",
        "currentHashesUnchanged": True, "structural": {"rows": 16538, "result": "passed"},
        "derivedStatic": {"rows": 178, "result": "passed"},
        "mandatoryRegression": {"count": regression["total"], "freshReads": regression["fresh"],
                                "reusedUnchangedIndependentDecisions": regression["reuse"], "result": "passed"},
        "preserveExactReport": exact, "authoredFiles": proof["authoredFiles"],
        "evidenceFiles": [{"path": p, "sha256": h} for p, h in sorted(evidence.items())],
        "remainingLimits": ["Runtime, actual font rendering, wrapping, bidi, layout and installation were not tested per owner instruction.",
                            "Three historical accepted candidate IDs have no compiled consumer; no runtime reachability is inferred.",
                            "Images and textures are excluded. Delivery is a serialized-verified isolated text preview archive without an installer.",
                            "No publication, push or deployment was performed."]}
    record = write("root-handoff.json", handoff)
    print(json.dumps({"locale": "fil", "rootHandoff": record, "rootReview": root_review,
                      "exactReceipt": exact, "evidenceFiles": len(evidence)}))


if __name__ == "__main__":
    main()
