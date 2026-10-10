"""Build cycle-03 Swahili dependency closure and exact independent-review delta.

This locale-owned recipe preserves applicable prior components, selects the
bounded repaired grammar surface by its documented predicates, and computes
all set differences from immutable canonical-order lists. No wording is made.
"""
import collections
import hashlib
import importlib.util
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path("/Users/antonkrutov/Desktop/no I'm not a human")
SW = ROOT / "Translations/sw"
HERE = SW / "semantic-correction-cycle-03"
PRIOR = SW / "semantic-correction-cycle-02"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def rel(path):
    return str(path.relative_to(ROOT))


def ref(path, count=None):
    out = {"path": rel(path), "sha256": sha(path)}
    if count is not None:
        out["count"] = count
    return out


def write_json(path, obj):
    encoded = (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode()
    if path.exists():
        assert path.read_bytes() == encoded, f"immutable output differs: {path}"
    else:
        path.write_bytes(encoded)


def write_jsonl(path, items):
    encoded = "".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n" for item in items).encode()
    if path.exists():
        assert path.read_bytes() == encoded, f"immutable output differs: {path}"
    else:
        path.write_bytes(encoded)


def norm(text):
    text = unicodedata.normalize("NFKC", text).casefold().replace("ё", "е")
    return "".join(char for char in text if char.isalnum())


inputs = json.loads((HERE / "inputs.json").read_text())
for pin in inputs["pins"].values():
    assert sha(ROOT / pin["path"]) == pin["sha256"], pin["path"]
prior_manifest = json.loads((PRIOR / "dependency-closure-v3.json").read_text())
for manual in prior_manifest["manuals"]:
    assert sha(Path(manual["path"])) == manual["sha256"], manual["path"]
image_plan = prior_manifest["imagePlan"]
assert sha(ROOT / image_plan["scopePath"]) == image_plan["scopeSha256"]
prior_rows = rows(PRIOR / "closure-ids-v3.jsonl")
prior_ids = {row["stableId"] for row in prior_rows}
assert len(prior_rows) == len(prior_ids) == 5948
assert prior_manifest["closureIds"]["sha256"] == sha(PRIOR / "closure-ids-v3.jsonl")

validation_path = HERE / "structural-validation.json"
payload_path = HERE / "final-payload-manifest.json"
assert validation_path.exists() and payload_path.exists()
validation = json.loads(validation_path.read_text())
payload = json.loads(payload_path.read_text())
assert validation["structuralResult"] == "passed" and validation["validatedUnits"] == 16538 and validation["validatedArtifacts"] == 187
assert payload["acceptedUnits"] == 16538 and payload["artifactCount"] == 187
assert json.loads((HERE / "preserve-exact-validation.json").read_text())["exactResult"] == "passed"
for record in validation["artifacts"]:
    assert sha(ROOT / record["artifact"]) == record["artifactSha256"]
    assert sha(ROOT / record["sidecar"]) == record["sidecarSha256"]

baseline = rows(PRIOR / "after-targets.jsonl")
current = rows(HERE / "projected-targets.jsonl")
assert len(baseline) == len(current) == 16538
order = [row["stableId"] for row in current]
rank = {sid: i for i, sid in enumerate(order)}
assert len(rank) == 16538
before = {row["stableId"]: row for row in baseline}
after = {row["stableId"]: row for row in current}
assert all(before[sid]["sourceIndex"] == after[sid]["sourceIndex"] == rank[sid] for sid in order)
adjudication = json.loads((HERE / "adjudication.json").read_text())
changed = {item["stableId"]: item for item in adjudication["items"]}
assert len(changed) == 11
assert set(changed) == {sid for sid in order if before[sid]["target"] != after[sid]["target"]}
assert all(changed[sid]["beforeTarget"] == before[sid]["target"] and changed[sid]["selectedFullTarget"] == after[sid]["target"] for sid in changed)

reviewed = {}
for path in sorted((SW / "semantic-audit-pass-01").glob("reviewed-*.jsonl")):
    for row in rows(path):
        assert row["stableId"] not in reviewed
        reviewed[row["stableId"]] = row
assert set(reviewed) == set(order)
source = {}
for path in (ROOT / "Source/localization-inventory-v3/strings.jsonl", ROOT / "Source/localization-inventory-v3/static-text.jsonl"):
    for row in rows(path):
        source[row["stableId"]] = row
assert all(reviewed[sid]["source"] == source[sid]["source"] for sid in order)

prior_components = {}
for name, pin in prior_manifest["components"].items():
    path = ROOT / pin["path"]
    assert sha(path) == pin["sha256"]
    prior_components[name] = set(json.loads(path.read_text())["stableIds"])
assert set().union(*prior_components.values()) == prior_ids

node_to_ids = collections.defaultdict(set)
for sid in order:
    row = reviewed[sid]
    for node in row.get("nodeNames", []):
        node_to_ids[(row["collection"], node)].add(sid)
current_context = set()
for sid in changed:
    row = reviewed[sid]
    for node in row.get("nodeNames", []):
        current_context.update(node_to_ids[(row["collection"], node)])
    if not row.get("nodeNames"):
        for pos in range(max(0, rank[sid] - 2), min(len(order), rank[sid] + 3)):
            neighbor = order[pos]
            if reviewed[neighbor]["collection"] == row["collection"]:
                current_context.add(neighbor)

old_new_targets = {before[sid]["target"] for sid in changed} | {after[sid]["target"] for sid in changed}
source_forms = {norm(source[sid]["source"]) for sid in changed}
repetitions = {sid for sid in order if norm(source[sid]["source"]) in source_forms or before[sid]["target"] in old_new_targets or after[sid]["target"] in old_new_targets}
risk_path = HERE / "bounded-risk-inventory-v2.jsonl"
risk_manifest_path = HERE / "bounded-risk-inventory-manifest-v2.json"
risk_manifest = json.loads(risk_manifest_path.read_text())
assert risk_manifest["inventorySha256"] == sha(risk_path) and risk_manifest["boundedUnits"] == 355
risk_rows = rows(risk_path)
all_read_risk = {row["stableId"] for row in risk_rows}
assert len(all_read_risk) == len(risk_rows) == 355
for row in risk_rows:
    sid = row["stableId"]
    assert row["sourceIndex"] == rank[sid] and row["source"] == source[sid]["source"] and row["target"] == before[sid]["target"]
# Glasses agreement was an adjudicated false positive: class-4 miwani takes
# i- agreement. Its extra 17 support rows stay in the read ledger but do not
# become new correction dependencies solely because they were inspected.
risk = {row["stableId"] for row in risk_rows if any(not name.startswith("glasses-") for name in row["components"])}
assert len(risk) == 338

components = {
    "changed": set(changed),
    "prior-correction-dependencies": prior_components["changed"] | prior_components["prior-correction-dependencies"],
    "containing-context": prior_components["containing-context"] | current_context,
    "exact-and-spelling-repetitions": prior_components["exact-and-spelling-repetitions"] | repetitions,
    "glossary-referents": prior_components["glossary-referents"] | {sid for row in risk_rows for sid in [row["stableId"]] if any(name in row["components"] for name in ("armpit-source-inflections", "armpit-target-nouns", "eye-open-agreement", "hands-wash-agreement", "finger-pointing-gesture", "examiner-pronouns"))},
    "runtime-binding-and-layout": prior_components["runtime-binding-and-layout"],
    "mandatory-regressions": prior_components["mandatory-regressions"],
    "bounded-remedial-grammar-and-consumers": risk,
}
closure = set().union(*components.values())
assert prior_ids <= closure, "applicable prior dependency retired unexpectedly"
new = closure - prior_ids
retired = prior_ids - closure
assert not retired

# Explicitly invalidate only previously reviewed rows within two visible
# instruction slots of a changed full unit in an actual compiled consumer.
spec = importlib.util.spec_from_file_location("sw_review_reader_02", SW / "independent-review-02/review_reader.py")
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
key_to_sid = {reviewed[sid].get("key"): sid for sid in order if reviewed[sid]["collection"] == "Dialogs"}
invalidated_by = collections.defaultdict(list)
for node, instructions in reader.nodes.items():
    visible = []
    for ins in instructions:
        args = ins["operands"]
        if ins["opcode"] in (2, 4) and args:
            visible.append((key_to_sid.get(args[0]), ins["index"]))
    for position, (sid, instruction_index) in enumerate(visible):
        if sid not in changed:
            continue
        for neighbor_sid, neighbor_index in visible[max(0, position - 2):min(len(visible), position + 3)]:
            if neighbor_sid in prior_ids - set(changed):
                invalidated_by[neighbor_sid].append({"correctedStableId": sid, "node": node, "correctedInstructionIndex": instruction_index, "neighborInstructionIndex": neighbor_index, "reason": "previous contextual judgment shares a compiled visible exchange within two instruction slots of corrected wording"})
for reasons in invalidated_by.values():
    reasons.sort(key=lambda item: (rank[item["correctedStableId"]], item["node"], item["correctedInstructionIndex"]))
invalidated = set(invalidated_by)
delta = set(changed) | new | invalidated
assert delta <= closure


def base_row(sid):
    r = reviewed[sid]
    return {"sourceIndex": rank[sid], "stableId": sid, "collection": r["collection"], "key": r.get("key"), "nodeNames": r.get("nodeNames", []), "source": source[sid]["source"], "target": after[sid]["target"], "previousTarget": before[sid]["target"], "authoredPath": after[sid]["artifact"]}


changed_rows = [dict(base_row(sid), findingId=changed[sid]["findingId"]) for sid in order if sid in changed]
write_jsonl(HERE / "changed-ids.jsonl", changed_rows)
component_refs = {}
for name, members in components.items():
    ids = [sid for sid in order if sid in members]
    path = HERE / ("component-" + name + ".json")
    write_json(path, {"schemaVersion": 1, "cycle": "sw-semantic-correction-03", "component": name, "count": len(ids), "stableIds": ids})
    component_refs[name] = ref(path, len(ids))
write_jsonl(HERE / "closure-ids.jsonl", [dict(base_row(sid), components=[name for name, members in components.items() if sid in members]) for sid in order if sid in closure])
write_jsonl(HERE / "new-ids.jsonl", [base_row(sid) for sid in order if sid in new])
write_jsonl(HERE / "retired-ids.jsonl", [base_row(sid) for sid in order if sid in retired])
write_jsonl(HERE / "invalidated-ids.jsonl", [dict(base_row(sid), invalidatedBy=invalidated_by[sid]) for sid in order if sid in invalidated])
write_jsonl(HERE / "review-delta.jsonl", [dict(base_row(sid), reasons=(["corrected"] if sid in changed else []) + (["new-closure-dependency"] if sid in new else []) + (["prior-evidence-invalidated"] if sid in invalidated else []), components=[name for name, members in components.items() if sid in members]) for sid in order if sid in delta])

manifest = {
    "schemaVersion": 1, "cycle": "sw-semantic-correction-03", "createdAtUtc": inputs["createdAtUtc"],
    "locale": "sw", "gameVersion": "1.3.19", "acceptedUnits": 16538,
    "priorClosure": ref(PRIOR / "closure-ids-v3.jsonl", len(prior_ids)),
    "changedIds": ref(HERE / "changed-ids.jsonl", len(changed)),
    "closureIds": ref(HERE / "closure-ids.jsonl", len(closure)),
    "newIds": ref(HERE / "new-ids.jsonl", len(new)),
    "invalidatedIds": ref(HERE / "invalidated-ids.jsonl", len(invalidated)),
    "retiredIds": ref(HERE / "retired-ids.jsonl", len(retired)),
    "reviewDelta": ref(HERE / "review-delta.jsonl", len(delta)),
    "components": component_refs,
    "inputs": ref(HERE / "inputs.json"), "adjudication": ref(HERE / "adjudication.json"),
    "boundedRemedialInventory": ref(risk_path, len(all_read_risk)), "boundedRemedialSelector": ref(HERE / "enumerate-remedial-surface-v2.py"),
    "applicableRemedialDependencyUnits": len(risk), "glassesOnlyContextReadAndRetiredAsFalsePositive": len(all_read_risk - risk),
    "appliedBatch": ref(HERE / "applied-batch-manifest.json"),
    "finalPayload": ref(payload_path), "structuralValidation": ref(validation_path), "preserveExact": ref(HERE / "preserve-exact-validation.json"),
    "assembledConsumerPreflight": ref(HERE / "assembled-consumer-preflight.jsonl"),
    "sourceAndGlossaryPins": prior_manifest["sourceAndGlossaryPins"],
    "manuals": prior_manifest["manuals"], "imagePlan": prior_manifest["imagePlan"],
    "compiledProgramSha256": reader.program_hash,
    "selectorRepair": "Cycle-02 supplementary reviewer findings for FunnyGuy and Fairytaller are selected by corrected compiled nodes; all accepted armpit source inflections and target noun uses, related noun agreement and immediate actual consumer neighbors are selected by the locale-owned bounded-risk recipe. Prior applicable dependency components remain included; no manual stable-ID additions.",
    "newlineConvention": "UTF-8 JSONL with LF separators and final LF when nonempty; zero-row retired file is empty",
    "independentReview": "pending cycle-03 delta", "editorialAcceptance": "pending", "runtime": "not-run-per-owner",
}
path = HERE / "dependency-closure.json"
write_json(path, manifest)
print(json.dumps({"changed": len(changed), "closure": len(closure), "new": len(new), "invalidated": len(invalidated), "retired": len(retired), "reviewDelta": len(delta), "manifestSha256": sha(path)}, ensure_ascii=False))
