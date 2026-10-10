#!/usr/bin/env python3
"""Pin cycle-2 Persian author decisions before changing any target file."""

import hashlib
import json
import pathlib
import re
import shutil
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


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def immutable(path, data):
    data = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode()
    if path.exists():
        assert path.read_bytes() == data, f"immutable evidence differs: {path}"
    else:
        path.write_bytes(data)


def main():
    verdict = read(REVIEW / "review-verdict.json")
    evidence = read(REVIEW / "evidence-index.json")
    assert all(sha(REVIEW / name) == pin for name, pin in evidence["files"].items())
    assert all(sha(pathlib.Path(name) if pathlib.Path(name).is_absolute() else ROOT / name) == pin
               for name, pin in verdict["pins"].items())
    assert all(sha(ROOT / name) == pin for name, pin in verdict["currentAuthoredHashes"].items())
    manifest = read(ROOT / "Source/preserve-exactly-v4.json")
    rules = {row["stableId"]: row for row in manifest["tableRows"] + manifest["staticRows"]}
    order = list(rules)
    assert len(order) == len(rules) == 16538
    source = {}
    for name in ("strings.jsonl", "static-text.jsonl"):
        for line in (ROOT / "Source/localization-inventory-v3" / name).open():
            row = json.loads(line)
            source[row["stableId"]] = row
    assert set(order) <= set(source)
    target, location = {}, {}
    for path in sorted(FA.glob("*batch-*.json")):
        if not re.fullmatch(r"(?:ui|dialogue|checks)-batch-\d{3}\.json", path.name):
            continue
        batch = read(path)
        for entry in batch["entries"]:
            sid = f"string:{GUID[batch['collection']]}:{entry['id']}"
            assert sid not in target
            target[sid], location[sid] = entry["target"], str(path.relative_to(ROOT))
    for entry in read(FA / "static-text-draft.json")["entries"]:
        sid = entry["stableId"]
        assert sid not in target
        target[sid], location[sid] = entry["target"], "Translations/fa/static-text-draft.json"
    assert set(target) == set(order)
    old = {row["stableId"] for row in read(FA / "audit-cycle-001/closure.json")["reviewRows"]}
    assert len(old) == 1506
    pattern = re.compile(r"фото|фотк|сним(?:ок|к)", re.IGNORECASE)
    matches = {sid for sid in order if pattern.search(source[sid]["source"])}
    seed_nodes = {node for sid in matches for node in source[sid].get("nodeNames", [])}
    photo_families = {node.split("_Photo")[0] for node in seed_nodes if "_Photo" in node}
    prefixes = tuple(family + "_Photo" for family in sorted(photo_families))
    same_node = {sid for sid in order if seed_nodes.intersection(source[sid].get("nodeNames", []))}
    branch = {sid for sid in order if any(node.startswith(prefixes)
              for node in source[sid].get("nodeNames", []))}
    remedial = [sid for sid in order if sid in (matches | same_node | branch) - old]
    reviewer_candidate = set((REVIEW / "candidateClosureDelta-ids.txt").read_text().splitlines())
    omissions = set((REVIEW / "selectorOmissions-ids.txt").read_text().splitlines())
    assert reviewer_candidate <= set(remedial) and omissions <= set(remedial)
    assert len(remedial) == 1195
    old_spec = read(FA / "audit-cycle-001/selector-spec.json")
    spec = dict(old_spec)
    spec["cycle"] = 2
    spec["sourceConceptPatterns"] = [value.replace("фотографир|снимк", "фото|фотк|сним(?:ок|к)")
                                     for value in old_spec["sourceConceptPatterns"]]
    spec["photoContext"] = {
        "pattern": "фото|фотк|сним(?:ок|к)",
        "seed": "every accepted source match, including matches already in reviewed closure",
        "sameNode": "all accepted IDs sharing a source-inventory nodeName with a seed",
        "branchFamily": "all accepted IDs in any <character>_Photo node family of a seed",
        "compiledTopologyGate": "each selected named node must exist in pinned compiled Yarn program",
        "unboundRows": "source matches with no nodeNames stay directly selected; no invented branch",
    }
    immutable(CYCLE / "selector-spec.json", spec)
    read_rows = [{"stableId": sid, "source": source[sid]["source"],
                  "targetBefore": target[sid], "path": location[sid],
                  "nodeNames": source[sid].get("nodeNames", []),
                  "photoDirect": sid in matches, "sameNode": sid in same_node,
                  "photoBranchFamily": sid in branch}
                 for sid in remedial]
    immutable(CYCLE / "remedial-read.json", {
        "schemaVersion": 1, "locale": "fa", "cycle": 2,
        "phase": "bounded author source-to-target read before cycle-2 corrections",
        "acceptedUnits": 16538, "previousIndependentlyReviewedUnits": len(old),
        "reviewerCandidateSubset": len(reviewer_candidate),
        "reviewerOmissionSubset": len(omissions),
        "photoDirectMatches": len(matches), "photoSeedNodes": len(seed_nodes),
        "photoFamilies": len(photo_families), "newAffectedUnits": len(remedial),
        "sourceManifestSha256": sha(ROOT / "Source/preserve-exactly-v4.json"),
        "reviewVerdictSha256": sha(REVIEW / "review-verdict.json"),
        "selectorSpecSha256": sha(CYCLE / "selector-spec.json"),
        "rows": read_rows,
        "readConclusion": "Four independent-review proposals and one additional daughter address-form finding; no other objective corrections found in this bounded read. Author read is not independent review.",
    })
    findings = read(REVIEW / "findings.json")["findings"]
    assert [x["findingId"] for x in findings] == ["F01", "F02", "F03", "F04"]
    plan = []
    for item in findings:
        sid = item["stableId"]
        assert source[sid]["source"] == item["source"]
        assert target[sid] == item["target"] and location[sid] == item["path"]
        plan.append({"findingId": item["findingId"], "stableId": sid,
                     "path": location[sid], "source": source[sid]["source"],
                     "before": target[sid], "acceptedTarget": item["proposedTarget"],
                     "reason": item["objectiveReason"], "evidence": item["contextEvidence"]})
    sid = "string:444ff14f1967f5a4c8eb9e4cf4c913f1:110504452048363530"
    assert sid in remedial
    assert source[sid]["source"] == "Daughter: Покажешь потом фото?"
    assert target[sid] == "Daughter: بعداً عکس رو نشونم می‌دین؟"
    plan.append({"findingId": "A05", "stableId": sid, "path": location[sid],
                 "source": source[sid]["source"], "before": target[sid],
                 "acceptedTarget": "Daughter: بعداً عکس رو نشونم می‌دی؟",
                 "reason": "Source Покажешь is informal singular; Persian می‌دین is formal/plural. Match the daughter's informal singular address in this line.",
                 "evidence": "pinned source full unit; adjacent Daughter photo lines in remedial read"})
    assert len({x["stableId"] for x in plan}) == len(plan) == 5
    for item in plan:
        check_value(rules[item["stableId"]], item["acceptedTarget"])
    plan = [next(item for item in plan if item["stableId"] == sid)
            for sid in order if sid in {x["stableId"] for x in plan}]
    immutable(CYCLE / "correction-plan.json", {
        "schemaVersion": 1, "locale": "fa", "cycle": 2,
        "phase": "adjudicated; preflight passed; not yet applied",
        "acceptedUnits": 16538, "reviewVerdictSha256": sha(REVIEW / "review-verdict.json"),
        "reviewFindingsSha256": sha(REVIEW / "findings.json"),
        "remedialReadSha256": sha(CYCLE / "remedial-read.json"),
        "rows": plan,
        "unchangedScreenedQuestions": [
            "Rocker's with-you photograph preserves source с тобой; no solo-photo inference applied.",
            "Intruder's colloquial camera/aura wording remains source-ambiguous; no invented mechanism.",
            "No unbound duplicate was assigned a new compiled branch without evidence.",
        ],
    })
    for path in sorted({ROOT / item["path"] for item in plan} | {FA / "static-phrase-map.json"}):
        destination = CYCLE / "before" / path.name
        destination.parent.mkdir(exist_ok=True)
        if destination.exists():
            assert destination.read_bytes() == path.read_bytes()
        else:
            shutil.copyfile(path, destination)
    immutable(CYCLE / "preflight.json", {
        "schemaVersion": 1, "locale": "fa", "cycle": 2,
        "result": "passed; no target applied at preflight time",
        "reviewerInputsPinned": len(evidence["files"]),
        "reviewerSourceAndRecipePins": len(verdict["pins"]),
        "authoredFilePins": len(verdict["currentAuthoredHashes"]),
        "reviewerFindingsAdjudicated": 4,
        "additionalAuthorFinding": 1,
        "correctionUnits": len(plan),
        "checks": ["exact prior source and target", "full replacement meaning, agency, participants and address",
                   "approved glossary", "compiled photo/branch or accepted static binding",
                   "speaker, placeholders, numbers, tags, exact spans and whitespace via preserve_exact.check_value"],
        "correctionPlanSha256": sha(CYCLE / "correction-plan.json"),
        "beforeFileHashes": {str(path.relative_to(ROOT)): sha(path) for path in sorted({ROOT / item["path"] for item in plan} | {FA / "static-phrase-map.json"})},
    })
    print(json.dumps({"remedialUnits": len(remedial), "photoDirect": len(matches),
                      "photoFamilies": len(photo_families), "correctionsPreflighted": len(plan)},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
