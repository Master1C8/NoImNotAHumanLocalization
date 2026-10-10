#!/usr/bin/env python3
"""Rebuild immutable Dutch correction closure in pinned canonical source order."""

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent / "closure"
CYCLE = HERE.parent
NAMES = ("changed", "context", "repetitions", "glossary-referents",
         "runtime-bindings", "mandatory-regressions", "closure", "delta", "new-dependencies", "retired-dependencies", "explicit-invalidated")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_new(path, value):
    assert not path.exists(), f"Immutable cycle output exists: {path}"
    path.write_text(value)


def key_family(key):
    if not key or not key.startswith("line:"):
        return None
    return key.rsplit("_", 1)[0]


# Source variants are deliberately explicit. New cycles revise this selector
# and recompute the whole closure, rather than appending missed IDs by hand.
CONCEPTS = {
    "strange-mushroom": r"(?iu)(странн[а-яё]* гриб|гриб[а-яё]*.*картош|картош[а-яё]*.*гриб)",
    "ear-wax": r"(?iu)(\bсер[ауы]\b|ушн[а-яё]* сер[а-яё]*)",
    "old-woman-address": r"(?iu)(дружоч[а-яё]*|дружок|милок|милочка)",
    "occupied-place-rhyme": r"(?iu)(рифм[а-яё]*|местечк[а-яё]*|освобод[а-яё]* мест)",
    "clock-ritual": r"(?iu)(показать часы|полночь|часы на 12)",
    "leper-expletive": r"(?iu)([её]баный свет)",
    "child-glasses": r"(?iu)(детск[а-яё]* очк|линз[а-яё]*.*отпечатк|отпечатк[а-яё]*.*линз)",
    "firefighter-ears": r"(?iu)(ушам теперь всё равно|душе -- ещё нет)",
}

MANDATORY = {
    "gender-and-kinship": r"(?iu)(сестр|брат|матер|мать|мам|отец|пап|доч|сын|ж[её]н|муж|бабуш|дедуш|девуш|парен|женщин|мужчин|\b(?:он|она|его|её|ее|ему|ей|им|них|ними)\b)",
    "guest-and-human": r"(?iu)(гост[ьи]|человек|люд[ией]|нечеловек|фема|FEMA|визит[её]р)",
    "profanity-wordplay": r"(?iu)(бля|нахуй|нахер|ху[йяеюи]|говн|жоп|пизд|[её]б|долбо|сука|шутк|смешн|редиск|овощ|рифм)",
    "format-markup": r"\{[0-9]+\}|<[^<>]+>",
}


def main():
    HERE.mkdir(exist_ok=False)
    out = HERE / "closure-manifest.json"
    assert not out.exists()
    adjudication_path = CYCLE / "adjudicated-corrections-v2.json"
    validation_path = CYCLE / "structural-validation.json"
    adjudication = json.loads(adjudication_path.read_text())
    validation = json.loads(validation_path.read_text())
    assert validation["adjudicationSha256"] == sha(adjudication_path)
    assert validation["fullExact"]["result"] == "passed"
    pass_path = ROOT / "Translations/nl/semantic-review-rows-pass1.jsonl"
    rows = [json.loads(line) for line in pass_path.open()]
    previous_path = ROOT / "Translations/nl/semantic-cycle-1/closure-v2/closure-manifest.json"
    previous = json.loads(previous_path.read_text())
    assert len(rows) == 16538 and sha(pass_path) == previous["pass1ReviewRowsSha256"]
    assert adjudication["previousClosureSha256"] == sha(previous_path)
    for pin in adjudication["pins"].values():
        path = Path(pin["path"])
        assert sha(path if path.is_absolute() else ROOT / path) == pin["sha256"]
    ids = [row["stableId"] for row in rows]
    assert len(set(ids)) == len(ids)
    inventory = {row["stableId"]: row for row in
                 (json.loads(line) for line in (ROOT / "Source/localization-inventory-v3/strings.jsonl").open())}
    source_rows = {row["stableId"]: row for row in rows}
    guids = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
             "UI": "0cbd8a7a4f543344bb95659de87f67a5",
             "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}
    target_by_id = {}
    progress = json.loads((ROOT / "Documentation/nl-text-progress.json").read_text())
    for authored in progress["authoredBatches"]:
        doc = json.loads((ROOT / authored["path"]).read_text())
        guid = guids[doc["collection"]]
        for entry in doc["entries"]:
            sid = f"string:{guid}:{entry['id']}"
            assert sid not in target_by_id
            target_by_id[sid] = entry["target"]
    static = ROOT / "Translations/nl/static-text-draft.json"
    for entry in json.loads(static.read_text())["entries"]:
        assert entry["stableId"] not in target_by_id
        target_by_id[entry["stableId"]] = entry["target"]
    assert set(target_by_id) == set(ids)
    for record in adjudication["corrections"]:
        assert target_by_id[record["stableId"]] == record["after"]
    before_strings = {record["before"] for record in adjudication["corrections"]}
    after_strings = {record["after"] for record in adjudication["corrections"]}
    source_strings = {record["source"] for record in adjudication["corrections"]}
    changed = {record["stableId"] for record in adjudication["corrections"]}
    assert len(changed) == 38
    source_manifest = json.loads((ROOT / "Source/preserve-exactly-v4.json").read_text())
    manifest_candidates = {r["stableId"] for r in source_manifest["tableRows"]
                           if "Occupied" in (r.get("key") or "") and r["formatSlots"]}
    consumer_path = ROOT / "Translations/nl/independent-review-01/consumer-context.json"
    consumer = json.loads(consumer_path.read_text())
    review_candidates = {r["stableId"] for r in consumer["occupiedPlaceholderCandidates"]}
    assert manifest_candidates == review_candidates and len(review_candidates) == 59
    item_path = next(r for r in consumer["occupiedPlaceholderCandidates"]
                     if r["key"] == "line:Jacket_Entrance_Occupied_YesLet_00e8dfe")
    assert "у меня есть {0}" in item_path["source"]
    occupied_ids = manifest_candidates - {item_path["stableId"]}
    assert len(occupied_ids) == 58
    label_ids = {r["stableId"] for r in source_manifest["tableRows"]
                 if r["collection"] == "UI" and (r.get("key") or "").startswith("characterName_")}
    assert len(label_ids) == 57
    node_names = set()
    families = set()
    for sid in changed | occupied_ids:
        info = inventory.get(sid, {})
        node_names.update(info.get("nodeNames", []))
        if key_family(info.get("key")):
            families.add(key_family(info["key"]))
    components = {name: set() for name in NAMES}
    components["changed"] = changed
    concept_hits = defaultdict(set)
    mandatory_hits = defaultdict(set)
    for row in rows:
        sid, source = row["stableId"], row["source"]
        info = inventory.get(sid, {})
        key = info.get("key")
        if set(info.get("nodeNames", [])) & node_names or key_family(key) in families:
            components["context"].add(sid)
        if source in source_strings or target_by_id[sid] in before_strings | after_strings:
            components["repetitions"].add(sid)
        for name, pattern in CONCEPTS.items():
            if re.search(pattern, source):
                concept_hits[name].add(sid)
                components["glossary-referents"].add(sid)
        if sid in occupied_ids or sid in label_ids or (
            ("{0}" in source or "<" in source) and
            (set(info.get("nodeNames", [])) & node_names or key_family(key) in families)):
            components["runtime-bindings"].add(sid)
        if row["collection"] == "UI" or sid.startswith("tmp:"):
            mandatory_hits["ui-and-static"].add(sid)
            components["mandatory-regressions"].add(sid)
        for name, pattern in MANDATORY.items():
            if (sid in changed or sid in components["context"] or sid in components["glossary-referents"]) and re.search(pattern, source):
                mandatory_hits[name].add(sid)
                components["mandatory-regressions"].add(sid)
    components["closure"] = set().union(*(components[name] for name in NAMES[:6]))
    previous_closure_path = ROOT / previous["components"]["closure"]["path"]
    assert sha(previous_closure_path) == previous["components"]["closure"]["sha256"]
    previous_closure = set(previous_closure_path.read_text().splitlines())
    assert len(previous_closure) == previous["components"]["closure"]["count"] == 1440
    components["new-dependencies"] = components["closure"] - previous_closure
    components["retired-dependencies"] = previous_closure - components["closure"]
    # The reviewer explicitly identified no unchanged previously reviewed row
    # whose evidence is invalidated outside corrected IDs. Existing occupied
    # rows were either corrected or remained valid; newly exposed rows enter
    # through new-dependencies.
    components["explicit-invalidated"] = set()
    components["delta"] = changed | components["new-dependencies"] | components["explicit-invalidated"]
    assert changed <= components["closure"] and components["closure"] <= set(ids)
    order = {sid: index for index, sid in enumerate(ids)}
    files = {}
    for name in NAMES:
        path = HERE / (name + "-ids.txt")
        ordered = sorted(components[name], key=order.__getitem__)
        write_new(path, "".join(sid + "\n" for sid in ordered))
        files[name] = {"path": str(path.relative_to(ROOT)), "count": len(ordered),
                       "sha256": sha(path), "newline": "UTF-8 LF; one stable ID per line"}
    nontext = HERE / "nontranslatable-context.txt"
    nontext_lines = [
        "GetCharacterOnPlace returns the exact article-free UI characterName_<enum> label; see pinned consumer-context.json.\n",
        "Compiled Yarn program SHA-256: " + consumer["compiledProgramSha256"] + "\n",
        "Consumer evidence SHA-256: " + sha(consumer_path) + "\n",
        "NotTrue key line:NotTrue_Entrance_Occupied_0abf2b1 is absent from pinned compiled program; runtime reachability unverified.\n",
    ]
    write_new(nontext, "".join(nontext_lines))
    review_path = HERE / "closure-review-rows.jsonl"
    review_rows = []
    for sid in sorted(components["closure"], key=order.__getitem__):
        row = source_rows[sid]
        info = inventory.get(sid, {})
        review_rows.append({"ordinal": row["ordinal"], "stableId": sid,
                            "collection": row["collection"], "key": row["key"],
                            "nodeNames": info.get("nodeNames", []),
                            "authoredPath": row["authoredPath"],
                            "source": row["source"], "target": target_by_id[sid],
                            "sourceSha256": row["sourceSha256"],
                            "targetSha256": text_sha(target_by_id[sid]),
                            "components": [name for name in NAMES[:6] if sid in components[name]]})
    write_new(review_path, "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                                   for row in review_rows))
    delta_path = HERE / "delta-review-rows.jsonl"
    write_new(delta_path, "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                                   for row in review_rows if row["stableId"] in components["delta"]))
    group_path = HERE / "selector-groups.json"
    groups = {"concepts": {name: {"regex": pattern, "count": len(concept_hits[name]),
                                   "idsSha256": text_sha("".join(sid + "\n" for sid in sorted(concept_hits[name], key=order.__getitem__)))}
                           for name, pattern in CONCEPTS.items()},
              "mandatory": {name: {"regex": MANDATORY.get(name, "all UI and supplemental static"),
                                     "count": len(mandatory_hits[name]),
                                     "idsSha256": text_sha("".join(sid + "\n" for sid in sorted(mandatory_hits[name], key=order.__getitem__)))}
                            for name in sorted(mandatory_hits)},
              "dynamicOccupant": {"selector": "accepted table rows with Occupied in source key and format slot; exclude documented item-gift branch",
                                  "manifestCandidates": 59, "characterLabelConsumers": 58,
                                  "excludedGiftItemStableId": item_path["stableId"],
                                  "consumerIdsSha256": text_sha("".join(sid + "\n" for sid in sorted(occupied_ids, key=order.__getitem__))),
                                  "uiCharacterNameLabels": 57,
                                  "labelIdsSha256": text_sha("".join(sid + "\n" for sid in sorted(label_ids, key=order.__getitem__)))}}
    write_new(group_path, json.dumps(groups, ensure_ascii=False, indent=2) + "\n")
    authored = [{"path": item["path"], "sha256": sha(ROOT / item["path"])}
                for item in json.loads((ROOT / "Documentation/nl-text-progress.json").read_text())["authoredBatches"]]
    authored_set_hash = text_sha("".join(item["path"] + " " + item["sha256"] + "\n" for item in authored))
    manifest = {
        "schemaVersion": 1, "locale": "nl", "cycle": 2,
        "status": "correction closure and exact delta ready for same independent reviewer; not yet clean or editorially accepted",
        "gameVersion": "1.3.19", "sourceLocale": "ru", "acceptedUnits": 16538,
        "recipePath": str(Path(__file__).relative_to(ROOT)), "recipeSha256": sha(Path(__file__)),
        "adjudicationPath": str(adjudication_path.relative_to(ROOT)),
        "adjudicationSha256": sha(adjudication_path),
        "preflightSha256": sha(CYCLE / "complete-batch-preflight-v2.json"),
        "beforeRowsSha256": sha(CYCLE / "before-rows.jsonl"),
        "afterRowsSha256": sha(CYCLE / "after-rows.jsonl"),
        "pass1ReviewRowsSha256": sha(pass_path),
        "pins": adjudication["pins"],
        "manual": {"authoredBatches": authored, "authoredSetSha256": authored_set_hash,
                   "staticMapSha256": sha(ROOT / "Translations/nl/static-text-map.json"),
                   "creditsRoleMapSha256": sha(ROOT / "Translations/nl/credits-role-map.json")},
        "derived": {"staticDraftSha256": sha(static),
                    "preserveExactAfterSha256": validation["fullExact"]["sha256"],
                    "structuralValidationSha256": sha(validation_path)},
        "imagePlan": "owner excluded translated images and textures; no changed image plan",
        "components": files,
        "selectorGroupsPath": str(group_path.relative_to(ROOT)),
        "selectorGroupsSha256": sha(group_path),
        "reviewRowsPath": str(review_path.relative_to(ROOT)),
        "reviewRowsSha256": sha(review_path),
        "nontranslatableContext": {"path": str(nontext.relative_to(ROOT)), "count": len(nontext_lines),
                                     "sha256": sha(nontext)},
        "previousClosurePath": str(previous_closure_path.relative_to(ROOT)),
        "previousClosureSha256": sha(previous_closure_path),
        "previousIndependentReviewEvidenceSha256": sha(ROOT / "Translations/nl/independent-review-01/evidence-manifest.json"),
        "consumerContextPath": str(consumer_path.relative_to(ROOT)),
        "consumerContextSha256": sha(consumer_path),
        "deltaReviewRowsPath": str(delta_path.relative_to(ROOT)),
        "deltaReviewRowsSha256": sha(delta_path),
        "closureReviewSet": "delta-ids.txt = changed IDs + (current closure - previous closure) + explicitly invalidated prior IDs; retired IDs listed separately",
        "runtime": "not-run", "independentReview": "pending", "editorialAcceptance": "pending",
        "selectorLimits": "All 59 accepted occupied-key format-slot rows are enumerated from the pinned manifest and reconciled to reviewer candidates. One Jacket item-gift slot is excluded from the character-label binding. The remaining 58 plus 57 UI characterName labels are runtime dependencies; unbound NotTrue reachability remains unknown. Node/key-family context uses inventory topology, not proof of compiled execution order.",
        "explicitInvalidatedRationale": "No unchanged previously reviewed ID has separately invalidated evidence: 38 corrected IDs are already in delta, and 50 newly exposed character-label consumers enter through new-dependencies. Valid previously reviewed rows need no repeat read.",
    }
    write_new(out, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"Changed {len(changed)}; closure {len(components['closure'])}; review rows {len(review_rows)}")


if __name__ == "__main__":
    main()
