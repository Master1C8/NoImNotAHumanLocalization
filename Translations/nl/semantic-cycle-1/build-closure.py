#!/usr/bin/env python3
"""Rebuild immutable Dutch correction closure in pinned canonical source order."""

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
NAMES = ("changed", "context", "repetitions", "glossary-referents",
         "runtime-bindings", "mandatory-regressions", "closure")


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
    "controller": r"(?iu)(геймпад|контроллер|джойстик)",
    "body-disposal": r"(?iu)(утилизац|труп|тел[ао] погибш)",
    "psychic-session": r"(?iu)(сеанс|Гостев[оы]|эксперт.*изгнан)",
    "for-rest": r"(?iu)(For Rest|Фор[ -]?Рест|доставк[а-яё]* (?:еды|продукт))",
    "radio-subject": r"(?iu)(субъ[е…\.]*кт|код 451|сожжен[а-яё]* тру)",
    "guest-person": r"(?iu)(Гост[ьи]|человек[а-яё]*|люд[а-яё]*|персон[а-яё]*)",
    "kchs": r"(?iu)(КЧС|сотрудник[а-яё]*|задержанн[а-яё]*)",
    "vigilante": r"(?iu)(охотник[а-яё]*|признак[а-яё]* Гост)",
    "neighbour": r"(?iu)(сосед[а-яё]*)",
    "step-family": r"(?iu)(сводн[а-яё]* родствен|арендодател[а-яё]*|высел[а-яё]*)",
    "occupied-house": r"(?iu)(жилец|жильц|лишн[а-яё]*|впуст[а-яё]*|пуск[а-яё]*)",
    "death": r"(?iu)(Смерт[ьи]|смерть)",
    "old-woman-address": r"(?iu)(дружоч[а-яё]*|дружок|милок|крыльц[а-яё]*)",
    "child-stretch": r"(?iu)(стра-а-а-шно|Доч[ье]|поможе-жете)",
    "person-and-cat": r"(?iu)(персон[а-яё]* с котом|кот[а-яё]*)",
    "rental": r"(?iu)(жильц[а-яё]*|ипотек[а-яё]*|аренд[а-яё]*)",
    "vegetable-callback": r"(?iu)(редиск[а-яё]*|овощ[а-яё]*)",
    "alcohol": r"(?iu)(выпить охота|пив[а-яё]*|самогон[а-яё]*)",
    "remembering": r"(?iu)(вспомина[а-яё]*|памят[а-яё]*)",
    "automatic-weapon": r"(?iu)(автомат[а-яё]*|огнестрел[а-яё]*)",
    "signs-and-body": r"(?iu)(сер[аыу] в ух|уш[а-яё]*|зуб[а-яё]*|глаз[а-яё]*|отпечатк[а-яё]* пальц|рук[а-яё]*)",
    "photo-check": r"(?iu)(фото[а-яё]*|щёлка[а-яё]*|из этого тоже будешь щёлкать)",
    "purge": r"(?iu)(чист[а-яё]* люд|карантин[а-яё]*)",
}

MANDATORY = {
    "gender-and-kinship": r"(?iu)(сестр|брат|матер|мать|мам|отец|пап|доч|сын|ж[её]н|муж|бабуш|дедуш|девуш|парен|женщин|мужчин|\b(?:он|она|его|её|ее|ему|ей|им|них|ними)\b)",
    "guest-and-human": r"(?iu)(гост[ьи]|человек|люд[ией]|нечеловек|фема|FEMA|визит[её]р)",
    "profanity-wordplay": r"(?iu)(бля|нахуй|нахер|ху[йяеюи]|говн|жоп|пизд|[её]б|долбо|сука|шутк|смешн|редиск|овощ|рифм)",
    "format-markup": r"\{[0-9]+\}|<[^<>]+>",
}


def main():
    out = HERE / "closure-manifest.json"
    assert not out.exists()
    adjudication_path = HERE / "adjudicated-corrections.json"
    validation_path = HERE / "structural-validation.json"
    adjudication = json.loads(adjudication_path.read_text())
    validation = json.loads(validation_path.read_text())
    assert validation["adjudicationSha256"] == sha(adjudication_path)
    assert validation["fullExact"]["result"] == "passed"
    pass_path = ROOT / "Translations/nl/semantic-review-rows-pass1.jsonl"
    rows = [json.loads(line) for line in pass_path.open()]
    assert len(rows) == 16538 and sha(pass_path) == adjudication["reviewRowsSha256"]
    ids = [row["stableId"] for row in rows]
    assert len(set(ids)) == len(ids)
    inventory = {row["stableId"]: row for row in
                 (json.loads(line) for line in (ROOT / "Source/localization-inventory-v3/strings.jsonl").open())}
    source_rows = {row["stableId"]: row for row in rows}
    target_by_id = {sid: row["target"] for sid, row in source_rows.items()}
    for record in adjudication["corrections"]:
        target_by_id[record["stableId"]] = record["after"]
    before_strings = {record["before"] for record in adjudication["corrections"]}
    after_strings = {record["after"] for record in adjudication["corrections"]}
    source_strings = {record["source"] for record in adjudication["corrections"]}
    changed = {record["stableId"] for record in adjudication["corrections"]}
    assert len(changed) == 138
    node_names = set()
    families = set()
    for sid in changed:
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
        if (row["collection"] == "UI" and (key or "").startswith("settings_")) or (
            ("{0}" in source or "<" in source) and
            (set(info.get("nodeNames", [])) & node_names or key_family(key) in families)):
            components["runtime-bindings"].add(sid)
        if row["collection"] == "UI" or sid.startswith("tmp:"):
            mandatory_hits["ui-and-static"].add(sid)
            components["mandatory-regressions"].add(sid)
        for name, pattern in MANDATORY.items():
            if re.search(pattern, source):
                mandatory_hits[name].add(sid)
                components["mandatory-regressions"].add(sid)
    components["closure"] = set().union(*(components[name] for name in NAMES if name != "closure"))
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
    write_new(nontext, "")
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
                            "components": [name for name in NAMES[:-1] if sid in components[name]]})
    write_new(review_path, "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                                   for row in review_rows))
    group_path = HERE / "selector-groups.json"
    groups = {"concepts": {name: {"regex": pattern, "count": len(concept_hits[name]),
                                   "idsSha256": text_sha("".join(sid + "\n" for sid in sorted(concept_hits[name], key=order.__getitem__)))}
                           for name, pattern in CONCEPTS.items()},
              "mandatory": {name: {"regex": MANDATORY.get(name, "all UI and supplemental static"),
                                     "count": len(mandatory_hits[name]),
                                     "idsSha256": text_sha("".join(sid + "\n" for sid in sorted(mandatory_hits[name], key=order.__getitem__)))}
                            for name in sorted(mandatory_hits)}}
    write_new(group_path, json.dumps(groups, ensure_ascii=False, indent=2) + "\n")
    authored = [{"path": item["path"], "sha256": sha(ROOT / item["path"])}
                for item in json.loads((ROOT / "Documentation/nl-text-progress.json").read_text())["authoredBatches"]]
    authored_set_hash = text_sha("".join(item["path"] + " " + item["sha256"] + "\n" for item in authored))
    static = ROOT / "Translations/nl/static-text-draft.json"
    manifest = {
        "schemaVersion": 1, "locale": "nl", "cycle": 1,
        "status": "correction closure ready for independent review; not independently reviewed or editorially accepted",
        "gameVersion": "1.3.19", "sourceLocale": "ru", "acceptedUnits": 16538,
        "recipePath": str(Path(__file__).relative_to(ROOT)), "recipeSha256": sha(Path(__file__)),
        "adjudicationPath": str(adjudication_path.relative_to(ROOT)),
        "adjudicationSha256": sha(adjudication_path),
        "preflightSha256": sha(HERE / "complete-batch-preflight.json"),
        "beforeRowsSha256": sha(HERE / "before-rows.jsonl"),
        "afterRowsSha256": sha(HERE / "after-rows.jsonl"),
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
        "nontranslatableContext": {"path": str(nontext.relative_to(ROOT)), "count": 0,
                                     "sha256": sha(nontext)},
        "closureReviewSet": "all IDs in closure-ids.txt; first independent cycle has no previous closure",
        "runtime": "not-run", "independentReview": "pending", "editorialAcceptance": "pending",
        "selectorLimits": "Node/key-family grouping uses inventory topology; compiled Yarn execution order is not asserted. Independent reviewer must inspect actual branch and dynamic consumer context where required.",
    }
    write_new(out, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"Changed {len(changed)}; closure {len(components['closure'])}; review rows {len(review_rows)}")


if __name__ == "__main__":
    main()
