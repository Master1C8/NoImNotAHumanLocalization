"""Independently check immutable cycle-03 lists, pins, and set arithmetic."""
import hashlib
import json
from pathlib import Path

ROOT = Path("/Users/antonkrutov/Desktop/no I'm not a human")
HERE = ROOT / "Translations/sw/semantic-correction-cycle-03"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


manifest_path = HERE / "dependency-closure.json"
manifest = json.loads(manifest_path.read_text())
refs = {name: manifest[name] for name in ("priorClosure", "changedIds", "closureIds", "newIds", "invalidatedIds", "retiredIds", "reviewDelta", "inputs", "adjudication", "boundedRemedialInventory", "boundedRemedialSelector", "appliedBatch", "finalPayload", "structuralValidation", "preserveExact", "assembledConsumerPreflight")}
refs.update({"component:" + name: pin for name, pin in manifest["components"].items()})
refs.update({"source:" + name: pin for name, pin in manifest["sourceAndGlossaryPins"].items()})
for name, pin in refs.items():
    assert sha(ROOT / pin["path"]) == pin["sha256"], name

lists = {}
for name in ("priorClosure", "changedIds", "closureIds", "newIds", "invalidatedIds", "retiredIds", "reviewDelta"):
    records = rows(ROOT / refs[name]["path"])
    ids = [row["stableId"] for row in records]
    assert len(records) == refs[name]["count"] == len(set(ids)), name
    assert [row["sourceIndex"] for row in records] == sorted(row["sourceIndex"] for row in records), name
    lists[name] = set(ids)

prior, changed, closure, new, invalidated, retired, delta = (lists[n] for n in ("priorClosure", "changedIds", "closureIds", "newIds", "invalidatedIds", "retiredIds", "reviewDelta"))
assert new == closure - prior
assert retired == prior - closure == set()
assert delta == changed | new | invalidated
assert changed <= closure and invalidated <= prior & closure
components = {}
for name, pin in manifest["components"].items():
    record = json.loads((ROOT / pin["path"]).read_text())
    ids = record["stableIds"]
    assert record["count"] == pin["count"] == len(ids) == len(set(ids)), name
    components[name] = set(ids)
assert set().union(*components.values()) == closure
for row in rows(ROOT / refs["closureIds"]["path"]):
    assert {name for name in row["components"]} == {name for name, ids in components.items() if row["stableId"] in ids}

current = rows(HERE / "projected-targets.jsonl")
assert len(current) == 16538
by_id = {row["stableId"]: row for row in current}
assert len(by_id) == 16538
for name in ("changedIds", "closureIds", "newIds", "invalidatedIds", "reviewDelta"):
    for row in rows(ROOT / refs[name]["path"]):
        target = by_id[row["stableId"]]
        assert row["sourceIndex"] == target["sourceIndex"] and row["target"] == target["target"] and row["authoredPath"] == target["artifact"], (name, row["stableId"])
adjudication = json.loads((ROOT / refs["adjudication"]["path"]).read_text())
assert {row["stableId"] for row in adjudication["items"]} == changed
assert {row["stableId"] for row in rows(ROOT / refs["reviewDelta"]["path"]) if "corrected" in row["reasons"]} == changed
assert {row["stableId"] for row in rows(ROOT / refs["reviewDelta"]["path"]) if "new-closure-dependency" in row["reasons"]} == new
assert {row["stableId"] for row in rows(ROOT / refs["reviewDelta"]["path"]) if "prior-evidence-invalidated" in row["reasons"]} == invalidated

risk_manifest = json.loads((HERE / "bounded-risk-inventory-manifest-v2.json").read_text())
risk = rows(ROOT / refs["boundedRemedialInventory"]["path"])
assert len(risk) == risk_manifest["boundedUnits"] == 355
for name, spec in risk_manifest["components"].items():
    assert set(spec["stableIds"]) == {row["stableId"] for row in risk if name in row["components"]}, name
assert len(components["bounded-remedial-grammar-and-consumers"]) == 338
assert set(r["stableId"] for r in risk if any(not c.startswith("glasses-") for c in r["components"])) == components["bounded-remedial-grammar-and-consumers"]

verify = {
    "schemaVersion": 1, "cycle": "sw-semantic-correction-03", "selectorRecipeSha256": sha(HERE / "build-review-delta.py"),
    "closureManifestSha256": sha(manifest_path), "acceptedUnits": 16538,
    "priorClosure": len(prior), "currentClosure": len(closure), "changed": len(changed), "new": len(new),
    "explicitlyInvalidated": len(invalidated), "retired": len(retired), "reviewDelta": len(delta),
    "checks": ["all manifest references hash match", "all JSONL sets unique and in canonical source order", "prior/current closure differences exact", "review delta equals corrected union new union explicitly invalidated", "component union equals current closure", "all review rows match pinned final target corpus", "bounded grammar selector component matches immutable inventory predicates"],
    "independentReview": "pending", "editorialAcceptance": "pending", "runtime": "not-run-per-owner"
}
path = HERE / "closure-verification.json"
encoded = (json.dumps(verify, ensure_ascii=False, indent=2) + "\n").encode()
if path.exists():
    assert path.read_bytes() == encoded, "immutable verification differs"
else:
    path.write_bytes(encoded)
print(json.dumps({"verificationSha256": sha(path), **{k: verify[k] for k in ("priorClosure", "currentClosure", "changed", "new", "explicitlyInvalidated", "retired", "reviewDelta")}}))
