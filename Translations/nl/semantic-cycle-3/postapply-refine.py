#!/usr/bin/env python3
"""Preserve and correct five cycle-3 assembled plural-label refinements."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
REFINEMENTS = {
    "NL-IR02-003": "Fairytaller: Maar ik vrees dat ik me ongemakkelijk zal voelen zolang ik de ruimte deel met dit gezelschap: {0}.",
    "NL-IR02-009": "Experienced: Dit gezelschap staat me niet aan: {0}.",
    "NL-IR02-012": "Twins: Ik vrees dat er al gezelschap bij u zit: {0}.",
    "NL-IR02-025": "Fanatic: Mens! De ZON gebiedt me niet binnen te gaan zolang dit gezelschap zich in je huis schuilhoudt: {0}.",
    "NL-IR02-030": "Teacher: Neem me niet kwalijk, ik zie dat u hier gezelschap hebt — {0}?",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_new(path, content):
    assert not path.exists(), path
    path.write_text(content)


def recipe():
    spec = importlib.util.spec_from_file_location("nl_cycle1", ROOT / "Translations/nl/semantic-cycle-1/prepare-and-apply.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare():
    old_path = HERE / "adjudicated-corrections-v2.json"
    old_preflight = HERE / "complete-batch-preflight-v2.json"
    old_closure = HERE / "closure/closure-manifest.json"
    old_validation = HERE / "structural-validation.json"
    old = json.loads(old_path.read_text())
    assert len(old["corrections"]) == 40
    assert json.loads(old_preflight.read_text())["adjudicationSha256"] == sha(old_path)
    assert json.loads(old_closure.read_text())["adjudicationSha256"] == sha(old_path)
    assert json.loads(old_validation.read_text())["adjudicationSha256"] == sha(old_path)
    exact = recipe().load_exact_validator()
    source_rules = json.loads((ROOT / "Source/preserve-exactly-v4.json").read_text())
    rules = {row["stableId"]: row for row in source_rules["tableRows"] + source_rules["staticRows"]}
    guids = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1"}
    current_hashes = {}
    changed = []
    for record in old["corrections"]:
        if record["findingId"] not in REFINEMENTS:
            continue
        path = record["authoredPath"]
        doc = json.loads((ROOT / path).read_text())
        sid = record["stableId"]
        entry = next(e for e in doc["entries"] if f"string:{guids[doc['collection']]}:{e['id']}" == sid)
        assert entry["target"] == record["after"]
        current_hashes[path] = sha(ROOT / path)
        after = REFINEMENTS[record["findingId"]]
        assert after != record["after"] and after.count("{0}") == record["after"].count("{0}") == 1
        exact.check_value(rules[sid], after)
        changed.append((sid, record["after"], after))
        record["after"] = after
        record["afterSha256"] = text_sha(after)
        record["decision"] = "accept with plural-safe full-unit refinement"
        record["contextAdjudication"] += " Final assembled-label check: article-free UI labels can be plural; collective gezelschap avoids introducing a singular person or identity assertion."
    assert len(changed) == len(REFINEMENTS) == 5
    old["supersedesAdjudicationSha256"] = sha(old_path)
    old["supersedesPreflightSha256"] = sha(old_preflight)
    old["supersedesInitialClosureSha256"] = sha(old_closure)
    old["postapplyRefinementBeforeAuthoredHashes"] = [{"path": p, "sha256": h} for p, h in sorted(current_hashes.items())]
    new_path = HERE / "adjudicated-corrections-v3.json"
    write_new(new_path, json.dumps(old, ensure_ascii=False, indent=2) + "\n")
    samples = json.loads((ROOT / "Translations/nl/independent-review-02/dynamic-label-examples.json").read_text())["samples"]
    after_by_id = {r["stableId"]: r["after"] for r in old["corrections"]}
    previews = [{"stableId": s["stableId"], "labelKey": s["labelKey"], "labelTarget": s["labelTarget"],
                 "assembledAfter": after_by_id[s["stableId"]].replace("{0}", s["labelTarget"])} for s in samples]
    preflight = {
        "schemaVersion": 1, "locale": "nl", "cycle": 3,
        "adjudicationSha256": sha(new_path), "fullUnitsRepreflighted": 40,
        "postapplyRefinements": len(changed), "changedIds": [x[0] for x in changed],
        "beforeAuthoredHashes": old["postapplyRefinementBeforeAuthoredHashes"],
        "allProtectedValuesPassed": True,
        "sampleBoundary": "Exact label substitution illustrations, including a plural label; admissible placements and unbound reachability are not inferred.",
        "assembledSamples": previews,
    }
    write_new(HERE / "complete-batch-preflight-v3.json", json.dumps(preflight, ensure_ascii=False, indent=2) + "\n")
    print("Repreflighted 40 full units; five plural-safe refinements prepared")


def apply():
    adj_path = HERE / "adjudicated-corrections-v3.json"
    preflight = json.loads((HERE / "complete-batch-preflight-v3.json").read_text())
    assert preflight["adjudicationSha256"] == sha(adj_path) and preflight["allProtectedValuesPassed"]
    adj = json.loads(adj_path.read_text())
    by_id = {r["stableId"]: r for r in adj["corrections"] if r["findingId"] in REFINEMENTS}
    assert len(by_id) == 5
    old_hashes = {x["path"]: x["sha256"] for x in preflight["beforeAuthoredHashes"]}
    guids = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1"}
    helper = recipe()
    writes, before, after = [], [], []
    for path, expected in old_hashes.items():
        assert sha(ROOT / path) == expected
        doc = json.loads((ROOT / path).read_text())
        style = helper.original_style(doc, expected)
        for entry in doc["entries"]:
            sid = f"string:{guids[doc['collection']]}:{entry['id']}"
            if sid not in by_id:
                continue
            record = by_id[sid]
            assert entry["target"] == next(r["after"] for r in json.loads((HERE / "adjudicated-corrections-v2.json").read_text())["corrections"] if r["stableId"] == sid)
            before.append({"ordinal": record["ordinal"], "stableId": sid, "target": entry["target"], "targetSha256": text_sha(entry["target"])})
            entry["target"] = record["after"]
            after.append({"ordinal": record["ordinal"], "stableId": sid, "target": entry["target"], "targetSha256": text_sha(entry["target"])})
        writes.append((ROOT / path, helper.serialize_batch(doc, style)))
    assert len(before) == len(after) == 5
    before.sort(key=lambda r: r["ordinal"])
    after.sort(key=lambda r: r["ordinal"])
    write_new(HERE / "postapply-refinement-before-rows.jsonl", "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in before))
    write_new(HERE / "postapply-refinement-after-rows.jsonl", "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in after))
    original_before = [json.loads(line) for line in (HERE / "before-rows.jsonl").open()]
    final_after = []
    for record in adj["corrections"]:
        final_after.append({"ordinal": record["ordinal"], "stableId": record["stableId"], "path": record["authoredPath"],
                            "source": record["source"], "target": record["after"], "targetSha256": record["afterSha256"]})
    assert [r["stableId"] for r in original_before] == [r["stableId"] for r in final_after]
    write_new(HERE / "after-rows-v3.jsonl", "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in final_after))
    for path, data in writes:
        path.write_text(data)
    print("Applied five plural-safe refinements to the same cycle-3 findings")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "apply"])
    args = parser.parse_args()
    prepare() if args.action == "prepare" else apply()
