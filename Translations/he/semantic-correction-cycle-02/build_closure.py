#!/usr/bin/env python3
"""Rebuild the second Hebrew correction closure and exact reviewer delta.

The selector carries forward the verified first-cycle dependencies, then
selects bounded new scene, referent and compiled-consumer dependencies from
the 31 adjudicated full-unit edits. It never invents translation IDs.
"""

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CYCLE = Path(__file__).resolve().parent
HE = CYCLE.parent
PRIOR = HE / "semantic-correction-cycle-01"
IR = HE / "independent-review-01"
GUID = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
        "UI": "0cbd8a7a4f543344bb95659de87f67a5",
        "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def once(path, data):
    if path.exists():
        assert path.read_bytes() == data, f"immutable evidence differs: {path}"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def lines(ids, order):
    return (("\n".join(sorted(ids, key=order.__getitem__)) + "\n") if ids else "").encode()


def main():
    pins = json.loads((CYCLE / "input-pins.json").read_text())
    pre = json.loads((CYCLE / "preflight.json").read_text())
    application = json.loads((CYCLE / "application.json").read_text())
    exact = json.loads((CYCLE / "preserve-exact-v4.json").read_text())
    consumer = json.loads((CYCLE / "consumer-preflight.json").read_text())
    assert application["status"] == "applied" and exact["checkedRows"] == 16538
    assert exact["exactResult"] == "passed"
    assert sha(CYCLE / "preflight.json") == application["preflightSha256"]
    prior_manifest = json.loads((PRIOR / "closure-manifest.json").read_text())
    assert sha(PRIOR / "closure-manifest.json") == pins["priorClosureManifestSha256"]
    assert sha(PRIOR / "closure-ids.txt") == pins["priorClosureIdsSha256"]
    assert sha(PRIOR / "review-rows.jsonl") == pins["priorReviewRowsSha256"]
    prior_ids = (PRIOR / "closure-ids.txt").read_text().splitlines()
    assert len(prior_ids) == prior_manifest["closureIds"]["count"] == 2111
    progress = json.loads((CYCLE / "baseline-progress.json").read_text())
    source_paths = pins["sourceInventory"]
    rules = json.loads((ROOT / source_paths["preserveExactPath"]).read_text())
    accepted = rules["tableRows"] + rules["staticRows"]
    ordered = [r["stableId"] for r in accepted]
    order = {sid: i for i, sid in enumerate(ordered)}
    assert len(order) == len(ordered) == 16538
    assert prior_ids == sorted(prior_ids, key=order.__getitem__)
    source = {r["stableId"]: r for r in map(json.loads, (ROOT / source_paths["stringsPath"]).open())}
    source.update({r["stableId"]: r for r in map(json.loads, (ROOT / source_paths["staticPath"]).open())})
    assert set(order) <= set(source)
    adjudications = json.loads((CYCLE / "adjudications.json").read_text())["records"]
    changed = {r["stableId"] for r in adjudications}
    assert len(changed) == 31 and (CYCLE / "changed-ids.txt").read_bytes() == lines(changed, order)
    # Current and pre-cycle-02 full authored values, bound to before snapshots.
    before, after = {}, {}
    for file in progress["files"]:
        rel = file["path"]
        if not re.search(r"(?:dialogue|ui|checks)-batch-\d{3}\.json$", rel):
            continue
        path = ROOT / rel
        current = json.loads(path.read_text())
        old_path = CYCLE / "before-authored" / path.name if rel in pre["files"] else path
        old = json.loads(old_path.read_text())
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
    # First-cycle dependencies remain applicable to unresolved corrected
    # language evidence. Retention does not ask the reviewer to reread them.
    components["retained-prior-closure"].update(prior_ids)
    affected_nodes = {n for a in adjudications for n in source[a["stableId"]].get("nodeNames", [])}
    for sid in ordered:
        if affected_nodes.intersection(source[sid].get("nodeNames", [])):
            components["scene-context"].add(sid)
    # Repair the missing branch selectors found by the independent review:
    # gasmask recruitment has both 15 and 18 nodes, fortune-teller formal
    # address is a multi-node scene, and Bald's kinship spans entrance/asking.
    scene_prefixes = ("entrance_gasmask_15", "entrance_gasmask_18",
                      "FortuneTeller_Entrance_3", "entrance_bald", "Bald_Asking_4",
                      "radio_12", "radio_13", "Leper_Ears_DontShoot", "Leper_Teeth_Gun",
                      "Tough_Asking_4", "Couple_Asking_5_2")
    for sid in ordered:
        if any(n.lower().startswith(p.lower()) for n in source[sid].get("nodeNames", [])
               for p in scene_prefixes):
            components["scene-context"].add(sid)
    src_exact = {a["source"] for a in adjudications}
    old_exact = {a["before"] for a in adjudications}
    new_exact = {a["after"] for a in adjudications}
    for sid in ordered:
        if source[sid]["source"] in src_exact or before[sid] in old_exact or after[sid] in new_exact:
            components["exact-repetitions-and-wording"].add(sid)
    # A single literal would miss ё/е, inflected kinship and interrupted
    # radio words. This selector is source-side and bounded by concepts that
    # were actually corrected; it does not select every line by a speaker.
    concepts = {
        "jerky-designation": re.compile(r"(?i)(?<!\w)д[её]рган\w*"),
        "bald-kinship": re.compile(r"(?i)(?<!\w)(?:ма\s+и\s+ба|мать|матери|матерью|матерей|матерям|матерями|матерях|бабушк\w*|бабк\w*|коллектор\w*)\b"),
        "radio-anonymous-entity": re.compile(r"(?i)(?<!\w)(?:субъ\w*|повт[\.\u2026]*ря\w*|подкр[\.\u2026]*плен\w*)"),
        "light-oath": re.compile(r"(?i)(?:[её]бан\w*\s+свет)"),
    }
    concept_hits = defaultdict(set)
    for sid in ordered:
        text = source[sid]["source"]
        for name, regex in concepts.items():
            if name == "bald-kinship" and not (
                text.startswith("Bald: ") or any(n.lower().startswith(("bald_", "entrance_bald"))
                for n in source[sid].get("nodeNames", []))):
                continue
            if regex.search(text):
                concept_hits[name].add(sid)
                components["glossary-referent-and-register"].add(sid)

    # Runtime selector: compiled placeholder command -> configured place or
    # deficit enum -> accepted UI label. No guessed alternate character is
    # added, and missing characterName_Twins is a context fragment only.
    compiled = {r["stableId"]: r for r in json.loads((IR / "all-format-consumer-context.json").read_text())["rows"]}
    domain = json.loads((IR / "character-consumer-domain.json").read_text())
    characters = {r["name"]: r for r in domain["characters"]}
    ui_by_key = {r.get("key"): sid for sid, r in source.items()
                 if r.get("collection") == "UI" and r.get("key")}
    runtime_links = []
    missing_runtime_labels = []
    for a in adjudications:
        sid = a["stableId"]
        if "{0}" not in a["after"]:
            continue
        consumers = compiled[sid]["consumer"]
        assert len(consumers) == 1
        ins = consumers[0]["instructions"]
        method = [x["operands"][0] for x in ins if x["opcode"] == 12 and x["operands"]][-1]
        if method == "GetCharacterOnPlace":
            caller = [x["operands"][0] for x in ins if x["opcode"] == 6 and x["operands"]][-1]
            place = characters[caller]["place"]
            names = [x for x in domain["placeDomains"][str(place)] if x != caller]
            keys = ["characterName_" + name for name in names]
        else:
            assert method == "LocalizeItem"
            caller, place = None, None
            keys = ["consumable_" + name.lower() + "_name" for name in
                    ("Enerjeka", "Cigarette", "Coffee", "CatFood", "Kombucha", "Povistka")]
        labels = []
        for key in keys:
            label_sid = ui_by_key.get(key)
            if label_sid is None:
                missing_runtime_labels.append({"consumerId": sid, "missingKey": key})
            else:
                components["runtime-bindings"].add(label_sid)
                labels.append(label_sid)
        components["runtime-bindings"].add(sid)
        runtime_links.append({"consumerId": sid, "method": method, "caller": caller,
                              "place": place, "labelIds": sorted(labels, key=order.__getitem__),
                              "missingKeys": [k for k in keys if k not in ui_by_key]})
    # If a UI label changes, invalidate only actual compiled consumers whose
    # configured alternate domain contains that character.
    changed_ui_keys = [source[sid].get("key") for sid in changed
                       if source[sid].get("collection") == "UI"]
    for key in changed_ui_keys:
        assert key and key.startswith("characterName_")
        name = key[len("characterName_"):]
        for row in compiled.values():
            for use in row["consumer"]:
                ins = use["instructions"]
                methods = [x["operands"][0] for x in ins if x["opcode"] == 12 and x["operands"]]
                if not methods or methods[-1] != "GetCharacterOnPlace":
                    continue
                caller = [x["operands"][0] for x in ins if x["opcode"] == 6 and x["operands"]][-1]
                place = characters[caller]["place"]
                if name in domain["placeDomains"][str(place)] and name != caller:
                    components["runtime-bindings"].add(row["stableId"])
                    runtime_links.append({"consumerId": row["stableId"], "method": "GetCharacterOnPlace",
                                          "labelKey": key, "caller": caller, "place": place})
    # Retain the project's stable mandatory catalog. The first cycle pinned
    # exactly these IDs; regenerate from the canonical preserve-exact rules.
    for rule in accepted:
        sid = rule["stableId"]
        if (sid.startswith("tmp:") or rule.get("collection") in ("UI", "ChecksDialogs") or
                rule["formatSlots"] or rule["tmpTags"] or rule["wholeTextExact"]):
            components["mandatory-regressions"].add(sid)
    first_baseline = json.loads((PRIOR / "baseline-semantic-review-progress.json").read_text())
    for note in first_baseline["knownEditorialFollowups"]:
        for number in re.findall(r"\b\d{15,18}\b", note):
            components["mandatory-regressions"].update(sid for sid in order if sid.endswith(":" + number))
    mandatory_old = set((PRIOR / "components" / "mandatory-regressions-ids.txt").read_text().splitlines())
    assert components["mandatory-regressions"] == mandatory_old

    closure = set().union(*components.values())
    old = set(prior_ids)
    new = closure - old
    retired = old - closure
    assert not retired, "retained first-cycle dependencies unexpectedly retired"
    # Previously reviewed evidence is invalidated only when an unchanged row
    # supplies the corrected exchange/referent/assembled consumer context.
    invalidated = ((components["scene-context"] |
                    components["exact-repetitions-and-wording"] |
                    components["glossary-referent-and-register"] |
                    components["runtime-bindings"]) & old) - changed
    # Do not make every original source-side concept hit an invalidation: a
    # previously reviewed distant use of 'mother' is evidence still valid.
    invalidated &= (components["scene-context"] |
                    components["exact-repetitions-and-wording"] |
                    components["runtime-bindings"])
    delta = changed | new | invalidated
    assert delta <= closure
    for name, ids in components.items():
        once(CYCLE / "components" / (name + "-ids.txt"), lines(ids, order))
    for name, ids in (("closure", closure), ("new-closure", new), ("retired", retired),
                      ("explicitly-invalidated", invalidated), ("delta", delta)):
        once(CYCLE / (name + "-ids.txt"), lines(ids, order))
    causes = {sid: sorted(name for name, ids in components.items() if sid in ids) for sid in closure}
    review_rows = []
    for sid in sorted(closure, key=order.__getitem__):
        row = source[sid]
        review_rows.append({"stableId": sid, "collection": row.get("collection", "StaticTMP"),
                            "key": row.get("key"), "nodeNames": row.get("nodeNames", []),
                            "source": row["source"], "before": before[sid], "after": after[sid],
                            "components": causes[sid], "reviewDelta": sid in delta,
                            "deltaReasons": [reason for reason, test in
                                (("corrected", sid in changed), ("new-closure", sid in new),
                                 ("explicitly-invalidated", sid in invalidated)) if test]})
    render = lambda rows: ("\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":"))
                                      for r in rows) + "\n").encode()
    once(CYCLE / "review-rows.jsonl", render(review_rows))
    delta_rows = [r for r in review_rows if r["reviewDelta"]]
    once(CYCLE / "delta-review-rows.jsonl", render(delta_rows))
    # Locale-owned derived maps are affected only by exact source or previous
    # target phrase bindings. A zero match documents why no map was rewritten.
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
    static_path = HE / "static-text-draft.json"
    assert not any(sid.startswith("tmp:") for sid in changed)
    context = {"schemaVersion": 1, "status": "context only; not additional translation units",
               "runtimeLinks": runtime_links, "missingRuntimeLabels": missing_runtime_labels,
               "consumerPreflightSha256": sha(CYCLE / "consumer-preflight.json"),
               "derivedMaps": map_status,
               "staticCredits": {"path": str(static_path.relative_to(ROOT)), "sha256": sha(static_path),
                                 "affectedRows": 0, "result": "current; no static source row corrected"},
               "retiredDependencies": [],
               "retentionReason": "All cycle-01 correction dependencies remain in the independently reviewed baseline; unchanged rows are not automatically part of the new review delta."}
    once(CYCLE / "runtime-context.json", encoded(context))
    stats = {}
    for name, ids in sorted(components.items()):
        path = CYCLE / "components" / (name + "-ids.txt")
        stats[name] = {"path": str(path.relative_to(ROOT)), "count": len(ids), "sha256": sha(path)}
    def ref(path, count):
        return {"path": str(path.relative_to(ROOT)), "count": count, "sha256": sha(path)}
    manifest = {"schemaVersion": 1,
        "status": "cycle-02 applied; exact independent delta ready; no independent cycle-02 verdict",
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
        "reviewRows": ref(CYCLE / "review-rows.jsonl", len(review_rows)),
        "deltaReviewRows": ref(CYCLE / "delta-review-rows.jsonl", len(delta_rows)),
        "runtimeContext": ref(CYCLE / "runtime-context.json", len(runtime_links)),
        "conceptHits": {name: len(ids) for name, ids in concept_hits.items()},
        "newlyRepairedSelectors": ["gasmask recruitment node 18 plus 15",
            "fortune-teller formal-singular exchange", "Bald mother/grandmother inflections",
            "radio anonymous entity with ellipsis spelling", "actual compiled place/item display labels"],
        "deltaFormula": "changed IDs union current-minus-previous closure union explicitly invalidated previously reviewed IDs",
        "editorialAcceptance": False}
    once(CYCLE / "closure-manifest.json", encoded(manifest))
    print(json.dumps({"changed": len(changed), "previous": len(old), "closure": len(closure),
                      "new": len(new), "invalidated": len(invalidated), "retired": len(retired),
                      "delta": len(delta), "manifestSha256": sha(CYCLE / "closure-manifest.json")}))


if __name__ == "__main__":
    main()
