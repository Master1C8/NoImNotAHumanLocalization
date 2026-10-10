#!/usr/bin/env python3
"""Build or verify the Serbian cycle 002 dependency closure and exact review delta."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SR = ROOT / "Translations/sr"
REVIEW = SR / "independent-review-01"
PREFIX = "semantic-cycle-002"
CORRECTION = SR / (PREFIX + "-corrections.json")
PREVIOUS = SR / "semantic-cycle-001-closure.json"
RISK = SR / (PREFIX + "-dynamic-risk.json")
CLOSURE = SR / (PREFIX + "-closure.json")
ROWS = SR / (PREFIX + "-review-rows.jsonl")
DELTA_ROWS = SR / (PREFIX + "-delta-review-rows.jsonl")
REGRESSIONS = SR / (PREFIX + "-regressions.json")
HANDOFF = SR / (PREFIX + "-independent-handoff.md")
GUIDS = {"UI": "0cbd8a7a4f543344bb95659de87f67a5",
         "Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
         "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def textsha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def idsha(ids):
    return textsha("".join(identifier + "\n" for identifier in ids))


def ordered(order, values):
    return [identifier for identifier in order if identifier in values]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def immutable(path, contents, write):
    if path.exists():
        require(path.read_text() == contents, "Immutable evidence differs: " + str(path))
    else:
        require(write, "Missing evidence: " + str(path))
        path.write_text(contents)


def membership(order, values):
    ids = ordered(order, values)
    return {"count": len(ids), "idsSha256": idsha(ids), "ids": ids}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    correction, previous, risk = read(CORRECTION), read(PREVIOUS), read(RISK)
    reviewer = read(REVIEW / "summary.json")
    consumers = read(REVIEW / "runtime-consumers.json")
    manifest = read(ROOT / "Source/preserve-exactly-v4.json")
    canonical = [r["stableId"] for r in manifest["tableRows"] + manifest["staticRows"]]
    rules = {r["stableId"]: r for r in manifest["tableRows"] + manifest["staticRows"]}
    require(len(canonical) == len(rules) == 16538, "Canonical accepted inventory changed")
    require(sha(PREVIOUS) == correction["priorClosureSha256"] and
            sha(RISK) == correction["dynamicRiskSha256"] and
            reviewer["closureReviewed"] == len(previous["closureIds"]) == 687 and
            reviewer["closureIdsSha256"] == previous["closureIdsSha256"] and
            reviewer["authoredFileSetSha256"] == previous["currentAuthoredFileSetSha256"],
            "Prior independent review boundary changed")
    strings = ROOT / "Source/localization-inventory-v3/strings.jsonl"
    static = ROOT / "Source/localization-inventory-v3/static-text.jsonl"
    glossary = ROOT / "Documentation/glossary-translations/sr/layer.json"
    require(sha(strings) == correction["sourceInventorySha256"] and
            sha(static) == correction["sourceStaticSha256"] and
            sha(glossary) == correction["glossaryFingerprint"] and
            sha(ROOT / "Documentation/text-source-acceptance-v1.json") ==
            correction["sourceAcceptanceSha256"], "Source or glossary changed")
    source = {r["stableId"]: r for r in (json.loads(line) for line in strings.open())}
    source.update({r["stableId"]: r for r in (json.loads(line) for line in static.open())})
    target, location, file_ids = {}, {}, defaultdict(list)
    for file in correction["currentAuthoredFileHashes"]:
        path = ROOT / file["path"]
        require(sha(path) == file["sha256"], "Corrected authored hash changed")
        batch = read(path)
        for entry in batch["entries"]:
            identifier = entry.get("stableId") or ("string:" + GUIDS[batch["collection"]]
                        + ":" + str(entry["id"]))
            require(identifier not in target, "Duplicate target ID")
            target[identifier], location[identifier] = entry["target"], file["path"]
            file_ids[file["path"]].append(identifier)
        sidecar = read(path.with_suffix(".validation.json"))
        require(sidecar["structuralResult"] == "passed" and
                sidecar.get("batchSha256", sidecar.get("draftSha256")) == file["sha256"],
                "Stale structural sidecar")
    require(set(target) == set(canonical) and len(correction["currentAuthoredFileHashes"]) == 341,
            "Corrected target coverage changed")
    fileset = textsha("".join(x["path"] + "\t" + x["sha256"] + "\n"
                             for x in sorted(correction["currentAuthoredFileHashes"],
                                             key=lambda x: x["path"])))
    require(fileset == correction["currentAuthoredFileSetSha256"],
            "Corrected authored file set changed")
    exact = ROOT / correction["fullPreserveExactReport"]
    require(sha(exact) == correction["fullPreserveExactReportSha256"] and
            read(exact)["exactResult"] == "passed" and
            read(exact)["checkedRows"] == 16538, "Full exact gate changed")

    plan = read(SR / "semantic-cycle-002-adjudication.json")
    require(sha(SR / "semantic-cycle-002-adjudication.json") ==
            correction["adjudicationSha256"], "Adjudication changed")
    changed = set(correction["changedIds"])
    require(len(changed) == 17 and changed == {x["stableId"] for x in plan["entries"]}
            and idsha(ordered(canonical, changed)) == correction["changedIdsSha256"],
            "Changed IDs differ from accepted batch")
    for item in plan["entries"]:
        require(target[item["stableId"]] == item["acceptedTarget"] and
                source[item["stableId"]]["source"] == item["source"],
                "Corrected value or source changed")

    risk_rows = {r["stableId"]: r for r in risk["rows"]}
    require(len(risk_rows) == 111 and all(identifier in rules for identifier in risk_rows),
            "Bounded consumer risk inventory changed")
    changed_nodes = {node for identifier in changed for node in
                     source[identifier].get("nodeNames", [])}
    scene = {identifier for identifier in canonical if
             set(source[identifier].get("nodeNames", [])) & changed_nodes}
    ui_files = {location[identifier] for identifier in changed
                if rules[identifier].get("collection") == "UI"}
    ui_context = {identifier for file in ui_files for identifier in file_ids[file]}

    changed_ui_labels = {identifier for identifier in changed if
                         (source[identifier].get("key") or "").startswith("characterName_")}
    label_dependent_nodes = {r["node"] for r in consumers["samePlaceLabelCandidates"]
                             if any(x.get("labelStableId") in changed_ui_labels for x in
                                    r["possibleLabels"])}
    label_dependent_context = {identifier for identifier in canonical if
                               set(source[identifier].get("nodeNames", [])) &
                               label_dependent_nodes}
    affected_dynamic_nodes = changed_nodes | label_dependent_nodes
    affected_dynamic_rows = {identifier for identifier, row in risk_rows.items()
                             if any(x["node"] in affected_dynamic_nodes for x in
                                    row["compiledInstructions"])}
    item_consumers = {identifier for identifier, row in risk_rows.items()
                      if row["consumerCategory"] == "LocalizeItem"}
    character_consumers = {identifier for identifier, row in risk_rows.items()
                           if row["consumerCategory"] == "GetCharacterOnPlace"}
    raw_labels = {x["labelStableId"] for x in consumers["deficitLabels"]}
    for row in consumers["samePlaceLabelCandidates"]:
        if row["node"] in affected_dynamic_nodes:
            raw_labels.update(x["labelStableId"] for x in row["possibleLabels"]
                              if x.get("labelStableId"))
    require(raw_labels <= set(canonical), "Runtime label dependency outside accepted scope")
    runtime_binding = (item_consumers | character_consumers | raw_labels |
                       affected_dynamic_rows | ui_context)

    original = {x["source"] for x in plan["entries"]}
    source_repetitions = {identifier for identifier in canonical if
                          source[identifier]["source"] in original}
    wordings = {x[k] for x in plan["entries"] for k in
                ("currentTarget", "acceptedTarget")}
    target_repetitions = {identifier for identifier in canonical if
                          target[identifier] in wordings}
    glossary_referents = changed_ui_labels | label_dependent_context | raw_labels
    prior_mandatory = read(SR / "semantic-cycle-001-regressions.json")["catalog"]
    regression_sets = {
        "allUiMenuSaveSettingsLanguageAndCreditsLabels": {
            identifier for identifier in canonical if rules[identifier].get("collection") == "UI"},
        "allSupplementalStaticIncludingCreditsAndLocationDisplays": {
            identifier for identifier in canonical if identifier.startswith("tmp:")},
        "allFormatSlotAndDynamicJoinRows": set(risk_rows),
        "allTmpMarkupRows": {identifier for identifier in canonical if rules[identifier]["tmpTags"]},
        "checksDialogAndExactSymbol": {identifier for identifier in canonical if
            rules[identifier].get("collection") == "ChecksDialogs" or
            rules[identifier]["wholeTextExact"]},
        "changedSceneSpeakerChoiceGenderAndAgency": scene | label_dependent_context,
    }
    for name in list(regression_sets)[:5]:
        require(idsha(ordered(canonical, regression_sets[name])) ==
                prior_mandatory[name]["idsSha256"],
                "Stable mandatory regression surface changed: " + name)
    components = {
        "changedIds": changed,
        "sceneContextIds": scene | ui_context,
        "exactSourceRepetitionIds": source_repetitions,
        "oldOrNewFullTargetRepetitionIds": target_repetitions,
        "glossaryAndReferentIds": glossary_referents,
        "runtimeBindingIds": runtime_binding,
        "dynamicConsumerAdjacentContextIds": scene | label_dependent_context,
        "mandatoryRegressionIds": set().union(*regression_sets.values()),
    }
    closure_ids = set().union(*components.values())
    require(changed <= closure_ids <= set(canonical), "Closure ID boundary invalid")
    previous_ids = set(previous["closureIds"])
    require(idsha(previous["closureIds"]) == previous["closureIdsSha256"],
            "Prior closure ID hash differs")
    new_dependencies = closure_ids - previous_ids
    retired = previous_ids - closure_ids
    reasons = defaultdict(set)
    for identifier in (scene | label_dependent_context) & previous_ids - changed:
        reasons[identifier].add("changed compiled exchange or changed runtime label now affects the prior contextual reading")
    for identifier in (source_repetitions | target_repetitions) & previous_ids - changed:
        reasons[identifier].add("a repeated source or old/new complete target is affected by the accepted wording")
    invalidated = set(reasons)
    delta = changed | new_dependencies | invalidated
    require(delta == (changed | (closure_ids - previous_ids) | invalidated),
            "Exact delta formula mismatch")
    regression_case = {
        "missedDirectAdjacentId": "string:444ff14f1967f5a4c8eb9e4cf4c913f1:110504457144442886",
        "hostNode": "Ballerina_Entrance_Occupied",
        "changedRawLabelId": "string:0cbd8a7a4f543344bb95659de87f67a5:167520134505766919",
        "requirement": "All accepted rows in an affected compiled node and every same-place consumer of a changed UI label remain selected during normal regeneration.",
    }
    # The reported adjacent defect is now itself changed. Check another
    # unchanged RunLine in the same compiled node, so the selector regression
    # cannot pass merely because changedIds forces the reported row in.
    unchanged_adjacent = "string:444ff14f1967f5a4c8eb9e4cf4c913f1:110504457144442887"
    require(regression_case["missedDirectAdjacentId"] in scene and
            regression_case["missedDirectAdjacentId"] in changed and
            unchanged_adjacent in scene and unchanged_adjacent not in changed and
            regression_case["changedRawLabelId"] in changed and
            "Ballerina_Entrance_Occupied" in label_dependent_nodes and
            any(x in label_dependent_context for x in character_consumers),
            "Dynamic adjacency selector regression failed")

    component_lists = {name: membership(canonical, values)
                       for name, values in components.items()}
    regression_lists = {name: membership(canonical, values)
                        for name, values in regression_sets.items()}
    ordered_closure, ordered_delta = ordered(canonical, closure_ids), ordered(canonical, delta)
    def make_row(identifier):
        row = source[identifier]
        return {"stableId": identifier, "collection": row.get("collection", "supplementalStatic"),
                "key": row.get("key"), "nodeNames": row.get("nodeNames", []),
                "source": row["source"], "sourceSha256": textsha(row["source"]),
                "target": target[identifier], "targetSha256": textsha(target[identifier]),
                "targetFile": location[identifier],
                "components": [name for name, values in components.items() if identifier in values],
                "deltaReasons": (["corrected ID"] if identifier in changed else []) +
                    (["new closure dependency"] if identifier in new_dependencies else []) +
                    sorted(reasons.get(identifier, []))}
    rows = "".join(json.dumps(make_row(i), ensure_ascii=False, separators=(",", ":")) + "\n"
                   for i in ordered_closure)
    delta_rows = "".join(json.dumps(make_row(i), ensure_ascii=False, separators=(",", ":")) + "\n"
                         for i in ordered_delta)
    immutable(ROWS, rows, args.write)
    immutable(DELTA_ROWS, delta_rows, args.write)
    regression = {
        "schemaVersion": 1, "locale": "sr", "cycle": "002",
        "status": "mandatory semantic regressions pending separate independent reviewer",
        "catalog": regression_lists,
        "currentAuthoredFileSetSha256": fileset,
        "sourceInventorySha256": correction["sourceInventorySha256"],
        "glossaryFingerprint": correction["glossaryFingerprint"],
        "preserveExactReportSha256": sha(exact),
        "contextOnlyGates": {
            "speakerServicePrefixesAndProtectedSyntax": "16,538 current units passed the pinned full preserve-exact gate; semantic consumer checks still pending.",
            "rawItemAndCharacterLabels": "Six pinned deficit item labels and actual same-place UI labels are selected by runtimeBindingIds; three missing UI labels stay explicitly unknown.",
            "unboundFormatRows": "Thirteen accepted format-slot rows lack a matching instruction in the pinned compiled program; no runtime reachability is inferred.",
            "imagesAndTextures": "excluded by owner", "runtimeVisual": "not run"},
    }
    immutable(REGRESSIONS, json.dumps(regression, ensure_ascii=False, indent=2) + "\n",
              args.write)
    context = {
        "runtimeConsumersSha256": sha(REVIEW / "runtime-consumers.json"),
        "runtimeDllSha256": consumers["sourceDllSha256"],
        "compiledProgramSha256": consumers["compiledProgramSha256"],
        "bindingsSha256": consumers["bindingsSha256"],
        "deficitConfigSha256": consumers["deficitConfigSha256"],
        "staticAuthoredMapSha256": correction["staticAuthoredRecipeSha256"],
        "staticDraftSha256": correction["staticDraftSha256"],
        "dialogueCommonRecipeSha256": correction["dialogueCommonRecipeSha256"],
        "unknownSamePlaceLabels": sorted({x["enum"] for r in consumers["samePlaceLabelCandidates"]
                                          for x in r["possibleLabels"] if not x.get("labelStableId")}),
    }
    closure = {
        "schemaVersion": 1, "locale": "sr", "gameVersion": "1.3.19", "cycle": "002",
        "status": "prepared for separate independent delta review; not accepted",
        "canonicalOrder": "Source/preserve-exactly-v4.json tableRows then staticRows",
        "idsHashEncoding": "UTF-8 stable ID followed by LF, including final LF",
        "acceptedUnits": 16538, "firstSemanticPassReviewedUnits": 16538,
        "sourceInventorySha256": correction["sourceInventorySha256"],
        "sourceStaticSha256": correction["sourceStaticSha256"],
        "sourceAcceptanceSha256": correction["sourceAcceptanceSha256"],
        "glossaryFingerprint": correction["glossaryFingerprint"],
        "preserveExactManifestSha256": sha(ROOT / "Source/preserve-exactly-v4.json"),
        "correctionEvidenceSha256": sha(CORRECTION),
        "priorClosureSha256": sha(PREVIOUS),
        "priorReviewedClosureIdsSha256": previous["closureIdsSha256"],
        "priorReviewerSummarySha256": sha(REVIEW / "summary.json"),
        "currentAuthoredFileSetSha256": fileset,
        "currentAuthoredFileHashes": correction["currentAuthoredFileHashes"],
        "currentPreserveExactReport": correction["fullPreserveExactReport"],
        "currentPreserveExactReportSha256": sha(exact),
        "changedIds": membership(canonical, changed),
        "closureIds": membership(canonical, closure_ids),
        "newDependencyIds": membership(canonical, new_dependencies),
        "retiredDependencyIds": membership(canonical, retired),
        "retiredDependencyReason": "Only prior correction scene/referent context; no current changed-unit, actual consumer, raw-label or mandatory regression dependency remains.",
        "explicitlyInvalidatedPriorIds": membership(canonical, invalidated),
        "explicitInvalidationReasons": {identifier: sorted(reasons[identifier])
                                        for identifier in ordered(canonical, invalidated)},
        "deltaReviewIds": membership(canonical, delta),
        "deltaFormula": "changed IDs union (current closure minus prior reviewed closure) union explicitly invalidated prior IDs",
        "componentLists": component_lists,
        "componentSelectors": {
            "sceneContextIds": "Every accepted unit in each changed Yarn node, plus the changed UI batch.",
            "exactSourceRepetitionIds": "Every accepted unit with a complete Russian source equal to a corrected source.",
            "oldOrNewFullTargetRepetitionIds": "Every current complete target equal to a corrected old or new target.",
            "glossaryAndReferentIds": "Changed approved-character UI labels, every actual same-place consumer node receiving them, and all pinned raw item/character labels feeding affected dynamic nodes.",
            "runtimeBindingIds": "All compiled raw item and raw character template IDs, affected compiled node rows, actual input labels, and the changed UI batch.",
            "dynamicConsumerAdjacentContextIds": "Every accepted row in a changed dynamic consumer's compiled Yarn node, including following RunLine rows without a slot.",
            "mandatoryRegressionIds": "Union of the explicit current Serbian regression catalog, separate from the exact diff delta."},
        "selectorRegressionCase": regression_case,
        "nontranslatableContextRuntime": context,
        "nontranslatableContextRuntimeSha256": textsha(json.dumps(
            context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))),
        "fullClosureReviewRows": str(ROWS.relative_to(ROOT)),
        "fullClosureReviewRowsSha256": sha(ROWS),
        "deltaReviewRows": str(DELTA_ROWS.relative_to(ROOT)),
        "deltaReviewRowsSha256": sha(DELTA_ROWS),
        "regressionCatalog": str(REGRESSIONS.relative_to(ROOT)),
        "regressionCatalogSha256": sha(REGRESSIONS),
        "independentReview": "pending", "editorialAcceptance": False,
    }
    immutable(CLOSURE, json.dumps(closure, ensure_ascii=False, indent=2) + "\n",
              args.write)
    handoff = (
        "# Serbian cycle 002 independent delta handoff\n\n"
        "The complete 16,538-unit first semantic pass and 687-row first independent review "
        "remain pinned. The first independent review required changes; its 15 findings plus "
        "two further bounded raw-item cases were adjudicated and applied as one 17-ID batch. "
        "No clean independent review or editorial acceptance is claimed.\n\n"
        f"- Corrected authored file-set SHA-256: `{fileset}`.\n"
        f"- Current closure: `{CLOSURE.relative_to(ROOT)}` (SHA-256 `{sha(CLOSURE)}`, "
        f"{len(ordered_closure)} IDs).\n"
        f"- Exact next diff set: `{DELTA_ROWS.relative_to(ROOT)}` "
        f"(SHA-256 `{sha(DELTA_ROWS)}`, {len(ordered_delta)} IDs).\n"
        f"- Full closure rows: `{ROWS.relative_to(ROOT)}` "
        f"(SHA-256 `{sha(ROWS)}`).\n"
        f"- Mandatory regression catalog: `{REGRESSIONS.relative_to(ROOT)}` "
        f"(SHA-256 `{sha(REGRESSIONS)}`).\n"
        f"- Full preserve-exact report: `{correction['fullPreserveExactReport']}` "
        f"(SHA-256 `{sha(exact)}`, 16,538 passed).\n\n"
        "A separate reviewer should first verify every pinned hash, compare every exact delta row "
        "against Russian source, approved glossary, compiled scene/branch and actual raw-label "
        "consumer, then check the entire mandatory regression catalog. The closure JSON records "
        "new and retired dependencies, each explicit prior-row invalidation reason, and the "
        "Ballerina adjacent-line selector regression. Preserve the dismissed Bestson and phone "
        "decisions. Unknown UI labels and unbound source rows remain classified limits, not "
        "fabricated runtime evidence. Record a clean verdict only on unchanged corrected hashes. "
        "Runtime, visual, fonts, packaging and Git integration remain separate.\n")
    immutable(HANDOFF, handoff, args.write)
    print(json.dumps({"result": "written" if args.write else "verified",
                      "changedIds": len(changed), "closureIds": len(ordered_closure),
                      "deltaReviewIds": len(ordered_delta),
                      "newDependencies": len(new_dependencies),
                      "invalidatedPrior": len(invalidated),
                      "retiredDependencies": len(retired),
                      "closureSha256": sha(CLOSURE),
                      "deltaIdsSha256": idsha(ordered_delta),
                      "deltaRowsSha256": sha(DELTA_ROWS)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
