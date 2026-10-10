"""Deterministically enumerate the bounded cycle-03 semantic risk surface.

This script selects evidence for a human/model full-unit read. It makes no
semantic decisions and never generates Swahili wording.
"""
import collections
import hashlib
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path("/Users/antonkrutov/Desktop/no I'm not a human")
SW = ROOT / "Translations/sw"
HERE = SW / "semantic-correction-cycle-03"
BASE = SW / "semantic-correction-cycle-02"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def write(path, text):
    if path.exists():
        assert path.read_text() == text, f"immutable output differs: {path}"
    else:
        path.write_text(text)


inputs = json.loads((HERE / "inputs.json").read_text())
assert inputs["acceptedUnits"] == 16538
after_path = BASE / "after-targets.jsonl"
assert sha(after_path) == next(v["sha256"] for v in inputs["pins"].values() if v["path"].endswith("after-targets.jsonl"))
accepted = rows(after_path)
assert len(accepted) == len({x["stableId"] for x in accepted}) == 16538
order = {row["stableId"]: row["sourceIndex"] for row in accepted}
final = {row["stableId"]: row for row in accepted}
reviewed = {}
for path in sorted((SW / "semantic-audit-pass-01").glob("reviewed-*.jsonl")):
    for row in rows(path):
        assert row["stableId"] not in reviewed
        reviewed[row["stableId"]] = row
assert set(reviewed) == set(final)
source = {}
for path in (ROOT / "Source/localization-inventory-v3/strings.jsonl", ROOT / "Source/localization-inventory-v3/static-text.jsonl"):
    for row in rows(path):
        source[row["stableId"]] = row
for sid in order:
    assert reviewed[sid]["source"] == source[sid]["source"]

spec = importlib.util.spec_from_file_location("sw_review_reader_02", SW / "independent-review-02/review_reader.py")
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
assert reader.program_hash == "33de1e80e55e4eb8ec2093078028aa83fc45ac8b77acc05c5a4f9477ebe92827"
key_to_sid = {reviewed[sid]["key"]: sid for sid in order if reviewed[sid]["collection"] == "Dialogs"}
visible_by_node = {}
consumers = collections.defaultdict(list)
for node, instructions in reader.nodes.items():
    visible = []
    for instruction in instructions:
        args = instruction["operands"]
        if instruction["opcode"] in (2, 4) and args and args[0] in key_to_sid:
            sid = key_to_sid[args[0]]
            visible.append((sid, instruction["index"], instruction["opcode"], args[1:]))
            consumers[sid].append((node, instruction["index"], instruction["opcode"], args[1:]))
    visible_by_node[node] = visible

patterns = {
    "armpit-source-inflections": ("source", r"подмыш[а-яё]*|подмых[а-яё]*|под\s+мышк[а-яё]*"),
    "armpit-target-nouns": ("target", r"(?<!\w)(?:kwapa|makwapa)(?!\w)"),
    "eye-open-agreement": ("target", r"(?<!\w)(?:ifungue|yafungue)(?!\w)"),
    "hands-wash-agreement": ("target", r"(?<!\w)(?:kuyaosha|kuiosha|kuziosha|kuosha\s+mikono|kuosha\s+kucha)(?!\w)"),
    "finger-pointing-gesture": ("target", r"(?<!\w)(?:kidole|vidole|kunyooshea|kumnyooshea)(?!\w)"),
    "examiner-pronouns": ("target", r"(?<!\w)(?:nisiangalie|usiangalie)(?!\w)"),
}
components = collections.defaultdict(set)
for name, (field, regex) in patterns.items():
    match = re.compile(regex, re.I)
    for sid in order:
        value = source[sid]["source"] if field == "source" else final[sid]["target"]
        if match.search(value):
            components[name].add(sid)

findings = json.loads((SW / "independent-review-02/final-findings-02.json").read_text())["findings"]
assert len(findings) == 10
finding_ids = {row["stableId"] for row in findings}
components["reviewer-full-unit-proposals"].update(finding_ids)
armpit = components["armpit-source-inflections"] | components["armpit-target-nouns"]
for sid in armpit:
    for node, _, _, _ in consumers.get(sid, []):
        visible = visible_by_node[node]
        for position, item in enumerate(visible):
            if item[0] == sid:
                for nearby in visible[max(0, position - 1):min(len(visible), position + 2)]:
                    components["armpit-compiled-adjacent-context"].add(nearby[0])
for sid in finding_ids:
    for node, _, _, _ in consumers.get(sid, []):
        components["reviewer-connected-full-consumer-nodes"].update(x[0] for x in visible_by_node[node])

selected = set().union(*components.values())
assert finding_ids <= selected
evidence = []
for sid in sorted(selected, key=order.__getitem__):
    r = reviewed[sid]
    evidence.append({
        "sourceIndex": order[sid], "stableId": sid, "collection": r["collection"],
        "key": r.get("key"), "nodeNames": r.get("nodeNames", []),
        "source": source[sid]["source"], "target": final[sid]["target"],
        "authoredPath": final[sid]["artifact"],
        "compiledConsumers": consumers.get(sid, []),
        "components": [name for name in patterns if sid in components[name]] + [name for name in ("reviewer-full-unit-proposals", "armpit-compiled-adjacent-context", "reviewer-connected-full-consumer-nodes") if sid in components[name]],
    })

inventory_path = HERE / "bounded-risk-inventory.jsonl"
write(inventory_path, "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in evidence))
manifest = {
    "schemaVersion": 1, "cycle": "sw-semantic-correction-03",
    "sourceAndGlossaryPins": {k: v for k, v in inputs["pins"].items() if any(v["path"].endswith(name) for name in ("strings.jsonl", "static-text.jsonl", "glossary.json", "layer.json"))},
    "acceptedUnits": 16538, "compiledProgramSha256": reader.program_hash,
    "reviewFindingsSha256": sha(SW / "independent-review-02/final-findings-02.json"),
    "baselineTargetsSha256": sha(after_path),
    "selectorPatterns": {name: {"field": field, "regex": regex} for name, (field, regex) in patterns.items()},
    "contextRule": "One visible compiled instruction before and after every direct armpit mention; complete compiled consumer node for each reviewer proposal; only accepted source IDs counted.",
    "components": {name: {"count": len(members), "stableIds": [sid for sid in sorted(members, key=order.__getitem__)]} for name, members in components.items()},
    "boundedUnits": len(evidence), "inventoryPath": str(inventory_path.relative_to(ROOT)), "inventorySha256": sha(inventory_path),
    "newlineConvention": "UTF-8 JSONL; LF separator and final LF",
    "semanticResult": "not determined by selector; every listed full source/target unit requires manual semantic reading",
}
manifest_path = HERE / "bounded-risk-inventory-manifest.json"
write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"boundedUnits": len(evidence), "components": {name: len(members) for name, members in components.items()}, "inventorySha256": sha(inventory_path), "manifestSha256": sha(manifest_path)}, ensure_ascii=False))
