"""Validate every Swahili authored artifact and the full preserve-exact corpus."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/Users/antonkrutov/Desktop/no I'm not a human")
SW = ROOT / "Translations/sw"
HERE = SW / "semantic-correction-cycle-03"
PRIOR = SW / "semantic-correction-cycle-02"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


checkpoint = json.loads((HERE / "checkpoint.json").read_text())
assert checkpoint["status"] == "applied-validation-pending"
inputs = json.loads((HERE / "inputs.json").read_text())
prior = json.loads((PRIOR / "final-payload-manifest.json").read_text())
applied = json.loads((HERE / "applied-batch-manifest.json").read_text())
expected = {record["artifact"]: record["afterSha256"] for record in applied["artifacts"]}
assert len(prior["artifacts"]) == len(expected) == 187
verified = []
for authored, derived in (("dialogue-repeat-map-001.json", "dialogue-batch-001.json"), ("dialogue-repeat-map-002.json", "dialogue-batch-004.json")):
    cmd = [sys.executable, str(ROOT / "Scripts/expand_exact_text_batch.py"), str(SW / authored), str(SW / derived), "--verify"]
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr[-1000:]
    verified.append({"authoredMap": str((SW / authored).relative_to(ROOT)), "authoredMapSha256": sha(SW / authored), "derivedBatch": str((SW / derived).relative_to(ROOT)), "derivedBatchSha256": sha(SW / derived), "result": "verified"})

artifacts = []
for record in prior["artifacts"]:
    path = ROOT / record["artifact"]
    assert sha(path) == expected[record["artifact"]], record["artifact"]
    script = ROOT / "Scripts" / ("validate_static_text_draft.py" if path.name == "static-text-draft.json" else "validate_game_text_batch.py")
    result = subprocess.run([sys.executable, str(script), str(path)], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print(json.dumps({"failed": record["artifact"], "stdout": result.stdout[-1200:], "stderr": result.stderr[-1200:]}, ensure_ascii=False), flush=True)
        sys.exit(1)
    sidecar = path.with_suffix(".validation.json")
    data = json.loads(sidecar.read_text())
    assert data["structuralResult"] == "passed" and data.get("batchSha256", data.get("draftSha256")) == sha(path)
    artifacts.append({"artifact": record["artifact"], "artifactSha256": sha(path), "sidecar": str(sidecar.relative_to(ROOT)), "sidecarSha256": sha(sidecar), "rows": len(json.loads(path.read_text())["entries"])})
    if len(artifacts) % 25 == 0:
        print(json.dumps({"validated": len(artifacts), "of": 187}), flush=True)
assert len(artifacts) == 187 and sum(row["rows"] for row in artifacts) == 16538

sys.path.insert(0, str(ROOT / "Scripts"))
import preserve_exact

exact_path = HERE / "preserve-exact-validation.json"
assert not exact_path.exists()
preserve_exact.validate("sw", exact_path)
exact = json.loads(exact_path.read_text())
assert exact["checkedRows"] == 16538 and exact["exactResult"] == "passed"
report = {
    "schemaVersion": 1, "cycle": "sw-semantic-correction-03", "createdAtUtc": inputs["createdAtUtc"],
    "validatedArtifacts": 187, "validatedUnits": 16538, "structuralResult": "passed",
    "preserveExactPath": str(exact_path.relative_to(ROOT)), "preserveExactSha256": sha(exact_path), "preserveExactRows": 16538,
    "derivedExpansions": verified,
    "creditsRoleMapSha256": sha(SW / "credits-role-map.json"),
    "creditsRoleMapValidation": "passed through static-text-draft validator",
    "runtime": "not-run-per-owner", "artifacts": artifacts,
}
out = HERE / "structural-validation.json"
assert not out.exists()
out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"validatedArtifacts": 187, "validatedUnits": 16538, "preserveExactRows": 16538, "structuralReportSha256": sha(out), "preserveExactSha256": sha(exact_path)}, ensure_ascii=False), flush=True)
