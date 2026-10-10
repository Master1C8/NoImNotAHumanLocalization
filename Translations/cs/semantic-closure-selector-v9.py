#!/usr/bin/env python3
"""Rebuild Czech cycle-008 review03-response closure from pinned IDs, nodes and catalog."""

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def file_hash(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def text_hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def ids_hash(values):
    return text_hash("".join(value + "\n" for value in values))


def read_json(path):
    return json.loads((ROOT / path).read_text())


def varint(data, offset):
    result = shift = 0
    while True:
        byte = data[offset]
        offset += 1
        result |= (byte & 127) << shift
        if byte < 128:
            return result, offset
        shift += 7


def fields(data):
    offset = 0
    while offset < len(data):
        tag, offset = varint(data, offset)
        number, wire = tag >> 3, tag & 7
        if wire == 2:
            length, offset = varint(data, offset)
            value = data[offset:offset + length]
            offset += length
        elif wire == 0:
            value, offset = varint(data, offset)
        elif wire == 5:
            value = data[offset:offset + 4]
            offset += 4
        elif wire == 1:
            value = data[offset:offset + 8]
            offset += 8
        else:
            raise ValueError(f"Unsupported protobuf wire type {wire}")
        yield number, wire, value


def compiled_nodes(program):
    result = {}
    for number, wire, entry in fields(program):
        if (number, wire) != (2, 2):
            continue
        entry_fields = list(fields(entry))
        name = entry_fields[0][2].decode("utf-8")
        node = entry_fields[1][2]
        instructions = []
        for field_number, field_wire, value in fields(node):
            if (field_number, field_wire) != (2, 2):
                continue
            instruction = list(fields(value))
            opcode = next((v for n, _, v in instruction if n == 1), None)
            operands = []
            for n, w, operand in instruction:
                if (n, w) != (2, 2):
                    continue
                nested = list(fields(operand))
                string = next((v.decode("utf-8") for k, t, v in nested
                               if (k, t) == (1, 2)), None)
                if string is not None:
                    operands.append(string)
            instructions.append({"opcode": opcode, "operands": operands})
        result[name] = instructions
    return result


def main():
    application_path = "Translations/cs/semantic-correction-cycle-002-application.json"
    before_path = "Translations/cs/semantic-correction-cycle-002-before.json"
    findings_path = "Translations/cs/semantic-findings-004.json"
    application = read_json(application_path)
    before = read_json(before_path)
    findings = read_json(findings_path)
    correction_path = "Translations/cs/semantic-correction-cycle-003-before.json"
    correction = read_json(correction_path)
    extension_path = "Translations/cs/semantic-correction-cycle-004-before.json"
    extension = read_json(extension_path)
    final_path = "Translations/cs/semantic-correction-cycle-005-before.json"
    final = read_json(final_path)
    sweep_path = "Translations/cs/semantic-correction-cycle-006-before.json"
    sweep = read_json(sweep_path)
    review02_before_path = "Translations/cs/semantic-correction-cycle-007-before.json"
    review02_application_path = "Translations/cs/semantic-correction-cycle-007-application.json"
    review02_before = read_json(review02_before_path)
    review02_application = read_json(review02_application_path)
    assert review02_application["beforeSha256"] == file_hash(review02_before_path)
    assert review02_application["changedIds"] == [r["stableId"] for r in review02_before["rows"]]
    assert len(review02_before["rows"]) == 15
    review03_before_path = "Translations/cs/semantic-correction-cycle-008-before.json"
    review03_application_path = "Translations/cs/semantic-correction-cycle-008-application.json"
    review03_before = read_json(review03_before_path)
    review03_application = read_json(review03_application_path)
    assert review03_application["beforeSha256"] == file_hash(review03_before_path)
    assert review03_application["changedIds"] == [review03_before["correction"]["stableId"]]
    catalog_path = "Translations/cs/semantic-regression-catalog-v2.json"
    catalog = read_json(catalog_path)
    assert application["beforeEvidenceSha256"] == file_hash(before_path)
    assert application["adjudicationSha256"] == file_hash(application["adjudication"])
    assert application["changedIds"] == before["changedIds"]
    source_path = "Source/localization-inventory-v3/strings.jsonl"
    static_path = "Source/localization-inventory-v3/static-text.jsonl"
    source = [json.loads(line) for line in (ROOT / source_path).open()]
    ui = [r for r in source if r["collection"] == "UI"]
    checks = [r for r in source if r["collection"] == "ChecksDialogs"
              and r["stableId"].endswith(":21377524158749")]
    dialogs = [r for r in source if r["collection"] == "Dialogs"]
    static = read_json("Translations/cs/static-text-draft.json")["entries"]
    static_source = {r["stableId"]: r for r in
                     (json.loads(line) for line in (ROOT / static_path).open())}
    accepted = ui + checks + dialogs + [static_source[e["stableId"]] for e in static]
    ordered_ids = [r["stableId"] for r in accepted]
    assert len(ordered_ids) == len(set(ordered_ids)) == 16538
    index = {sid: i for i, sid in enumerate(ordered_ids)}
    by_id = {r["stableId"]: r for r in accepted}
    key_to_id = {r["key"]: r["stableId"] for r in dialogs}
    assert len(key_to_id) == len(dialogs)

    current = {}
    for path in sorted(HERE.iterdir()):
        if not re.fullmatch(r"(dialogue|ui|checks)-batch-\d{3}\.json", path.name):
            continue
        batch = json.loads(path.read_text())
        guid = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
                "UI": "0cbd8a7a4f543344bb95659de87f67a5",
                "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}[batch["collection"]]
        for entry in batch["entries"]:
            sid = f"string:{guid}:{entry['id']}"
            assert sid not in current
            current[sid] = entry["target"]
    for entry in static:
        assert entry["stableId"] not in current
        current[entry["stableId"]] = entry["target"]
    assert set(current) == set(ordered_ids)
    files = sorted(str(path.relative_to(ROOT)) for path in HERE.iterdir()
                   if re.fullmatch(r"(dialogue|ui|checks)-batch-\d{3}\.json|static-text-draft\.json", path.name))
    file_set_hash = text_hash("".join(path + "\t" + file_hash(path) + "\n" for path in files))
    assert len(correction["rows"]) == correction["changedCount"] == 7
    assert len(extension["rows"]) == extension["changedCount"] == 7
    assert len(final["rows"]) == final["changedCount"] == 1
    assert len(sweep["rows"]) == sweep["changedCount"] == 4
    for entry in correction["rows"] + extension["rows"] + final["rows"] + sweep["rows"] + review02_before["rows"] + [review03_before["correction"]]:
        assert text_hash(entry["before"]) == entry["beforeSha256"]
        assert text_hash(entry["after"]) == entry["afterSha256"]
        assert current[entry["stableId"]] == entry["after"]

    bindings_path = "Source/glossary-corpus-v2/runtime-bindings.json"
    bindings = read_json(bindings_path)
    program = bytes(bindings["sharedassets0.assets:2743"]["compiledYarnProgram"])
    assert hashlib.sha256(program).hexdigest() == read_json(
        "Source/glossary-corpus-v2/current-dialogs-scope.json")["compiledProgramSha256"]
    nodes = compiled_nodes(program)
    node_lines = {}
    key_nodes = defaultdict(list)
    for name, instructions in nodes.items():
        keys = [ins["operands"][0] for ins in instructions
                if ins["opcode"] in (2, 4) and ins["operands"]
                and ins["operands"][0].startswith("line:")]
        node_lines[name] = keys
        for key in keys:
            key_nodes[key].append(name)

    corrected = {entry["stableId"] for entry in correction["rows"] + extension["rows"] + final["rows"] + sweep["rows"]}
    review02_corrected = {entry["stableId"] for entry in review02_before["rows"]}
    review03_corrected = {review03_before["correction"]["stableId"]}
    changed = set(application["changedIds"]) | corrected | review02_corrected | review03_corrected
    assert len(corrected) == 19 and len(application["changedIds"]) == 76
    assert changed <= set(index)
    components = {name: set() for name in
                  ("changed", "context", "repetitions", "glossaryReferents",
                   "runtimeBindings", "mandatoryRegressions")}
    components["changed"] = changed
    topology_gaps = []
    for sid in changed:
        row = by_id[sid]
        key = row["key"]
        owning_nodes = key_nodes.get(key, [])
        if not owning_nodes and row["nodeNames"]:
            topology_gaps.append({"stableId": sid, "nodeNames": row["nodeNames"],
                                  "reason": "No compiled Yarn node carries this accepted table key"})
        for name in owning_nodes:
            keys = node_lines[name]
            for position, candidate in enumerate(keys):
                if candidate != key:
                    continue
                for nearby in keys[max(0, position - 2):position + 3]:
                    if nearby in key_to_id:
                        components["context"].add(key_to_id[nearby])
    for group, entry in findings["dependencyCandidates"].items():
        component = {"invasionOfHosts": "glossaryReferents",
                     "greatmotherResearch": "glossaryReferents",
                     "exConFormerWife": "repetitions",
                     "coupleChoicePolarity": "repetitions",
                     "buddyJoke": "repetitions"}.get(group, "context")
        for source_index in entry["sourceIndices"]:
            components[component].add(dialogs[source_index]["stableId"])
    for row in findings["dependentAffectedRows"]:
        components["context"].add(row["stableId"])

    repeated = defaultdict(list)
    for row in dialogs:
        repeated[row["source"]].append(row["stableId"])
    for sid in changed:
        for sibling in repeated[by_id[sid]["source"]]:
            components["repetitions"].add(sibling)

    concept_rules = {
        "visitorInvasion": lambda ru, cs: bool(re.search(r"нашеств\w*.*Гост", ru, re.I))
                                      or "příliv Hostů" in cs or "invazí Hostů" in cs,
        "skinDefect": lambda ru, cs: bool(re.search(r"дефектн\w* кож", ru, re.I))
                                  or "poškozená kůže" in cs or "kožní vada" in cs,
        "researchOnPeople": lambda ru, cs: "исследован" in ru.casefold()
                                            or "odvezli k výzkumu" in cs,
        "sacrifices": lambda ru, cs: "жертвопринош" in ru.casefold()
                                     or "Přinášení obětí" in cs,
        "kcsInstitution": lambda ru, cs: "КЧС" in ru or "KČS" in cs
            or bool(re.search(r"(?<!\w)комитет(?:а|у|ом|е|ы|ов|ам|ами|ах)?(?!\w)", ru, re.I))
            or bool(re.search(r"(?<!\w)výbor(?:u|em|y|ů|ům|ech|e|a)?(?!\w)", cs, re.I)),
        "earwaxBlockage": lambda ru, cs: bool(re.search(
            r"ушн\w*\s+(?:пробк\w*|сер\w*)|серн\w*\s+пробк\w*|"
            r"сер\w*\s+в\s+(?:уш\w*|ух\w*)", ru, re.I))
            or "mazové zátky" in cs,
    }
    committee_spec_path = "Translations/cs/semantic-committee-selector-v8-spec.json"
    committee_spec = read_json(committee_spec_path)
    for example in committee_spec["selectorExamples"]:
        sid = example["stableId"]
        assert sid in by_id and by_id[sid]["source"] == example["source"]
        assert current[sid] == example["target"]
        assert concept_rules["kcsInstitution"](example["source"], example["target"]) is example["expected"]
    for example in committee_spec["grammarRegressionExamples"]:
        target = current[example["stableId"]]
        assert example["mustContain"] in target
        assert not example["mustNotContain"] or example["mustNotContain"] not in target
    distance_spec_path = "Translations/cs/semantic-correction-cycle-008-regression-spec.json"
    distance_spec = read_json(distance_spec_path)
    distance_sid = distance_spec["stableId"]
    assert distance_sid in by_id and distance_spec["sourcePhrase"] in by_id[distance_sid]["source"]
    assert distance_spec["targetRequired"] in current[distance_sid]
    assert distance_spec["targetForbidden"] not in current[distance_sid]
    concept_hits = {}
    for name, selector in concept_rules.items():
        hits = {sid for sid in ordered_ids if selector(by_id[sid]["source"], current[sid])}
        concept_hits[name] = hits
        components["glossaryReferents"].update(hits)
    assert len(concept_hits["kcsInstitution"]) == 521, len(concept_hits["kcsInstitution"])
    full_name = {row["stableId"] for row in read_json("Translations/cs/independent-review-02/committee-full-name-adjudication.json")["conceptRows"]}
    assert len(full_name) == 26 and full_name <= concept_hits["kcsInstitution"]
    assert len(full_name - set(read_json("Translations/cs/semantic-correction-cycle-006-closure.json")["closureIds"])) == 16
    assert not (set(read_json("Translations/cs/independent-review-02/committee-full-name-adjudication.json")["falseCandidateIds"]) & concept_hits["kcsInstitution"])
    # A bare Russian сера/серы in the eighth-day TV_Ear passage and its
    # following pronoun is determined by compiled scene context, not a global
    # chemical-sulfur search. Ear-check callbacks are selected by their node.
    earwax_context = {row["stableId"] for row in dialogs if
                      any(name.startswith("tv_8_necessary") for name in row["nodeNames"])
                      or (any("_Ears" in name for name in row["nodeNames"])
                          and re.search(r"сер\w*|пробк\w*|ушн\w*", row["source"], re.I))}
    concept_hits["earwaxCompiledContext"] = earwax_context
    components["glossaryReferents"].update(earwax_context)
    for sid in earwax_context:
        for name in by_id[sid]["nodeNames"]:
            if "_Ears" not in name:
                continue
            for key in node_lines.get(name, []):
                if key in key_to_id:
                    components["context"].add(key_to_id[key])
    adjudication = read_json(application["adjudication"])
    for entry in adjudication["candidateRows"]:
        for sid in ordered_ids:
            if current[sid] == entry["before"] or current[sid] == entry["acceptedFullReplacement"]:
                components["glossaryReferents"].add(sid)

    binding_nodes = adjudication["runtimeBindingNodes"]
    nontranslatable = []
    for name in binding_nodes:
        assert name in nodes
        instructions = nodes[name]
        assert any(ins["opcode"] == 12 and ins["operands"] == ["GetCharacterOnPlace"]
                   for ins in instructions), name
        line_keys = []
        for linked in [name, name + "_YesLet", name + "_NoLet"]:
            for key in node_lines.get(linked, []):
                line_keys.append(key)
                if key in key_to_id:
                    components["runtimeBindings"].add(key_to_id[key])
                else:
                    nontranslatable.append({"node": linked, "lineKey": key,
                                             "reason": "Compiled line key is outside selected Russian table"})
        nontranslatable.append({"node": name, "function": "GetCharacterOnPlace",
                                 "lineKeys": line_keys,
                                 "reason": "Runtime name substitution and option branching"})

    glossary = read_json("Documentation/glossary-translations/cs/layer.json")
    assert file_hash("Documentation/glossary-translations/cs/layer.json") == correction["approvedGlossarySha256"]
    catalog_hits = {}
    for collection, rows, groups in (("UI", ui, catalog["uiSurfaces"]),
                                      ("Dialogs", dialogs, catalog["dialogueSurfaces"])):
        for group in groups:
            for glossary_id in group.get("glossaryIds", []):
                assert glossary_id in glossary, (group["name"], glossary_id)
            exact = set(group.get("exactKeys", []))
            present = {row["key"] for row in rows}
            assert exact <= present, (group["name"], sorted(exact - present))
            prefixes = tuple(group.get("keyPrefixes", []))
            hits = {row["stableId"] for row in rows if row["key"] in exact or
                    (row["key"] and row["key"].startswith(prefixes))}
            for position in group.get("sourceIndexExamples", []):
                assert collection == "Dialogs" and 0 <= position < len(dialogs)
                hits.add(dialogs[position]["stableId"])
            assert hits, group["name"]
            assert group["name"] not in catalog_hits
            catalog_hits[group["name"]] = hits
            components["mandatoryRegressions"].update(hits)
    components["mandatoryRegressions"].add(checks[0]["stableId"])
    assert checks[0]["stableId"].endswith(":" + catalog["selectedChecksDialog"])
    components["mandatoryRegressions"].update(catalog["fixedAcceptedIds"])

    # Bounded serialized CharacterSO place data supplies actual admissible
    # occupants for the corrected GetCharacterOnPlace dynamic name joins.
    label_path = catalog["dynamicResidentTopology"]
    label_data = read_json(label_path)
    ui_keys = {row["key"]: row for row in ui if row["key"]}
    labels = set()
    for item in label_data["rows"]:
        key = "characterName_" + item["occupant"]
        assert key in ui_keys, key
        row = ui_keys[key]
        assert row["stableId"] == item["stableId"] and row["source"] == item["source"]
        labels.add(row["stableId"])
    assert len(labels) == 14
    components["runtimeBindings"].update(labels)

    rendered_components = {}
    for name, values in components.items():
        assert values <= set(index), name
        ids = sorted(values, key=index.__getitem__)
        rendered_components[name] = {"ids": ids, "count": len(ids),
                                     "sha256": ids_hash(ids)}
    closure_set = set().union(*components.values())
    closure = sorted(closure_set, key=index.__getitem__)
    assert changed <= closure_set
    assert len(closure) == len(closure_set)
    assert closure == sorted(set().union(*(set(x["ids"]) for x in
                                            rendered_components.values())), key=index.__getitem__)
    rows = [{"stableId": sid, "collection": by_id[sid]["collection"] if sid.startswith("string:") else "StaticTMP",
             "sourceSha256": text_hash(by_id[sid]["source"]),
             "targetSha256": text_hash(current[sid]),
             "source": by_id[sid]["source"], "target": current[sid]}
            for sid in closure]
    previous_path = "Translations/cs/semantic-correction-cycle-007-closure.json"
    previous = read_json(previous_path)
    previous_ids = set(previous["closureIds"])
    new_ids = set(closure) - previous_ids
    retired_ids = previous_ids - set(closure)
    # Review03 cleared the bounded committee domain on exact pins. The new
    # factual correction is local and does not invalidate unrelated prior reads.
    invalidated_prior = set()
    # Exact next reviewer set: the one review03 correction, new dependencies,
    # and any prior rows explicitly invalidated beyond correction itself.
    next_delta = sorted(review03_corrected | new_ids | invalidated_prior, key=index.__getitem__)
    output = {"schemaVersion": 5,
              "kind": "cs-semantic-correction-cycle-008-dependency-closure",
              "locale": "cs", "gameVersion": "1.3.19", "sourceLocale": "ru",
              "status": "author closure; independent reviewer and editorial acceptance pending",
              "selectorPath": "Translations/cs/semantic-closure-selector-v9.py",
              "selectorSha256": file_hash("Translations/cs/semantic-closure-selector-v9.py"),
              "review03BeforePath": review03_before_path, "review03BeforeSha256": file_hash(review03_before_path),
              "review03ApplicationPath": review03_application_path, "review03ApplicationSha256": file_hash(review03_application_path),
              "review03VerdictSha256": file_hash("Translations/cs/independent-review-03/final-verdict.json"),
              "review03ManifestSha256": file_hash("Translations/cs/independent-review-03/evidence-manifest.json"),
              "cycleSpecificRegressionSpecPath": distance_spec_path, "cycleSpecificRegressionSpecSha256": file_hash(distance_spec_path),
              "historicalBatch020ReconciliationSha256": file_hash("Translations/cs/semantic-correction-cycle-008-batch020-reconciliation.json"),
              "review02BeforePath": review02_before_path, "review02BeforeSha256": file_hash(review02_before_path),
              "review02ApplicationPath": review02_application_path, "review02ApplicationSha256": file_hash(review02_application_path),
              "review02VerdictSha256": file_hash("Translations/cs/independent-review-02/final-verdict.json"),
              "review02FindingsSha256": file_hash("Translations/cs/independent-review-02/findings.json"),
              "committeeSelectorSpecPath": committee_spec_path,
              "committeeSelectorSpecSha256": file_hash(committee_spec_path),
              "priorApplicationPath": application_path, "priorApplicationSha256": file_hash(application_path),
              "correctionBeforePath": correction_path, "correctionBeforeSha256": file_hash(correction_path),
              "extensionBeforePath": extension_path, "extensionBeforeSha256": file_hash(extension_path),
              "finalBeforePath": final_path, "finalBeforeSha256": file_hash(final_path),
              "sweepBeforePath": sweep_path, "sweepBeforeSha256": file_hash(sweep_path),
              "interimAuthorClosurePath": "Translations/cs/semantic-correction-cycle-003-closure.json",
              "interimAuthorClosureSha256": file_hash("Translations/cs/semantic-correction-cycle-003-closure.json"),
              "supersededCurrentCycleClosurePath": "Translations/cs/semantic-correction-cycle-004-closure.json",
              "supersededCurrentCycleClosureSha256": file_hash("Translations/cs/semantic-correction-cycle-004-closure.json"),
              "supersededRepairedCycleClosurePath": "Translations/cs/semantic-correction-cycle-004-closure-repaired.json",
              "supersededRepairedCycleClosureSha256": file_hash("Translations/cs/semantic-correction-cycle-004-closure-repaired.json"),
              "supersededCycle005ClosurePath": "Translations/cs/semantic-correction-cycle-005-closure.json",
              "supersededCycle005ClosureSha256": file_hash("Translations/cs/semantic-correction-cycle-005-closure.json"),
              "supersededCycle005FinalClosurePath": "Translations/cs/semantic-correction-cycle-005-closure-final.json",
              "supersededCycle005FinalClosureSha256": file_hash("Translations/cs/semantic-correction-cycle-005-closure-final.json"),
              "supersessionReason": "One bounded factual distance correction after independent review03; committee and catalog selectors unchanged.",
              "priorClosurePath": previous_path, "priorClosureSha256": file_hash(previous_path),
              "regressionCatalogPath": catalog_path, "regressionCatalogSha256": file_hash(catalog_path),
              "dynamicResidentTopologyPath": label_path,
              "dynamicResidentTopologySha256": file_hash(label_path),
              "sourceInventorySha256": file_hash(source_path),
              "staticInventorySha256": file_hash(static_path),
              "sourceAcceptanceSha256": application["sourceAcceptanceSha256"],
              "glossaryFingerprint": application["glossaryFingerprint"],
              "preserveExactManifestSha256": application["preserveExactManifestSha256"],
              "compiledYarnProgramSha256": hashlib.sha256(program).hexdigest(),
              "runtimeBindingsSha256": file_hash(bindings_path),
              "authoredFileSetSha256": file_set_hash,
              "newlineConvention": "LF; each hash is SHA-256 of one stable ID plus LF per row",
              "components": rendered_components,
              "catalogHits": {name: {"count": len(values),
                                      "sha256": ids_hash(sorted(values, key=index.__getitem__))}
                              for name, values in catalog_hits.items()},
              "conceptRuleHits": {name: {"count": len(values),
                                         "sha256": ids_hash(sorted(values, key=index.__getitem__))}
                                  for name, values in concept_hits.items()},
              "topologyGaps": topology_gaps,
              "nontranslatableRuntimeFragments": nontranslatable,
              "nontranslatableRuntimeFragmentsSha256": text_hash(
                  json.dumps(nontranslatable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))),
              "closureIds": closure, "closureCount": len(closure),
              "closureIdsSha256": ids_hash(closure),
              "correctedIds": sorted(review03_corrected, key=index.__getitem__),
              "correctedIdsSha256": ids_hash(sorted(review03_corrected, key=index.__getitem__)),
              "newDependencyIds": sorted(new_ids, key=index.__getitem__),
              "newDependencyIdsSha256": ids_hash(sorted(new_ids, key=index.__getitem__)),
              "retiredDependencyIds": sorted(retired_ids, key=index.__getitem__),
              "retiredDependencyIdsSha256": ids_hash(sorted(retired_ids, key=index.__getitem__)),
              "retiredReason": "Previously selected local neighbors or source-excerpt candidates outside the repaired current dependency scope; unchanged reviewed values retain first-pass evidence.",
              "explicitInvalidatedPriorIds": sorted(invalidated_prior, key=index.__getitem__),
              "explicitInvalidationReason": "None: review03 freshly read the complete 561-ID delta and retained 570 unchanged exact-pinned prior decisions; the local distance omission changes no shared source, glossary, bindings, selector or unrelated target.",
              "nextDeltaIds": next_delta, "nextDeltaCount": len(next_delta),
              "nextDeltaIdsSha256": ids_hash(next_delta),
              "missingAcceptedIds": [], "extraIds": [],
              "reviewRows": rows, "reviewRowsCount": len(rows),
              "reviewRowsSha256": text_hash("".join(json.dumps(row, ensure_ascii=False,
                                                         sort_keys=True, separators=(",", ":")) + "\n"
                                               for row in rows)),
              "independentDiffAudit": "pending distinct reviewer"}
    path = HERE / "semantic-correction-cycle-008-closure.json"
    data = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        assert path.read_text() == data, "Existing immutable closure differs"
    else:
        path.write_text(data)
    print(json.dumps({"closure": len(closure), "changed": len(changed),
                      "corrected": len(review03_corrected), "new": len(new_ids),
                      "retired": len(retired_ids), "nextDelta": len(next_delta),
                      "components": {k: v["count"] for k, v in rendered_components.items()},
                      "topologyGaps": len(topology_gaps),
                      "sha256": file_hash("Translations/cs/semantic-correction-cycle-008-closure.json")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
