#!/usr/bin/env python3
"""Build/verify the Hindi cycle-001 independent-review dependency closure.

Only pinned source inventories and already authored Hindi files are read. The
output is an ordered set of accepted IDs, not an assertion of editorial review.
"""

import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HI = ROOT / "Translations/hi"
SOURCE = ROOT / "Source/localization-inventory-v3/strings.jsonl"
STATIC = ROOT / "Source/localization-inventory-v3/static-text.jsonl"
GLOSSARY = ROOT / "Documentation/glossary-translations/hi/layer.json"
RUNTIME = ROOT / "Source/glossary-corpus-v2/runtime-bindings.json"
OUT = HI / "semantic-cycle-001-closure.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jread(path):
    return json.loads(path.read_text(encoding="utf-8"))


def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def id_hash(ids):
    return hashlib.sha256(("\n".join(ids) + "\n").encode()).hexdigest()


def varint(buf, offset):
    value = shift = 0
    while True:
        byte = buf[offset]
        offset += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, offset
        shift += 7


def fields(buf):
    offset = 0
    while offset < len(buf):
        tag, offset = varint(buf, offset)
        number, wire = tag >> 3, tag & 7
        if wire == 0:
            value, offset = varint(buf, offset)
        elif wire == 1:
            value = buf[offset:offset + 8]
            offset += 8
        elif wire == 2:
            length, offset = varint(buf, offset)
            value = buf[offset:offset + length]
            offset += length
        elif wire == 5:
            value = buf[offset:offset + 4]
            offset += 4
        else:
            raise ValueError(f"unsupported protobuf wire type {wire}")
        yield number, wire, value


def compiled_nodes():
    blob = bytes(jread(RUNTIME)["sharedassets0.assets:2743"]["compiledYarnProgram"])
    result = {}
    for number, wire, entry in fields(blob):
        if (number, wire) != (2, 2):
            continue
        parts = list(fields(entry))
        if len(parts) < 2 or parts[0][:2] != (1, 2) or parts[1][:2] != (2, 2):
            continue
        name = parts[0][2].decode("utf-8")
        node = parts[1][2]
        lines = []
        for field_number, field_wire, instruction in fields(node):
            if (field_number, field_wire) != (2, 2):
                continue
            for _, operand_wire, operand in fields(instruction):
                if operand_wire != 2:
                    continue
                try:
                    text = operand.decode("utf-8")
                except UnicodeDecodeError:
                    continue
                # Yarn's string operand is wrapped in its value submessage.
                for match in re.finditer(r"line:[A-Za-z0-9_]+", text):
                    lines.append(match.group())
        if lines:
            result[name] = list(dict.fromkeys(lines))
    return result


# Deliberately narrow source-language referents for facts corrected this cycle.
# Each motif is checked against approved glossary entries before it is used.
GLOSSARY_MOTIFS = {
    "fema": r"КЧС|Комитет[а-яё ]*Чрезвычайн",
    "pale-visitor": r"бледн[а-яё]* (?:маньяк|Гость|человек)",
    "auracam-film": r"фотопл[её]нк|Ауракам",
    "photo-check": r"(?:сво[юи] фотографи[юи]|свой снимок|фотографир[а-яё]* собеседник)",
    "hairless-armpits": r"подмышк[а-яё]*|брить[яе]",
    "armpit-fungus": r"грибок на|грибк[а-яё]* на",
    "sun-faced-one": r"СОЛНЕЧН[А-ЯЁ]* ЛИДЕР|Солнцеликий",
    "death": r"(?:Смерть|смерть) (?:говорит|пряч|верн)|непризнанный брат",
    "quarantine-zone": r"карантинн[а-яё]* зон",
    "visitor-signs": r"признак[а-яё]* Гост|красн[а-яё]* глаз",
}


def build():
    original = jread(HI / "semantic-pass-001-progress-immutable.json")
    findings = jread(HI / "semantic-pass-001-findings-immutable.json")
    adjudication = jread(HI / "semantic-cycle-001-adjudication.json")
    gate = jread(HI / "semantic-cycle-001-structural-gate.json")
    assert digest(SOURCE) == original["reviewedInputHashes"][str(SOURCE.relative_to(ROOT))]
    assert digest(STATIC) == original["reviewedInputHashes"][str(STATIC.relative_to(ROOT))]
    assert digest(GLOSSARY) == original["reviewedInputHashes"][str(GLOSSARY.relative_to(ROOT))]
    assert digest(HI / "semantic-pass-001-progress-immutable.json") == adjudication["firstPassProgressSha256"]
    assert digest(HI / "semantic-pass-001-findings-immutable.json") == adjudication["firstPassFindingsSha256"]
    assert len(findings["findings"]) == len(adjudication["items"]) == 94
    assert digest(RUNTIME) == adjudication["compiledRuntimeBindingsSha256"]
    assert gate["acceptedIds"] == 16538 and not any(gate[x] for x in ("duplicateIds", "missingIds", "extraIds", "exactSpanFailures"))
    for file in gate["files"]:
        assert digest(ROOT / file["path"]) == file["sha256"], file["path"]
        if file.get("validationPath"):
            assert digest(ROOT / file["validationPath"]) == file["validationSha256"], file["validationPath"]

    all_source = jsonl(SOURCE)
    all_static = jsonl(STATIC)
    authored_keys = set()
    static_ids = set()
    for file in gate["files"]:
        data = jread(ROOT / file["path"])
        if file["path"].endswith("static-text-draft.json"):
            static_ids.update(row["stableId"] for row in data["entries"])
        else:
            authored_keys.update((data["collection"], str(row["id"])) for row in data["entries"])
    selected_source = [row for row in all_source if (row["collection"], row["stableId"].rsplit(":", 1)[1]) in authored_keys]
    selected_static = [row for row in all_static if row["stableId"] in static_ids]
    assert len(selected_source) == 16360 and len(selected_static) == 178
    accepted = selected_source + selected_static
    ids = [row["stableId"] for row in accepted]
    assert len(ids) == len(set(ids)) == gate["acceptedIds"]
    assert id_hash(ids) == original["reviewOrderIdListSha256LfFinalNewline"]
    order = {sid: index for index, sid in enumerate(ids)}
    rows = {row["stableId"]: row for row in accepted}
    by_key = collections.defaultdict(list)
    by_source = collections.defaultdict(list)
    for row in selected_source:
        by_key[row["key"]].append(row["stableId"])
        # Keep an exact full-source repeat as well as a speaker-free repeat.
        by_source[row["source"]].append(row["stableId"])
        by_source[re.sub(r"^[A-Za-z][A-Za-z0-9_]*: ", "", row["source"])].append(row["stableId"])

    components = {name: set() for name in (
        "changed", "sceneContext", "repetition", "glossaryReferent", "runtimeBinding", "mandatoryRegression"
    )}
    changed = {item["stableId"] for item in adjudication["items"]}
    assert len(changed) == 94 and changed <= order.keys()
    components["changed"] = changed
    for item in adjudication["items"]:
        for index in item.get("relatedReviewIndices", []):
            assert 0 <= index < len(ids)
            components["sceneContext"].add(ids[index])
        source = rows[item["stableId"]]["source"]
        variants = {source, re.sub(r"^[A-Za-z][A-Za-z0-9_]*: ", "", source)}
        for variant in variants:
            components["repetition"].update(by_source[variant])

    # Compiled instruction ordering is used for bounded neighbors and for
    # complete dynamic-placeholder consumers, including entry/choice branches.
    nodes = compiled_nodes()
    runtime_occurrences = collections.defaultdict(list)
    for name, lines in nodes.items():
        for index, key in enumerate(lines):
            runtime_occurrences[key].append((name, index))
    runtime_fragments = []
    uncompiled_changed_rows = []
    changed_runtime_nodes = set()
    for item in adjudication["items"]:
        row = rows[item["stableId"]]
        key = row.get("key")
        occurrences = runtime_occurrences.get(key, [])
        if not occurrences:
            # Serialized source candidates can be unreferenced in compiled Yarn.
            inferred_node = key[5:].rsplit("_", 1)[0] if key and key.startswith("line:") else None
            matched_node = inferred_node in nodes
            if inferred_node:
                for candidate in selected_source:
                    if (candidate.get("key") or "").startswith(f"line:{inferred_node}_") or inferred_node in candidate.get("nodeNames", []):
                        components["sceneContext"].add(candidate["stableId"])
                if matched_node:
                    for candidate_key in nodes[inferred_node]:
                        components["runtimeBinding"].update(by_key[candidate_key])
            uncompiled_changed_rows.append({
                "stableId": item["stableId"], "sourceKey": key,
                "inferredNode": inferred_node, "inferredNodeCompiled": matched_node,
                "status": "accepted source row has no exact compiled line reference; scene family and serialized neighbors included",
            })
            idx = order[item["stableId"]]
            for near in range(max(0, idx - 2), min(len(selected_source), idx + 3)):
                if accepted[near]["collection"] == row["collection"]:
                    components["sceneContext"].add(ids[near])
            continue
        for node, index in occurrences:
            changed_runtime_nodes.add(node)
            keys = nodes[node]
            for near in keys[max(0, index - 2):min(len(keys), index + 3)]:
                components["sceneContext"].update(by_key[near])
            if any("{" in rows[sid]["source"] for candidate_key in keys for sid in by_key[candidate_key]):
                for near in keys:
                    components["runtimeBinding"].update(by_key[near])
                runtime_fragments.append({"node": node, "lineKey": key, "consumer": "compiled Yarn dynamic line instruction", "untranslated": True})

    glossary = jread(GLOSSARY)
    for term, pattern in GLOSSARY_MOTIFS.items():
        assert term in glossary, term
        regex = re.compile(pattern, re.IGNORECASE)
        for row in selected_source:
            if regex.search(row["source"]):
                components["glossaryReferent"].add(row["stableId"])

    # The high-risk deterministic regression catalog is the entire UI and TMP
    # surface, plus every compiled node carrying an edited line with a slot.
    components["mandatoryRegression"].update(row["stableId"] for row in selected_source if row["collection"] == "UI")
    components["mandatoryRegression"].update(static_ids)
    for node in changed_runtime_nodes:
        if any("{" in rows[sid]["source"] for key in nodes[node] for sid in by_key[key]):
            for key in nodes[node]:
                components["mandatoryRegression"].update(by_key[key])

    union = set().union(*components.values())
    assert union <= set(ids)
    ordered_components = {name: [sid for sid in ids if sid in member] for name, member in components.items()}
    closure = [sid for sid in ids if sid in union]
    per_id = [{"stableId": sid, "reviewIndex": order[sid], "components": [name for name in components if sid in components[name]]} for sid in closure]
    assert len(closure) == len(set(closure))
    assert set(closure) == union
    result = {
        "schemaVersion": 1,
        "locale": "hi",
        "gameVersion": "1.3.19",
        "status": "complete deterministic dependency closure; independent semantic review pending",
        "sourceOrderIdListSha256LfFinalNewline": id_hash(ids),
        "sourceInventorySha256": digest(SOURCE),
        "staticInventorySha256": digest(STATIC),
        "glossaryLayerSha256": digest(GLOSSARY),
        "compiledRuntimeBindingsSha256": digest(RUNTIME),
        "firstPassProgressSha256": digest(HI / "semantic-pass-001-progress-immutable.json"),
        "firstPassFindingsSha256": digest(HI / "semantic-pass-001-findings-immutable.json"),
        "adjudicationSha256": digest(HI / "semantic-cycle-001-adjudication.json"),
        "postCorrectionStructuralGateSha256": digest(HI / "semantic-cycle-001-structural-gate.json"),
        "selectorSha256": digest(Path(__file__)),
        "acceptedCount": len(ids),
        "changedCount": len(changed),
        "closureCount": len(closure),
        "closureIdListSha256LfFinalNewline": id_hash(closure),
        "missingAcceptedIds": [],
        "extraUnacceptedIds": [],
        "componentCounts": {name: len(value) for name, value in ordered_components.items()},
        "componentIdListSha256LfFinalNewline": {name: id_hash(value) for name, value in ordered_components.items()},
        "components": ordered_components,
        "glossaryReferentMotifs": GLOSSARY_MOTIFS,
        "nontranslatableRuntimeBindingFragments": list({(x["node"], x["lineKey"]): x for x in runtime_fragments}.values()),
        "changedRowsWithoutExactCompiledLineReference": uncompiled_changed_rows,
        "reviewRows": per_id,
        "scopeNote": "Compiled scene neighbors, exact/reduced speaker repetitions, pinned glossary motifs, whole dynamic consumer nodes, and UI/TMP regression catalog. Unmatched accepted IDs remain outside this dependency closure, not outside the completed first pass.",
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    result = build()
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.verify:
        assert OUT.read_text(encoding="utf-8") == text, "closure differs from regenerated result"
        print(f"verified {result['closureCount']} closure IDs / {result['acceptedCount']} accepted IDs")
    else:
        OUT.write_text(text, encoding="utf-8")
        print(f"wrote {result['closureCount']} closure IDs / {result['acceptedCount']} accepted IDs")
        print(result["componentCounts"])


if __name__ == "__main__":
    main()
