#!/usr/bin/env python3
"""Reproduce Serbian cycle 003 closure, regressions, and exact reviewer delta."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SR = ROOT / "Translations/sr"
PREVIOUS = SR / "semantic-cycle-002-closure.json"
CORRECTION = SR / "semantic-cycle-003-corrections.json"
PLAN = SR / "semantic-cycle-003-adjudication.json"
REVIEW = SR / "independent-review-02"
PREFIX = "semantic-cycle-003"
GUIDS = {"UI": "0cbd8a7a4f543344bb95659de87f67a5",
         "Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
         "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def textsha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def ordered(order, values):
    return [identifier for identifier in order if identifier in values]


def ids_sha(ids):
    return textsha("".join(identifier + "\n" for identifier in ids))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def emit(path, value, write):
    contents = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        require(path.read_text() == contents, "Immutable evidence differs: " + str(path))
    else:
        require(write, "Missing immutable evidence: " + str(path))
        path.write_text(contents)


def membership(order, values):
    result = ordered(order, values)
    return {"count": len(result), "idsSha256": ids_sha(result), "ids": result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    previous, correction, plan = read(PREVIOUS), read(CORRECTION), read(PLAN)
    summary = read(REVIEW / "summary.json")
    verification = read(REVIEW / "verification.json")
    review_manifest = read(REVIEW / "artifact-manifest.json")
    require(review_manifest["authoredFileSetSha256"] == summary["authoredFileSetSha256"] and
            len(review_manifest["files"]) == 19 and
            all(sha(ROOT / item["path"]) == item["sha256"] and
                (ROOT / item["path"]).stat().st_size == item["bytes"]
                for item in review_manifest["files"]),
            "Independent review artifact manifest changed")
    consumers = read(SR / "independent-review-01/runtime-consumers.json")
    risk = read(SR / "semantic-cycle-002-dynamic-risk.json")
    manifest = read(ROOT / "Source/preserve-exactly-v4.json")
    canonical = [row["stableId"] for row in manifest["tableRows"] + manifest["staticRows"]]
    rules = {row["stableId"]: row for row in manifest["tableRows"] + manifest["staticRows"]}
    require(len(canonical) == len(rules) == 16538, "Canonical inventory changed")
    require(sha(PREVIOUS) == correction["priorClosureSha256"] == plan["priorClosureSha256"]
            and sha(REVIEW / "summary.json") == correction["review02SummarySha256"]
            and summary["closureCount"] == len(previous["closureIds"]["ids"]) == 604
            and summary["deltaReviewed"] == previous["deltaReviewIds"]["count"] == 77
            and summary["authoredFileSetSha256"] == previous["currentAuthoredFileSetSha256"]
            and verification["authoredFileSetSha256"] == summary["authoredFileSetSha256"],
            "Prior independent review boundary changed")
    require(all(sha(ROOT / path) == pin["expectedSha256"] == pin["actualSha256"]
                for path, pin in verification["pins"].items() if not path.startswith("Translations/sr/dialogue-batch-251")),
            "Prior review input changed unexpectedly")
    for name, expected in (("Source/localization-inventory-v3/strings.jsonl", correction["sourceInventorySha256"]),
                           ("Source/localization-inventory-v3/static-text.jsonl", correction["sourceStaticSha256"]),
                           ("Documentation/text-source-acceptance-v1.json", correction["sourceAcceptanceSha256"]),
                           ("Documentation/glossary-translations/sr/layer.json", correction["glossaryFingerprint"]),
                           ("Documentation/glossary-translations/canonical-reviews/sr.json", correction["canonicalGlossaryReviewSha256"])):
        require(sha(ROOT / name) == expected, "Source/glossary pin changed: " + name)
    source_path = ROOT / "Source/localization-inventory-v3/strings.jsonl"
    static_path = ROOT / "Source/localization-inventory-v3/static-text.jsonl"
    source = {row["stableId"]: row for row in
              (json.loads(line) for path in (source_path, static_path) for line in path.open())}
    require(set(canonical) <= set(source), "Accepted source IDs changed")
    target, location, file_ids = {}, {}, defaultdict(list)
    for row in correction["currentAuthoredFileHashes"]:
        path = ROOT / row["path"]
        require(sha(path) == row["sha256"], "Authored file changed: " + row["path"])
        batch = read(path)
        for entry in batch["entries"]:
            identifier = entry.get("stableId") or "string:" + GUIDS[batch["collection"]] + ":" + str(entry["id"])
            require(identifier not in target, "Duplicate target")
            target[identifier], location[identifier] = entry["target"], row["path"]
            file_ids[row["path"]].append(identifier)
        sidecar = read(path.with_suffix(".validation.json"))
        require(sidecar["structuralResult"] == "passed" and
                sidecar.get("batchSha256", sidecar.get("draftSha256")) == row["sha256"],
                "Structural sidecar stale")
    require(len(correction["currentAuthoredFileHashes"]) == 341 and set(target) == set(canonical),
            "Current target coverage changed")
    fileset = textsha("".join(x["path"] + "\t" + x["sha256"] + "\n"
                           for x in sorted(correction["currentAuthoredFileHashes"], key=lambda x: x["path"])))
    require(fileset == correction["currentAuthoredFileSetSha256"], "File-set hash differs")
    exact_path = ROOT / correction["fullPreserveExactReport"]
    require(sha(exact_path) == correction["fullPreserveExactReportSha256"] and
            read(exact_path)["checkedRows"] == 16538 and
            read(exact_path)["exactResult"] == "passed", "Full exact gate changed")
    require(sha(PLAN) == correction["adjudicationSha256"] and
            len(plan["entries"]) == 1, "Adjudication changed")
    changed = set(correction["changedIds"])
    require(changed == {x["stableId"] for x in plan["entries"]} and
            ids_sha(ordered(canonical, changed)) == correction["changedIdsSha256"],
            "Changed ID set differs")
    for entry in plan["entries"]:
        require(target[entry["stableId"]] == entry["acceptedTarget"] and
                source[entry["stableId"]]["source"] == entry["source"],
                "Corrected source/target differs")
    changed_nodes = {node for identifier in changed for node in source[identifier].get("nodeNames", [])}
    require(changed_nodes == {"Hunter_Entrance_Occupied"}, "Unexpected changed scene")
    scene = {identifier for identifier in canonical if
             set(source[identifier].get("nodeNames", [])) & changed_nodes}
    risk_rows = {row["stableId"]: row for row in risk["rows"]}
    require(len(risk_rows) == 111, "Dynamic risk catalog changed")
    item_consumers = {identifier for identifier, row in risk_rows.items()
                      if row["consumerCategory"] == "LocalizeItem"}
    character_consumers = {identifier for identifier, row in risk_rows.items()
                           if row["consumerCategory"] == "GetCharacterOnPlace"}
    affected_dynamic = {identifier for identifier, row in risk_rows.items()
                        if any(x["node"] in changed_nodes for x in row["compiledInstructions"])}
    raw_labels = {x["labelStableId"] for x in consumers["deficitLabels"]}
    for row in consumers["samePlaceLabelCandidates"]:
        if row["node"] in changed_nodes:
            raw_labels.update(x["labelStableId"] for x in row["possibleLabels"]
                              if x.get("labelStableId"))
    source_repetitions = {identifier for identifier in canonical if
                          source[identifier]["source"] in {x["source"] for x in plan["entries"]}}
    target_wordings = {x[k] for x in plan["entries"] for k in ("currentTarget", "acceptedTarget")}
    target_repetitions = {identifier for identifier in canonical if target[identifier] in target_wordings}
    prior_mandatory = read(SR / "semantic-cycle-002-regressions.json")["catalog"]
    regression_sets = {
        "allUiMenuSaveSettingsLanguageAndCreditsLabels": {i for i in canonical if rules[i].get("collection") == "UI"},
        "allSupplementalStaticIncludingCreditsAndLocationDisplays": {i for i in canonical if i.startswith("tmp:")},
        "allFormatSlotAndDynamicJoinRows": set(risk_rows),
        "allTmpMarkupRows": {i for i in canonical if rules[i]["tmpTags"]},
        "checksDialogAndExactSymbol": {i for i in canonical if rules[i].get("collection") == "ChecksDialogs" or rules[i]["wholeTextExact"]},
        "changedSceneSpeakerChoiceGenderAndAgency": scene,
    }
    for name in list(regression_sets)[:5]:
        require(ids_sha(ordered(canonical, regression_sets[name])) == prior_mandatory[name]["idsSha256"],
                "Stable regression catalog changed")
    components = {
        "changedIds": changed,
        "sceneContextIds": scene,
        "exactSourceRepetitionIds": source_repetitions,
        "oldOrNewFullTargetRepetitionIds": target_repetitions,
        "glossaryAndReferentIds": raw_labels,
        "runtimeBindingIds": item_consumers | character_consumers | affected_dynamic | raw_labels,
        "dynamicConsumerAdjacentContextIds": scene,
        "mandatoryRegressionIds": set().union(*regression_sets.values()),
    }
    closure_ids = set().union(*components.values())
    previous_ids = set(previous["closureIds"]["ids"])
    require(ids_sha(previous["closureIds"]["ids"]) == previous["closureIds"]["idsSha256"],
            "Prior closure ID hash differs")
    new = closure_ids - previous_ids
    retired = previous_ids - closure_ids
    reasons = defaultdict(list)
    for identifier in ordered(canonical, (scene | source_repetitions | target_repetitions) & previous_ids - changed):
        if identifier in scene:
            reasons[identifier].append("Hunter occupied-place compiled exchange must be reread after its opening label template changed")
        if identifier in source_repetitions or identifier in target_repetitions:
            reasons[identifier].append("Exact source or complete old/new target repetition depends on the corrected wording")
    invalidated = set(reasons)
    delta = changed | new | invalidated
    adjacent = "string:444ff14f1967f5a4c8eb9e4cf4c913f1:110504457169608705"
    choice1 = "string:444ff14f1967f5a4c8eb9e4cf4c913f1:110504457169608706"
    choice2 = "string:444ff14f1967f5a4c8eb9e4cf4c913f1:110504457169608707"
    require({adjacent, choice1, choice2} <= scene & invalidated and
            {adjacent, choice1, choice2}.isdisjoint(changed) and
            all(identifier in delta for identifier in (adjacent, choice1, choice2)),
            "Hunter adjacent-line selector regression failed")
    def row(identifier):
        source_row = source[identifier]
        return {"stableId": identifier, "collection": source_row.get("collection", "supplementalStatic"),
                "key": source_row.get("key"), "nodeNames": source_row.get("nodeNames", []),
                "source": source_row["source"], "sourceSha256": textsha(source_row["source"]),
                "target": target[identifier], "targetSha256": textsha(target[identifier]),
                "targetFile": location[identifier],
                "components": [name for name, values in components.items() if identifier in values],
                "deltaReasons": (["corrected ID"] if identifier in changed else []) +
                                (["new closure dependency"] if identifier in new else []) +
                                reasons.get(identifier, [])}
    closure_order = ordered(canonical, closure_ids)
    delta_order = ordered(canonical, delta)
    rows_path = SR / (PREFIX + "-review-rows.jsonl")
    delta_path = SR / (PREFIX + "-delta-review-rows.jsonl")
    regression_path = SR / (PREFIX + "-regressions.json")
    closure_path = SR / (PREFIX + "-closure.json")
    emit(rows_path, "".join(json.dumps(row(i), ensure_ascii=False, separators=(",", ":")) + "\n"
                            for i in closure_order), args.write)
    emit(delta_path, "".join(json.dumps(row(i), ensure_ascii=False, separators=(",", ":")) + "\n"
                             for i in delta_order), args.write)
    regressions = {"schemaVersion": 1, "locale": "sr", "cycle": "003",
                   "status": "mandatory regression catalog; separate independent review pending",
                   "catalog": {name: membership(canonical, values) for name, values in regression_sets.items()},
                   "currentAuthoredFileSetSha256": fileset,
                   "sourceInventorySha256": correction["sourceInventorySha256"],
                   "glossaryFingerprint": correction["glossaryFingerprint"],
                   "preserveExactReportSha256": sha(exact_path),
                   "contextOnlyGates": {"speakerServicePrefixesAndProtectedSyntax": "16,538 passed current preserve-exact",
                                        "rawCharacterLabels": "Three known Hunter place-10 UI labels assembled; Neighbour UI label unknown",
                                        "unboundFormatRows": "13 remain unbound to pinned compiled instructions",
                                        "runtimeVisual": "not run", "imagesAndTextures": "excluded by owner"}}
    emit(regression_path, regressions, args.write)
    closure = {
        "schemaVersion": 1, "locale": "sr", "gameVersion": "1.3.19", "cycle": "003",
        "status": "prepared for separate independent delta review; not accepted",
        "canonicalOrder": "Source/preserve-exactly-v4.json tableRows then staticRows",
        "idsHashEncoding": "UTF-8 stable ID followed by LF, including final LF",
        "acceptedUnits": 16538, "firstSemanticPassReviewedUnits": 16538,
        "sourceInventorySha256": correction["sourceInventorySha256"],
        "sourceStaticSha256": correction["sourceStaticSha256"],
        "sourceAcceptanceSha256": correction["sourceAcceptanceSha256"],
        "glossaryFingerprint": correction["glossaryFingerprint"],
        "canonicalGlossaryReviewSha256": correction["canonicalGlossaryReviewSha256"],
        "preserveExactManifestSha256": sha(ROOT / "Source/preserve-exactly-v4.json"),
        "correctionEvidenceSha256": sha(CORRECTION),
        "priorClosureSha256": sha(PREVIOUS),
        "priorReviewedClosureIdsSha256": previous["closureIds"]["idsSha256"],
        "priorReviewerSummarySha256": sha(REVIEW / "summary.json"),
        "priorReviewerManifestSha256": sha(REVIEW / "artifact-manifest.json"),
        "currentAuthoredFileSetSha256": fileset,
        "currentAuthoredFileHashes": correction["currentAuthoredFileHashes"],
        "currentPreserveExactReport": correction["fullPreserveExactReport"],
        "currentPreserveExactReportSha256": sha(exact_path),
        "changedIds": membership(canonical, changed),
        "closureIds": membership(canonical, closure_ids),
        "newDependencyIds": membership(canonical, new),
        "retiredDependencyIds": membership(canonical, retired),
        "retiredDependencyReason": "Previous cycle changed-scene/referent dependencies no longer connect to the sole Hunter correction, its actual input labels, runtime templates, or mandatory regressions; historical evidence retained.",
        "explicitlyInvalidatedPriorIds": membership(canonical, invalidated),
        "explicitInvalidationReasons": {i: reasons[i] for i in ordered(canonical, invalidated)},
        "deltaReviewIds": membership(canonical, delta),
        "deltaFormula": "changed IDs union (current closure minus previous independently reviewed closure) union explicitly invalidated prior IDs",
        "componentLists": {name: membership(canonical, values) for name, values in components.items()},
        "componentSelectors": {
            "sceneContextIds": "All accepted rows in Hunter_Entrance_Occupied, including following RunLine and both choices",
            "exactSourceRepetitionIds": "Every accepted row with the identical complete Russian source",
            "oldOrNewFullTargetRepetitionIds": "Every current complete target equal to the correction's old or new complete target",
            "glossaryAndReferentIds": "Pinned raw deficit and Hunter place-10 UI label IDs; unknown Neighbour excluded",
            "runtimeBindingIds": "All 111 compiled/raw-item/character templates plus actual Hunter label IDs",
            "dynamicConsumerAdjacentContextIds": "Every accepted row in the changed compiled Hunter node",
            "mandatoryRegressionIds": "Union of the explicit current Serbian regression catalog"},
        "selectorRegressionCase": {"changedId": next(iter(changed)), "hostNode": "Hunter_Entrance_Occupied",
                                   "unchangedFollowingRunLineId": adjacent, "unchangedChoiceIds": [choice1, choice2],
                                   "requirement": "All accepted rows in the affected compiled node are selected independently of changedIds"},
        "nontranslatableContextRuntime": {
            "runtimeConsumersSha256": sha(SR / "independent-review-01/runtime-consumers.json"),
            "compiledProgramSha256": consumers["compiledProgramSha256"],
            "bindingsSha256": consumers["bindingsSha256"],
            "deficitConfigSha256": consumers["deficitConfigSha256"],
            "review02CompiledContextSha256": sha(REVIEW / "compiled-delta-context.json"),
            "review02RawLabelCasesSha256": sha(REVIEW / "raw-label-cases.json"),
            "unknownSamePlaceLabels": ["Neighbour"]},
        "fullClosureReviewRows": str(rows_path.relative_to(ROOT)),
        "fullClosureReviewRowsSha256": sha(rows_path),
        "deltaReviewRows": str(delta_path.relative_to(ROOT)),
        "deltaReviewRowsSha256": sha(delta_path),
        "regressionCatalog": str(regression_path.relative_to(ROOT)),
        "regressionCatalogSha256": sha(regression_path),
        "independentReview": "pending", "editorialAcceptance": False}
    emit(closure_path, closure, args.write)
    print(json.dumps({"result": "written" if args.write else "verified",
                      "changedIds": len(changed), "closureIds": len(closure_order),
                      "newDependencies": len(new), "retiredDependencies": len(retired),
                      "invalidatedPrior": len(invalidated), "deltaReviewIds": len(delta_order),
                      "closureSha256": sha(closure_path), "deltaIdsSha256": ids_sha(delta_order),
                      "deltaRowsSha256": sha(delta_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
