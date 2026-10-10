#!/usr/bin/env python3
"""Prepare, apply, and reproduce the bounded Persian aunt correction cycle."""

import argparse
import hashlib
import json
import pathlib
import re
import runpy
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
CYCLE = pathlib.Path(__file__).resolve().parent
FA = ROOT / "Translations/fa"
REVIEW = FA / "independent-review-02"
PRIOR = FA / "audit-cycle-002"
GUID = {"UI": "0cbd8a7a4f543344bb95659de87f67a5",
        "Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
        "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}
SID = "string:444ff14f1967f5a4c8eb9e4cf4c913f1:110504452790755329"
AUTHORED = FA / "dialogue-batch-348.json"
SIDECAR = FA / "dialogue-batch-348.validation.json"
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import check_value  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def write_once(path, payload):
    if path.exists():
        assert path.read_bytes() == payload, f"immutable evidence differs: {path}"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


def id_bytes(ids):
    return "".join(sid + "\n" for sid in ids).encode()


def compiled_names():
    decoder = runpy.run_path(str(PRIOR / "build-closure.py"))["compiled_names"]
    return decoder(ROOT / "Source/glossary-corpus-v1/sharedassets0.assets-2743.json")


def pin_reviewer(before=False):
    verdict = read(REVIEW / "review-verdict.json")
    index = read(REVIEW / "evidence-index.json")
    assert len(index["files"]) == 14
    assert all(sha(REVIEW / name) == pin for name, pin in index["files"].items())
    for name, pin in verdict["pins"].items():
        path = ROOT / name
        if before and path == AUTHORED:
            path = CYCLE / "before" / AUTHORED.name
        assert sha(path) == pin, name
    return verdict


def corpus():
    manifest = read(ROOT / "Source/preserve-exactly-v4.json")
    rules = {row["stableId"]: row for row in manifest["tableRows"] + manifest["staticRows"]}
    order = list(rules)
    assert len(order) == len(rules) == 16538
    source = {}
    for name in ("strings.jsonl", "static-text.jsonl"):
        for line in (ROOT / "Source/localization-inventory-v3" / name).open():
            row = json.loads(line)
            assert row["stableId"] not in source
            source[row["stableId"]] = row
    target, location = {}, {}
    authored_files = []
    for path in sorted(FA.glob("*batch-*.json")):
        if not re.fullmatch(r"(?:ui|dialogue|checks)-batch-\d{3}\.json", path.name):
            continue
        batch = read(path)
        assert batch["glossaryFingerprint"] == sha(ROOT / "Documentation/glossary-translations/fa/layer.json")
        for entry in batch["entries"]:
            sid = f"string:{GUID[batch['collection']]}:{entry['id']}"
            assert sid in rules and sid not in target
            target[sid], location[sid] = entry["target"], str(path.relative_to(ROOT))
        authored_files.append(path)
    static_path = FA / "static-text-draft.json"
    for entry in read(static_path)["entries"]:
        sid = entry["stableId"]
        assert sid in rules and sid not in target
        target[sid], location[sid] = entry["target"], str(static_path.relative_to(ROOT))
    authored_files.append(static_path)
    assert set(target) == set(rules)
    for sid in order:
        check_value(rules[sid], target[sid])
    return order, source, target, location, authored_files, rules


def prepare():
    verdict = pin_reviewer()
    order, source, target, location, files, rules = corpus()
    finding = read(REVIEW / "findings.json")["rows"]
    assert len(finding) == 1 and finding[0]["findingId"] == "R02-F01"
    item = finding[0]
    assert item["stableId"] == SID and item["path"] == str(AUTHORED.relative_to(ROOT))
    assert source[SID]["source"] == item["source"] and target[SID] == item["currentTarget"]
    assert location[SID] == item["path"]
    assert item["proposedTarget"] == "Scammer: یک بار خانهٔ عمه یا خاله‌ام را توی ورق‌بازی باختم، آن‌قدر هم به من سخت نگرفتند. حالا برای یک عکس..."
    assert target[SID].replace("خاله‌ام", "عمه یا خاله‌ام") == item["proposedTarget"]
    check_value(rules[SID], item["proposedTarget"])
    aunt_source = [sid for sid in order if re.search(r"\bт[её]т\w*\b", source[sid]["source"], re.I)]
    aunt_target = [sid for sid in order if any(term in target[sid] for term in
                   ("خاله", "عمه", "خواهرِ پدر", "خواهرِ مادر", "خواهر پدر", "خواهر مادر"))]
    exact_source = [sid for sid in order if source[sid]["source"] == source[SID]["source"]]
    exact_target = [sid for sid in order if target[sid] == target[SID]]
    assert aunt_source == aunt_target == exact_source == exact_target == [SID]
    family = {"Scammer_Photo", "Scammer_Photo_Gun", "Scammer_Photo_DontShoot", "Scammer_Death"}
    family_rows = [sid for sid in order if family.intersection(source[sid].get("nodeNames", []))]
    assert SID in family_rows
    compiled = read(REVIEW / "compiled-context.json")
    names, program_hash = compiled_names()
    assert family <= names and family - set(compiled["nodes"]) == {"Scammer_Death"}
    gun = compiled["nodes"]["Scammer_Photo_Gun"]["instructions"]
    assert [v["1"] for x in gun[:2] for v in x["operands"] if "1" in v] == [
        "line:Scammer_Photo_Gun_0fcc1e6", "line:Scammer_Photo_Gun_0602b39"]
    assert {v["1"] for x in gun for v in x["operands"] if v.get("1") in
            ("Scammer_Death", "Scammer_Photo_DontShoot")} == {
        "Scammer_Death", "Scammer_Photo_DontShoot"}
    recipe_paths = [FA / "common-options-001.authored.json", FA / "static-phrase-map.json",
                    FA / "credits-role-map.json", FA / "static-text-draft.json"]
    for path in recipe_paths:
        assert item["source"] not in path.read_text() and item["currentTarget"] not in path.read_text()
    spec = {
        "schemaVersion": 1, "locale": "fa", "cycle": 3,
        "sourceAuntPattern": r"\bт[её]т\w*\b",
        "targetAuntFragments": ["خاله", "عمه", "خواهرِ پدر", "خواهرِ مادر", "خواهر پدر", "خواهر مادر"],
        "exactRepetition": "full Russian source or full prior/current Persian target equality",
        "contextNodeNames": sorted(family),
        "contextRule": "accepted IDs in the compiled Scammer photo encounter, its gun choice, continuation and death branch",
        "mandatoryRegression": "reuse prior cycle's accepted UI, static, exact-text, placeholder and markup ID catalog",
        "runtimeBinding": "reuse prior cycle's accepted placeholder and occupied-node catalog; include current Scammer branch context",
        "contextWatchlist": "reuse prior four first-pass IDs",
        "order": "Source/preserve-exactly-v4.json tableRows followed by staticRows",
        "hashFormat": "UTF-8 stable IDs, one per line, final LF",
        "regressionExamples": [
            {"source": "своей тётки", "expected": "aunt, side unspecified", "selectedId": SID},
            {"source": "лететь", "expected": "not selected as kinship", "reason": "word boundary"},
            {"targetBefore": "خاله‌ام", "targetAfter": "عمه یا خاله‌ام", "expected": "both wording variants select the referent"},
            {"node": "Scammer_Photo_Gun", "expected": "include two lines, both choices, continuation and death branch"},
        ],
    }
    write_once(CYCLE / "selector-spec.json", encoded(spec))
    enumeration = {"schemaVersion": 1, "locale": "fa", "cycle": 3,
                   "acceptedUnits": len(order), "sourceAuntIds": aunt_source,
                   "targetAuntIdsBefore": aunt_target, "exactSourceRepeatIds": exact_source,
                   "exactTargetRepeatIdsBefore": exact_target, "affectedBranchIds": family_rows,
                   "sourceInventorySha256": sha(ROOT / "Source/localization-inventory-v3/strings.jsonl"),
                   "selectorSpecSha256": sha(CYCLE / "selector-spec.json"),
                   "assembledConsumer": "one complete Yarn dialogue line, no placeholders or dynamic joins; branch order from pinned compiled Scammer_Photo_Gun",
                   "compiledContextSha256": sha(REVIEW / "compiled-context.json"),
                   "compiledYarnProgramSha256": program_hash}
    write_once(CYCLE / "aunt-enumeration.json", encoded(enumeration))
    row = {"findingId": "R02-F01", "stableId": SID, "path": item["path"],
           "source": item["source"], "before": item["currentTarget"],
           "acceptedTarget": item["proposedTarget"],
           "reason": "Source aunt side is unspecified; maternal-only Persian was unsupported.",
           "factsRetained": ["singular aunt", "her house lost in cards", "prior consequence", "comparison with one photo"],
           "protectedSyntax": "unchanged speaker prefix and trailing ellipsis; no dynamic placeholders"}
    plan = {"schemaVersion": 1, "locale": "fa", "cycle": 3, "acceptedUnits": len(order),
            "phase": "adjudicated and preflighted before application",
            "reviewVerdictSha256": sha(REVIEW / "review-verdict.json"),
            "reviewFindingsSha256": sha(REVIEW / "findings.json"),
            "selectorSpecSha256": sha(CYCLE / "selector-spec.json"),
            "enumerationSha256": sha(CYCLE / "aunt-enumeration.json"),
            "rows": [row], "unchangedDecisions": "Both review02 watchlist wording decisions and all cycle02 findings retained."}
    write_once(CYCLE / "correction-plan.json", encoded(plan))
    write_once(CYCLE / "before" / AUTHORED.name, AUTHORED.read_bytes())
    write_once(CYCLE / "before" / SIDECAR.name, SIDECAR.read_bytes())
    preflight = {"schemaVersion": 1, "locale": "fa", "cycle": 3,
                 "result": "passed before target edit", "acceptedUnits": len(order),
                 "reviewerEvidenceFilesVerified": len(read(REVIEW / "evidence-index.json")["files"]),
                 "reviewerPinsVerified": len(verdict["pins"]),
                 "sourceManifestSha256": sha(ROOT / "Source/preserve-exactly-v4.json"),
                 "sourceStringsSha256": sha(ROOT / "Source/localization-inventory-v3/strings.jsonl"),
                 "sourceStaticSha256": sha(ROOT / "Source/localization-inventory-v3/static-text.jsonl"),
                 "glossaryLayerSha256": sha(ROOT / "Documentation/glossary-translations/fa/layer.json"),
                 "beforeAuthoredSha256": sha(AUTHORED), "beforeSidecarSha256": sha(SIDECAR),
                 "correctionPlanSha256": sha(CYCLE / "correction-plan.json"),
                 "recipeHashes": {str(p.relative_to(ROOT)): sha(p) for p in recipe_paths},
                 "checks": ["exact pinned full source and current target", "one accepted aunt source/target/repetition",
                            "compiled branch order and both outcomes", "whole replacement facts and uncertainty",
                            "speaker prefix, exact spans, syntax, whitespace and 16538 pre-edit values via check_value"],
                 "dependentRegeneration": "none: direct dialogue-batch-348 authored row; phrase/static/credits recipes and common-options expansion have no old/source phrase"}
    write_once(CYCLE / "preflight.json", encoded(preflight))
    print(json.dumps({"acceptedUnits": len(order), "auntSource": len(aunt_source),
                      "auntTarget": len(aunt_target), "branchContext": len(family_rows),
                      "correctionUnitsPreflighted": 1}))


def apply():
    pre = read(CYCLE / "preflight.json")
    assert pre["result"] == "passed before target edit"
    assert sha(AUTHORED) == pre["beforeAuthoredSha256"]
    assert sha(SIDECAR) == pre["beforeSidecarSha256"]
    assert sha(CYCLE / "correction-plan.json") == pre["correctionPlanSha256"]
    assert (CYCLE / "before" / AUTHORED.name).read_bytes() == AUTHORED.read_bytes()
    row = read(CYCLE / "correction-plan.json")["rows"][0]
    text = AUTHORED.read_text()
    lead = r'("id":\s*' + re.escape(SID.rsplit(":", 1)[1]) + r'\s*,\s*"target":\s*)'
    before = json.dumps(row["before"], ensure_ascii=False)
    after = json.dumps(row["acceptedTarget"], ensure_ascii=False)
    pattern = re.compile(lead + re.escape(before))
    assert len(pattern.findall(text)) == 1
    changed = pattern.sub(lambda m: m.group(1) + after, text, count=1).encode()
    parsed_before = read(AUTHORED)
    parsed_after = json.loads(changed)
    assert len(parsed_before["entries"]) == len(parsed_after["entries"])
    diffs = [(a, b) for a, b in zip(parsed_before["entries"], parsed_after["entries"]) if a != b]
    assert len(diffs) == 1 and diffs[0][0]["id"] == int(SID.rsplit(":", 1)[1])
    assert diffs[0][1]["target"] == row["acceptedTarget"]
    write_once(CYCLE / "after" / AUTHORED.name, changed)
    temp = AUTHORED.with_name(AUTHORED.name + ".cycle3-tmp")
    assert not temp.exists()
    temp.write_bytes(changed)
    temp.replace(AUTHORED)
    assert AUTHORED.read_bytes() == (CYCLE / "after" / AUTHORED.name).read_bytes()
    write_once(CYCLE / "file-delta-manifest.json", encoded({
        "schemaVersion": 1, "locale": "fa", "cycle": 3,
        "correctionPlanSha256": sha(CYCLE / "correction-plan.json"),
        "correctedIds": [SID],
        "files": [{"path": str(AUTHORED.relative_to(ROOT)),
                   "beforeSha256": pre["beforeAuthoredSha256"], "afterSha256": sha(AUTHORED)}],
        "boundary": "single authored file atomic replacement; sidecar refreshed separately by validator",
        "derivedArtifacts": "none depend on this direct Yarn dialogue row"}))
    print(json.dumps({"correctedUnits": 1, "authoredSha256": sha(AUTHORED)}))


def closure():
    pin_reviewer(before=True)
    pre = read(CYCLE / "preflight.json")
    assert sha(CYCLE / "before" / AUTHORED.name) == pre["beforeAuthoredSha256"]
    assert sha(AUTHORED) == read(CYCLE / "file-delta-manifest.json")["files"][0]["afterSha256"]
    assert sha(CYCLE / "after" / AUTHORED.name) == sha(AUTHORED)
    order, source, target, location, files, rules = corpus()
    spec = read(CYCLE / "selector-spec.json")
    old = set((PRIOR / "closure-ids.txt").read_text().splitlines())
    assert len(old) == 2701
    review_delta = set((PRIOR / "nextReviewDelta-ids.txt").read_text().splitlines())
    review02_ids = {row["stableId"] for row in read(REVIEW / "per-id-review.json")["reviewRows"]}
    review01_ids = {row["stableId"] for row in read(FA / "independent-review-01/per-id-review.json")["reviewRows"]}
    assert review_delta == review02_ids and old == review01_ids | review02_ids
    source_aunt = {sid for sid in order if re.search(spec["sourceAuntPattern"], source[sid]["source"], re.I)}
    target_aunt = {sid for sid in order if any(t in target[sid] for t in spec["targetAuntFragments"])}
    assert source_aunt == target_aunt == {SID}
    family = set(spec["contextNodeNames"])
    names, program_hash = compiled_names()
    assert family <= names
    context = {sid for sid in order if family.intersection(source[sid].get("nodeNames", []))}
    plan = read(CYCLE / "correction-plan.json")["rows"]
    repetition = {sid for sid in order if source[sid]["source"] == plan[0]["source"] or
                  target[sid] in (plan[0]["before"], plan[0]["acceptedTarget"])}
    mandatory = set((PRIOR / "mandatoryRegression-ids.txt").read_text().splitlines())
    runtime = set((PRIOR / "runtimeBinding-ids.txt").read_text().splitlines()) | context
    watchlist = set((PRIOR / "contextWatchlist-ids.txt").read_text().splitlines())
    components = {"changed": {SID}, "context": context, "repetition": repetition,
                  "glossaryReferent": source_aunt | target_aunt,
                  "runtimeBinding": runtime, "mandatoryRegression": mandatory,
                  "contextWatchlist": watchlist}
    current = set().union(*components.values())
    assert current <= set(order) and SID in current
    new = current - old
    retired = old - current
    invalidated = {sid for sid in old if location[sid] == str(AUTHORED.relative_to(ROOT))}
    corrected = {SID}
    delta = corrected | new | invalidated
    ordered = {k: [sid for sid in order if sid in v] for k, v in
               {**components, "closure": current, "newlySelected": new,
                "invalidatedPrior": invalidated, "retiredPrior": retired,
                "nextReviewDelta": delta}.items()}
    hashes = {k: {"count": len(v), "sha256": digest(id_bytes(v))} for k, v in ordered.items()}
    for k, ids in ordered.items():
        write_once(CYCLE / f"{k}-ids.txt", id_bytes(ids))
    rows = [{"stableId": sid, "path": location[sid], "source": source[sid]["source"],
             "target": target[sid], "nodeNames": source[sid].get("nodeNames", []),
             "components": [k for k, v in components.items() if sid in v]}
            for sid in ordered["closure"]]
    result = {"schemaVersion": 1, "locale": "fa", "cycle": 3,
              "phase": "author correction handoff; distinct review pending", "acceptedUnits": len(order),
              "sourceManifestSha256": sha(ROOT / "Source/preserve-exactly-v4.json"),
              "sourceInventorySha256": sha(ROOT / "Source/localization-inventory-v3/strings.jsonl"),
              "staticInventorySha256": sha(ROOT / "Source/localization-inventory-v3/static-text.jsonl"),
              "glossaryLayerSha256": sha(ROOT / "Documentation/glossary-translations/fa/layer.json"),
              "compiledContextSha256": sha(REVIEW / "compiled-context.json"),
              "compiledYarnProgramSha256": program_hash,
              "firstPassSnapshotSha256": sha(FA / "audit-cycle-001/first-pass.snapshot.json"),
              "review01VerdictSha256": sha(FA / "independent-review-01/review-verdict.json"),
              "review02VerdictSha256": sha(REVIEW / "review-verdict.json"),
              "review02PerIdSha256": sha(REVIEW / "per-id-review.json"),
              "previousClosureSha256": sha(PRIOR / "closure.json"),
              "previousClosureIdsSha256": sha(PRIOR / "closure-ids.txt"),
              "correctionPlanSha256": sha(CYCLE / "correction-plan.json"),
              "selectorSpecSha256": sha(CYCLE / "selector-spec.json"),
              "fileDeltaManifestSha256": sha(CYCLE / "file-delta-manifest.json"),
              "componentHashes": hashes, "missingAcceptedIds": [], "extraUnacceptedIds": [],
              "retiredReason": "prior photo and other resolved correction dependencies outside the sole aunt correction and stable mandatory catalog",
              "unresolvedQuestions": read(PRIOR / "closure.json")["unresolvedQuestions"],
              "reviewRows": rows}
    write_once(CYCLE / "closure.json", encoded(result))
    delta_rows = [{"stableId": sid, "path": location[sid], "source": source[sid]["source"],
                   "target": target[sid], "reason": [k for k, vals in
                   (("corrected", corrected), ("newlySelected", new),
                    ("invalidatedPriorFileHash", invalidated)) if sid in vals]}
                  for sid in ordered["nextReviewDelta"]]
    write_once(CYCLE / "next-review-delta.json", encoded({
        "schemaVersion": 1, "locale": "fa", "cycle": 3,
        "formula": "corrected union (current closure minus previous independently reviewed closure) union explicit invalidated prior IDs",
        "previousIndependentClosureIdsSha256": sha(PRIOR / "closure-ids.txt"),
        "currentClosureSha256": sha(CYCLE / "closure.json"),
        "componentHashes": {k: hashes[k] for k in
                            ("changed", "newlySelected", "invalidatedPrior", "retiredPrior", "nextReviewDelta")},
        "invalidatedPolicy": "all previously reviewed stable IDs in the changed authored batch-348 file; conservative file-hash invalidation",
        "missingAcceptedIds": [], "extraUnacceptedIds": [], "rows": delta_rows}))
    write_once(CYCLE / "deterministic-gate.json", encoded({
        "schemaVersion": 1, "locale": "fa", "cycle": 3, "acceptedUnits": len(order),
        "checkedTargets": len(target), "structuralAndPreserveExact": "passed",
        "sourceManifestSha256": sha(ROOT / "Source/preserve-exactly-v4.json"),
        "authoredFileHashes": {str(path.relative_to(ROOT)): sha(path) for path in files},
        "staticPhraseMapSha256": sha(FA / "static-phrase-map.json"),
        "commonOptionsSha256": sha(FA / "common-options-001.authored.json"),
        "creditsRoleMapSha256": sha(FA / "credits-role-map.json"),
        "semanticReview": "full first pass reusable; author correction only; distinct delta review pending",
        "runtime": "not-run"}))
    print(json.dumps({"acceptedUnits": len(order), "closure": len(current),
                      "newlySelected": len(new), "invalidatedPrior": len(invalidated),
                      "retiredPrior": len(retired), "nextReviewDelta": len(delta),
                      "componentHashes": hashes}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "apply", "closure"))
    phase = parser.parse_args().phase
    {"prepare": prepare, "apply": apply, "closure": closure}[phase]()
