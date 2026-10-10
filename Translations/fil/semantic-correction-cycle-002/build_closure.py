#!/usr/bin/env python3
"""Rebuild Filipino correction cycle 002 closure and exact independent delta."""

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FIL = ROOT / "Translations/fil"
CYCLE = Path(__file__).resolve().parent
OUT = CYCLE / "closure.json"
PAIRED = CYCLE / "closure-paired.jsonl"
PENDING = CYCLE / "pending-delta-paired.jsonl"
G = {
    "UI": "0cbd8a7a4f543344bb95659de87f67a5",
    "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6",
    "Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def load(path):
    return json.loads(path.read_text())


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def id_hash(ids):
    return digest("".join(sid + "\n" for sid in ids).encode())


def build():
    plan_path = CYCLE / "plan.json"
    after_path = CYCLE / "after.json"
    gate_path = CYCLE / "full-structural-validation.json"
    spec_path = CYCLE / "selector-specification.json"
    plan, after, gate, spec = map(load, (plan_path, after_path, gate_path, spec_path))
    require(sha(plan_path) == after["planSha256"] == gate["planSha256"],
            "Correction plan or gate changed")
    require(sha(gate_path) == after["fullStructuralValidationSha256"],
            "Full deterministic gate changed")
    require(gate["checkedIds"] == 16538 and gate["missingIds"] ==
            gate["extraIds"] == gate["duplicateIds"] == 0,
            "Full deterministic gate incomplete")
    for pin in plan["sourceAndGlossaryFingerprints"].values():
        require(sha(ROOT / pin["path"]) == pin["sha256"],
                "Source or glossary changed")
    for file in after["files"]:
        require(sha(ROOT / file["authoredPath"]) == file["afterSha256"] and
                sha(ROOT / file["afterSnapshotPath"]) == file["afterSha256"],
                "Corrected authored file changed")
    previous_path = FIL / "semantic-correction-cycle-001.closure.json"
    previous = load(previous_path)
    require(sha(previous_path) == plan["previousClosureSha256"] ==
            spec["previousClosureSha256"], "Previous closure changed")
    require(sha(FIL / "semantic-correction-cycle-001.paired.jsonl") ==
            plan["previousPairedSha256"], "Previous paired evidence changed")
    for name, expected in plan["reviewEvidenceSha256"].items():
        require(sha(FIL / "independent-review-01" / name) == expected,
                "Independent evidence changed: " + name)
    require(sha(CYCLE / "compiled-context.json") == plan["compiledContextSha256"],
            "Compiled scene context changed")
    erratum_path = CYCLE / "compiled-context-erratum.json"
    corrected_context_path = CYCLE / "compiled-context-corrected.json"
    erratum = load(erratum_path)
    require(erratum["previousSnapshotSha256"] == plan["compiledContextSha256"] and
            erratum["correctedSnapshotSha256"] == sha(corrected_context_path) and
            erratum["compiledProgramSha256"] ==
            load(corrected_context_path)["compiledProgramSha256"],
            "Compiled opcode correction differs")
    require(sha(ROOT / "Source/preserve-exactly-v4.json") ==
            plan["preserveExactManifestSha256"], "Preserve-exact contract changed")

    targets = {}
    for report in gate["batchReports"]:
        path = ROOT / report["path"]
        require(sha(path) == report["sha256"] and
                sha(ROOT / report["sidecarPath"]) == report["sidecarSha256"],
                "Authored batch or validator sidecar changed")
        doc = load(path)
        for entry in doc["entries"]:
            sid = f"string:{G[doc['collection']]}:{entry['id']}"
            require(sid not in targets, "Duplicate authored ID")
            targets[sid] = entry["target"]
    for entry in load(FIL / "static-text-draft.json")["entries"]:
        sid = entry["stableId"]
        require(sid not in targets, "Duplicate static ID")
        targets[sid] = entry["target"]
    require(len(targets) == 16538, "Accepted denominator changed")

    inventory = [json.loads(line) for line in
                 (ROOT / "Source/localization-inventory-v3/strings.jsonl").open()]
    order = [row["stableId"] for collection in ("UI", "ChecksDialogs", "Dialogs")
             for row in inventory if row["collection"] == collection
             and row["stableId"] in targets]
    order += [entry["stableId"] for entry in
              load(FIL / "static-text-draft.json")["entries"]]
    require(len(order) == len(set(order)) == 16538 and set(order) == set(targets),
            "Canonical accepted order differs")
    require(id_hash(order) == previous["acceptedOrderSha256"],
            "Previous accepted-ID order differs")
    rank = {sid: n + 1 for n, sid in enumerate(order)}
    source = {row["stableId"]: row for row in inventory if row["stableId"] in targets}
    source.update({row["stableId"]: row for row in
                   (json.loads(line) for line in
                    (ROOT / "Source/localization-inventory-v3/static-text.jsonl").open())
                   if row["stableId"] in targets})
    require(set(source) == set(targets), "Accepted source mapping differs")

    changed = {row["stableId"] for row in plan["rows"]}
    require(len(changed) == 19 and all(targets[row["stableId"]] ==
                                    row["acceptedFullTarget"] for row in plan["rows"]),
            "Corrected target differs")
    node_names = {row["compiledNode"] for row in plan["rows"]
                  if row["compiledNode"]}
    node_names.add("NotTrue_Photo_Gun")
    context = {sid for sid in order if
               set(source[sid].get("nodeNames", [])) & node_names}
    exact_sources = {row["source"] for row in plan["rows"]}
    repetition = {sid for sid in order if source[sid]["source"] in exact_sources}
    require(changed <= repetition, "Exact-source repetition lost a correction")

    def select_regex(patterns, field):
        groups = {}
        for name, pattern in patterns.items():
            groups[name] = {sid for sid in order if
                            re.search(pattern, source[sid][field])}
            require(groups[name], "Empty selector: " + name)
        return groups

    referent_groups = select_regex(spec["affectedReferentSourceRegex"], "source")
    referents = set().union(*referent_groups.values())
    localized_groups = {pattern: {sid for sid in order if
                                  re.search(pattern, targets[sid])}
                        for pattern in spec["localizedWordingRegex"]}
    localized_exact = {sid for sid in order if targets[sid] in
                       {row["currentTarget"] for row in plan["rows"]} |
                       {row["acceptedFullTarget"] for row in plan["rows"]}}
    localized = set().union(localized_exact, *localized_groups.values())

    options = {row["source"] for row in
               load(FIL / "common-options-001.authored.json")["phrases"]}
    mandatory_groups = {
        "all-ui": {sid for sid in order if source[sid].get("collection") == "UI"},
        "all-static": {sid for sid in order if sid.startswith("tmp:")},
        "all-common-option-exact-sources": {sid for sid in order
                                            if source[sid]["source"] in options},
    }
    mandatory_groups.update(select_regex(spec["mandatorySourceRegex"], "source"))
    require(len(mandatory_groups["all-common-option-exact-sources"]) == 2675,
            "Common-option source selector lost the independent Нет row")
    mandatory = set().union(*mandatory_groups.values())

    for test in spec["regressionExamples"]:
        sid = test["stableId"]
        require(sid in targets and source[sid]["source"] == test["source"] and
                sid in mandatory_groups[test["expectedSelector"]],
                "Real selector regression failed: " + sid)
    for test in spec["syntheticSelectorRegressions"]:
        require(bool(re.search(spec["mandatorySourceRegex"][test["selector"]],
                               test["source"])) == test["mustMatch"],
                "Synthetic selector regression failed: " + test["source"])

    dynamic = set(previous["runtimeDynamicPlaceholderConsumers"]["ids"])
    require(len(dynamic) == 6, "Prior dynamic-consumer topology differs")
    for pin in plan["unchangedDynamicConsumers"]:
        sid = pin["stableId"]
        require(sid in dynamic and source[sid]["sourceSha256"] ==
                pin["sourceSha256"] and digest(targets[sid].encode()) ==
                pin["targetSha256"], "Dynamic consumer input changed")
    runtime_binding = context | dynamic
    components = {
        "changed": changed,
        "explicitContext": context,
        "exactSourceRepetition": repetition,
        "glossaryReferent": referents,
        "localizedWording": localized,
        "runtimeBinding": runtime_binding,
        "mandatoryRegression": mandatory,
    }
    closure = set().union(*components.values())
    require(closure <= set(order), "Closure contains nonaccepted IDs")

    previous_ids = set(previous["closureIds"])
    newly_added = closure - previous_ids
    retired = previous_ids - closure
    focus = set().union(*(referent_groups[name] for name in
                         ("ear-wax-source-forms", "gun-threat-expletive",
                          "child-murder-victim")))
    invalidated = (previous_ids & (context | repetition | focus)) - changed
    delta = changed | newly_added | invalidated
    supplement = {pin["stableId"] for pin in plan["verifiedSupplementalIndependentReads"]}
    require(len(supplement) == 20 and supplement <= newly_added,
            "Supplemental reviewer reads were not added by the repaired selector")
    for pin in plan["verifiedSupplementalIndependentReads"]:
        sid = pin["stableId"]
        require(source[sid]["sourceSha256"] == pin["sourceSha256"] and
                digest(targets[sid].encode()) == pin["targetSha256"],
                "Supplemental reviewer read no longer applies")
    pending = delta - supplement
    require(delta == changed | newly_added | invalidated and
            not (retired & closure), "Delta accounting differs")

    def ids(members):
        return [sid for sid in order if sid in members]

    def packed(name, members):
        selected = ids(members)
        return {"name": name, "count": len(selected),
                "idsSha256": id_hash(selected), "ids": selected}

    component_rows = [packed(name, members) for name, members in components.items()]
    previous_components = {row["name"]: set(row["ids"])
                           for row in previous["components"]}
    component_deltas = [{"name": name,
                         "new": packed(name + ":new", members - previous_components.get(name, set())),
                         "retired": packed(name + ":retired", previous_components.get(name, set()) - members)}
                        for name, members in components.items()]
    retired_component_names = sorted(set(previous_components) - set(components))
    require(set().union(*(set(row["ids"]) for row in component_rows)) == closure,
            "Unexplained closure IDs")

    def pair(sid):
        row = source[sid]
        return {"acceptedOrdinal": rank[sid], "stableId": sid,
                "collection": row.get("collection", "static"),
                "key": row.get("key"), "nodeNames": row.get("nodeNames", []),
                "source": row["source"],
                "sourceSha256": digest(row["source"].encode()),
                "target": targets[sid], "targetSha256": digest(targets[sid].encode()),
                "components": [name for name, members in components.items() if sid in members],
                "deltaReason": ([name for name, members in
                                 (("corrected", changed), ("newClosure", newly_added),
                                  ("explicitlyInvalidated", invalidated),
                                  ("supplementalIndependentReadReused", supplement))
                                 if sid in members]),
                }

    def jsonl(members):
        return "".join(json.dumps(pair(sid), ensure_ascii=False,
                                  separators=(",", ":")) + "\n"
                       for sid in ids(members)).encode()

    paired_raw, pending_raw = jsonl(closure), jsonl(pending)
    result = {
        "schemaVersion": 2, "locale": "fil", "gameVersion": "1.3.19",
        "status": "correction cycle 002 reproducible closure and independent delta; review pending",
        "planSha256": sha(plan_path), "afterSha256": sha(after_path),
        "fullStructuralValidationSha256": sha(gate_path),
        "selectorSpecificationPath": str(spec_path.relative_to(ROOT)),
        "selectorSpecificationSha256": sha(spec_path),
        "previousClosureSha256": sha(previous_path),
        "previousPairedSha256": plan["previousPairedSha256"],
        "sourceAndGlossaryFingerprints": plan["sourceAndGlossaryFingerprints"],
        "compiledContextSha256": plan["compiledContextSha256"],
        "compiledContextErratumSha256": sha(erratum_path),
        "compiledContextCorrectedSha256": sha(corrected_context_path),
        "nontranslatableContext": {"compiledNodeCount": len(node_names),
                                    "compiledNodeNames": sorted(node_names),
                                    "compiledContextSha256": sha(corrected_context_path),
                                    "opcodeErratumSha256": sha(erratum_path),
                                    "translationIdsAdded": 0},
        "acceptedUnits": 16538, "acceptedOrderSha256": id_hash(order),
        "idHashConvention": "UTF-8 LF, one stable ID per line in canonical accepted order",
        "components": component_rows,
        "referentSelectors": [dict(packed(name, members),
                                   sourceRegex=spec["affectedReferentSourceRegex"][name])
                              for name, members in referent_groups.items()],
        "mandatorySelectors": [dict(packed(name, members),
                                    sourceRegex=spec["mandatorySourceRegex"].get(name))
                               for name, members in mandatory_groups.items()],
        "localizedSelectors": [dict(packed(str(n), members), targetRegex=pattern)
                               for n, (pattern, members) in enumerate(localized_groups.items(), 1)],
        "componentDeltas": component_deltas,
        "retiredPreviousComponentNames": retired_component_names,
        "previousClosureCount": len(previous_ids),
        "currentClosure": packed("currentClosure", closure),
        "newCurrentMinusPrevious": packed("newCurrentMinusPrevious", newly_added),
        "retiredPreviousMinusCurrent": packed("retiredPreviousMinusCurrent", retired),
        "corrected": packed("corrected", changed),
        "explicitlyInvalidatedPriorEvidence": packed("explicitlyInvalidatedPriorEvidence", invalidated),
        "invalidationRule": "Previously reviewed IDs in a corrected compiled scene, exact-source repetition (including the live camera/gun counterpart), or the earwax, gun-threat expletive and child-murder risk selectors; corrected IDs are counted separately. Broader unchanged photo/gun rows retain their exact-hash independent review.",
        "exactNextDelta": packed("exactNextDelta", delta),
        "supplementalIndependentReadsReused": packed("supplementalIndependentReadsReused", supplement),
        "pendingDistinctReviewerDelta": packed("pendingDistinctReviewerDelta", pending),
        "pairedPath": str(PAIRED.relative_to(ROOT)), "pairedSha256": digest(paired_raw),
        "pendingDeltaPairedPath": str(PENDING.relative_to(ROOT)),
        "pendingDeltaPairedSha256": digest(pending_raw),
        "unexplainedMissingIds": [], "unexplainedExtraIds": [],
        "independentReviewer": None,
        "reviewStatus": "pending; author checks and prior supplemental reads are not a clean delta review",
    }
    return result, paired_raw, pending_raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    require(args.write != args.verify, "Choose --write or --verify")
    result, paired, pending = build()
    raw = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode()
    if args.write:
        require(not any(path.exists() for path in (OUT, PAIRED, PENDING)),
                "Immutable cycle 002 closure already exists")
        PAIRED.write_bytes(paired)
        PENDING.write_bytes(pending)
        OUT.write_bytes(raw)
    else:
        require(OUT.read_bytes() == raw and PAIRED.read_bytes() == paired and
                PENDING.read_bytes() == pending, "Stored closure or paired rows differ")
    print(json.dumps({"closureSha256": sha(OUT),
                      "previous": result["previousClosureCount"],
                      "current": result["currentClosure"]["count"],
                      "new": result["newCurrentMinusPrevious"]["count"],
                      "retired": result["retiredPreviousMinusCurrent"]["count"],
                      "corrected": result["corrected"]["count"],
                      "invalidated": result["explicitlyInvalidatedPriorEvidence"]["count"],
                      "exactNextDelta": result["exactNextDelta"]["count"],
                      "supplementalReused": result["supplementalIndependentReadsReused"]["count"],
                      "pendingDistinctReviewer": result["pendingDistinctReviewerDelta"]["count"],
                      "unexplainedMissing": 0, "unexplainedExtra": 0}))


if __name__ == "__main__":
    main()
