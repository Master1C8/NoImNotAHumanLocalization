#!/usr/bin/env python3
"""Reproduce the Persian cycle-2 accepted-ID dependency closure and next review delta."""

import hashlib
import json
import pathlib
import re
import struct
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
CYCLE = pathlib.Path(__file__).resolve().parent
FA = ROOT / "Translations/fa"
REVIEW = FA / "independent-review-01"
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import check_value  # noqa: E402

GUID = {"UI": "0cbd8a7a4f543344bb95659de87f67a5",
        "Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
        "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def read(path):
    return json.loads(path.read_text())


def lines(ids):
    return "".join(sid + "\n" for sid in ids).encode()


def immutable(path, data):
    if path.exists():
        assert path.read_bytes() == data, f"immutable evidence differs: {path}"
    else:
        path.write_bytes(data)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def varint(data, position):
    value = shift = 0
    while True:
        byte = data[position]
        position += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, position
        shift += 7


def fields(data):
    position = 0
    while position < len(data):
        tag, position = varint(data, position)
        number, wire = tag >> 3, tag & 7
        if wire == 0:
            value, position = varint(data, position)
        elif wire == 2:
            length, position = varint(data, position)
            value = data[position:position + length]
            position += length
        elif wire == 5:
            value = struct.unpack("<f", data[position:position + 4])[0]
            position += 4
        elif wire == 1:
            value = struct.unpack("<d", data[position:position + 8])[0]
            position += 8
        else:
            raise ValueError((number, wire, position))
        yield number, wire, value


def compiled_names(asset_path):
    raw = bytes(read(asset_path)["compiledYarnProgram"])
    names = set()
    for number, _, value in fields(raw):
        if number != 2:
            continue
        name = next(item.decode() for key, _, item in fields(value) if key == 1)
        assert name not in names
        names.add(name)
    return names, digest(raw)


def main():
    verdict = read(REVIEW / "review-verdict.json")
    review_index = read(REVIEW / "evidence-index.json")
    assert all(sha(REVIEW / name) == pin for name, pin in review_index["files"].items())
    for name, pin in verdict["pins"].items():
        path = pathlib.Path(name)
        current = path if path.is_absolute() else ROOT / path
        prior = CYCLE / "before" / current.name
        assert sha(prior if prior.exists() else current) == pin, name
    for name, pin in verdict["currentAuthoredHashes"].items():
        current = ROOT / name
        prior = CYCLE / "before" / current.name
        assert sha(prior if prior.exists() else current) == pin, name
    manifest_path = ROOT / "Source/preserve-exactly-v4.json"
    manifest = read(manifest_path)
    rules = {row["stableId"]: row for row in manifest["tableRows"] + manifest["staticRows"]}
    order = list(rules)
    accepted = set(order)
    assert len(order) == len(accepted) == 16538
    source_paths = [ROOT / "Source/localization-inventory-v3" / name
                    for name in ("strings.jsonl", "static-text.jsonl")]
    source = {}
    for path in source_paths:
        for line in path.open():
            row = json.loads(line)
            source[row["stableId"]] = row
    assert accepted <= set(source)
    target, location = {}, {}
    authored_files = []
    for path in sorted(FA.glob("*batch-*.json")):
        if not re.fullmatch(r"(?:ui|dialogue|checks)-batch-\d{3}\.json", path.name):
            continue
        batch = read(path)
        for entry in batch["entries"]:
            sid = f"string:{GUID[batch['collection']]}:{entry['id']}"
            assert sid in accepted and sid not in target
            target[sid], location[sid] = entry["target"], str(path.relative_to(ROOT))
        authored_files.append(path)
    static_path = FA / "static-text-draft.json"
    for entry in read(static_path)["entries"]:
        sid = entry["stableId"]
        assert sid in accepted and sid not in target
        target[sid], location[sid] = entry["target"], str(static_path.relative_to(ROOT))
    authored_files.append(static_path)
    assert set(target) == accepted
    for sid in order:
        check_value(rules[sid], target[sid])
    plan1 = read(FA / "audit-cycle-001/correction-plan.json")["rows"]
    plan2_path = CYCLE / "correction-plan.json"
    plan2 = read(plan2_path)["rows"]
    delta_path = CYCLE / "file-delta-manifest.json"
    file_delta = read(delta_path)
    assert file_delta["correctionPlanSha256"] == sha(plan2_path)
    for item in file_delta["files"]:
        path = ROOT / item["path"]
        assert sha(path) == item["afterSha256"]
        assert sha(CYCLE / "before" / path.name) == item["beforeSha256"]
        assert sha(CYCLE / "after" / path.name) == item["afterSha256"]
    all_changes = plan1 + plan2
    changed = {row["stableId"] for row in all_changes}
    assert len(plan1) == 76 and len(plan2) == 5 and len(changed) == 81
    for row in plan2:
        sid = row["stableId"]
        assert source[sid]["source"] == row["source"]
        assert target[sid] == row["acceptedTarget"] and location[sid] == row["path"]
    spec_path = CYCLE / "selector-spec.json"
    spec = read(spec_path)
    source_patterns = [re.compile(value, re.IGNORECASE)
                       for value in spec["sourceConceptPatterns"]]
    fragments = tuple(spec["targetConceptFragments"])
    photo = re.compile(spec["photoContext"]["pattern"], re.IGNORECASE)
    photo_matches = {sid for sid in order if photo.search(source[sid]["source"])}
    photo_nodes = {node for sid in photo_matches for node in source[sid].get("nodeNames", [])}
    families = {node.split("_Photo")[0] for node in photo_nodes if "_Photo" in node}
    prefixes = tuple(family + "_Photo" for family in sorted(families))
    photo_same_node = {sid for sid in order if photo_nodes.intersection(source[sid].get("nodeNames", []))}
    photo_family = {sid for sid in order if any(node.startswith(prefixes)
                    for node in source[sid].get("nodeNames", []))}
    source_match_nodes = {node for sid in changed for node in source[sid].get("nodeNames", [])}
    context_prefixes = tuple(spec["contextNodeFamilyPrefixes"])
    context = {sid for sid in order if
               source_match_nodes.intersection(source[sid].get("nodeNames", [])) or
               any(node.startswith(context_prefixes) for node in source[sid].get("nodeNames", [])) or
               sid in photo_same_node or sid in photo_family}
    changed_source = {row["source"] for row in all_changes}
    changed_before = {row["before"] for row in all_changes}
    changed_after = {row["acceptedTarget"] for row in all_changes}
    repetition = {sid for sid in order if source[sid]["source"] in changed_source or
                  target[sid] in changed_before or target[sid] in changed_after}
    glossary = {sid for sid in order if
                any(pattern.search(source[sid]["source"]) for pattern in source_patterns) or
                any(fragment in target[sid] for fragment in fragments)}
    runtime = {sid for sid in order if
               re.search(r"\{[^{}]+\}|<[^<>]+>", source[sid]["source"]) or
               any("_Occupied" in node for node in source[sid].get("nodeNames", []))}
    exact = {sid for sid in order if rules[sid].get("wholeTextExact")}
    mandatory = {sid for sid in order if sid.startswith("tmp:") or
                 sid.startswith("string:" + GUID["UI"] + ":") or sid in exact or
                 re.search(r"\{[^{}]+\}|<[^<>]+>", source[sid]["source"])}
    first = read(FA / "audit-cycle-001/first-pass.snapshot.json")
    watchlist = {item["stableId"] for item in first["contextWatchlist"]}
    assert len(watchlist) == 4
    components = {"changed": changed, "context": context, "repetition": repetition,
                  "glossaryReferent": glossary, "runtimeBinding": runtime,
                  "mandatoryRegression": mandatory, "contextWatchlist": watchlist}
    closure = set().union(*components.values()) | photo_matches
    components["photoSourceConcept"] = photo_matches
    old_closure = read(FA / "audit-cycle-001/closure.json")
    previously_reviewed_rows = read(REVIEW / "per-id-review.json")["reviewRows"]
    previous = {row["stableId"] for row in previously_reviewed_rows}
    assert previous == {row["stableId"] for row in old_closure["reviewRows"]}
    assert len(previous) == 1506 and digest(lines([sid for sid in order if sid in previous])) == verdict["components"]["closure"]["sha256"]
    changed_authored_paths = {item["path"] for item in file_delta["files"]
                            if item["path"] != "Translations/fa/static-phrase-map.json"}
    invalidated = {row["stableId"] for row in previously_reviewed_rows
                   if row["path"] in changed_authored_paths}
    assert invalidated <= previous
    newly_selected = closure - previous
    retired = previous - closure
    next_delta = (set(plan2_sid["stableId"] for plan2_sid in plan2) |
                  newly_selected | invalidated)
    assert next_delta <= closure | invalidated
    assert not (closure - accepted) and not (next_delta - accepted)
    asset_path = ROOT / "Source/glossary-corpus-v1/sharedassets0.assets-2743.json"
    names, compiled_hash = compiled_names(asset_path)
    selected_nodes = {node for sid in closure for node in source[sid].get("nodeNames", [])}
    assert selected_nodes <= names, f"unknown compiled nodes: {selected_nodes - names}"
    missing_photo = {sid for sid in photo_matches if sid not in closure}
    missing_same = {sid for sid in photo_same_node if sid not in closure}
    missing_family = {sid for sid in photo_family if sid not in closure}
    assert not (missing_photo or missing_same or missing_family)
    reviewer_candidate = set((REVIEW / "candidateClosureDelta-ids.txt").read_text().splitlines())
    reviewer_omissions = set((REVIEW / "selectorOmissions-ids.txt").read_text().splitlines())
    assert reviewer_candidate <= closure and reviewer_omissions <= closure
    ordered = {name: [sid for sid in order if sid in values]
               for name, values in {**components, "closure": closure,
                                    "newlySelected": newly_selected,
                                    "invalidatedPrior": invalidated,
                                    "retiredPrior": retired,
                                    "nextReviewDelta": next_delta,
                                    "photoSameNode": photo_same_node,
                                    "photoBranchFamily": photo_family}.items()}
    hashes = {name: {"count": len(ids), "sha256": digest(lines(ids))}
              for name, ids in ordered.items()}
    for name, ids in ordered.items():
        immutable(CYCLE / f"{name}-ids.txt", lines(ids))
    review_rows = [{"stableId": sid, "path": location[sid],
                    "source": source[sid]["source"], "target": target[sid],
                    "nodeNames": source[sid].get("nodeNames", []),
                    "components": [name for name, values in components.items() if sid in values]}
                   for sid in ordered["closure"]]
    result = {"schemaVersion": 1, "locale": "fa", "cycle": 2,
              "phase": "author correction handoff; independent review pending",
              "acceptedUnits": len(order), "sourceManifestSha256": sha(manifest_path),
              "sourceInventorySha256": sha(source_paths[0]),
              "staticInventorySha256": sha(source_paths[1]),
              "glossaryLayerSha256": sha(ROOT / "Documentation/glossary-translations/fa/layer.json"),
              "compiledYarnAssetSha256": sha(asset_path),
              "compiledYarnProgramSha256": compiled_hash,
              "firstPassSnapshotSha256": sha(FA / "audit-cycle-001/first-pass.snapshot.json"),
              "previousIndependentPerIdReviewSha256": sha(REVIEW / "per-id-review.json"),
              "correctionPlanSha256": sha(plan2_path),
              "fileDeltaManifestSha256": sha(delta_path),
              "selectorSpecSha256": sha(spec_path),
              "remedialReadSha256": sha(CYCLE / "remedial-read.json"),
              "componentHashes": hashes,
              "missingAcceptedIds": [], "extraUnacceptedIds": [],
              "photoSelectorCompleteness": {
                  "directMatches": len(photo_matches), "seedNodes": len(photo_nodes),
                  "photoFamilies": len(families), "sameNodeUnits": len(photo_same_node),
                  "branchFamilyUnits": len(photo_family), "compiledSelectedNodes": len(selected_nodes),
                  "missingPhotoDirect": [], "missingPhotoSameNode": [],
                  "missingPhotoBranchFamily": [],
                  "reviewerCandidateSubset": len(reviewer_candidate),
                  "reviewerOmissionSubset": len(reviewer_omissions)},
              "reviewRows": review_rows,
              "unresolvedQuestions": [
                  "tmp:level1:3842:m_text: standalone Psychics source role/binding remains unproven from serialized data.",
                  "string:444ff14f1967f5a4c8eb9e4cf4c913f1:110504456997642245: MushroomEater drink/ordeal wordplay remains ambiguous.",
                  "RTL shaping and runtime layout were not tested under no-game instruction."],
    }
    immutable(CYCLE / "closure.json", json_bytes(result))
    delta_rows = [{"stableId": sid, "path": location[sid],
                   "source": source[sid]["source"], "target": target[sid],
                   "reason": [name for name, values in
                              (("corrected", {row["stableId"] for row in plan2}),
                               ("newlySelected", newly_selected),
                               ("invalidatedPriorFileHash", invalidated)) if sid in values]}
                  for sid in ordered["nextReviewDelta"]]
    immutable(CYCLE / "next-review-delta.json", json_bytes({
        "schemaVersion": 1, "locale": "fa", "cycle": 2,
        "formula": "corrected union (current closure minus prior independently reviewed closure) union explicit invalidated prior IDs",
        "previousIndependentReviewSha256": sha(REVIEW / "per-id-review.json"),
        "currentClosureSha256": sha(CYCLE / "closure.json"),
        "componentHashes": {key: hashes[key] for key in
                            ("changed", "newlySelected", "invalidatedPrior",
                             "retiredPrior", "nextReviewDelta")},
        "invalidatedPolicy": "all prior reviewed IDs in an authored file changed in cycle 2; conservative file-hash invalidation",
        "missingAcceptedIds": [], "extraUnacceptedIds": [],
        "rows": delta_rows,
    }))
    immutable(CYCLE / "deterministic-gate.json", json_bytes({
        "schemaVersion": 1, "locale": "fa", "cycle": 2,
        "acceptedUnits": len(order), "checkedTargets": len(target),
        "structuralAndPreserveExact": "passed",
        "sourceManifestSha256": sha(manifest_path),
        "authoredFileHashes": {str(path.relative_to(ROOT)): sha(path)
                              for path in authored_files},
        "staticPhraseMapSha256": sha(FA / "static-phrase-map.json"),
        "semanticReview": "author remedial read; next independent review pending",
        "runtime": "not-run",
    }))
    print(json.dumps({"acceptedUnits": len(order), "closure": len(closure),
                      "newlySelected": len(newly_selected),
                      "invalidatedPrior": len(invalidated),
                      "retiredPrior": len(retired), "nextReviewDelta": len(next_delta),
                      "compiledNodes": len(selected_nodes), "componentHashes": hashes},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
