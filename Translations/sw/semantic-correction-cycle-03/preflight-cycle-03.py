"""Preflight the selected full-unit Swahili correction batch without applying it.

Wording is read from immutable adjudication.json; this script only transfers,
checks, and serializes it. It writes within this locale's cycle directory.
"""
import collections
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

ROOT = Path("/Users/antonkrutov/Desktop/no I'm not a human")
SW = ROOT / "Translations/sw"
HERE = SW / "semantic-correction-cycle-03"
PRIOR = SW / "semantic-correction-cycle-02"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def write(path, data):
    if path.exists():
        assert path.read_bytes() == data, f"immutable output differs: {path}"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


inputs = json.loads((HERE / "inputs.json").read_text())
adjudication = json.loads((HERE / "adjudication.json").read_text())
selected = {item["stableId"]: item for item in adjudication["items"]}
assert len(selected) == adjudication["acceptedFullUnitCorrections"] == 11
baseline_path = PRIOR / "after-targets.jsonl"
baseline = rows(baseline_path)
assert len(baseline) == 16538
by_sid = {row["stableId"]: row for row in baseline}
assert len(by_sid) == len(baseline)
payload = json.loads((PRIOR / "final-payload-manifest.json").read_text())
assert len(payload["artifacts"]) == 187
source = {}
for path in (ROOT / "Source/localization-inventory-v3/strings.jsonl", ROOT / "Source/localization-inventory-v3/static-text.jsonl"):
    for row in rows(path):
        source[row["stableId"]] = row
for item in selected.values():
    sid = item["stableId"]
    assert item["source"] == source[sid]["source"]
    assert item["beforeTarget"] == by_sid[sid]["target"]
    assert item["authoredPath"] == by_sid[sid]["artifact"]
    assert item["selectedFullTarget"] != item["beforeTarget"]

by_numeric = {int(sid.rsplit(":", 1)[1]): sid for sid in by_sid if sid.startswith("string:")}
changed_artifacts = collections.defaultdict(list)
for item in selected.values():
    changed_artifacts[item["authoredPath"]].append(item)
assert len(changed_artifacts) == 10
candidate_refs = []
for record in payload["artifacts"]:
    path = ROOT / record["artifact"]
    assert sha(path) == record["artifactSha256"]
    assert sha(ROOT / record["sidecar"]) == record["sidecarSha256"]
    if record["artifact"] not in changed_artifacts:
        continue
    batch = json.loads(path.read_text())
    for entry in batch["entries"]:
        sid = entry.get("stableId") or by_numeric.get(entry.get("id"))
        if sid in selected:
            item = selected[sid]
            assert entry["target"] == item["beforeTarget"]
            entry["target"] = item["selectedFullTarget"]
    candidate = HERE / "preflight-artifacts" / path.name
    encoded = (json.dumps(batch, ensure_ascii=False, indent=2) + "\n").encode()
    write(candidate, encoded)
    candidate_refs.append({"authoredPath": record["artifact"], "beforeSha256": record["artifactSha256"], "candidatePath": str(candidate.relative_to(ROOT)), "candidateSha256": sha(candidate), "changedIds": sorted((item["stableId"] for item in changed_artifacts[record["artifact"]]), key=lambda sid: by_sid[sid]["sourceIndex"]), "rowCount": len(batch["entries"])})
assert len(candidate_refs) == 10

# Run the project's ordinary per-batch syntax validator against the candidate
# copies. This checks all rows in each affected batch, not only corrected rows.
for record in candidate_refs:
    path = ROOT / record["candidatePath"]
    proc = subprocess.run([str(ROOT / ".venv/bin/python"), str(ROOT / "Scripts/validate_game_text_batch.py"), str(path)], cwd=ROOT, text=True, capture_output=True)
    assert proc.returncode == 0, (path, proc.stdout, proc.stderr)
    report = json.loads(path.with_suffix(".validation.json").read_text())
    assert report["structuralResult"] == "passed" and report["batchSha256"] == sha(path)
    record["validationPath"] = str(path.with_suffix(".validation.json").relative_to(ROOT))
    record["validationSha256"] = sha(path.with_suffix(".validation.json"))

projected = []
for row in baseline:
    item = selected.get(row["stableId"])
    projected.append(dict(row, target=item["selectedFullTarget"] if item else row["target"]))
assert len(projected) == 16538
assert {row["stableId"] for row in projected if row["target"] != by_sid[row["stableId"]]["target"]} == set(selected)
projected_path = HERE / "projected-targets.jsonl"
write(projected_path, "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in projected).encode())

# Bind every planned line to the actual compiled node/slot, including options
# and control operations. No dynamic placeholder occurs in this correction set.
spec = importlib.util.spec_from_file_location("sw_review_reader_02", SW / "independent-review-02/review_reader.py")
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
key_to_sid = {source[sid].get("key"): sid for sid in by_sid if source[sid].get("collection") == "Dialogs"}
node_names = sorted({node for item in selected.values() for node, *_ in item["compiledConsumers"]})
assert len(node_names) == 11
consumer_rows = []
compared = set()
for node in node_names:
    visible = []
    control = []
    for instruction in reader.nodes[node]:
        args = instruction["operands"]
        if instruction["opcode"] in (2, 4) and args and args[0] in key_to_sid:
            sid = key_to_sid[args[0]]
            current = by_sid[sid]["target"]
            planned = selected[sid]["selectedFullTarget"] if sid in selected else current
            assert reader.targets[sid] == current
            visible.append({"instructionIndex": instruction["index"], "opcode": instruction["opcode"], "stableId": sid, "key": args[0], "source": source[sid]["source"], "currentTarget": current, "plannedTarget": planned, "optionOperands": args[1:] if instruction["opcode"] == 4 else []})
            if sid in selected:
                assert (node, instruction["index"], instruction["opcode"], args[1:]) in [tuple((n, i, op, a)) for n, i, op, a in selected[sid]["compiledConsumers"]]
                compared.add(sid)
        elif instruction["opcode"] in (0, 3, 6, 10, 12, 13, 14, 16):
            control.append({"instructionIndex": instruction["index"], "opcode": instruction["opcode"], "operands": args})
    consumer_rows.append({"node": node, "visible": visible, "control": control})
assert compared == set(selected)
consumer_path = HERE / "assembled-consumer-preflight.jsonl"
write(consumer_path, "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in consumer_rows).encode())

exact = []
for item in adjudication["items"]:
    sid = item["stableId"]
    src = source[sid]["source"]
    old = item["beforeTarget"]
    new = item["selectedFullTarget"]
    spans = source[sid].get("exactSpans", [])
    prefixes = [span["value"] for span in spans if span["reason"] == "Yarn speaker/service prefix"]
    placeholders = [span["value"] for span in spans if span["reason"] == "Runtime placeholder or markup"]
    assert not prefixes or old.startswith(prefixes[0]) and new.startswith(prefixes[0])
    assert all(old.count(token) == new.count(token) == src.count(token) for token in placeholders)
    assert re.findall(r"\d+", src) == re.findall(r"\d+", new)
    assert re.findall(r"\r\n|\r|\n", src) == re.findall(r"\r\n|\r|\n", new)
    assert re.search(r"[ \t\r\n]*$", src).group() == re.search(r"[ \t\n\r]*$", new).group()
    exact.append({"stableId": sid, "sourceIndex": item["sourceIndex"], "speakerPrefix": prefixes, "protectedMarkupAndPlaceholders": placeholders, "numericAndLinebreaks": "equal", "candidateFullTargetSha256": hashlib.sha256(new.encode()).hexdigest()})

manifest = {
    "schemaVersion": 1, "cycle": "sw-semantic-correction-03", "createdAtUtc": inputs["createdAtUtc"],
    "inputsSha256": sha(HERE / "inputs.json"), "adjudicationSha256": sha(HERE / "adjudication.json"),
    "baselineTargetsSha256": sha(baseline_path), "projectedTargetsSha256": sha(projected_path),
    "acceptedUnits": 16538, "changedUnits": 11, "affectedArtifacts": candidate_refs,
    "allOtherArtifactHashes": "verified against cycle-02 final-payload-manifest.json; unchanged",
    "candidateBatchValidators": "passed all 10 affected full batch files",
    "assembledConsumers": {"path": str(consumer_path.relative_to(ROOT)), "sha256": sha(consumer_path), "nodes": len(consumer_rows), "changedVisibleSlots": len(compared)},
    "protectedSyntax": exact,
    "dynamicSubstitution": "none in changed compiled slots; branch/option/control operands retained verbatim",
    "fullCorpusPostApplyGate": "required on actual authored files; preflight validates projected exact IDs and all affected full batches",
}
manifest_path = HERE / "correction-batch-preflight.json"
write(manifest_path, (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode())
print(json.dumps({"changedUnits": 11, "affectedArtifacts": len(candidate_refs), "projectedUnits": len(projected), "assembledNodes": len(consumer_rows), "manifestSha256": sha(manifest_path)}, ensure_ascii=False))
