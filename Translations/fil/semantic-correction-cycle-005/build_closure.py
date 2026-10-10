#!/usr/bin/env python3
"""Rebuild Filipino cycle 005 closure and exact next independent delta."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FIL = ROOT / "Translations/fil"
CYCLE = Path(__file__).resolve().parent
REVIEW = FIL / "independent-review-04"
OUT = CYCLE / "closure.json"
PAIRED = CYCLE / "closure-paired.jsonl"
DELTA = CYCLE / "next-delta-paired.jsonl"
G = {"UI": "0cbd8a7a4f543344bb95659de87f67a5",
     "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6",
     "Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1"}


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
            "Correction plan or structural gate changed")
    require(sha(gate_path) == after["fullStructuralValidationSha256"] and
            gate["checkedIds"] == 16538 and gate["missingIds"] ==
            gate["extraIds"] == gate["duplicateIds"] == 0,
            "Full exact gate differs")
    for pin in plan["sourceAndGlossaryFingerprints"].values():
        require(sha(ROOT / pin["path"]) == pin["sha256"],
                "Source or glossary changed")
    require(sha(ROOT / "Source/preserve-exactly-v4.json") ==
            plan["preserveExactManifestSha256"], "Preserve-exact contract changed")
    previous_path = FIL / "semantic-correction-cycle-004/closure.json"
    previous = load(previous_path)
    require(sha(previous_path) == plan["previousClosureSha256"] ==
            after["previousClosureSha256"] == spec["previousClosureSha256"],
            "Previous closure changed")
    previous_paired_path = FIL / "semantic-correction-cycle-004/closure-paired.jsonl"
    require(sha(previous_paired_path) == plan["previousPairedSha256"] ==
            after["previousPairedSha256"], "Previous paired review input changed")
    for name, expected in after["reviewEvidenceSha256"].items():
        require(sha(REVIEW / name) == expected, "Review04 evidence changed: " + name)
    require(sha(REVIEW / "independent-compiled-context.json") ==
            plan["compiledContextSha256"] and
            load(REVIEW / "independent-compiled-context.json")["compiledProgramSha256"] ==
            plan["compiledProgramSha256"], "Compiled scene binding changed")
    file = after["file"]
    require(sha(ROOT / file["authoredPath"]) == file["afterSha256"] ==
            sha(ROOT / file["afterSnapshotPath"]) and
            sha(ROOT / file["beforeSnapshotPath"]) == file["beforeSha256"] and
            sha(ROOT / file["validationPath"]) == file["validationSha256"],
            "Before/after correction bytes changed")
    require(sha(CYCLE / "full-corpus-validation.json") ==
            gate["freshCorpusValidationSha256"] ==
            after["freshCorpusValidationSha256"],
            "Fresh locale-only corpus guard changed")

    targets = {}
    for report in gate["authoredFiles"]:
        path = ROOT / report["path"]
        require(sha(path) == report["sha256"],
                "Authored input changed after fresh corpus guard")
        if path.name == "static-text-draft.json":
            continue
        doc = load(path)
        for entry in doc["entries"]:
            sid = f"string:{G[doc['collection']]}:{entry['id']}"
            require(sid not in targets, "Duplicate authored ID")
            targets[sid] = entry["target"]
    for entry in load(FIL / "static-text-draft.json")["entries"]:
        sid = entry["stableId"]
        require(sid not in targets, "Duplicate static ID")
        targets[sid] = entry["target"]
    require(len(targets) == 16538 and
            sha(FIL / "static-text-draft.json") == gate["staticDraftSha256"],
            "Accepted denominator or static draft changed")
    inventory = [json.loads(line) for line in
                 (ROOT / "Source/localization-inventory-v3/strings.jsonl").open()]
    order = [row["stableId"] for collection in ("UI", "ChecksDialogs", "Dialogs")
             for row in inventory if row["collection"] == collection and
             row["stableId"] in targets]
    order += [entry["stableId"] for entry in
              load(FIL / "static-text-draft.json")["entries"]]
    require(len(order) == len(set(order)) == 16538 and set(order) == set(targets) and
            id_hash(order) == previous["acceptedOrderSha256"],
            "Canonical accepted order differs")
    rank = {sid: n + 1 for n, sid in enumerate(order)}
    source = {row["stableId"]: row for row in inventory if row["stableId"] in targets}
    source.update({row["stableId"]: row for row in
                   (json.loads(line) for line in
                    (ROOT / "Source/localization-inventory-v3/static-text.jsonl").open())
                   if row["stableId"] in targets})
    require(set(source) == set(targets), "Accepted source mapping differs")

    row = plan["row"]
    changed = {row["stableId"]}
    require(len(changed) == 1 and targets[row["stableId"]] ==
            row["acceptedFullTarget"],
            "Corrected complete target differs")
    bounded = load(ROOT / plan["boundedCompiledContextPath"])
    require(sha(ROOT / plan["boundedCompiledContextPath"]) == plan["boundedCompiledContextSha256"], "Bounded scene evidence changed")
    node_names = set(bounded["nodes"])
    require(len(node_names) == 7 and bounded["compiledProgramSha256"] == plan["compiledProgramSha256"], "Actual bounded compiled context differs")
    context = {sid for sid in order if
               set(source[sid].get("nodeNames", [])) & node_names}
    exact_sources = {row["source"]}
    repetition = {sid for sid in order if source[sid]["source"] in exact_sources}
    require(changed <= context & repetition,
            "Changed ID omitted from scene or exact repetition")

    def regex_groups(patterns, field, require_nonempty=True):
        groups = {name: {sid for sid in order if
                         re.search(pattern, source[sid][field] if field == "source" else targets[sid])}
                  for name, pattern in patterns.items()}
        if require_nonempty:
            require(all(groups.values()), "Empty canonical selector")
        return groups

    referent_groups = regex_groups(spec["affectedReferentSourceRegex"], "source")
    referents = set().union(*referent_groups.values())
    localized_patterns = {str(n): p for n, p in enumerate(spec["localizedWordingRegex"], 1)}
    localized_groups = regex_groups(localized_patterns, "target", False)
    localized_exact = {sid for sid in order if targets[sid] in
                       {row["currentTarget"], row["acceptedFullTarget"]}}
    localized = set().union(localized_exact, *localized_groups.values())
    options = {row["source"] for row in
               load(FIL / "common-options-001.authored.json")["phrases"]}
    mandatory_groups = {
        "all-ui": {sid for sid in order if source[sid].get("collection") == "UI"},
        "all-static": {sid for sid in order if sid.startswith("tmp:")},
        "all-common-option-exact-sources": {sid for sid in order
                                            if source[sid]["source"] in options},
    }
    mandatory_groups.update(regex_groups(spec["mandatorySourceRegex"], "source"))
    require(len(mandatory_groups["all-common-option-exact-sources"]) == 2675,
            "Common-option selector lost accepted independent Нет row")
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
    dynamic_pins = load(FIL / "semantic-correction-cycle-002/plan.json")["unchangedDynamicConsumers"]
    dynamic = {p["stableId"] for p in dynamic_pins}
    require(len(dynamic) == 6, "Six independently verified dynamic consumers changed")
    for pin in dynamic_pins:
        sid = pin["stableId"]
        require(source[sid]["sourceSha256"] == pin["sourceSha256"] and
                digest(targets[sid].encode()) == pin["targetSha256"],
                "Dynamic consumer changed")
    runtime_binding = context | dynamic
    components = {"changed": changed, "explicitContext": context,
                  "exactSourceRepetition": repetition,
                  "glossaryReferent": referents, "localizedWording": localized,
                  "runtimeBinding": runtime_binding,
                  "mandatoryRegression": mandatory}
    closure = set().union(*components.values())
    require(closure <= set(order), "Closure has nonaccepted IDs")
    previous_ids = set(previous["currentClosure"]["ids"])
    require(len(previous_ids) == 7612, "Prior reviewed closure size differs")
    reviewer_rows = [json.loads(line) for line in
                     (REVIEW / "closure-decision-applicability.jsonl").open()]
    reviewed = {r["stableId"]: r for r in reviewer_rows}
    require(len(reviewed) == len(previous_ids) == len(reviewer_rows) and
            set(reviewed) == previous_ids, "Review04 full prior closure accounting differs")
    prior_pairs = {r["stableId"]: r for r in
                   (json.loads(line) for line in previous_paired_path.open())}
    require(set(prior_pairs) == previous_ids, "Prior paired ID set differs")
    for sid in previous_ids:
        old = prior_pairs[sid]
        decision = reviewed[sid]
        require(decision["sourceSha256"] == old["sourceSha256"] ==
                digest(source[sid]["source"].encode()) and
                decision["targetSha256"] == old["targetSha256"] and
                decision["key"] == old["key"] and
                decision["nodeNames"] == old["nodeNames"] and
                (sid in changed or old["targetSha256"] == digest(targets[sid].encode())),
                "Prior reviewed source/target pin invalid without correction: " + sid)
    retired_review04 = [json.loads(line) for line in
                        (REVIEW / "retired-final-applicability.jsonl").open()]
    require(len(retired_review04) == 54 and
            len({r["stableId"] for r in retired_review04}) == 54,
            "Review04 retired dependency count differs")
    for prior_retired in retired_review04:
        sid = prior_retired["stableId"]
        require(sid in source and
                digest(source[sid]["source"].encode()) == prior_retired["sourceSha256"] and
                digest(targets[sid].encode()) == prior_retired["targetSha256"] and
                source[sid].get("nodeNames", []) == prior_retired["nodeNames"],
                "Review04 retired dependency changed on final hashes: " + sid)
    for prior_retired in retired_review04:
        sid = prior_retired["stableId"]
        require(source[sid].get("key") == prior_retired["key"], "Retired key changed")
    prior_mandatory = [json.loads(line) for line in (REVIEW / "mandatory-regression-applicability.jsonl").open()]
    require(len(prior_mandatory) == 7240 and {r["stableId"] for r in prior_mandatory} == set(next(r["ids"] for r in previous["components"] if r["name"] == "mandatoryRegression")), "Prior mandatory accounting differs")
    newly_added = closure - previous_ids
    retired = previous_ids - closure
    new_referents = referent_groups["attributed-perception-causality"]
    require(new_referents == {r["stableId"] for r in (json.loads(line) for line in (CYCLE / "bounded-family-paired.jsonl").open())} and len(new_referents) == 83, "Canonical family scan differs")
    new_wording = localized_groups[str(len(localized_groups))]
    invalidated = (previous_ids & (context | repetition | new_referents | new_wording)) - changed
    delta = changed | newly_added | invalidated
    require(delta == changed | (closure - previous_ids) | invalidated and
            not (retired & closure), "Exact delta accounting differs")

    def ids(members):
        return [sid for sid in order if sid in members]

    def packed(name, members):
        selected = ids(members)
        return {"name": name, "count": len(selected),
                "idsSha256": id_hash(selected), "ids": selected}

    component_rows = [packed(name, members) for name, members in components.items()]
    prior_components = {r["name"]: set(r["ids"]) for r in previous["components"]}
    component_deltas = [{"name": name,
                         "new": packed(name + ":new", members - prior_components.get(name, set())),
                         "retired": packed(name + ":retired", prior_components.get(name, set()) - members)}
                        for name, members in components.items()]
    require(set().union(*(set(r["ids"]) for r in component_rows)) == closure,
            "Unexplained closure ID")

    def pair(sid):
        row = source[sid]
        return {"acceptedOrdinal": rank[sid], "stableId": sid,
                "collection": row.get("collection", "static"), "key": row.get("key"),
                "nodeNames": row.get("nodeNames", []), "source": row["source"],
                "sourceSha256": digest(row["source"].encode()),
                "target": targets[sid], "targetSha256": digest(targets[sid].encode()),
                "components": [name for name, members in components.items() if sid in members],
                "deltaReason": [name for name, members in
                                (("corrected", changed), ("newClosure", newly_added),
                                 ("explicitlyInvalidated", invalidated)) if sid in members]}

    def jsonl(members):
        return "".join(json.dumps(pair(sid), ensure_ascii=False,
                                  separators=(",", ":")) + "\n"
                       for sid in ids(members)).encode()

    paired_raw, delta_raw = jsonl(closure), jsonl(delta)
    result = {"schemaVersion": 5, "locale": "fil", "gameVersion": "1.3.19",
              "status": "cycle005 reproducible dependency closure and exact next delta; distinct review pending",
              "planSha256": sha(plan_path), "afterSha256": sha(after_path),
              "fullStructuralValidationSha256": sha(gate_path),
              "selectorSpecificationPath": str(spec_path.relative_to(ROOT)),
              "selectorSpecificationSha256": sha(spec_path),
              "previousClosureSha256": sha(previous_path),
              "previousPairedSha256": sha(previous_paired_path),
              "reviewEvidenceSha256": after["reviewEvidenceSha256"],
              "freshCorpusValidationSha256": gate["freshCorpusValidationSha256"],
              "sourceAndGlossaryFingerprints": plan["sourceAndGlossaryFingerprints"],
              "compiledProgramSha256": plan["compiledProgramSha256"],
              "compiledContextSha256": plan["compiledContextSha256"],
              "boundedCompiledContextSha256": plan["boundedCompiledContextSha256"],
              "boundedAuthorReviewSha256": plan["boundedAuthorReviewSha256"],
              "acceptedUnits": 16538, "acceptedOrderSha256": id_hash(order),
              "idHashConvention": "UTF-8 LF, one stable ID per line in canonical accepted order",
              "components": component_rows,
              "referentSelectors": [dict(packed(name, members),
                                         sourceRegex=spec["affectedReferentSourceRegex"][name])
                                    for name, members in referent_groups.items()],
              "mandatorySelectors": [dict(packed(name, members),
                                          sourceRegex=spec["mandatorySourceRegex"].get(name))
                                     for name, members in mandatory_groups.items()],
              "localizedSelectors": [dict(packed(name, members),
                                          targetRegex=localized_patterns[name])
                                     for name, members in localized_groups.items()],
              "componentDeltas": component_deltas,
              "previousClosureCount": len(previous_ids),
              "currentClosure": packed("currentClosure", closure),
              "newCurrentMinusPrevious": packed("newCurrentMinusPrevious", newly_added),
              "retiredPreviousMinusCurrent": packed("retiredPreviousMinusCurrent", retired),
              "review04RetiredDependenciesReentered": packed(
                  "review04RetiredDependenciesReentered",
                  {r["stableId"] for r in retired_review04} & closure),
              "review04RetiredDependenciesStillRetired": packed(
                  "review04RetiredDependenciesStillRetired",
                  {r["stableId"] for r in retired_review04} - closure),
              "corrected": packed("corrected", changed),
              "explicitlyInvalidatedPriorEvidence": packed("explicitlyInvalidatedPriorEvidence", invalidated),
              "invalidationRule": "Previously reviewed rows in the seven bounded compiled nodes, exact corrected source repetitions, the repaired attributed-perception/causality source family, or belief+dahil/distorted-face target family; the corrected ID counts separately. Author readings invalidate these dependencies explicitly and do not count as independent acceptance.",
              "retirementRule": "A prior dependency retires only when no current selector component chooses it; source, target, key and node hashes remain exact to its independent review04 decision. The54 prior retired dependencies are separately reconciled on final hashes; any reentered unit enters the exact delta as new closure.",
              "exactNextDelta": packed("exactNextDelta", delta),
              "pairedPath": str(PAIRED.relative_to(ROOT)), "pairedSha256": digest(paired_raw),
              "nextDeltaPairedPath": str(DELTA.relative_to(ROOT)),
              "nextDeltaPairedSha256": digest(delta_raw),
              "unexplainedMissingIds": [], "unexplainedExtraIds": [],
              "reviewStatus": "pending distinct reviewer; author read is not independent acceptance"}
    return result, paired_raw, delta_raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    require(args.write != args.verify, "Choose write or verify")
    result, paired, delta = build()
    raw = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode()
    if args.write:
        require(not any(p.exists() for p in (OUT, PAIRED, DELTA)),
                "Immutable cycle005 closure already exists")
        PAIRED.write_bytes(paired)
        DELTA.write_bytes(delta)
        OUT.write_bytes(raw)
    else:
        require(OUT.read_bytes() == raw and PAIRED.read_bytes() == paired and
                DELTA.read_bytes() == delta, "Stored closure or paired rows differ")
    print(json.dumps({"closureSha256": sha(OUT),
                      "previous": result["previousClosureCount"],
                      "current": result["currentClosure"]["count"],
                      "new": result["newCurrentMinusPrevious"]["count"],
                      "retired": result["retiredPreviousMinusCurrent"]["count"],
                      "corrected": result["corrected"]["count"],
                      "invalidated": result["explicitlyInvalidatedPriorEvidence"]["count"],
                      "exactNextDelta": result["exactNextDelta"]["count"],
                      "unexplainedMissing": 0, "unexplainedExtra": 0}))


if __name__ == "__main__":
    main()
