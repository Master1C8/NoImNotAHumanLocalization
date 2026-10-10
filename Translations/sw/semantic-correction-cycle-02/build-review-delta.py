"""Reproduce the Swahili cycle-02 dependency closure and independent-review delta.

This is a locale-owned evidence recipe. It reads pinned source and prior review
evidence, never writes authored text, and refuses to overwrite immutable output.
"""
import collections
import datetime
import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path("/Users/antonkrutov/Desktop/no I'm not a human")
LOCALE = ROOT / "Translations/sw"
HERE = LOCALE / "semantic-correction-cycle-02"
PRIOR = LOCALE / "semantic-correction-cycle-01"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def write_json(path, obj):
    content = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        require(path.read_text() == content, f"immutable output differs: {path}")
    else:
        path.write_text(content)


def write_jsonl(path, items):
    content = "".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n" for item in items)
    if path.exists():
        require(path.read_text() == content, f"immutable output differs: {path}")
    else:
        path.write_text(content)


def rel(path):
    return str(path.relative_to(ROOT))


def ref(path, count=None):
    result = {"path": rel(path), "sha256": sha(path)}
    if count is not None:
        result["count"] = count
    return result


def norm(text):
    text = unicodedata.normalize("NFKC", text).casefold().replace("ё", "е")
    return "".join(char for char in text if char.isalnum())


inputs = json.loads((HERE / "inputs.json").read_text())
for name, pin in inputs["pins"].items():
    if name == "priorCorrectionProgress":
        continue  # mutable current summary; its original SHA remains in inputs.json
    if name == "sourceAndGlossary":
        for item in pin.values():
            require(sha(ROOT / item["path"]) == item["sha256"], "input drift: " + item["path"])
    else:
        require(sha(ROOT / pin["path"]) == pin["sha256"], "input drift: " + pin["path"])

validation_path = HERE / "structural-validation.json"
require(validation_path.exists(), "complete structural validation required")
validation = json.loads(validation_path.read_text())
require(validation["validatedUnits"] == 16538 and validation["validatedArtifacts"] == 187, "validation counts")
require(validation["structuralResult"] == "passed", "structural result")
for artifact in validation["artifacts"]:
    require(sha(ROOT / artifact["artifact"]) == artifact["artifactSha256"], "authored artifact drift: " + artifact["artifact"])
    require(sha(ROOT / artifact["sidecar"]) == artifact["sidecarSha256"], "validation sidecar drift: " + artifact["sidecar"])
exact_report = json.loads((HERE / "preserve-exact-validation.json").read_text())
require(exact_report["exactResult"] == "passed" and exact_report["checkedRows"] == 16538, "preserve-exact status")

source = {}
for path in (ROOT / "Source/localization-inventory-v3/strings.jsonl", ROOT / "Source/localization-inventory-v3/static-text.jsonl"):
    for row in rows(path):
        require(row["stableId"] not in source, "duplicate source ID")
        source[row["stableId"]] = row

after_rows = rows(HERE / "after-targets.jsonl")
before_rows = rows(HERE / "baseline-targets.jsonl")
require(len(after_rows) == len(before_rows) == 16538, "accepted inventory mismatch")
order = [row["stableId"] for row in after_rows]
require(len(set(order)) == len(order), "duplicate accepted ID")
require(all(a["stableId"] == b["stableId"] and a["sourceIndex"] == b["sourceIndex"] == index for index, (a, b) in enumerate(zip(after_rows, before_rows))), "canonical order mismatch")
require(set(order) <= set(source), "source inventory mismatch")
reviewed = {}
for path in sorted((LOCALE / "semantic-audit-pass-01").glob("reviewed-*.jsonl")):
    for row in rows(path):
        require(row["stableId"] not in reviewed, "duplicate reviewed ID")
        reviewed[row["stableId"]] = row
require(set(reviewed) == set(order), "reviewed evidence coverage")
for sid in order:
    require(reviewed[sid]["source"] == source[sid]["source"], "reviewed source drift")
before = {row["stableId"]: row for row in before_rows}
after = {row["stableId"]: row for row in after_rows}
preflight = json.loads((HERE / "correction-batch-preflight.json").read_text())
replacements = {row["stableId"]: row for row in preflight["replacements"]}
changed = set(replacements)
require(len(changed) == 85, "correction count")
require(changed == {sid for sid in order if before[sid]["target"] != after[sid]["target"]}, "actual changed IDs differ")
for sid, row in replacements.items():
    require(before[sid]["target"] == row["oldTarget"] and after[sid]["target"] == row["selectedFullTarget"], "replacement drift: " + sid)

prior_rows = rows(PRIOR / "closure-ids-v2.jsonl")
prior_ids = {row["stableId"] for row in prior_rows}
require(len(prior_ids) == len(prior_rows) == 5211, "prior closure count")
require([sid for sid in order if sid in prior_ids] == [row["stableId"] for row in prior_rows], "prior closure order")
prior_manifest = json.loads((PRIOR / "dependency-closure-v2.json").read_text())
require(prior_manifest["closureIds"]["sha256"] == sha(PRIOR / "closure-ids-v2.jsonl"), "prior closure pin")
for manual in prior_manifest["manuals"]:
    require(sha(Path(manual["path"])) == manual["sha256"], "manual drift: " + manual["path"])
image_scope = prior_manifest["imagePlan"]
require(sha(ROOT / image_scope["scopePath"]) == image_scope["scopeSha256"], "image plan drift")

prior_components = {}
for name, pin in prior_manifest["components"].items():
    path = ROOT / pin["path"]
    require(sha(path) == pin["sha256"], "prior component drift: " + name)
    prior_components[name] = set(json.loads(path.read_text())["stableIds"])
require(set().union(*prior_components.values()) == prior_ids, "prior component union")

node_to_ids = collections.defaultdict(set)
for sid in order:
    row = reviewed[sid]
    for node in row.get("nodeNames", []):
        node_to_ids[(row["collection"], node)].add(sid)
index = {sid: number for number, sid in enumerate(order)}

# Repair the prior selector's missing-node boundary. All independently found
# dependent context rows are now correction inputs. Every corrected unit selects
# its complete compiled node, even when the prior anchor came only from a
# glossary concept hit. No reviewer-supplied stable-ID exception list is used.
current_context = set()
for sid in changed:
    row = reviewed[sid]
    for node in row.get("nodeNames", []):
        current_context.update(node_to_ids[(row["collection"], node)])
    if not row.get("nodeNames"):
        for position in range(max(0, index[sid] - 2), min(len(order), index[sid] + 3)):
            neighbor = order[position]
            if reviewed[neighbor]["collection"] == row["collection"]:
                current_context.add(neighbor)

source_forms = {norm(source[sid]["source"]) for sid in changed}
target_forms = {before[sid]["target"] for sid in changed} | {after[sid]["target"] for sid in changed}
current_repetitions = {sid for sid in order if norm(source[sid]["source"]) in source_forms or before[sid]["target"] in target_forms or after[sid]["target"] in target_forms}

# The prior concept families remain applicable because cycle-01 corrections
# remain in the payload. Add source/target forms for newly affected body checks.
new_patterns = {
    "hands-and-fingers": r"рук[а-яё]*|пальц[а-яё]*|(?<!\w)mikono?(?!\w)|(?<!\w)vidole?(?!\w)",
    "armpits": r"подмыш[а-яё]*|подмых[а-яё]*|(?<!\w)kwapa(?!\w)|(?<!\w)makwapa(?!\w)",
    "ears-and-hearing": r"уш[а-яё]*|ух[а-яё]*|(?<!\w)sikio(?!\w)|(?<!\w)masikio(?!\w)",
}
concepts = {}
for name, pin in prior_manifest["glossaryConceptSelectors"].items():
    path = ROOT / pin["path"]
    require(sha(path) == pin["sha256"], "prior concept drift: " + name)
    data = json.loads(path.read_text())
    concepts[name] = set(data["stableIds"])
for name, pattern in new_patterns.items():
    regex = re.compile(pattern, re.I)
    concepts[name] = {sid for sid in order if regex.search(source[sid]["source"] + " " + after[sid]["target"])}

components = {
    "changed": changed,
    "prior-correction-dependencies": prior_components["changed"],
    "containing-context": prior_components["containing-context"] | current_context,
    "exact-and-spelling-repetitions": prior_components["exact-and-spelling-repetitions"] | current_repetitions,
    "glossary-referents": prior_components["glossary-referents"] | set().union(*concepts.values()),
    "runtime-binding-and-layout": prior_components["runtime-binding-and-layout"],
    "mandatory-regressions": prior_components["mandatory-regressions"],
}
require(set().union(*components.values()) >= prior_ids, "applicable prior dependencies lost")
current_ids = set().union(*components.values())
new_ids = current_ids - prior_ids
retired_ids = prior_ids - current_ids
require(not retired_ids, "unexpected retired dependency")

# The previous reviewer interpreted glossary-anchor rows within the same
# compiled exchange as a corrected unit. Their contextual evidence changed.
invalidated_by = collections.defaultdict(list)
glossary_anchor = prior_components["glossary-referents"]
for sid in changed:
    row = reviewed[sid]
    for node in row.get("nodeNames", []):
        for anchor in node_to_ids[(row["collection"], node)] & glossary_anchor & prior_ids - changed:
            invalidated_by[anchor].append({"correctedStableId": sid, "node": node, "reason": "prior glossary-referent judgment shared this compiled exchange with a corrected full unit"})
invalidated_ids = set(invalidated_by)

finding_by_id = {row["stableId"]: row["findingId"] for row in preflight["replacements"]}


def base_row(sid):
    row = reviewed[sid]
    return {
        "sourceIndex": index[sid], "stableId": sid, "collection": row["collection"],
        "key": row.get("key"), "nodeNames": row.get("nodeNames", []),
        "source": row["source"], "target": after[sid]["target"],
        "previousTarget": before[sid]["target"], "authoredPath": after[sid]["artifact"],
    }


changed_rows = [dict(base_row(sid), findingId=finding_by_id[sid]) for sid in order if sid in changed]
write_jsonl(HERE / "changed-ids.jsonl", changed_rows)

component_refs = {}
for name, members in components.items():
    ids = [sid for sid in order if sid in members]
    path = HERE / ("component-" + name + ".json")
    write_json(path, {"schemaVersion": 1, "cycle": "sw-semantic-correction-02", "component": name, "count": len(ids), "stableIds": ids})
    component_refs[name] = ref(path, len(ids))

concept_refs = {}
for name, members in concepts.items():
    ids = [sid for sid in order if sid in members]
    path = HERE / ("concept-" + name + ".json")
    write_json(path, {"schemaVersion": 1, "cycle": "sw-semantic-correction-02", "concept": name, "selectorRegex": new_patterns.get(name, "pinned prior cycle selector"), "count": len(ids), "stableIds": ids})
    concept_refs[name] = ref(path, len(ids))

closure_rows = [dict(base_row(sid), components=[name for name, members in components.items() if sid in members]) for sid in order if sid in current_ids]
write_jsonl(HERE / "closure-ids.jsonl", closure_rows)
write_jsonl(HERE / "new-ids.jsonl", [base_row(sid) for sid in order if sid in new_ids])
write_jsonl(HERE / "retired-ids.jsonl", [base_row(sid) for sid in order if sid in retired_ids])
write_jsonl(HERE / "invalidated-ids.jsonl", [dict(base_row(sid), invalidatedBy=invalidated_by[sid]) for sid in order if sid in invalidated_ids])
delta_ids = changed | new_ids | invalidated_ids
write_jsonl(HERE / "review-delta.jsonl", [dict(base_row(sid), reasons=(["corrected"] if sid in changed else []) + (["new-closure-dependency"] if sid in new_ids else []) + (["prior-evidence-invalidated"] if sid in invalidated_ids else []), components=[name for name, members in components.items() if sid in members]) for sid in order if sid in delta_ids])

supplementary = {row["stableId"] for row in json.loads((LOCALE / "independent-review-01/final-findings-01.json").read_text())["findings"] if row["stableId"] not in prior_ids}
require(len(supplementary) == 32 and supplementary <= changed & current_context, "missing supplementary dependency repair")
require(len(delta_ids) == len(changed | new_ids | invalidated_ids), "delta union")
require(delta_ids <= current_ids, "review delta outside closure")

manifest = {
    "schemaVersion": 1, "cycle": "sw-semantic-correction-02", "createdAtUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "locale": "sw", "gameVersion": "1.3.19", "acceptedUnits": 16538,
    "priorClosure": ref(PRIOR / "closure-ids-v2.jsonl", len(prior_ids)),
    "changedIds": ref(HERE / "changed-ids.jsonl", len(changed)),
    "closureIds": ref(HERE / "closure-ids.jsonl", len(current_ids)),
    "newIds": ref(HERE / "new-ids.jsonl", len(new_ids)),
    "invalidatedIds": ref(HERE / "invalidated-ids.jsonl", len(invalidated_ids)),
    "retiredIds": ref(HERE / "retired-ids.jsonl", len(retired_ids)),
    "reviewDelta": ref(HERE / "review-delta.jsonl", len(delta_ids)),
    "components": component_refs, "concepts": concept_refs,
    "inputs": ref(HERE / "inputs.json"), "appliedBatch": ref(HERE / "applied-batch-manifest.json"),
    "structuralValidation": ref(validation_path), "preserveExact": ref(HERE / "preserve-exact-validation.json"),
    "sourceAndGlossaryPins": inputs["pins"]["sourceAndGlossary"],
    "manuals": prior_manifest["manuals"], "imagePlan": prior_manifest["imagePlan"],
    "newlineConvention": "UTF-8 JSONL with LF separators and final LF; empty retired set has zero-byte file",
    "selectorRepair": "Every corrected full unit selects its complete compiled containing node; glossary-only prior anchors no longer leave independently confirmed dependent lines outside context. Prior applicable component membership retained; new body-check concept selectors added.",
    "independentReview": "pending cycle-02 delta", "editorialAcceptance": "pending", "runtime": "not-run-per-owner",
}
path = HERE / "dependency-closure.json"
write_json(path, manifest)
print(json.dumps({"changed": len(changed), "closure": len(current_ids), "new": len(new_ids), "invalidated": len(invalidated_ids), "retired": len(retired_ids), "reviewDelta": len(delta_ids), "supplementaryRepaired": len(supplementary), "manifestSha256": sha(path)}, ensure_ascii=False))
