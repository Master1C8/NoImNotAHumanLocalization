#!/usr/bin/env python3
"""Build or verify the Filipino correction cycle 001 reviewer closure.

This reads pinned source and authored evidence. It never changes translation files.
The first write is immutable; --verify recomputes the whole result.
"""

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCALE = ROOT / "Translations/fil"
OUT = LOCALE / "semantic-correction-cycle-001.closure.json"
PAIRED = LOCALE / "semantic-correction-cycle-001.paired.jsonl"
G = {
    "UI": "0cbd8a7a4f543344bb95659de87f67a5",
    "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6",
    "Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def id_hash(ids):
    return hashlib.sha256("".join(x + "\n" for x in ids).encode()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def build():
    before_path = LOCALE / "semantic-correction-cycle-001.before.json"
    after_path = LOCALE / "semantic-correction-cycle-001.after.json"
    validation_path = LOCALE / "semantic-correction-cycle-001.full-structural-validation.json"
    before, after, validation = map(load, (before_path, after_path, validation_path))
    require(sha(before_path) == after["beforeEvidenceSha256"], "Before evidence changed")
    require(sha(validation_path) == after["fullStructuralValidationSha256"], "Full gate changed")
    require(sha(LOCALE / "semantic-review-progress.json") == before["firstPassProgressSha256"],
            "First-pass progress changed")
    require(sha(LOCALE / "semantic-review-findings-in-progress.json") == before["firstPassFindingsSha256"],
            "First-pass findings changed")
    for item in before["sourceAndGlossaryFingerprints"].values():
        require(sha(ROOT / item["path"]) == item["sha256"], "Source or glossary changed")
    require(validation["checkedIds"] == 16538 and validation["missingIds"] == 0
            and validation["extraIds"] == 0, "Full structural gate incomplete")
    for item in after["files"]:
        require(sha(ROOT / item["path"]) == item["afterSha256"], "Corrected batch changed")
        require(sha(ROOT / item["validationPath"]) == item["validationSha256"],
                "Corrected validation sidecar changed")

    authored = set()
    targets = {}
    for item in validation["batchReports"]:
        require(sha(ROOT / item["path"]) == item["sha256"], "Batch changed")
        doc = load(ROOT / item["path"])
        guid = G[doc["collection"]]
        for entry in doc["entries"]:
            sid = f"string:{guid}:{entry['id']}"
            require(sid not in authored, "Duplicate authored ID")
            authored.add(sid)
            targets[sid] = entry["target"]
    for entry in load(LOCALE / "static-text-draft.json")["entries"]:
        sid = entry["stableId"]
        require(sid not in authored, "Duplicate static ID")
        authored.add(sid)
        targets[sid] = entry["target"]
    require(len(authored) == 16538, "Accepted denominator changed")

    inventory = [json.loads(line) for line in
                 (ROOT / "Source/localization-inventory-v3/strings.jsonl").open()]
    order = [row["stableId"] for collection in ("UI", "ChecksDialogs", "Dialogs")
             for row in inventory if row["collection"] == collection
             and row["stableId"] in authored]
    static_order = [entry["stableId"] for entry in
                    load(LOCALE / "static-text-draft.json")["entries"]]
    order += static_order
    require(len(order) == len(set(order)) == 16538 and set(order) == authored,
            "Canonical accepted order has missing, extra or duplicate IDs")
    rank = {sid: i for i, sid in enumerate(order)}
    source = {row["stableId"]: row for row in inventory if row["stableId"] in authored}
    source.update({row["stableId"]: row for row in
                   (json.loads(line) for line in
                    (ROOT / "Source/localization-inventory-v3/static-text.jsonl").open())
                   if row["stableId"] in authored})

    changed = {row["stableId"] for row in before["rows"]}
    context = {item["stableId"] for row in before["rows"] for item in row["context"]}
    require(changed <= authored and context <= authored, "Finding or context outside accepted scope")
    changed_text = {source[sid]["source"] for sid in changed}
    repetition = {sid for sid in order if source[sid]["source"] in changed_text}
    require(changed <= repetition, "Exact-source repetition selector lost changed IDs")

    # These referents are directly affected by the 64 corrections. Broad Russian
    # stems deliberately include inflected forms and every accepted collection.
    referents = {
        "fema": r"(?i)\b(?:кчс|комитет[а-яё]*)\b",
        "visitors": r"(?i)\bгост[а-яё]*\b",
        "smile-guide-and-clock": r"гриб|Гриб|стрелк|Стрелк|час[аоы]|Час[аоы]",
        "board-up": r"заколот|Заколот|забива|Забива|окн|Окн",
        "kinship-and-reveal": r"сестр|Сестр|брат|Брат|муж|Муж|доч|Доч|родител|Родител|родствен|Родствен|сводн|Сводн|пап|Пап|матер|Матер|мать|Мать",
        "skin-irritation": r"раздражен|Раздражен|кож|Кож",
        "photo-and-weapon": r"фото|Фото|пл[её]нк|Пл[её]нк|щёлк|Щёлк|ружь|Ружь",
        "teeth": r"зуб|Зуб|д[её]сн|Д[её]сн",
        "quarantine": r"карантин|Карантин",
        "for-rest-order": r"заказ|Заказ|доставк|Доставк",
        "sulfur": r"\bсер[аыеуой]\b|\bСер[аыеуой]\b",
        "radio-subject": r"субъект|Субъект",
    }
    referent_groups = {}
    for name, pattern in referents.items():
        matched = {sid for sid in order if re.search(pattern, source[sid]["source"])}
        require(matched, "Empty glossary referent selector: " + name)
        referent_groups[name] = matched
    glossary_referent = set().union(*referent_groups.values())

    # A changed line and explicit context can share a scene or branch with
    # options and dynamic placeholders. Include the entire serialized node.
    nodes = set()
    for sid in changed | context:
        nodes.update(source[sid].get("nodeNames", []))
    runtime_binding = {sid for sid in order if
                       set(source[sid].get("nodeNames", [])) & nodes}
    compiled = bytes(load(ROOT / "Source/glossary-corpus-v2/runtime-bindings.json")
                     ["sharedassets0.assets:2743"]["compiledYarnProgram"])
    require(hashlib.sha256(compiled).hexdigest() == before["compiledYarnProgramSha256"],
            "Serialized compiled Yarn program changed")
    runtime_compiled = {sid for sid in runtime_binding
                        if source[sid].get("key") and
                        source[sid]["key"].encode() in compiled}
    runtime_uncompiled = runtime_binding - runtime_compiled
    dynamic_consumers = {sid for sid in runtime_binding
                         if re.search(r"\{[0-9]+\}", source[sid]["source"])}
    require(changed - runtime_binding ==
            {row["stableId"] for row in before["rows"]
             if not row["nodeNames"]}, "Unexpected changed node binding gap")

    option_sources = {item["source"] for item in
                      load(LOCALE / "common-options-001.authored.json")["phrases"]}
    mandatory_patterns = {
        "family-identity": r"(?i)сестр|брат|матер|мать|мам|отец|пап|доч|сын|ж[её]н|муж|бабуш|дедуш|\b(?:он|она|его|её|ее|ему|ей|им|них|ними)\b",
        "guest-human": r"гост|Гост|человек|Человек|люд|Люд|нечеловек|Нечеловек|фема|ФЕМА|FEMA|визит|Визит",
        "profanity-humor": r"бля|Бля|нахуй|нахер|говн|Говн|жоп|Жоп|пизд|Пизд|[её]б|[ЕЁ]б|долбо|Долбо|сука|Сука|шутк|Шутк|смешн|Смешн",
        "markup-format": r"\{[0-9]+\}|<[^<>]+>",
    }
    mandatory_groups = {
        "all-ui": {sid for sid in order if source[sid].get("collection") == "UI"},
        "all-static": {sid for sid in order if sid.startswith("tmp:")},
        "all-common-option-exact-sources": {sid for sid in order
                                            if source[sid]["source"] in option_sources},
    }
    for name, pattern in mandatory_patterns.items():
        mandatory_groups[name] = {sid for sid in order if
                                  re.search(pattern, source[sid]["source"])}
    mandatory_regression = set().union(*mandatory_groups.values())
    require(len(mandatory_groups["all-common-option-exact-sources"]) == 2675,
            "Common-option selector missed the independently authored Нет row")
    require(all(mandatory_groups.values()), "Empty mandatory regression group")

    components = {"changed": changed, "explicitContext": context,
                  "exactSourceRepetition": repetition,
                  "glossaryReferent": glossary_referent,
                  "runtimeBinding": runtime_binding,
                  "mandatoryRegression": mandatory_regression}
    closure = set().union(*components.values())
    require(closure <= authored, "Closure outside accepted scope")

    def packed(name, members):
        ids = [sid for sid in order if sid in members]
        return {"name": name, "count": len(ids), "idsSha256": id_hash(ids), "ids": ids}

    packed_components = [packed(name, members) for name, members in components.items()]
    packed_referents = [dict(packed(name, members), selector=referents[name])
                        for name, members in referent_groups.items()]
    packed_mandatory = [dict(packed(name, members), selector=(
        "all accepted UI" if name == "all-ui" else
        "all accepted static" if name == "all-static" else
        "all accepted exact-source option phrases, including independent rows"
        if name == "all-common-option-exact-sources" else mandatory_patterns[name]))
        for name, members in mandatory_groups.items()]
    ids = [sid for sid in order if sid in closure]
    explained = set().union(*(set(item["ids"]) for item in packed_components))
    require(explained == closure, "Closure explanation mismatch")
    paired_rows = [{
        "acceptedOrdinal": rank[sid] + 1,
        "stableId": sid,
        "collection": source[sid].get("collection", "static"),
        "key": source[sid].get("key"),
        "nodeNames": source[sid].get("nodeNames", []),
        "source": source[sid]["source"],
        "sourceSha256": hashlib.sha256(source[sid]["source"].encode()).hexdigest(),
        "target": targets[sid],
        "components": [name for name, members in components.items() if sid in members],
    } for sid in ids]
    paired_raw = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
                         for row in paired_rows).encode()
    result = {
        "schemaVersion": 1, "locale": "fil", "gameVersion": "1.3.19",
        "status": "reproducible correction dependency closure for distinct reviewer; review pending",
        "beforeEvidenceSha256": sha(before_path), "afterEvidenceSha256": sha(after_path),
        "fullStructuralValidationSha256": sha(validation_path),
        "sourceAndGlossaryFingerprints": before["sourceAndGlossaryFingerprints"],
        "acceptedUnits": 16538, "acceptedOrderSha256": id_hash(order),
        "idHashConvention": "UTF-8 LF, one stable ID per line in canonical accepted order",
        "components": packed_components, "glossaryReferentSelectors": packed_referents,
        "mandatoryRegressionSelectors": packed_mandatory,
        "runtimeNodeCount": len(nodes), "runtimeNodes": sorted(nodes),
        "compiledYarnProgramSha256": before["compiledYarnProgramSha256"],
        "runtimeCompiledIds": packed("runtimeCompiled", runtime_compiled),
        "runtimeUncompiledIds": packed("runtimeUncompiled", runtime_uncompiled),
        "runtimeDynamicPlaceholderConsumers": packed("runtimeDynamicPlaceholderConsumers",
                                                     dynamic_consumers),
        "compiledAbsentChangedOrdinals": [row["acceptedOrdinal"] for row in before["rows"]
                                          if row["compiledKeyOccurrences"] == 0],
        "closureCount": len(ids), "closureIdsSha256": id_hash(ids), "closureIds": ids,
        "pairedPath": str(PAIRED.relative_to(ROOT)), "pairedRows": len(paired_rows),
        "pairedSha256": hashlib.sha256(paired_raw).hexdigest(),
        "unexplainedMissingIds": [], "unexplainedExtraIds": [],
        "independentReviewer": None,
        "reviewStatus": "not started; self reread and deterministic validation are not independent review",
    }
    return result, paired_raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    require(args.write != args.verify, "Choose --write or --verify")
    result, paired_raw = build()
    raw = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode()
    if args.write:
        require(not OUT.exists() and not PAIRED.exists(), "Immutable closure already exists")
        PAIRED.write_bytes(paired_raw)
        OUT.write_bytes(raw)
    else:
        require(OUT.read_bytes() == raw, "Stored closure differs from recomputed result")
        require(PAIRED.read_bytes() == paired_raw, "Stored paired review input differs")
    print(json.dumps({"path": str(OUT.relative_to(ROOT)), "sha256": sha(OUT),
                      "acceptedUnits": result["acceptedUnits"],
                      "closureCount": result["closureCount"],
                      "componentCounts": {x["name"]: x["count"] for x in result["components"]},
                      "unexplainedMissing": 0, "unexplainedExtra": 0}))


if __name__ == "__main__":
    main()
