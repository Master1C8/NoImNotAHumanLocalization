#!/usr/bin/env python3
"""Reproduce cycle-03 dependencies and the exact independent reviewer delta."""

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CYCLE = Path(__file__).resolve().parent
HE = CYCLE.parent
PRIOR = HE / "semantic-correction-cycle-02"
IR1 = HE / "independent-review-01"
IR2 = HE / "independent-review-02"
GUID = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
        "UI": "0cbd8a7a4f543344bb95659de87f67a5",
        "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}
OCCUPIED = {"Greatmother_Entrance_Occupied": "Greatmother",
            "Fan_Entrance_Occupied": "Fan",
            "Luka_Entrance_Occupied": "Luka",
            "Nun_Entrance_Occupied": "Nun"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def once(path, data):
    if path.exists():
        assert path.read_bytes() == data, f"immutable evidence differs: {path}"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def encoded(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode()


def lines(ids, order):
    return ("\n".join(sorted(ids, key=order.__getitem__)) + "\n").encode() if ids else b""


def main():
    pins = json.loads((CYCLE / "input-pins.json").read_text())
    pre = json.loads((CYCLE / "preflight.json").read_text())
    app = json.loads((CYCLE / "application.json").read_text())
    exact = json.loads((CYCLE / "preserve-exact-v4.json").read_text())
    assert app["status"] == "applied" and app["changedStableIds"] == 71
    assert exact["exactResult"] == "passed" and exact["checkedRows"] == 16538
    assert sha(CYCLE / "preflight.json") == app["preflightSha256"]
    prior_manifest = json.loads((PRIOR / "closure-manifest.json").read_text())
    assert sha(PRIOR / "closure-manifest.json") == pins["priorClosureManifestSha256"]
    assert sha(PRIOR / "closure-ids.txt") == pins["priorClosureIdsSha256"]
    prior_ids = (PRIOR / "closure-ids.txt").read_text().splitlines()
    assert len(prior_ids) == prior_manifest["closureIds"]["count"] == 2191
    progress = json.loads((CYCLE / "baseline-progress.json").read_text())
    srcpaths = pins["sourceInventory"]
    rules = json.loads((ROOT / srcpaths["preserveExactPath"]).read_text())
    accepted = rules["tableRows"] + rules["staticRows"]
    ordered = [x["stableId"] for x in accepted]
    order = {sid: i for i, sid in enumerate(ordered)}
    assert len(order) == len(ordered) == 16538
    assert prior_ids == sorted(prior_ids, key=order.__getitem__)
    source = {x["stableId"]: x for x in map(json.loads, (ROOT / srcpaths["stringsPath"]).open())}
    source.update({x["stableId"]: x for x in map(json.loads, (ROOT / srcpaths["staticPath"]).open())})
    assert set(order) <= set(source)
    adj = json.loads((CYCLE / "adjudications.json").read_text())["records"]
    changed = {x["stableId"] for x in adj}
    assert len(changed) == 71 and (CYCLE / "changed-ids.txt").read_bytes() == lines(changed, order)
    before, after = {}, {}
    for f in progress["files"]:
        rel = f["path"]
        if not re.search(r"(?:dialogue|ui|checks)-batch-\d{3}\.json$", rel):
            continue
        current_path = ROOT / rel
        old_path = CYCLE / "before-authored" / current_path.name if rel in pre["files"] else current_path
        current, old = json.loads(current_path.read_text()), json.loads(old_path.read_text())
        assert len(current["entries"]) == len(old["entries"])
        for a, b in zip(old["entries"], current["entries"]):
            assert a["id"] == b["id"]
            sid = f"string:{GUID[current['collection']]}:{b['id']}"
            assert sid in order and sid not in after
            before[sid], after[sid] = a["target"], b["target"]
    for row in json.loads((HE / "static-text-draft.json").read_text())["entries"]:
        sid = row["stableId"]
        assert sid in order and sid not in after
        before[sid] = after[sid] = row["target"]
    assert set(before) == set(after) == set(order)
    assert {sid for sid in order if before[sid] != after[sid]} == changed

    components = defaultdict(set)
    components["changed"].update(changed)
    # The prior 2191-ID closure remains a reviewed dependency baseline while
    # its correction evidence is unresolved. Retention never requests a full
    # reread: the exact delta below names only invalidated or newly added IDs.
    components["retained-prior-closure"].update(prior_ids)
    affected_nodes = {n for a in adj for n in source[a["stableId"]].get("nodeNames", [])}
    for sid in ordered:
        if affected_nodes.intersection(source[sid].get("nodeNames", [])):
            components["scene-context"].add(sid)
    # This repairs the cycle-02 selector's omission of occupied continuations
    # and Nun's formally addressed branches beyond the initial occupied node.
    node_families = ("Nun_Entrance_", "Nun_Asking_", "Nun_Photo", "Nun_Ears",
                     "Nun_Eyes", "Nun_Hands", "Nun_Teeth", "Nun_Armpit",
                     "entrance_bald", "Bald_Asking_4",
                     "Greatmother_Entrance_Occupied", "Fan_Entrance_Occupied",
                     "Luka_Entrance_Occupied")
    for sid in ordered:
        if any(n.startswith(node_families) for n in source[sid].get("nodeNames", [])):
            components["scene-context"].add(sid)
    src_exact = {a["source"] for a in adj}
    old_exact = {a["before"] for a in adj}
    new_exact = {a["after"] for a in adj}
    for sid in ordered:
        if source[sid]["source"] in src_exact or before[sid] in old_exact or after[sid] in new_exact:
            components["exact-repetitions-and-wording"].add(sid)
    nun_formal = re.compile(r"(?i)(?<!\w)(?:вы|вас|вам|ваш\w*|ты|тебя|тебе|твой\w*)\b")
    bald_coarse = re.compile(r"(?i)(?:пизд|хер|хуй|бля|[её]бан|сука|мраз)")
    concept_hits = {"nun-direct-address": set(), "bald-coarse-register": set()}
    for sid in ordered:
        value = source[sid]["source"]
        if value.startswith("Nun: ") and nun_formal.search(value):
            concept_hits["nun-direct-address"].add(sid)
            components["glossary-referent-and-register"].add(sid)
        if value.startswith("Bald: ") and bald_coarse.search(value):
            concept_hits["bald-coarse-register"].add(sid)
            components["glossary-referent-and-register"].add(sid)

    # Compiled node line order and configured resident place yield the actual
    # dynamic template, continuation and UI label closure. This recipe is
    # reusable: a newly changed occupied continuation keeps the dependency.
    compiled = json.loads((IR2 / "compiled-scene-context.json").read_text())
    domain = json.loads((IR1 / "character-consumer-domain.json").read_text())
    characters = {x["name"]: x for x in domain["characters"]}
    by_key = {x.get("key"): sid for sid, x in source.items() if x.get("key")}
    runtime_links = []
    for node, caller in OCCUPIED.items():
        lines_in_node = [x["operands"][0] for x in compiled["nodes"][node] if x["opcode"] == 2]
        line_ids = [by_key[key] for key in lines_in_node if key in by_key]
        assert line_ids and "{0}" in source[line_ids[0]]["source"]
        assert changed.intersection(line_ids), node
        place = characters[caller]["place"]
        names = [x for x in domain["placeDomains"][str(place)] if x != caller]
        label_ids = []
        for name in names:
            key = "characterName_" + name
            assert key in by_key, (node, key)
            label_ids.append(by_key[key])
        components["runtime-bindings"].update(line_ids)
        components["runtime-bindings"].update(label_ids)
        runtime_links.append({"node": node, "caller": caller, "place": place,
            "lineIds": line_ids, "residentNames": names,
            "labelIds": sorted(label_ids, key=order.__getitem__)})
    for rule in accepted:
        sid = rule["stableId"]
        if (sid.startswith("tmp:") or rule.get("collection") in ("UI", "ChecksDialogs") or
                rule["formatSlots"] or rule["tmpTags"] or rule["wholeTextExact"]):
            components["mandatory-regressions"].add(sid)
    first_baseline = json.loads((HE / "semantic-correction-cycle-01" / "baseline-semantic-review-progress.json").read_text())
    for note in first_baseline["knownEditorialFollowups"]:
        for number in re.findall(r"\b\d{15,18}\b", note):
            components["mandatory-regressions"].update(sid for sid in order if sid.endswith(":" + number))
    old_mandatory = set((PRIOR / "components" / "mandatory-regressions-ids.txt").read_text().splitlines())
    assert components["mandatory-regressions"] == old_mandatory and len(old_mandatory) == 549

    closure = set().union(*components.values())
    old = set(prior_ids)
    new = closure - old
    retired = old - closure
    assert not retired
    invalidated = ((components["scene-context"] |
                    components["exact-repetitions-and-wording"] |
                    components["glossary-referent-and-register"] |
                    components["runtime-bindings"]) & old) - changed
    delta = changed | new | invalidated
    assert delta <= closure
    for name, ids in components.items():
        once(CYCLE / "components" / (name + "-ids.txt"), lines(ids, order))
    for name, ids in (("closure", closure), ("new-closure", new), ("retired", retired),
                      ("explicitly-invalidated", invalidated), ("delta", delta)):
        once(CYCLE / (name + "-ids.txt"), lines(ids, order))
    causes = {sid: sorted(name for name, ids in components.items() if sid in ids) for sid in closure}
    rows = []
    for sid in sorted(closure, key=order.__getitem__):
        row = source[sid]
        rows.append({"stableId": sid, "collection": row.get("collection", "StaticTMP"),
            "key": row.get("key"), "nodeNames": row.get("nodeNames", []),
            "source": row["source"], "before": before[sid], "after": after[sid],
            "components": causes[sid], "reviewDelta": sid in delta,
            "deltaReasons": [name for name, yes in (("corrected", sid in changed),
                ("new-closure", sid in new), ("explicitly-invalidated", sid in invalidated)) if yes]})
    def render(values):
        return ("\n".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) for x in values) + "\n").encode()
    once(CYCLE / "review-rows.jsonl", render(rows))
    delta_rows = [x for x in rows if x["reviewDelta"]]
    once(CYCLE / "delta-review-rows.jsonl", render(delta_rows))
    map_status = {}
    for name in ("action-label-map.json", "visitor-choice-map.json", "repeated-choices-map.json",
                 "repeated-ambient-map.json", "credits-replacements.json", "credits-role-map.json"):
        path = HE / name
        obj = json.loads(path.read_text())
        phrases = obj.get("phrases", obj.get("entries", obj.get("replacements", [])))
        affected = [x for x in phrases if x.get("source") in src_exact or x.get("target") in old_exact]
        assert not affected, name
        map_status[name] = {"sha256": sha(path), "affectedPhrases": affected,
                            "result": "current; no corrected source/old-target binding"}
    static = HE / "static-text-draft.json"
    assert not any(sid.startswith("tmp:") for sid in changed)
    context = {"schemaVersion": 1, "status": "context only; not additional translation units",
        "runtimeLinks": runtime_links,
        "compiledSceneContextSha256": sha(IR2 / "compiled-scene-context.json"),
        "characterDomainSha256": sha(IR1 / "character-consumer-domain.json"),
        "consumerPreflightSha256": sha(CYCLE / "consumer-preflight.json"),
        "derivedMaps": map_status,
        "staticCredits": {"path": str(static.relative_to(ROOT)), "sha256": sha(static),
                          "affectedRows": 0, "result": "current; no static source row corrected"},
        "retiredDependencies": [],
        "retentionReason": "All cycle-02 dependencies remain the independently reviewed baseline; only corrected, new and explicitly invalidated rows enter the next review delta.",
        "sourceDomainConflict": "Fixed masculine Russian in Fan/Luka continuations conflicts with configured female residents; target neutralization assigns no unsupported gender."}
    once(CYCLE / "runtime-context.json", encoded(context))
    def ref(path, count):
        return {"path": str(path.relative_to(ROOT)), "count": count, "sha256": sha(path)}
    stats = {name: ref(CYCLE / "components" / (name + "-ids.txt"), len(ids))
             for name, ids in sorted(components.items())}
    manifest = {"schemaVersion": 1,
        "status": "cycle-03 applied; exact independent delta ready; no cycle-03 verdict",
        "canonicalOrder": "preserve-exactly-v4 tableRows then staticRows; UTF-8, one ID per line, final LF for nonempty files",
        "selectorScriptSha256": sha(Path(__file__)), "inputPinsSha256": sha(CYCLE / "input-pins.json"),
        "sourceInventorySha256": pins["sourceInventory"]["stringsSha256"],
        "staticInventorySha256": pins["sourceInventory"]["staticSha256"],
        "preserveExactSha256": pins["sourceInventory"]["preserveExactSha256"],
        "glossarySha256": pins["glossary"]["sha256"],
        "priorClosureManifestSha256": pins["priorClosureManifestSha256"],
        "independentReviewSha256": pins["independentFinalReviewSha256"],
        "independentFindingsSha256": pins["independentFinalFindingsSha256"],
        "changedIds": ref(CYCLE / "changed-ids.txt", len(changed)),
        "previousClosureIds": ref(PRIOR / "closure-ids.txt", len(old)),
        "closureIds": ref(CYCLE / "closure-ids.txt", len(closure)),
        "newClosureIds": ref(CYCLE / "new-closure-ids.txt", len(new)),
        "explicitlyInvalidatedIds": ref(CYCLE / "explicitly-invalidated-ids.txt", len(invalidated)),
        "retiredIds": ref(CYCLE / "retired-ids.txt", len(retired)),
        "deltaIds": ref(CYCLE / "delta-ids.txt", len(delta)),
        "components": stats,
        "reviewRows": ref(CYCLE / "review-rows.jsonl", len(rows)),
        "deltaReviewRows": ref(CYCLE / "delta-review-rows.jsonl", len(delta_rows)),
        "runtimeContext": ref(CYCLE / "runtime-context.json", len(runtime_links)),
        "conceptHits": {name: len(ids) for name, ids in concept_hits.items()},
        "repairedSelectors": ["Nun formal-singular address across compiled entrance, asking, inspection and refusal branches",
            "Bald overt profanity across his bounded lines", "compiled occupied continuation plus dynamic label and actual place-domain bindings"],
        "deltaFormula": "corrected IDs union current-minus-previous closure union explicitly invalidated previously reviewed IDs",
        "retiredDependencyReason": "none; all prior closure dependencies retained as applicable baseline",
        "editorialAcceptance": False}
    once(CYCLE / "closure-manifest.json", encoded(manifest))
    print(json.dumps({"changed": len(changed), "previous": len(old), "closure": len(closure),
                      "new": len(new), "invalidated": len(invalidated), "retired": len(retired),
                      "delta": len(delta), "manifestSha256": sha(CYCLE / "closure-manifest.json")}))


if __name__ == "__main__":
    main()
