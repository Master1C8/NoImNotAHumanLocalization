#!/usr/bin/env python3
"""Assemble corrected Hebrew format lines over pinned compiled consumer domains."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CYCLE = Path(__file__).resolve().parent
HE = CYCLE.parent
IR = HE / "independent-review-01"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def once(path, obj):
    data = (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode()
    if path.exists():
        assert path.read_bytes() == data
    else:
        path.write_bytes(data)


def main():
    adjudications = json.loads((CYCLE / "adjudications.json").read_text())["records"]
    pins = json.loads((CYCLE / "input-pins.json").read_text())
    source = {r["stableId"]: r for r in map(json.loads, (ROOT / pins["sourceInventory"]["stringsPath"]).open())}
    label_by_key = {}
    for path in sorted(HE.glob("ui-batch-[0-9][0-9][0-9].json")):
        draft = CYCLE / "after-authored" / path.name
        batch = json.loads((draft if draft.exists() else path).read_text())
        for row in batch["entries"]:
            sid = "string:0cbd8a7a4f543344bb95659de87f67a5:" + str(row["id"])
            key = source[sid].get("key")
            if key:
                label_by_key[key] = row["target"]
    domain = json.loads((IR / "character-consumer-domain.json").read_text())
    characters = {r["name"]: r for r in domain["characters"]}
    compiled = {r["stableId"]: r for r in
                json.loads((IR / "all-format-consumer-context.json").read_text())["rows"]}
    items = json.loads((IR / "dynamic-consumer-il-02.json").read_text())
    # These enum values are pinned in the compiled consumer evidence.
    enum = items["consumableEnum"]
    item_keys = ["Enerjeka", "Cigarette", "Coffee", "CatFood", "Kombucha", "Povistka"]
    assert [enum[k] for k in item_keys] == [3, 1, 2, 6, 8, 7]
    assembled = []
    unresolved_labels = []
    for a in adjudications:
        if "{0}" not in a["after"]:
            continue
        sid = a["stableId"]
        consumers = compiled[sid]["consumer"]
        assert len(consumers) == 1, sid
        instructions = consumers[0]["instructions"]
        method = [z["operands"][0] for z in instructions
                  if z["opcode"] == 12 and z["operands"]]
        assert method
        binding = method[-1]
        if binding == "GetCharacterOnPlace":
            character = [z["operands"][0] for z in instructions
                         if z["opcode"] == 6 and z["operands"]][-1]
            place = characters[character]["place"]
            alternatives = [x for x in domain["placeDomains"][str(place)] if x != character]
            assert alternatives
            variants = []
            for other in alternatives:
                label = label_by_key.get("characterName_" + other)
                if label is None:
                    unresolved_labels.append({"stableId": sid, "character": other,
                        "place": place, "reason": "no exact characterName_ key in accepted UI source; runtime fallback unverified"})
                    continue
                variants.append({"value": label, "assembled": a["after"].replace("{0}", label),
                                 "occupant": other})
            assembled.append({"stableId": sid, "method": binding, "caller": character,
                              "place": place, "alternatives": alternatives, "variants": variants})
        elif binding == "LocalizeItem":
            assert method[-2:] == ["PeekDeficitItem", "LocalizeItem"]
            variants = []
            for name in item_keys:
                key = "consumable_" + name.lower() + "_name"
                label = label_by_key.get(key)
                assert label, key
                variants.append({"value": label, "assembled": a["after"].replace("{0}", label),
                                 "item": name, "enumValue": enum[name]})
            assembled.append({"stableId": sid, "method": binding, "variants": variants})
        else:
            raise AssertionError((sid, method))
    assert len(assembled) == 15
    # No character label is inserted after an indefinite יש construction in
    # the corrected full units. This is a mechanical guard, not a language verdict.
    for row in assembled:
        for variant in row["variants"]:
            value = variant["value"]
            display = variant["assembled"]
            assert "{0}" not in display and value in display
            assert "יש כאן " + value not in display
            assert "יש שם " + value not in display
            assert "כבר יש " + value not in display
    once(CYCLE / "consumer-preflight.json", {"schemaVersion": 1,
        "status": "actual compiled consumer domains assembled before authored application",
        "compiledContextSha256": sha(IR / "all-format-consumer-context.json"),
        "characterDomainSha256": sha(IR / "character-consumer-domain.json"),
        "itemDomainSha256": sha(IR / "dynamic-consumer-il-02.json"),
        "correctedFormatRows": len(assembled), "assembled": assembled,
        "unresolvedCharacterLabels": unresolved_labels,
        "limitation": "Static assembly only. An accepted UI key for characterName_Twins is absent; no runtime fallback or display was invented."})
    print(json.dumps({"correctedFormatRows": len(assembled),
                      "assembledVariants": sum(len(r["variants"]) for r in assembled),
                      "unresolvedLabels": len(unresolved_labels),
                      "sha256": sha(CYCLE / "consumer-preflight.json")}))


if __name__ == "__main__":
    main()
