#!/usr/bin/env python3
"""Build or verify the immutable Serbian correction closure and reviewer handoff."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCALE = ROOT / "Translations" / "sr"
MANIFEST = ROOT / "Source" / "preserve-exactly-v4.json"
STRINGS = ROOT / "Source" / "localization-inventory-v3" / "strings.jsonl"
STATIC = ROOT / "Source" / "localization-inventory-v3" / "static-text.jsonl"
PRE = LOCALE / "semantic-cycle-001-precorrection.json"
CORRECTIONS = LOCALE / "semantic-cycle-001-corrections.json"
REGEN = LOCALE / "semantic-cycle-001-static-regeneration.json"
ROWS = LOCALE / "semantic-cycle-001-review-rows.jsonl"
REGRESSIONS = LOCALE / "semantic-cycle-001-regressions.json"
CLOSURE = LOCALE / "semantic-cycle-001-closure.json"
HANDOFF = LOCALE / "independent-review-handoff.md"
GUIDS = {
    "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6",
    "UI": "0cbd8a7a4f543344bb95659de87f67a5",
    "Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def ids_digest(ids: list[str]) -> str:
    return text_digest("".join(identifier + "\n" for identifier in ids))


def read(path: Path):
    return json.loads(path.read_text())


def require(condition: bool, message: str):
    if not condition:
        raise ValueError(message)


def write_or_verify(path: Path, contents: str, write: bool):
    if path.exists():
        require(path.read_text() == contents, "Immutable evidence differs: " + str(path))
    else:
        require(write, "Missing evidence: " + str(path))
        path.write_text(contents)


def ordered_subset(order: list[str], identifiers: set[str]) -> list[str]:
    return [identifier for identifier in order if identifier in identifiers]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Create missing immutable evidence")
    args = parser.parse_args()
    pre, correction, regen, manifest = read(PRE), read(CORRECTIONS), read(REGEN), read(MANIFEST)
    require(digest(PRE) == correction["priorEvidenceSha256"], "First-pass evidence changed")
    require(digest(CORRECTIONS) == regen["previousCorrectionEvidenceSha256"],
            "Correction evidence changed")
    require(digest(STRINGS) == pre["sourceInventorySha256"] ==
            correction["sourceInventorySha256"], "Russian table source changed")
    require(digest(STATIC) == pre["sourceStaticSha256"] ==
            correction["sourceStaticSha256"], "Russian static source changed")
    require(digest(ROOT / "Documentation/text-source-acceptance-v1.json") ==
            pre["sourceAcceptanceSha256"], "Acceptance changed")
    require(digest(ROOT / "Documentation/glossary-translations/sr/layer.json") ==
            pre["glossaryFingerprint"], "Approved glossary changed")
    require(digest(MANIFEST) == pre["preserveExactlyManifestSha256"],
            "Preserve-exact manifest changed")
    require(digest(LOCALE / "static-authored-map.json") ==
            regen["authoredStaticMapSha256"] and
            digest(LOCALE / "credits-role-map.json") == regen["creditsRoleMapSha256"] and
            digest(LOCALE / "reproduce_static_draft.py") ==
            regen["reproductionScriptSha256"], "Static regeneration inputs changed")
    require(digest(LOCALE / "static-text-draft.json") ==
            regen["currentStaticDraftSha256"], "Regenerated static draft changed")

    canonical = [row["stableId"] for row in manifest["tableRows"] +
                 manifest["staticRows"]]
    require(len(canonical) == len(set(canonical)) == 16538,
            "Canonical accepted-ID order changed")
    source = {row["stableId"]: row for row in
              (json.loads(line) for line in STRINGS.open())}
    source.update({row["stableId"]: row for row in
                   (json.loads(line) for line in STATIC.open())})
    target = {}
    location = {}
    file_ids = defaultdict(list)
    current_files = regen["currentAuthoredFileHashes"]
    require(len(current_files) == 341, "Current authored file count changed")
    for file in current_files:
        path = ROOT / file["path"]
        require(digest(path) == file["sha256"], "Current authored file changed")
        batch = read(path)
        for entry in batch["entries"]:
            identifier = entry.get("stableId") or ("string:" +
                         GUIDS[batch["collection"]] + ":" + str(entry["id"]))
            require(identifier not in target, "Duplicate target ID")
            target[identifier] = entry["target"]
            location[identifier] = file["path"]
            file_ids[file["path"]].append(identifier)
    require(set(target) == set(canonical), "Current target coverage changed")
    current_set = text_digest("".join(file["path"] + "\t" + file["sha256"] + "\n"
                                      for file in sorted(current_files,
                                                         key=lambda item: item["path"])))
    require(current_set == regen["currentAuthoredFileSetSha256"],
            "Current authored file set changed")
    for file in current_files:
        sidecar = read((ROOT / file["path"]).with_suffix(".validation.json"))
        require(sidecar["structuralResult"] == "passed" and
                sidecar.get("batchSha256", sidecar.get("draftSha256")) == file["sha256"],
                "Stale structural sidecar")
    preserve = ROOT / regen["fullPreserveExactReport"]
    require(digest(preserve) == regen["fullPreserveExactReportSha256"] and
            read(preserve)["exactResult"] == "passed", "Current exact gate changed")

    findings = pre["acceptedCorrectionFindings"]
    changed = {finding["stableId"] for finding in findings}
    require(len(changed) == len(findings) == 26 and
            changed == set(correction["changedIds"]), "Correction ID set changed")
    for finding in findings:
        identifier = finding["stableId"]
        require(source[identifier]["source"] == finding["source"] and
                target[identifier] == finding["proposedTarget"],
                "Corrected source/target row changed")

    scene_names = {name for identifier in changed
                   for name in source[identifier].get("nodeNames", [])}
    scene = {identifier for identifier in canonical
             if set(source[identifier].get("nodeNames", [])) & scene_names}
    changed_ui_files = {location[identifier] for identifier in changed
                        if source[identifier].get("collection") == "UI"}
    ui_context = {identifier for path in changed_ui_files for identifier in file_ids[path]}
    source_values = {finding["source"] for finding in findings}
    source_repetitions = {identifier for identifier in canonical
                          if source[identifier]["source"] in source_values}
    target_values = {value for finding in findings for value in
                     (finding["currentTarget"], finding["proposedTarget"])}
    target_repetitions = {identifier for identifier in canonical
                          if target[identifier] in target_values}
    # One-based positions in the 26 accepted findings, not the original
    # proposal sequence (which also contained one dismissed false positive).
    referent_finding_numbers = {4, 5, 6, 10, 11, 12, 17, 18, 19, 20, 21,
                                23, 24, 25, 26}
    referent_nodes = {name for number in referent_finding_numbers
                      for name in source[pre["acceptedCorrectionFindings"][number - 1]
                                             ["stableId"]].get("nodeNames", [])}
    referents = {identifier for identifier in canonical
                 if set(source[identifier].get("nodeNames", [])) & referent_nodes}
    runtime_binding = set(ui_context) | {
        identifier for identifier in changed if identifier.startswith("tmp:")}
    components = {
        "changedIds": changed,
        "sceneContextIds": scene | ui_context,
        "exactSourceRepetitionIds": source_repetitions,
        "oldOrNewFullTargetRepetitionIds": target_repetitions,
        "referentAndAgencyContextIds": referents,
        "runtimeBindingIds": runtime_binding,
        "glossaryChangedConceptIds": set(),
    }

    rules = {row["stableId"]: row for row in manifest["tableRows"] +
             manifest["staticRows"]}
    regression_sets = {
        "allUiMenuSaveSettingsLanguageAndCreditsLabels": {
            identifier for identifier in canonical if rules[identifier].get("collection") == "UI"},
        "allSupplementalStaticIncludingCreditsAndLocationDisplays": {
            identifier for identifier in canonical if identifier.startswith("tmp:")},
        "allFormatSlotAndDynamicJoinRows": {
            identifier for identifier in canonical if rules[identifier]["formatSlots"]},
        "allTmpMarkupRows": {
            identifier for identifier in canonical if rules[identifier]["tmpTags"]},
        "checksDialogAndExactSymbol": {
            identifier for identifier in canonical
            if rules[identifier].get("collection") == "ChecksDialogs" or
            rules[identifier]["wholeTextExact"]},
        "changedSceneSpeakerChoiceGenderAndAgency": scene | referents,
    }
    components["mandatoryRegressionIds"] = set().union(*regression_sets.values())
    closure_ids = set().union(*components.values())
    require(changed <= closure_ids and closure_ids <= set(canonical),
            "Closure boundary invalid")
    ordered_components = {name: ordered_subset(canonical, values)
                          for name, values in components.items()}
    ordered_regressions = {name: ordered_subset(canonical, values)
                           for name, values in regression_sets.items()}
    ordered_closure = ordered_subset(canonical, closure_ids)
    ordered_changed = ordered_subset(canonical, changed)
    require(set(ordered_changed) == set(correction["changedIds"]),
            "Changed IDs differ from correction evidence")

    review_rows = []
    for identifier in ordered_closure:
        item = source[identifier]
        original, localized = item["source"], target[identifier]
        review_rows.append({
            "stableId": identifier,
            "collection": item.get("collection", "supplementalStatic"),
            "source": original,
            "target": localized,
            "sourceSha256": text_digest(original),
            "targetSha256": text_digest(localized),
            "targetFile": location[identifier],
            "key": item.get("key"),
            "nodeNames": item.get("nodeNames", []),
            "components": [name for name, values in components.items()
                           if identifier in values],
        })
    rows_text = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
                        for row in review_rows)
    write_or_verify(ROWS, rows_text, args.write)

    regressions = {
        "schemaVersion": 1, "locale": "sr", "cycle": "001",
        "canonicalOrder": "Source/preserve-exactly-v4.json tableRows then staticRows",
        "catalog": {name: {"count": len(ids), "idsSha256": ids_digest(ids), "ids": ids}
                    for name, ids in ordered_regressions.items()},
        "contextOnlyGates": {
            "speakerServicePrefixes": "All 16,538 current values checked by the pinned preserve-exact manifest; changed scenes are in the review rows.",
            "glossaryRosterAndCharacterRules": "Approved Serbian glossary hash unchanged; changed gender, person, weapon and agency scenes are in referentAndAgencyContextIds.",
            "protectedCommandsBranchesAndExactValues": "Full current preserve-exact gate passed; no shared parser or binding changed.",
            "textBearingImages": "Not applicable: translated images and textures excluded by owner.",
            "rtlShaping": "Not applicable to Serbian Cyrillic LTR; runtime font and layout remain untested.",
            "runtimeVisual": "Not run under this text-only assignment.",
        },
        "reviewRows": str(ROWS.relative_to(ROOT)),
        "reviewRowsSha256": digest(ROWS),
    }
    regressions_text = json.dumps(regressions, ensure_ascii=False, indent=2) + "\n"
    write_or_verify(REGRESSIONS, regressions_text, args.write)

    protected_context = {
        "preserveExactManifestSha256": digest(MANIFEST),
        "staticAuthoredMapSha256": digest(LOCALE / "static-authored-map.json"),
        "creditsRoleMapSha256": digest(LOCALE / "credits-role-map.json"),
        "staticReproductionScriptSha256": digest(LOCALE / "reproduce_static_draft.py"),
        "correctedRows": [{"stableId": identifier,
                           "speakerPrefix": rules[identifier]["speakerPrefix"],
                           "formatSlots": rules[identifier]["formatSlots"],
                           "tmpTags": rules[identifier]["tmpTags"],
                           "numbers": rules[identifier]["numbers"],
                           "lineBreaks": rules[identifier]["lineBreaks"]}
                          for identifier in ordered_changed],
    }
    closure = {
        "schemaVersion": 1, "locale": "sr", "gameVersion": "1.3.19",
        "cycle": "001", "status": "prepared for independent review; not reviewed",
        "canonicalOrder": "Source/preserve-exactly-v4.json tableRows then staticRows",
        "acceptedUnits": 16538,
        "firstSemanticPassReviewedUnits": 16538,
        "firstSemanticPassReviewedPrefixIdsSha256": pre["reviewedPrefixIdsSha256"],
        "sourceInventorySha256": digest(STRINGS),
        "sourceStaticSha256": digest(STATIC),
        "sourceAcceptanceSha256": digest(ROOT / "Documentation/text-source-acceptance-v1.json"),
        "glossaryFingerprint": digest(ROOT / "Documentation/glossary-translations/sr/layer.json"),
        "precorrectionEvidenceSha256": digest(PRE),
        "correctionEvidenceSha256": digest(CORRECTIONS),
        "staticRegenerationEvidenceSha256": digest(REGEN),
        "currentAuthoredFileSetSha256": current_set,
        "currentAuthoredFileHashes": current_files,
        "currentPreserveExactReport": regen["fullPreserveExactReport"],
        "currentPreserveExactReportSha256": digest(preserve),
        "changedIds": ordered_changed,
        "changedIdsCount": len(ordered_changed),
        "changedIdsSha256": ids_digest(ordered_changed),
        "closureIds": ordered_closure,
        "closureIdsCount": len(ordered_closure),
        "closureIdsSha256": ids_digest(ordered_closure),
        "componentLists": {name: {"count": len(ids), "idsSha256": ids_digest(ids), "ids": ids}
                           for name, ids in ordered_components.items()},
        "componentSelector": {
            "sceneContextIds": "All accepted Dialogs IDs sharing any pinned Yarn nodeName with a corrected ID; all UI rows in a corrected UI batch.",
            "exactSourceRepetitionIds": "Every accepted ID whose complete Russian source equals a corrected source value.",
            "oldOrNewFullTargetRepetitionIds": "Every current target exactly equal to a corrected old or new complete target value.",
            "referentAndAgencyContextIds": "Whole pinned Yarn nodes for corrections affecting person, gender, referent, agency, weapon or action roles.",
            "runtimeBindingIds": "Corrected UI batch rows and corrected static TMP ID; shared runtime binding and parser unchanged.",
            "glossaryChangedConceptIds": "Empty because no approved glossary concept or character evidence changed; local uses remain in scene context.",
            "mandatoryRegressionIds": "Union of the pinned explicit Serbian regression catalog, independent of correction-specific dependencies.",
        },
        "nontranslatableContextRuntime": protected_context,
        "nontranslatableContextRuntimeSha256": text_digest(json.dumps(
            protected_context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))),
        "reviewRows": str(ROWS.relative_to(ROOT)),
        "reviewRowsCount": len(review_rows),
        "reviewRowsSha256": digest(ROWS),
        "regressionCatalog": str(REGRESSIONS.relative_to(ROOT)),
        "regressionCatalogSha256": digest(REGRESSIONS),
        "independentReview": "not performed",
        "editorialAcceptance": False,
    }
    closure_text = json.dumps(closure, ensure_ascii=False, indent=2) + "\n"
    write_or_verify(CLOSURE, closure_text, args.write)

    handoff = ("# Serbian text independent review handoff\n\n"
               "The first direct Russian-to-Serbian semantic pass covered all 16,538 accepted IDs. "
               "One adjudicated correction batch changed 26 IDs; one false-positive proposal was dismissed. "
               "The corrected corpus has not received an independent diff review or editorial acceptance.\n\n"
               f"- Corrected authored file-set SHA-256: `{current_set}`.\n"
               f"- Closure: `Translations/sr/semantic-cycle-001-closure.json` "
               f"(SHA-256 `{digest(CLOSURE)}`, {len(ordered_closure)} IDs).\n"
               f"- Review rows: `Translations/sr/semantic-cycle-001-review-rows.jsonl` "
               f"(SHA-256 `{digest(ROWS)}`, {len(review_rows)} rows).\n"
               f"- Regression catalog: `Translations/sr/semantic-cycle-001-regressions.json` "
               f"(SHA-256 `{digest(REGRESSIONS)}`).\n"
               f"- Current full preserve-exact report: `{regen['fullPreserveExactReport']}` "
               f"(SHA-256 `{digest(preserve)}`, 16,538 passed).\n"
               "- Immutable first-pass, correction and static-regeneration evidence: "
               "`semantic-cycle-001-precorrection.json`, `semantic-cycle-001-corrections.json`, "
               "`semantic-cycle-001-static-regeneration.json`.\n\n"
               "## Reviewer task\n\n"
               "Independently compare every review row's Russian source and current Serbian target "
               "with its Yarn node, character rules, approved glossary and actual scene meaning. "
               "Check all regression-catalog categories. Record findings by stable ID with objective "
               "reason and full proposed target; record a clean result only if every closure row and "
               "mandatory regression passes on unchanged hashes. Do not treat structural validators "
               "or this handoff as independent semantic evidence.\n\n"
               "If corrections result, construct the next exact delta from corrected IDs, new closure "
               "dependencies and explicitly invalidated prior rows. Keep this cycle immutable. "
               "The full semantic pass is reusable unless a restart boundary in the universal workflow "
               "changes. Runtime, visual, fonts, images, textures, Git integration and release remain separate.\n")
    write_or_verify(HANDOFF, handoff, args.write)
    print(json.dumps({"result": "written" if args.write else "verified",
                      "changedIds": len(ordered_changed),
                      "closureIds": len(ordered_closure),
                      "reviewRowsSha256": digest(ROWS),
                      "regressionCatalogSha256": digest(REGRESSIONS),
                      "closureSha256": digest(CLOSURE),
                      "handoffSha256": digest(HANDOFF)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
