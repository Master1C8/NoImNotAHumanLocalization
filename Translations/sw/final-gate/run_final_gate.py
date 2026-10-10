"""Reproduce the Swahili offline final gate without changing reviewed inputs."""
import contextlib
import hashlib
import io
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/antonkrutov/Desktop/no I'm not a human")
SW = ROOT / "Translations/sw"
HERE = SW / "final-gate"
SCRIPTS = ROOT / "Scripts"
sys.path.insert(0, str(SCRIPTS))
import validate_game_text_batch
import validate_static_text_draft
import preserve_exact


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def ref(path):
    return {"path": str(path.relative_to(ROOT)), "sha256": sha(path)}


def checked(ref_record):
    path = Path(ref_record["path"])
    if not path.is_absolute():
        path = ROOT / path
    assert path.exists() and sha(path) == ref_record["sha256"], path
    return path


def write_once(path, data):
    encoded = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode()
    if path.exists():
        assert path.read_bytes() == encoded, f"immutable output differs: {path}"
    else:
        path.write_bytes(encoded)


review_dir = SW / "independent-review-03"
cycle = SW / "semantic-correction-cycle-03"
first_progress = load(SW / "semantic-review-progress.json")
assert first_progress["acceptedUnits"] == first_progress["reviewedUnits"] == 16538
assert first_progress["nextSourceIndex"] == 16538 and first_progress["nextId"] is None
assert first_progress["objectiveFindings"] == 211 and first_progress["affectedFindingUnits"] == 267
source_inventory = ROOT / "Source/localization-inventory-v3/strings.jsonl"
static_inventory = ROOT / "Source/localization-inventory-v3/static-text.jsonl"
assert sha(source_inventory) == first_progress["sourceInventorySha256"]
assert sha(static_inventory) == first_progress["staticInventorySha256"]
assert sha(ROOT / "Documentation/glossary-translations/sw/layer.json") == first_progress["approvedGlossarySha256"]
assert sha(ROOT / "Source/preserve-exactly-v4.json") == first_progress["preserveExactlySha256"]
accepted = load(ROOT / "Documentation/text-source-acceptance-v1.json")
assert (accepted["selectedStringRows"], accepted["selectedSupplementalStaticRows"], accepted["selectedTotalRows"]) == (16360, 178, 16538)
assert (accepted["sourceStringsSha256"], accepted["sourceStaticSha256"]) == (sha(source_inventory), sha(static_inventory))
for record in accepted["evidence"].values():
    checked(record)

source_records = lines(source_inventory)
static_records = lines(static_inventory)
source_by_id = {r["stableId"]: r["source"] for r in source_records + static_records}
first_ids = []
first_evidence = []
next_index = 0
for segment in first_progress["reviewedEvidence"]:
    path = checked({"path": segment["path"], "sha256": segment["sha256"]})
    checked({"path": segment["findingsPath"], "sha256": segment["findingsSha256"]})
    rows = lines(path)
    start, end = segment["sourceIndices"]
    assert start == next_index and end - start + 1 == len(rows)
    for row in rows:
        assert row["sourceIndex"] == next_index and row["source"] == source_by_id[row["stableId"]]
        assert row["sourceSha256"] == text_sha(row["source"])
        assert row["reviewDecision"].startswith(("read-", "objective-finding-"))
        first_ids.append(row["stableId"])
        next_index += 1
    first_evidence.append(ref(path))
assert next_index == len(first_ids) == len(set(first_ids)) == 16538
assert sha(SW / "semantic-review-progress.json") == load(cycle / "inputs.json")["pins"]["semantic-review-progress.json"]["sha256"]

# Reconcile the immutable correction/review chain. Historical artifact hashes
# are tied to their historical payload, never imposed on current files.
for number in (1, 2, 3):
    payload = load(SW / f"semantic-correction-cycle-{number:02d}/final-payload-manifest.json")
    assert payload["acceptedUnits"] == 16538 and payload["artifactCount"] == 187
for number in (2, 3):
    folder = SW / f"semantic-correction-cycle-{number:02d}"
    payload = load(folder / "final-payload-manifest.json")
    previous = SW / f"semantic-correction-cycle-{number-1:02d}/final-payload-manifest.json"
    assert payload["priorPayloadSha256"] == sha(previous)
    for pin in load(folder / "inputs.json")["pins"].values():
        if "path" not in pin or "sha256" not in pin:
            continue
        if pin["path"] == "Translations/sw/correction-progress.json" and number == 2:
            assert sha(folder / "prior-correction-progress-snapshot.json") == pin["sha256"]
        else:
            checked(pin)

for number in (1, 2, 3):
    folder = SW / f"independent-review-{number:02d}"
    manifest = load(folder / f"evidence-manifest-{number:02d}.json")
    for item in manifest["files"]:
        path = checked(item)
        assert path.stat().st_size == item["bytes"]
review_manifest = load(review_dir / "evidence-manifest-03.json")
findings = load(review_dir / "final-findings-03.json")
assert review_manifest["verdict"] == findings["verdict"] == "clean"
assert findings["findings"] == [] and findings["fullUnitFindingCount"] == 0 and findings["deltaUnits"] == 69
assert findings["payloadManifestSha256"] == sha(cycle / "final-payload-manifest.json")
assert findings["closureManifestSha256"] == sha(cycle / "dependency-closure.json")
assert findings["reviewDeltaSha256"] == sha(cycle / "review-delta.jsonl")
assert load(review_dir / "read-evidence-03.json")["deltaUnitsRead"] == 69
assert load(review_dir / "final-unchanged-hash-verification-03.json")["badPaths"] == []
review_refs = load(review_dir / "input-verification-03.json")["hashChecks"]
for item in review_refs:
    checked(item)
assert len(review_refs) == 589

closure = load(cycle / "dependency-closure.json")
for name in ("priorClosure", "changedIds", "closureIds", "newIds", "invalidatedIds", "retiredIds", "reviewDelta", "inputs", "adjudication", "boundedRemedialInventory", "boundedRemedialSelector", "appliedBatch", "finalPayload", "structuralValidation", "preserveExact", "assembledConsumerPreflight"):
    checked(closure[name])
for group in ("components", "sourceAndGlossaryPins"):
    for pin in closure[group].values():
        checked(pin)
verification = load(cycle / "closure-verification.json")
assert (verification["priorClosure"], verification["currentClosure"], verification["changed"], verification["new"], verification["explicitlyInvalidated"], verification["retired"], verification["reviewDelta"]) == (5948, 6004, 11, 56, 4, 0, 69)
assert verification["closureManifestSha256"] == sha(cycle / "dependency-closure.json")

payload = load(cycle / "final-payload-manifest.json")
assert len(payload["artifacts"]) == 187
authored = []
sidecars = []
actual = {}
guids = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1", "UI": "0cbd8a7a4f543344bb95659de87f67a5", "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}
collections = Counter()
for item in payload["artifacts"]:
    path = checked({"path": item["artifact"], "sha256": item["artifactSha256"]})
    sidecar = checked({"path": item["sidecar"], "sha256": item["sidecarSha256"]})
    batch = load(path)
    assert batch["locale"] == "sw" and len(batch["entries"]) == item["rows"]
    for entry in batch["entries"]:
        sid = entry.get("stableId") or f"string:{guids[batch['collection']]}:{entry['id']}"
        assert sid not in actual
        actual[sid] = entry["target"]
        collections[batch.get("collection", "SupplementalStatic")] += 1
    authored.append(ref(path))
    sidecars.append(ref(sidecar))
assert len(actual) == 16538 and set(actual) == set(first_ids)
assert collections == {"Dialogs": 16100, "UI": 259, "ChecksDialogs": 1, "SupplementalStatic": 178}

# Exercise owning validators while checking the exact bytes each proposes to
# write. The reviewed sidecars stay byte-for-byte unchanged.
original_write = Path.write_text
original_open = Path.open
original_loads = json.loads
def cached_open(self, *args, **kwargs):
    if not args and not kwargs and self == source_inventory:
        return iter(("source", index) for index in range(len(source_records)))
    if not args and not kwargs and self == static_inventory:
        return iter(("static", index) for index in range(len(static_records)))
    return original_open(self, *args, **kwargs)
def cached_loads(value, *args, **kwargs):
    if isinstance(value, tuple) and len(value) == 2 and value[0] in ("source", "static"):
        return (source_records if value[0] == "source" else static_records)[value[1]]
    return original_loads(value, *args, **kwargs)
Path.open = cached_open
json.loads = cached_loads
validated = 0
try:
    for item in payload["artifacts"]:
        path = ROOT / item["artifact"]
        expected_sidecar = ROOT / item["sidecar"]
        writes = []
        def guarded_write(self, data, *args, **kwargs):
            assert self.resolve() == expected_sidecar.resolve(), self
            assert data.encode(kwargs.get("encoding") or "utf-8") == expected_sidecar.read_bytes(), self
            writes.append(str(self))
            return len(data)
        Path.write_text = guarded_write
        old_argv = sys.argv
        try:
            sys.argv = ["owning-validator", str(path)]
            with contextlib.redirect_stdout(io.StringIO()):
                (validate_static_text_draft if path.name == "static-text-draft.json" else validate_game_text_batch).main()
        finally:
            Path.write_text = original_write
            sys.argv = old_argv
        assert len(writes) == 1 and sha(expected_sidecar) == item["sidecarSha256"]
        validated += 1
        if validated % 25 == 0:
            print(json.dumps({"validated": validated, "of": 187}), flush=True)
finally:
    Path.open = original_open
    json.loads = original_loads
assert validated == 187

static_path = SW / "static-text-draft.json"
static = load(static_path)
assert len(static["entries"]) == 178
assert len({row["stableId"] for row in static["entries"]}) == 178
credits = load(SW / "credits-role-map.json")
assert credits["stableId"] == "tmp:level5:59:m_text"
for authored_name, derived_name in (("dialogue-repeat-map-001.json", "dialogue-batch-001.json"), ("dialogue-repeat-map-002.json", "dialogue-batch-004.json")):
    result = subprocess.run([sys.executable, str(SCRIPTS / "expand_exact_text_batch.py"), str(SW / authored_name), str(SW / derived_name), "--verify"], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

# The parser-derived contract validates current authored values, exact accepted
# coverage and every protected value. It writes only this new immutable report.
exact_path = HERE / "preserve-exact-report.json"
if exact_path.exists():
    assert sha(exact_path) == sha(review_dir / "preserve-exact-current-03.json")
else:
    preserve_exact.validate("sw", exact_path)
assert sha(exact_path) == sha(review_dir / "preserve-exact-current-03.json")
exact = load(exact_path)
assert exact["checkedRows"] == 16538 and exact["exactResult"] == "passed"

# Regression decisions are checked per category/ID against current source and
# target hashes, with prior independent reuse only where those hashes agree.
catalog_path = SW / "semantic-correction-cycle-01/mandatory-regression-catalog-v2.json"
catalog = load(catalog_path)
result = load(review_dir / "mandatory-regression-result-03.json")
decisions = lines(review_dir / "mandatory-regression-reviewed-03.jsonl")
prior_decisions = {(r["category"], r["stableId"]): r for r in lines(SW / "independent-review-02/mandatory-regression-reviewed-02.jsonl")}
decisions_by_key = {(r["category"], r["stableId"]): r for r in decisions}
fresh_review = {r["stableId"] for r in lines(review_dir / "final-reviewed-rows-03.jsonl")}
assert len(decisions_by_key) == len(decisions) and len(fresh_review) == 69
category_counts = []
regression_ids = set()
fresh_ids = set()
reused_ids = set()
for name, pin in catalog["categories"].items():
    ids = load(checked(pin))["stableIds"]
    category = next(r for r in result["categories"] if r["category"] == name)
    assert len(ids) == category["count"] and category["sha256"] == pin["sha256"]
    fresh = reused = 0
    for sid in ids:
        regression_ids.add(sid)
        d = decisions_by_key[(name, sid)]
        assert d["findingId"] is None and d["sourceSha256"] == text_sha(source_by_id[sid]) and d["targetSha256"] == text_sha(actual[sid])
        if d["reviewMode"].startswith("fresh"):
            assert sid in fresh_review
            fresh_ids.add(sid)
            fresh += 1
        else:
            prior = prior_decisions[(name, sid)]
            assert prior["findingId"] is None and prior["sourceSha256"] == d["sourceSha256"] and prior["targetSha256"] == d["targetSha256"]
            reused_ids.add(sid)
            reused += 1
    assert (fresh, reused) == (category["freshDeltaRead"], category["exactPriorIndependentReuse"])
    category_counts.append({"category": name, "count": len(ids), "fresh": fresh, "reused": reused})
assert len(regression_ids) == result["uniqueIdsCovered"] == 1592 and result["missingIds"] == []
assert len(fresh_ids) == 1 and len(reused_ids) == 1591 and not fresh_ids & reused_ids

integration = []
for path in sorted(SW.rglob("*")):
    if path.is_file() and not path.is_relative_to(HERE) and "__pycache__" not in path.parts:
        integration.append(ref(path))
integration_manifest = {"schemaVersion": 1, "locale": "sw", "scope": "existing locale-owned files before new final-gate outputs", "files": integration}
write_once(HERE / "proposed-integration-paths.json", integration_manifest)

evidence_names = [
    SW / "semantic-review-progress.json",
    SW / "semantic-correction-cycle-01/final-payload-manifest.json",
    SW / "semantic-correction-cycle-02/final-payload-manifest.json",
    cycle / "final-payload-manifest.json",
    cycle / "dependency-closure.json",
    cycle / "closure-verification.json",
    cycle / "review-delta.jsonl",
    review_dir / "evidence-manifest-03.json",
    review_dir / "final-report-03.md",
    review_dir / "final-findings-03.json",
    review_dir / "input-verification-03.json",
    review_dir / "mandatory-regression-result-03.json",
    review_dir / "mandatory-regression-reviewed-03.jsonl",
    review_dir / "unchanged-closure-reused-03.jsonl",
    ROOT / "Documentation/text-source-acceptance-v1.json",
    source_inventory, static_inventory,
    ROOT / "Documentation/glossary-research/review-candidate-v2/glossary.json",
    ROOT / "Documentation/glossary-translations/sw/layer.json",
    ROOT / "Source/preserve-exactly-v4.json",
    HERE / "proposed-integration-paths.json",
    exact_path,
]
evidence = [ref(path) for path in evidence_names]
receipt = {
    "schemaVersion": 1, "locale": "sw", "gameVersion": "1.3.19", "reviewCutoffUtc": review_manifest["createdAtUtc"],
    "acceptedUnits": 16538, "firstSemanticPassUnits": 16538,
    "firstPassEvidenceSegments": len(first_evidence), "firstPassFindings": 211,
    "correctionChain": {"cycles": 3, "appliedLastCycleUnits": 11, "finalPayloadSha256": sha(cycle / "final-payload-manifest.json"), "closureSha256": sha(cycle / "dependency-closure.json")},
    "independentClean": True, "independentReviewer": review_manifest["reviewer"], "unresolvedObjectiveFindings": 0,
    "reviewedDeltaUnits": 69, "unchangedIndependentClosureDecisions": 5935,
    "currentHashesUnchanged": True, "reviewInputReferencesChecked": len(review_refs),
    "mandatoryRegression": {"count": 1592, "freshReads": 1, "reusedUnchangedIndependentDecisions": 1591, "result": "passed", "categories": category_counts},
    "structural": {"authoredFiles": 187, "rows": 16538, "validatorsRun": 187, "sidecarBytesUnchanged": True, "acceptedIdCoverage": "exact", "collections": dict(collections), "result": "passed"},
    "derivedStatic": {"rows": 178, "creditsRoleMapSha256": sha(SW / "credits-role-map.json"), "repeatMapExpansionsVerified": 2, "result": "passed"},
    "preserveExactReport": ref(exact_path), "preserveExact": {"rows": 16538, "result": "passed"},
    "authorProgressDocumentChanged": False, "reviewEvidenceChanged": False,
    "evidenceFiles": evidence,
    "integrationPathManifest": ref(HERE / "proposed-integration-paths.json"),
    "runtime": "not-run-per-owner", "build": "not-run-per-owner", "visual": "not-run-per-owner", "gitIntegration": "pending-root-coordinator",
}
write_once(HERE / "full-gate-receipt.json", receipt)
handoff = {
    "schemaVersion": 1, "locale": "sw", "gameVersion": "1.3.19", "acceptedUnits": 16538,
    "firstSemanticPassUnits": 16538, "unresolvedObjectiveFindings": 0,
    "independentClean": True, "independentReviewer": review_manifest["reviewer"],
    "currentHashesUnchanged": True,
    "mandatoryRegression": {"count": 1592, "freshReads": 1, "reusedUnchangedIndependentDecisions": 1591, "result": "passed"},
    "structural": {"rows": 16538, "result": "passed"},
    "derivedStatic": {"rows": 178, "result": "passed"},
    "preserveExactReport": ref(exact_path), "authoredFiles": authored,
    "evidenceFiles": evidence + [ref(HERE / "run_final_gate.py"), ref(HERE / "full-gate-receipt.json")],
    "proposedIntegrationPaths": ref(HERE / "proposed-integration-paths.json"),
    "sidecarFiles": sidecars,
    "limits": ["text-only offline gate", "game/runtime/visual QA not run per owner", "build/install/package not run per owner", "Git stage/commit/integration pending root coordinator"],
}
write_once(HERE / "root-handoff.json", handoff)
print(json.dumps({"authoredFiles": len(authored), "acceptedUnits": len(actual), "regressionIds": len(regression_ids), "independentClean": True, "gateReceiptSha256": sha(HERE / "full-gate-receipt.json"), "rootHandoffSha256": sha(HERE / "root-handoff.json")}, ensure_ascii=False))
