#!/usr/bin/env python3
"""Reproduce Indonesian correction-cycle closure and exact independent-review delta.

This selects evidence only. It never generates translated wording or edits shared files.
Use --dry-run before freezing a cycle, --write once, and --verify afterward.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = Path(__file__).with_name("closure-selector-config-v3.json")
GUIDS = {
    "Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
    "UI": "0cbd8a7a4f543344bb95659de87f67a5",
    "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6",
}
PRONOUNS = re.compile(
    r"(?i)\b(?:он|она|её|его|ей|ему|вы|вас|вам|ваш\w*|ты|тебя|тебе|твой\w*)\b"
)


def raw(path):
    return (ROOT / path).read_bytes()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def load(path):
    return json.loads(raw(path))


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def list_bytes(order, selected):
    return "".join(sid + "\n" for sid in order if sid in selected).encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    config_path = args.config.resolve()
    assert config_path.is_relative_to(ROOT / "Translations/id")
    config = json.loads(config_path.read_text())
    assert config["schemaVersion"] == 3 and config["locale"] == "id"
    cycle = ROOT / config["cycleDirectory"]
    assert cycle.is_dir() and cycle.is_relative_to(ROOT / "Translations/id")
    assert digest(raw(config["previousClosure"])) == config["previousClosureSha256"]
    assert digest(raw(config["independentReview"])) == config["independentReviewSha256"]

    manifest = load("Source/preserve-exactly-v4.json")
    rules = manifest["tableRows"] + manifest["staticRows"]
    order = [r["stableId"] for r in rules]
    assert len(order) == len(set(order)) == 16538
    valid = set(order)
    rules_by_id = {r["stableId"]: r for r in rules}
    position = {sid: i + 1 for i, sid in enumerate(order)}
    source = {}
    for name in ("strings", "static-text"):
        path = ROOT / "Source/localization-inventory-v3" / (name + ".jsonl")
        for line in path.open():
            row = json.loads(line)
            if row["stableId"] in valid:
                assert row["stableId"] not in source
                source[row["stableId"]] = row
    assert set(source) == valid

    targets, owners = {}, {}
    locale = ROOT / "Translations/id"
    for path in sorted(locale.glob("*-batch-???.json")):
        if not re.fullmatch(r"(?:dialogue|ui|checks)-batch-\d{3}\.json", path.name):
            continue
        batch = json.loads(path.read_text())
        for entry in batch["entries"]:
            sid = "string:" + GUIDS[batch["collection"]] + ":" + str(entry["id"])
            assert sid not in targets
            targets[sid] = entry["target"]
            owners[sid] = str(path.relative_to(ROOT))
    static_path = locale / "static-text-draft.json"
    for entry in json.loads(static_path.read_text())["entries"]:
        sid = entry["stableId"]
        assert sid not in targets
        targets[sid] = entry["target"]
        owners[sid] = str(static_path.relative_to(ROOT))
    assert set(targets) == valid

    adjudication = load(config["cycleDirectory"] + "/adjudication.json")
    changed = {r["stableId"] for r in adjudication["rows"] if r["decision"] == "accepted"}
    assert len(changed) == len(adjudication["rows"]) == config["expectedChangedCount"]
    assert all(targets[r["stableId"]] == r["after"] for r in adjudication["rows"])
    nodes = {n for sid in changed for n in source[sid].get("nodeNames", [])}
    prefixes = tuple(config["context"]["uiKeyPrefixes"])
    context = {
        sid for sid in order
        if nodes.intersection(source[sid].get("nodeNames", []))
        or ((source[sid].get("key") or "").startswith(prefixes))
    }
    changed_sources = {source[sid]["source"] for sid in changed}
    repetitions = {sid for sid in order if source[sid]["source"] in changed_sources}
    patterns = {k: re.compile(v) for k, v in config["conceptSourceRegex"].items()}
    concepts = {
        sid for sid in order
        if any(p.search(source[sid]["source"]) for p in patterns.values())
    }
    # Enumerate phone UI dependencies from the compiled consumer's actual token.
    phone = config["phoneContactConsumer"]
    assert digest(raw(phone["compiledContextPath"])) == phone["compiledContextSha256"]
    compiled = load(phone["compiledContextPath"])["nodes"][phone["compiledNode"]]
    calls = [i for i, instruction in enumerate(compiled)
             if instruction["opcode"] == 12
             and instruction["operands"] == [phone["getPhoneNumberFunction"]]]
    assert len(calls) == 1
    call = calls[0]
    assert compiled[call-2]["opcode"] == 6
    token = compiled[call-2]["operands"][0]
    assert compiled[call+1]["opcode"] == 2 and compiled[call+1]["operands"][1] == 1.0
    assert compiled[call+2]["opcode"] == 3 and compiled[call+2]["operands"] == ["UnlockPhoneNumber " + token, 0.0]
    phone_contacts = {sid for sid in order if source[sid].get("collection") == "UI"
                      and source[sid].get("key") == phone["uiKeyPrefix"] + token}
    assert len(phone_contacts) == phone["expectedContactUiRows"]
    assert all(patterns[phone["sourcePatternKey"]].search(source[sid]["source"])
               for sid in phone_contacts)
    assert phone_contacts <= concepts
    def protected(sid):
        return any(rules_by_id[sid].get(k) for k in (
            "formatSlots", "tmpTags", "wholeTextExact", "exactSubstrings",
            "lineBreaks", "trailingWhitespace"))
    runtime = {
        sid for sid in changed | context | phone_contacts
        if source[sid].get("collection") in ("UI", "ChecksDialogs") or protected(sid)
    }

    old_manifest = load(config["previousComponentManifest"])
    groups = {}
    for name, entry in old_manifest["regressionGroups"].items():
        assert digest(raw(entry["path"])) == entry["sha256"]
        groups[name] = set(raw(entry["path"]).decode("utf-8").splitlines())
        assert len(groups[name]) == entry["count"] and groups[name] <= valid
    groups["gender-kinship-address"] |= {
        sid for sid in context if PRONOUNS.search(source[sid]["source"])
    }
    groups["mixed-script-target"] |= {
        sid for sid in order if re.search(r"[А-Яа-яЁё]", targets[sid])
    }
    mandatory = set().union(*groups.values())
    components = {
        "changed": changed,
        "context": context,
        "repetitions": repetitions,
        "glossary-referents": concepts,
        "phone-contact-consumers": phone_contacts,
        "runtime-bindings": runtime,
        "mandatory-regressions": mandatory,
    }
    closure = set().union(*components.values())
    components["closure"] = closure
    previous = set(raw(config["previousClosure"]).decode("utf-8").splitlines())
    assert len(previous) == config["expectedPreviousClosureCount"] and previous <= valid
    invalidated = {r["stableId"] for r in config["explicitlyInvalidatedPrior"]}
    assert len(invalidated) == len(config["explicitlyInvalidatedPrior"])
    assert invalidated <= previous & closure
    assert all(position[r["stableId"]] == r["sourceOrderIndex"]
               for r in config["explicitlyInvalidatedPrior"])
    new = closure - previous
    retired = previous - closure
    delta = changed | new | invalidated
    assert delta <= closure and len(delta) == len(changed | new | invalidated)

    cases = []
    for case in config["regressionCases"]:
        kind = case["kind"]
        if kind == "source-regex-subset":
            subset = re.compile(case["subsetRegex"])
            selected = {sid for sid in order if subset.search(source[sid]["source"])}
            assert len(selected) == case["requiredCount"]
            assert {position[sid] for sid in selected} == set(case["requiredSourceOrderIndices"])
            assert selected <= concepts & closure
            assert len(selected & new) == case["requiredNewCount"]
            required_count = len(selected)
        elif kind == "phone-contact":
            sid = order[case["requiredSourceOrderIndex"]-1]
            assert sid in phone_contacts & runtime & closure
            required_count = 1
        elif kind == "source-order":
            sid = order[case["requiredSourceOrderIndex"]-1]
            assert sid in components[case["requiredComponent"]] & closure
            if case.get("mustBeNew"): assert sid in new
            required_count = 1
        elif kind == "prior-witness-applicability":
            selected = {order[i-1] for i in case["requiredSourceOrderIndices"]}
            assert selected <= previous
            assert selected == (selected & closure) | (selected & retired)
            required_count = len(selected)
        else: raise AssertionError(kind)
        cases.append({"name": case["name"], "result": "passed", "requiredCount": required_count})
    # Preserve the two resolved candidate decisions from cycle 1.
    assert targets[order[197 - 1]] == "Tak ada siapa-siapa lagi. Apa ini... gara-gara mimpi itu?"
    old_adjudication = load("Translations/id/semantic-correction-cycle-01/adjudication.json")
    fatman = next(r for r in old_adjudication["rows"] if r["findingNumber"] == 31)
    assert fatman["decision"] == "rejected" and targets[fatman["stableId"]] == fatman["after"]

    outputs = {}
    def add(path, data):
        assert path not in outputs
        outputs[path] = data
        return {"path": config["cycleDirectory"] + "/" + path,
                "count": len(data.splitlines()), "sha256": digest(data),
                "newlineConvention": config["idListConvention"]}
    component_manifest = {
        "schemaVersion": 3, "locale": "id", "cycle": config["cycle"],
        "selectorConfigPath": str(config_path.relative_to(ROOT)),
        "selectorConfigSha256": digest(config_path.read_bytes()),
        "selectorRecipePath": str(Path(__file__).resolve().relative_to(ROOT)),
        "selectorRecipeSha256": digest(Path(__file__).read_bytes()),
        "components": {}, "regressionGroups": {},
    }
    for name, selected in components.items():
        component_manifest["components"][name] = add(name + ".ids.txt", list_bytes(order, selected))
    for name, selected in groups.items():
        component_manifest["regressionGroups"][name] = add(
            "regression-" + name + ".ids.txt", list_bytes(order, selected))
    for name, selected in (("new-dependencies", new),
                           ("invalidated-prior", invalidated),
                           ("retired-dependencies", retired),
                           ("delta-review", delta)):
        add(name + ".ids.txt", list_bytes(order, selected))
    outputs["component-manifest.json"] = json_bytes(component_manifest)

    old_components = {
        name: set(raw(entry["path"]).decode("utf-8").splitlines())
        for name, entry in old_manifest["components"].items() if name != "closure"
    }
    retired_rows = []
    for sid in order:
        if sid in retired:
            retired_rows.append(json.dumps({
                "sourceOrderIndex": position[sid], "stableId": sid,
                "previousComponents": [k for k, v in old_components.items() if sid in v],
                "reason": "Previously reviewed cycle-02 dependency absent from the corrected cycle-03 source-pattern, same-node, consumer, repetition and mandatory-regression closure. Its unchanged reading remains prior evidence; review only the exact cycle-03 delta."
            }, ensure_ascii=False, separators=(",", ":")))
    outputs["retired-dependencies.jsonl"] = ("\n".join(retired_rows) + "\n").encode("utf-8")

    def row(sid):
        r = source[sid]
        return {
            "sourceOrderIndex": position[sid], "stableId": sid,
            "collection": r.get("collection", "Static"), "key": r.get("key"),
            "nodeNames": r.get("nodeNames", []), "source": r["source"],
            "target": targets[sid], "targetFile": owners[sid],
            "targetFileSha256": digest(raw(owners[sid])),
            "components": [name for name, selected in components.items()
                           if name != "closure" and sid in selected],
        }
    outputs["closure-review-rows.jsonl"] = (
        "".join(json.dumps(row(sid), ensure_ascii=False, separators=(",", ":")) + "\n"
                for sid in order if sid in closure)).encode("utf-8")
    outputs["delta-review-rows.jsonl"] = (
        "".join(json.dumps({**row(sid), "deltaReasons": [name for name, selected in
                (("corrected", changed), ("newDependency", new),
                 ("explicitlyInvalidatedPrior", invalidated)) if sid in selected]},
                ensure_ascii=False, separators=(",", ":")) + "\n"
                for sid in order if sid in delta)).encode("utf-8")
    regression = {
        "schemaVersion": 3, "locale": "id", "cycle": config["cycle"],
        "status": "selector regression assertions passed; semantic review pending",
        "cases": cases,
        "priorDecisions": ["BodyEater UI uses mimpi", "Fatman singular-object candidate rejected"],
        "sourceVariantRule": "Female friend подруг*/подруж* and child девоч* are covered in one source family. Contact UI is derived from compiled GetPhoneNumber token; previous KChS, brother, sister, mushroom and dental patterns remain active."
    }
    outputs["selector-regression.json"] = json_bytes(regression)
    delta_manifest = {
        "schemaVersion": 3, "locale": "id", "cycle": config["cycle"],
        "previousReviewedClosurePath": config["previousClosure"],
        "previousReviewedClosureSha256": config["previousClosureSha256"],
        "independentReviewPath": config["independentReview"],
        "independentReviewSha256": config["independentReviewSha256"],
        "currentClosureSha256": component_manifest["components"]["closure"]["sha256"],
        "counts": {"corrected": len(changed), "previousReviewed": len(previous),
                   "currentClosure": len(closure), "newDependencies": len(new),
                   "explicitlyInvalidatedPrior": len(invalidated),
                   "retiredDependencies": len(retired), "exactNextReviewSet": len(delta)},
        "formula": "corrected IDs union (current closure minus previous reviewed closure) union explicitly invalidated prior IDs",
        "lists": {name: {"path": config["cycleDirectory"] + "/" + name + ".ids.txt",
                         "sha256": digest(outputs[name + ".ids.txt"]),
                         "count": len(selected)}
                  for name, selected in (("changed", changed), ("closure", closure),
                                         ("new-dependencies", new),
                                         ("invalidated-prior", invalidated),
                                         ("retired-dependencies", retired),
                                         ("delta-review", delta))},
        "retiredRowsPath": config["cycleDirectory"] + "/retired-dependencies.jsonl",
        "retiredRowsSha256": digest(outputs["retired-dependencies.jsonl"]),
        "closureReviewRowsSha256": digest(outputs["closure-review-rows.jsonl"]),
        "deltaReviewRowsSha256": digest(outputs["delta-review-rows.jsonl"]),
        "selectorRegressionSha256": digest(outputs["selector-regression.json"]),
        "componentManifestSha256": digest(outputs["component-manifest.json"]),
    }
    outputs["delta-manifest.json"] = json_bytes(delta_manifest)

    if args.write:
        assert all(not (cycle / name).exists() for name in outputs)
        for name, data in outputs.items():
            (cycle / name).write_bytes(data)
    elif args.verify:
        for name, data in outputs.items():
            assert (cycle / name).read_bytes() == data, name
    print(json.dumps({
        "mode": "write" if args.write else "verify" if args.verify else "dry-run",
        "components": {k: len(v) for k, v in components.items()},
        "regressionGroups": {k: len(v) for k, v in groups.items()},
        "newDependencies": len(new), "invalidatedPrior": len(invalidated),
        "retiredDependencies": len(retired), "exactNextReviewSet": len(delta),
        "closureSha256": digest(outputs["closure.ids.txt"]),
        "deltaSha256": digest(outputs["delta-review.ids.txt"]),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
