#!/usr/bin/env python3
"""Build or verify the Bulgarian cycle-004 dependency closure from current hashes."""

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BG = ROOT / "Translations/bg"
SELECTOR = BG / "semantic-closure-selector-cycle-004.json"
EVIDENCE = BG / "semantic-closure-cycle-004.json"
COMPONENTS = ("changed", "context", "repetitions", "glossaryReferents",
              "runtimeBindings", "mandatoryRegressions", "closure")
GUIDS = {
    "UI": "0cbd8a7a4f543344bb95659de87f67a5",
    "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6",
    "Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded_ids(ids):
    return ("\n".join(ids) + ("\n" if ids else "")).encode("utf-8")


def stable_id(collection, entry):
    if collection == "StaticTMP":
        return entry["stableId"]
    return "string:" + GUIDS[collection] + ":" + str(entry["id"])


def node_set(row):
    names = set(row.get("nodeNames") or [])
    match = re.fullmatch(r"line:(.+)_[0-9a-f]{7}", row.get("key") or "")
    if match:
        names.add(match.group(1))
    return names


def clause_matches(clause, row, target):
    checks = []
    if "sourceRegex" in clause:
        checks.append(bool(re.search(clause["sourceRegex"], row["source"])))
    if "targetRegex" in clause:
        checks.append(bool(re.search(clause["targetRegex"], target)))
    if "sourceExact" in clause:
        checks.append(row["source"] == clause["sourceExact"])
    if "keyPrefix" in clause:
        checks.append((row.get("key") or "").startswith(clause["keyPrefix"]))
    if "nodeRegex" in clause:
        checks.append(any(re.search(clause["nodeRegex"], n) for n in node_set(row)))
    assert checks, clause
    return all(checks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preview", "build", "verify"))
    args = parser.parse_args()
    selector = json.loads(SELECTOR.read_text())
    assert selector["schemaVersion"] == 3 and selector["locale"] == "bg"
    for relpath, expected in selector["pinnedInputs"].items():
        assert digest(ROOT / relpath) == expected, "Pinned input changed: " + relpath
    result = json.loads((BG / "correction-batch-004-result.json").read_text())
    plan = json.loads((BG / "correction-batch-004.json").read_text())
    prior = json.loads((BG / "correction-batch-003-result.json").read_text())
    assert result["changedIdCount"] == len(result["changedIds"]) == 3
    assert prior["changedIdCount"] == len(prior["changedIds"]) == 41
    assert result["planSha256"] == digest(BG / "correction-batch-004.json")

    targets = {}
    target_paths = {}
    for rec in result["allAuthoredFiles"]:
        path = ROOT / rec["path"]
        validation = ROOT / rec["validationPath"]
        assert digest(path) == rec["sha256"], rec["path"]
        assert digest(validation) == rec["validationSha256"], rec["validationPath"]
        batch = json.loads(path.read_text())
        for entry in batch["entries"]:
            sid = stable_id(rec["collection"], entry)
            assert sid not in targets, sid
            targets[sid] = entry["target"]
            target_paths[sid] = rec["path"]

    source_by_id = {}
    by_collection = defaultdict(list)
    for line in (ROOT / "Source/localization-inventory-v3/strings.jsonl").open():
        row = json.loads(line)
        if row["collection"] in GUIDS and row["stableId"] in targets:
            source_by_id[row["stableId"]] = row
            by_collection[row["collection"]].append(row["stableId"])
    for line in (ROOT / "Source/localization-inventory-v3/static-text.jsonl").open():
        row = json.loads(line)
        if row["stableId"] in targets:
            row["collection"] = "StaticTMP"
            source_by_id[row["stableId"]] = row
    static_batch = json.loads((BG / "static-text-draft.json").read_text())
    by_collection["StaticTMP"] = [entry["stableId"] for entry in static_batch["entries"]]
    order = [sid for collection in selector["order"] for sid in by_collection[collection]]
    assert len(order) == len(set(order)) == len(targets) == 16538
    assert set(order) == set(source_by_id)
    rank = {sid: i for i, sid in enumerate(order)}
    ordered = lambda ids: sorted(ids, key=rank.__getitem__)

    oldest = json.loads((BG / "correction-batch-001-result.json").read_text())
    assert oldest["changedIdCount"] == len(oldest["changedIds"]) == 60
    changed = set()
    for active in selector["activeCorrectionResults"]:
        active_path = ROOT / active["path"]
        assert digest(active_path) == active["sha256"]
        record = json.loads(active_path.read_text())
        assert record["changedIdCount"] == len(record["changedIds"]) == active["changedIdCount"]
        changed.update(record["changedIds"])
    assert len(changed) <= 251 and changed <= set(order)
    for row in plan["decisions"]:
        assert row["stableId"] in changed
        assert targets[row["stableId"]] == row["acceptedFullTarget"]
        assert source_by_id[row["stableId"]]["source"] == row["source"]

    changed_dialogue_nodes = set()
    for sid in changed:
        if source_by_id[sid]["collection"] == "Dialogs":
            names = node_set(source_by_id[sid])
            assert names, "Changed dialogue has no mapped Yarn node: " + sid
            changed_dialogue_nodes.update(names)
    proposal_nodes = set()
    for record in selector["proposalContextInputs"]:
        proposal_path = ROOT / record["path"]
        assert digest(proposal_path) == record["sha256"]
        proposal = json.loads(proposal_path.read_text())
        proposal_nodes.update(n for finding in proposal["findings"] for n in finding["sceneNodes"])
    context_nodes = changed_dialogue_nodes | proposal_nodes
    context = set(changed)
    for sid in by_collection["Dialogs"]:
        if node_set(source_by_id[sid]) & context_nodes:
            context.add(sid)
    for sid in by_collection["UI"]:
        key = source_by_id[sid].get("key") or ""
        if any(key.startswith(prefix) for prefix in selector["context"]["uiKeyPrefixes"]):
            context.add(sid)

    source_to_ids = defaultdict(list)
    for sid in order:
        source_to_ids[source_by_id[sid]["source"]].append(sid)
    repetitions = set()
    for sid in changed:
        repetitions.update(source_to_ids[source_by_id[sid]["source"]])

    rule_hits = {}
    glossary_referents = set()
    voice_candidates = json.loads((BG / "voice-remedial-candidates-v6.json").read_text())
    voice_ids = {row["stableId"] for row in voice_candidates["candidates"]}
    assert len(voice_ids) == voice_candidates["candidateCount"] == 741
    for rule in selector["glossaryReferentRules"]:
        if rule["name"] == "vulgarCharacterVoice":
            assert rule["any"] == [{"canonicalVoiceCandidateIds": selector["voiceRiskCandidatesPath"]}]
            hits = voice_ids
        else:
            hits = {sid for sid in order if any(clause_matches(clause, source_by_id[sid], targets[sid])
                                                for clause in rule["any"])}
        assert hits, "Empty concept selector: " + rule["name"]
        if "expectedSourceMatchCount" in rule:
            assert len(hits) == rule["expectedSourceMatchCount"], rule["name"]
        rule_hits[rule["name"]] = ordered(hits)
        glossary_referents.update(hits)

    runtime = set(changed)
    for sid in context:
        row = source_by_id[sid]
        if row["collection"] == "UI":
            runtime.add(sid)
        elif row["collection"] == "Dialogs":
            prefix = any(span["reason"] == "Yarn speaker/service prefix"
                         for span in row.get("exactSpans", []))
            if not prefix or re.search(r"\{[0-9]+\}|<[^<>]+>", row["source"]):
                runtime.add(sid)

    mandatory_groups = {
        "allUiMenusSaveLocaleHudTitles": set(by_collection["UI"]),
        "allStaticCreditsEnvironmentAndTechnicalLiterals": set(by_collection["StaticTMP"]),
        "acceptedChecksDialogue": set(by_collection["ChecksDialogs"]),
        "genderSensitiveReleaseChoices": {
            sid for sid in by_collection["Dialogs"]
            if source_by_id[sid]["source"].strip() == "Отпустить"},
        "dialogueFormatSlotsAndMarkup": {
            sid for sid in by_collection["Dialogs"]
            if re.search(r"\{[0-9]+\}|<[^<>]+>", source_by_id[sid]["source"])},
    }
    assert [x["name"] for x in selector["mandatoryRegressionGroups"]] == list(mandatory_groups)
    mandatory = set().union(*mandatory_groups.values())

    sets = {
        "changed": changed,
        "context": context,
        "repetitions": repetitions,
        "glossaryReferents": glossary_referents,
        "runtimeBindings": runtime,
        "mandatoryRegressions": mandatory,
    }
    sets["closure"] = set().union(*sets.values())
    assert changed <= sets["closure"] <= set(order)

    components = {}
    outputs = {}
    for name in COMPONENTS:
        ids = ordered(sets[name])
        payload = encoded_ids(ids)
        relpath = f"Translations/bg/semantic-cycle-004-{name}.ids"
        outputs[relpath] = payload
        components[name] = {"path": relpath, "count": len(ids),
                            "sha256": hashlib.sha256(payload).hexdigest(), "ids": ids}

    def subgroup(value):
        ids = ordered(value)
        return {"count": len(ids), "idsSha256": hashlib.sha256(encoded_ids(ids)).hexdigest(),
                "ids": ids}

    review_rows = []
    for sid in components["closure"]["ids"]:
        row = source_by_id[sid]
        review_rows.append({
            "stableId": sid,
            "collection": row["collection"],
            "sourceIndex": rank[sid],
            "key": row.get("key"),
            "sceneNodes": sorted(node_set(row)) if row["collection"] == "Dialogs" else [],
            "source": row["source"],
            "target": targets[sid],
            "authoredPath": target_paths[sid],
            "components": [name for name in COMPONENTS[:-1] if sid in sets[name]],
        })
    assert len(review_rows) == len(sets["closure"])
    evidence = {
        "schemaVersion": 1,
        "locale": "bg",
        "gameVersion": "1.3.19",
        "sourceLocale": "ru",
        "status": "cycle-004 dependency closure ready for exact independent delta; no clean or editorial acceptance",
        "acceptedUnits": 16538,
        "firstPassReviewedUnits": 16538,
        "oldestCorrectionResultPath": "Translations/bg/correction-batch-001-result.json",
        "oldestCorrectionResultSha256": digest(BG / "correction-batch-001-result.json"),
        "firstPassEvidencePath": "Translations/bg/semantic-first-pass-cycle-000.json",
        "firstPassEvidenceSha256": digest(BG / "semantic-first-pass-cycle-000.json"),
        "correctionPlanPath": "Translations/bg/correction-batch-004.json",
        "correctionPlanSha256": digest(BG / "correction-batch-004.json"),
        "correctionResultPath": "Translations/bg/correction-batch-004-result.json",
        "correctionResultSha256": digest(BG / "correction-batch-004-result.json"),
        "priorCorrectionResultPath": "Translations/bg/correction-batch-003-result.json",
        "priorCorrectionResultSha256": digest(BG / "correction-batch-003-result.json"),
        "selectorPath": "Translations/bg/semantic-closure-selector-cycle-004.json",
        "selectorSha256": digest(SELECTOR),
        "recipePath": "Translations/bg/build_semantic_closure_cycle_004.py",
        "recipeSha256": digest(Path(__file__)),
        "pinnedInputs": selector["pinnedInputs"],
        "activeCorrectionResults": selector["activeCorrectionResults"],
        "idiomDependencySpecSha256": selector["idiomDependencySpecSha256"],
        "currentAuthoredFiles": result["allAuthoredFiles"],
        "currentAuthoredFileCount": len(result["allAuthoredFiles"]),
        "newlineConvention": selector["newlineConvention"],
        "components": components,
        "glossaryReferentGroups": {name: subgroup(set(ids)) for name, ids in rule_hits.items()},
        "mandatoryRegressionGroups": {name: subgroup(ids) for name, ids in mandatory_groups.items()},
        "consumerTopology": {
            "editedYarnNodes": sorted(changed_dialogue_nodes),
            "editedYarnNodeCount": len(changed_dialogue_nodes),
            "reviewerProposalYarnNodes": sorted(proposal_nodes),
            "reviewerProposalYarnNodeCount": len(proposal_nodes),
            "dialogueTableGuid": GUIDS["Dialogs"],
            "uiTableGuid": GUIDS["UI"],
            "checksTableGuid": GUIDS["ChecksDialogs"],
            "runtimeBindingsPath": "Source/glossary-corpus-v2/runtime-bindings.json",
            "runtimeBindingsSha256": digest(ROOT / "Source/glossary-corpus-v2/runtime-bindings.json"),
            "yarnMetadataPath": "Source/glossary-corpus-v2/current-dialogs.jsonl",
            "yarnMetadataSha256": digest(ROOT / "Source/glossary-corpus-v2/current-dialogs.jsonl"),
            "note": "Compiled Yarn, binding objects and branch mechanics are hashed context, not translated units. Review consumer joins, option order, trimming and dynamic values separately before acceptance.",
        },
        "imageTextPlan": selector["imageTextPlan"],
        "derivedArtifact": "No built Bulgarian runtime artifact; integration and runtime gates remain pending.",
        "independentDiffReview": "Review03 three proposals adjudicated; cycle-004 exact delta pending separate reviewer",
        "reviewRows": review_rows,
    }
    outputs[str(EVIDENCE.relative_to(ROOT))] = (json.dumps(evidence, ensure_ascii=False,
                                                     indent=2) + "\n").encode("utf-8")

    if args.action == "preview":
        print(json.dumps({"components": {name: components[name]["count"] for name in COMPONENTS},
                          "glossaryReferentGroups": {name: len(ids) for name, ids in rule_hits.items()},
                          "mandatoryRegressionGroups": {name: len(ids) for name, ids in mandatory_groups.items()},
                          "editedYarnNodes": len(changed_dialogue_nodes),
                          "proposalYarnNodes": len(proposal_nodes)}, indent=2))
        return
    for relpath, payload in outputs.items():
        path = ROOT / relpath
        if args.action == "build":
            if path.exists():
                assert path.read_bytes() == payload, "Immutable evidence drift: " + relpath
            else:
                path.write_bytes(payload)
        else:
            assert path.read_bytes() == payload, "Evidence changed: " + relpath
    print(json.dumps({"action": args.action, "closureIds": components["closure"]["count"],
                      "evidenceSha256": digest(EVIDENCE)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
