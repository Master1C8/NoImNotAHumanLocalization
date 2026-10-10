"""Apply the preflighted cycle-03 full-unit batch with exact-state guards."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path("/Users/antonkrutov/Desktop/no I'm not a human")
HERE = ROOT / "Translations/sw/semantic-correction-cycle-03"
PRIOR = ROOT / "Translations/sw/semantic-correction-cycle-02"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def immutable(path, obj):
    encoded = (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode()
    if path.exists():
        assert path.read_bytes() == encoded, f"immutable evidence differs: {path}"
    else:
        path.write_bytes(encoded)


preflight_path = HERE / "correction-batch-preflight.json"
preflight = json.loads(preflight_path.read_text())
assert preflight["changedUnits"] == 11 and len(preflight["affectedArtifacts"]) == 10
assert preflight["adjudicationSha256"] == sha(HERE / "adjudication.json")
baseline = rows(PRIOR / "after-targets.jsonl")
projected = rows(HERE / "projected-targets.jsonl")
assert len(baseline) == len(projected) == 16538
assert preflight["baselineTargetsSha256"] == sha(PRIOR / "after-targets.jsonl")
assert preflight["projectedTargetsSha256"] == sha(HERE / "projected-targets.jsonl")
prior_manifest = json.loads((PRIOR / "final-payload-manifest.json").read_text())
by_path = {record["artifact"]: record for record in prior_manifest["artifacts"]}
changed = {record["authoredPath"]: record for record in preflight["affectedArtifacts"]}
assert len(by_path) == 187 and len(changed) == 10
for path, record in by_path.items():
    current = sha(ROOT / path)
    if path in changed:
        assert current in (record["artifactSha256"], changed[path]["candidateSha256"]), f"ambiguous authored state: {path}"
    else:
        assert current == record["artifactSha256"], f"unrelated artifact drift: {path}"
for record in changed.values():
    assert record["beforeSha256"] == by_path[record["authoredPath"]]["artifactSha256"]
    assert sha(ROOT / record["candidatePath"]) == record["candidateSha256"]
    assert sha(ROOT / record["validationPath"]) == record["validationSha256"]

intent = {
    "schemaVersion": 1, "cycle": "sw-semantic-correction-03",
    "inputsSha256": sha(HERE / "inputs.json"),
    "preflightSha256": sha(preflight_path),
    "baselineTargetsSha256": sha(PRIOR / "after-targets.jsonl"),
    "projectedTargetsSha256": sha(HERE / "projected-targets.jsonl"),
    "affectedArtifacts": preflight["affectedArtifacts"],
    "commitBoundary": "Per-file atomic replace only; multi-file batch is not a transaction. Resume accepts exact before or candidate hash per file and requires complete projected corpus equality before success.",
}
intent_path = HERE / "apply-intent.json"
immutable(intent_path, intent)
for record in preflight["affectedArtifacts"]:
    path = ROOT / record["authoredPath"]
    current = sha(path)
    if current == record["candidateSha256"]:
        continue
    assert current == record["beforeSha256"]
    temporary = path.with_name(path.name + ".cycle03.tmp")
    assert not temporary.exists()
    temporary.write_bytes((ROOT / record["candidatePath"]).read_bytes())
    assert sha(temporary) == record["candidateSha256"]
    os.replace(temporary, path)
    assert sha(path) == record["candidateSha256"]

by_number = {int(row["stableId"].rsplit(":", 1)[1]): row["stableId"] for row in baseline if row["stableId"].startswith("string:")}
actual = {}
for record in prior_manifest["artifacts"]:
    path = ROOT / record["artifact"]
    expected = changed[record["artifact"]]["candidateSha256"] if record["artifact"] in changed else record["artifactSha256"]
    assert sha(path) == expected
    batch = json.loads(path.read_text())
    for entry in batch["entries"]:
        sid = entry.get("stableId") or by_number[entry["id"]]
        assert sid not in actual
        actual[sid] = entry["target"]
assert len(actual) == 16538
for row in projected:
    assert actual[row["stableId"]] == row["target"], row["stableId"]
changed_ids = [after["stableId"] for before, after in zip(baseline, projected) if before["target"] != after["target"]]
assert len(changed_ids) == 11
manifest = {
    "schemaVersion": 1, "cycle": "sw-semantic-correction-03",
    "applyIntentSha256": sha(intent_path),
    "acceptedUnits": 16538, "changedIds": 11, "changedArtifactCount": 10,
    "changedStableIdsInCanonicalOrder": changed_ids,
    "beforeTargetsSha256": sha(PRIOR / "after-targets.jsonl"),
    "afterTargetsSha256": sha(HERE / "projected-targets.jsonl"),
    "allOtherArtifactsByteIdentical": True,
    "artifacts": [dict(record, afterSha256=(changed[record["artifact"]]["candidateSha256"] if record["artifact"] in changed else record["artifactSha256"]), changed=(record["artifact"] in changed)) for record in prior_manifest["artifacts"]],
    "derivedMapsAndStaticCredits": "no corrected ID belongs to an authored repeat map, derived expansion batch, or static credits artifact; verify unchanged exact hashes in final gate",
}
path = HERE / "applied-batch-manifest.json"
immutable(path, manifest)
print(json.dumps({"changedIds": len(changed_ids), "changedArtifacts": len(changed), "acceptedUnits": len(actual), "manifestSha256": sha(path)}, ensure_ascii=False))
