#!/usr/bin/env python3
"""Build or verify the pinned Greek correction-cycle dependency closure.

This selects IDs and records existing wording. It never writes translation text.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PREFIX = "correction-cycle-001"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def encoded(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("preview", "write", "verify"))
    args = parser.parse_args()

    spec_path = HERE / f"{PREFIX}-selectors.json"
    plan_path = HERE / f"{PREFIX}-adjudication.json"
    applied_path = HERE / f"{PREFIX}-applied.json"
    first_path = HERE / "semantic-review-progress.json"
    exact_path = HERE / f"{PREFIX}-preserve-exact.validation.json"
    full_path = HERE / f"{PREFIX}-full-structural.validation.json"
    spec = json.loads(spec_path.read_text())
    plan = json.loads(plan_path.read_text())
    applied = json.loads(applied_path.read_text())
    first = json.loads(first_path.read_text())
    exact = json.loads(exact_path.read_text())
    full = json.loads(full_path.read_text())
    assert spec["locale"] == plan["locale"] == applied["locale"] == "el"
    assert first["reviewedUnits"] == first["acceptedUnits"] == 16538
    assert digest(first_path) == plan["firstPassProgressSha256"]
    assert exact["checkedRows"] == 16538 and exact["exactResult"] == "passed"
    assert full["result"] == "passed" and full["preserveExactSha256"] == digest(exact_path)
    assert digest(ROOT / first["inputs"]["sourceStringsPath"]) == plan["sourceInventorySha256"]
    assert digest(ROOT / first["inputs"]["sourceStaticPath"]) == plan["sourceStaticSha256"]
    assert digest(ROOT / first["inputs"]["approvedGreekGlossaryPath"]) == plan["approvedGlossarySha256"]
    assert digest(ROOT / first["inputs"]["preserveManifestPath"]) == plan["preserveManifestSha256"]

    manifest = json.loads((ROOT / first["inputs"]["preserveManifestPath"]).read_text())
    table_ids = {r["stableId"] for r in manifest["tableRows"]}
    static_ids = {r["stableId"] for r in manifest["staticRows"]}
    all_dialogue = [json.loads(line) for line in (ROOT / first["inputs"]["sourceStringsPath"]).open()
                    if '"collection":"Dialogs"' in line]
    table = [r for line in (ROOT / first["inputs"]["sourceStringsPath"]).open()
             if (r := json.loads(line))["stableId"] in table_ids]
    static = [r for line in (ROOT / first["inputs"]["sourceStaticPath"]).open()
              if (r := json.loads(line))["stableId"] in static_ids]
    source = table + static
    assert len(table) == 16360 and len(static) == 178 and len(source) == 16538
    ids = [r["stableId"] for r in source]
    accepted = set(ids)
    assert len(accepted) == len(ids)
    by_id = {r["stableId"]: r for r in source}
    ordinal = {sid: i for i, sid in enumerate(ids)}

    prior = {}
    next_ordinal = 0
    for segment in first["reviewedSegments"]:
        assert segment["startOrdinal"] == next_ordinal
        path = ROOT / segment["evidencePath"]
        assert digest(path) == segment["evidenceSha256"]
        for line in path.open():
            row = json.loads(line)
            assert row["ordinal"] == next_ordinal and row["stableId"] == ids[next_ordinal]
            prior[row["stableId"]] = row
            next_ordinal += 1
        assert next_ordinal == segment["endOrdinalExclusive"]
    assert next_ordinal == 16538

    current = {}
    current_file = {}
    guids = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
             "UI": "0cbd8a7a4f543344bb95659de87f67a5",
             "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}
    for file in exact["inputFiles"]:
        path = ROOT / file["path"]
        assert digest(path) == file["sha256"]
        obj = json.loads(path.read_text())
        if "collection" in obj:
            for entry in obj["entries"]:
                sid = f"string:{guids[obj['collection']]}:{entry['id']}"
                assert sid in accepted and sid not in current
                current[sid] = entry["target"]
                current_file[sid] = file
        else:
            for entry in obj["entries"]:
                sid = entry["stableId"]
                assert sid in accepted and sid not in current
                current[sid] = entry["target"]
                current_file[sid] = file
    assert set(current) == accepted

    changed = {row["stableId"] for row in plan["corrections"]}
    assert len(changed) == plan["objectiveFindingsAccepted"] + plan["contextQuestionCorrections"] == 40
    assert changed == set(applied["changedIds"])
    for row in plan["corrections"]:
        sid = row["stableId"]
        assert ordinal[sid] == row["ordinal"]
        assert prior[sid]["target"] == row["before"] and current[sid] == row["after"]
        assert prior[sid]["source"] == row["source"]
        assert digest(ROOT / row["authoredInput"]) == next(
            f["afterSha256"] for f in applied["files"] if f["path"] == row["authoredInput"])
    for file in applied["files"]:
        assert digest(ROOT / file["path"]) == file["afterSha256"]

    context = set()
    radius = spec["contextNeighborRadius"]
    for sid in changed:
        i = ordinal[sid]
        row = by_id[sid]
        if sid in static_ids:
            continue
        collection = row["collection"]
        for j in range(max(0, i - radius), min(len(table), i + radius + 1)):
            if source[j]["collection"] == collection:
                context.add(ids[j])
        nodes = set(row.get("nodeNames", []))
        if nodes:
            context.update(r["stableId"] for r in table
                           if r["collection"] == collection and nodes.intersection(r.get("nodeNames", [])))
    for prefix in spec["contextNodePrefixes"]:
        matches = {r["stableId"] for r in table if any(n.startswith(prefix) for n in r.get("nodeNames", []))}
        assert matches, prefix
        context.update(matches)

    repeated = set()
    changed_sources = {by_id[sid]["source"] for sid in changed}
    changed_before = {prior[sid]["target"] for sid in changed}
    changed_after = {current[sid] for sid in changed}
    for sid in ids:
        if by_id[sid]["source"] in changed_sources or current[sid] in changed_before | changed_after or prior[sid]["target"] in changed_before:
            repeated.add(sid)

    referent = set()
    pattern_hits = {}
    for selector in spec["glossaryReferentSelectors"]:
        source_pattern = re.compile(selector["sourceRegex"], re.IGNORECASE)
        target_pattern = re.compile(selector["targetRegex"], re.IGNORECASE)
        hits = {sid for sid in ids if source_pattern.search(by_id[sid]["source"])
                or target_pattern.search(current[sid]) or target_pattern.search(prior[sid]["target"])}
        assert hits, selector["name"]
        referent.update(hits)
        pattern_hits[selector["name"]] = len(hits)

    runtime = set()
    runtime_spec = spec["runtimeBinding"]
    for key in runtime_spec["uiKeys"]:
        matches = {r["stableId"] for r in table if r.get("collection") == "UI" and r.get("key") == key}
        assert len(matches) == 1, key
        runtime.update(matches)
    name_pattern = re.compile(runtime_spec["uiKeyRegex"])
    names = {r["stableId"] for r in table if r.get("collection") == "UI" and name_pattern.search(r.get("key") or "")}
    assert names
    runtime.update(names)
    for sid in runtime_spec["staticStableIds"]:
        assert sid in static_ids and "x1" in by_id[sid]["source"]
        runtime.add(sid)

    mandatory = set()
    regression = spec["mandatoryRegression"]
    if regression["allAcceptedUI"]:
        mandatory.update(r["stableId"] for r in table if r["collection"] == "UI")
    if regression["allAcceptedStatic"]:
        mandatory.update(static_ids)
    for row in manifest["tableRows"]:
        if ((regression["protectedFormatSlots"] and row["formatSlots"])
                or (regression["protectedTmpTags"] and row["tmpTags"])
                or (regression["protectedExactTexts"] and row["wholeTextExact"])
                or (regression["protectedNumbers"] and row["numbers"])):
            mandatory.add(row["stableId"])
    kinship = re.compile(regression["kinshipSourceRegex"], re.IGNORECASE)
    mandatory.update(r["stableId"] for r in table if kinship.search(r["source"]))
    for start, end in regression["foreignerDialogueSourceIndexRanges"]:
        assert 0 <= start < end <= len(all_dialogue)
        mandatory.update(r["stableId"] for r in all_dialogue[start:end] if r["stableId"] in accepted)

    components = {"changed": changed, "context": context, "repetition": repeated,
                  "glossary-referent": referent, "runtime-binding": runtime,
                  "mandatory-regression": mandatory}
    assert all(part <= accepted for part in components.values())
    closure = set().union(*components.values())
    assert changed <= closure and len(closure) <= 16538
    component_ordered = {name: [sid for sid in ids if sid in part] for name, part in components.items()}
    component_ordered["closure"] = [sid for sid in ids if sid in closure]
    outputs = {}
    summaries = {}
    for name, ordered in component_ordered.items():
        path = HERE / f"{PREFIX}-{name}-ids.txt"
        content = ("\n".join(ordered) + "\n").encode("utf-8")
        outputs[path] = content
        summaries[name] = {"path": str(path.relative_to(ROOT)), "count": len(ordered),
                           "sha256": hashlib.sha256(content).hexdigest(), "newline": "LF, terminal newline"}
    context_path = HERE / f"{PREFIX}-nontranslatable-context.txt"
    nontranslatable = ("\n".join(spec["nontranslatableContext"]) + "\n").encode("utf-8")
    outputs[context_path] = nontranslatable
    rows_path = HERE / f"{PREFIX}-closure-review.jsonl"
    review_lines = []
    for sid in component_ordered["closure"]:
        row = by_id[sid]
        review = {"ordinal": ordinal[sid], "stableId": sid, "collection": row.get("collection", "static"),
                  "key": row.get("key"), "components": [name for name, part in components.items() if sid in part],
                  "source": row["source"], "sourceSha256": text_digest(row["source"]),
                  "firstPassTarget": prior[sid]["target"], "firstPassTargetSha256": prior[sid]["targetSha256"],
                  "currentTarget": current[sid], "currentTargetSha256": text_digest(current[sid]),
                  "targetFile": current_file[sid]["path"], "targetFileSha256": current_file[sid]["sha256"]}
        review_lines.append(json.dumps(review, ensure_ascii=False, separators=(",", ":")))
    rows_content = ("\n".join(review_lines) + "\n").encode("utf-8")
    outputs[rows_path] = rows_content
    result = {"schemaVersion": 1, "locale": "el", "cycle": 1,
              "status": "correction closure ready for a distinct reviewer; no independent or editorial acceptance claim",
              "acceptedUnits": 16538, "firstPassReviewedUnits": 16538,
              "sourceInventorySha256": plan["sourceInventorySha256"],
              "sourceStaticSha256": plan["sourceStaticSha256"],
              "approvedGlossarySha256": plan["approvedGlossarySha256"],
              "firstPassProgressSha256": digest(first_path),
              "adjudicationSha256": digest(plan_path), "appliedSha256": digest(applied_path),
              "selectorPath": str(spec_path.relative_to(ROOT)), "selectorSha256": digest(spec_path),
              "preserveExactValidationPath": str(exact_path.relative_to(ROOT)),
              "preserveExactValidationSha256": digest(exact_path),
              "fullStructuralValidationPath": str(full_path.relative_to(ROOT)),
              "fullStructuralValidationSha256": digest(full_path),
              "components": summaries, "patternHitCounts": pattern_hits,
              "selectorRepairEvidence": spec["selectorRepairEvidence"],
              "nontranslatableContext": {"path": str(context_path.relative_to(ROOT)),
                                         "sha256": hashlib.sha256(nontranslatable).hexdigest(),
                                         "lines": len(spec["nontranslatableContext"])},
              "reviewRows": {"path": str(rows_path.relative_to(ROOT)), "count": len(review_lines),
                             "sha256": hashlib.sha256(rows_content).hexdigest(),
                             "newline": "LF, terminal newline"},
              "currentTargetFiles": exact["inputFiles"],
              "authoredAndRegenerationInputs": applied["files"],
              "unchangedReproductionInputs": [
                  {"path": str((HERE / name).relative_to(ROOT)), "sha256": digest(HERE / name)}
                  for name in ("expand_ordered.py", "expand_static.py", "static-lexicon-001.authored.json",
                               "credits-role-map.json", "dialogue-repeats-001.authored.json")],
              "imageTextScope": "excluded by owner",
              "missingAcceptedIds": 0, "extraIds": 0, "unexplainedMissingOrExtraIds": 0,
              "independentReview": "not-started", "editorialAcceptance": "pending"}
    result_path = HERE / f"{PREFIX}-closure-manifest.json"
    outputs[result_path] = encoded(result)
    if args.mode == "preview":
        print(json.dumps({"counts": {k: v["count"] for k, v in summaries.items()},
                          "patternHitCounts": pattern_hits, "missingOrExtra": 0}, indent=2))
        return
    for path, content in outputs.items():
        if args.mode == "write":
            assert not path.exists(), path
            path.write_bytes(content)
        else:
            assert path.read_bytes() == content, path
    print(json.dumps({"result": args.mode, "closureCount": len(closure),
                      "changedCount": len(changed), "manifestSha256": digest(result_path)}, indent=2))


if __name__ == "__main__":
    main()
