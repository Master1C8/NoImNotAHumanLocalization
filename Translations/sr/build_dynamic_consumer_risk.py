#!/usr/bin/env python3
"""Verify the bounded Serbian format-slot consumer inventory for cycle 002."""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SR = ROOT / "Translations/sr"
REVIEW = SR / "independent-review-01"
OUT = SR / "semantic-cycle-002-dynamic-risk.json"
GUIDS = {"UI": "0cbd8a7a4f543344bb95659de87f67a5",
         "Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
         "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def idsha(ids):
    return hashlib.sha256("".join(i + "\n" for i in ids).encode()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--write", action="store_true")
    args = p.parse_args()
    verification = read(REVIEW / "verification.json")
    closure = read(SR / "semantic-cycle-001-closure.json")
    mandatory = read(SR / "semantic-cycle-001-regressions.json")
    reviewer = read(REVIEW / "findings.json")
    extra = read(SR / "semantic-cycle-002-additional-findings.json")
    consumers = read(REVIEW / "runtime-consumers.json")
    yarn = read(REVIEW / "yarn-context.json")["nodes"]
    manifest = read(ROOT / "Source/preserve-exactly-v4.json")
    canonical = [r["stableId"] for r in manifest["tableRows"] + manifest["staticRows"]]
    slots = mandatory["catalog"]["allFormatSlotAndDynamicJoinRows"]["ids"]
    require(len(slots) == 111 and idsha(slots) ==
            mandatory["catalog"]["allFormatSlotAndDynamicJoinRows"]["idsSha256"],
            "Pinned 111-row slot catalog changed")
    require(sha(SR / "semantic-cycle-001-closure.json") == reviewer["closureSha256"] and
            closure["currentAuthoredFileSetSha256"] == reviewer["inputAuthoredFileSetSha256"] ==
            verification["authoredFileSetSha256"], "Reviewer baseline differs")
    for pin in verification["pins"]:
        path = Path(pin["path"])
        path = path if path.is_absolute() else ROOT / path
        require(sha(path) == pin["expectedSha256"], "Pinned input changed: " + pin["path"])
    targets, paths = {}, {}
    for file in verification["authoredFiles"]:
        path = ROOT / file["path"]
        require(sha(path) == file["sha256"], "Authored baseline changed")
        batch = read(path)
        for entry in batch["entries"]:
            identifier = entry.get("stableId") or ("string:" + GUIDS[batch["collection"]]
                        + ":" + str(entry["id"]))
            targets[identifier], paths[identifier] = entry["target"], file["path"]
    source = {r["stableId"]: r for r in
              (json.loads(line) for line in
               (ROOT / "Source/localization-inventory-v3/strings.jsonl").open())}
    instructions = defaultdict(list)
    for node, record in yarn.items():
        preceding = None
        for entry in record["instructions"]:
            if entry["opcode"] == 12:
                preceding = entry["operands"][0]
            if entry.get("stableId") in slots:
                instructions[entry["stableId"]].append({"node": node,
                    "consumer": preceding, "instructionIndex": entry["index"]})
    same_place = defaultdict(list)
    for entry in consumers["samePlaceLabelCandidates"]:
        same_place[entry["node"]].extend(entry["possibleLabels"])
    findings = {f["stableId"]: f["findingId"] for f in reviewer["findings"]}
    findings.update({f["stableId"]: f["findingId"] for f in extra["findings"]})
    rows = []
    for identifier in slots:
        refs = instructions.get(identifier, [])
        command = refs[0]["consumer"] if refs else None
        require(all(x["consumer"] == command for x in refs), "Ambiguous consumer")
        category = (command if command in {"GetCharacterOnPlace", "LocalizeItem",
                                          "GetCourierOrder", "GetPhoneNumber"}
                    else "unboundInPinnedCompiledProgram")
        possible = []
        if category == "GetCharacterOnPlace":
            possible = [{"enum": x["enum"], "labelStableId": x.get("labelStableId"),
                         "target": x.get("target")}
                        for ref in refs for x in same_place[ref["node"]]]
        elif category == "LocalizeItem":
            possible = [{"enum": x["enum"], "labelStableId": x["labelStableId"],
                         "target": x["target"]} for x in consumers["deficitLabels"]]
        rows.append({"stableId": identifier, "key": source[identifier].get("key"),
                     "source": source[identifier]["source"], "currentTarget": targets[identifier],
                     "targetFile": paths[identifier], "consumerCategory": category,
                     "compiledInstructions": refs, "possibleRawLabels": possible,
                     "findingId": findings.get(identifier),
                     "riskDisposition": ("proposed correction" if identifier in findings else
                        "compiled known inputs checked; no objective correction" if refs else
                        "accepted text; matching compiled instruction not established")})
    require([x["stableId"] for x in rows] == [i for i in canonical if i in set(slots)],
            "Risk rows differ from canonical source order")
    counts = dict(Counter(r["consumerCategory"] for r in rows))
    require(counts == {"unboundInPinnedCompiledProgram": 13,
                       "GetPhoneNumber": 18, "GetCharacterOnPlace": 55,
                       "GetCourierOrder": 4, "LocalizeItem": 21},
            "Consumer category count changed")
    require(len([r for r in rows if r["findingId"]]) == 15 and
            len(reviewer["findings"]) == 15, "Finding boundary changed")
    result = {"schemaVersion": 1, "locale": "sr", "cycle": "002",
              "status": "bounded risk inventory before correction; no runtime execution",
              "baselineAuthoredFileSetSha256": verification["authoredFileSetSha256"],
              "sourceInventorySha256": sha(ROOT / "Source/localization-inventory-v3/strings.jsonl"),
              "glossaryFingerprint": sha(ROOT / "Documentation/glossary-translations/sr/layer.json"),
              "reviewerFindingsSha256": sha(REVIEW / "findings.json"),
              "additionalFindingsSha256": sha(SR / "semantic-cycle-002-additional-findings.json"),
              "runtimeConsumersSha256": sha(REVIEW / "runtime-consumers.json"),
              "yarnContextSha256": sha(REVIEW / "yarn-context.json"),
              "acceptedFormatSlotRows": 111, "acceptedFormatSlotIdsSha256": idsha(slots),
              "consumerCategoryCounts": counts, "rows": rows,
              "adjacentDirectContextFinding": reviewer["findings"][-1]["stableId"],
              "limitations": ["Thirteen accepted slot rows have no matching instruction in the pinned compiled program; their runtime consumer cannot be inferred.",
                              "Three same-place candidate enum keys lack a pinned UI label; no target label or reachability is invented.",
                              "Source gender/default inconsistencies and the dismissed Bestson resemblance candidate are retained as review evidence, not changes."]}
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if OUT.exists():
        require(OUT.read_text() == text, "Immutable risk inventory differs")
    else:
        require(args.write, "Risk inventory is missing")
        OUT.write_text(text)
    print(json.dumps({"result": "written" if args.write else "verified",
                      "rows": len(rows), "categories": counts,
                      "sha256": sha(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
