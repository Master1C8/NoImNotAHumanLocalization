#!/usr/bin/env python3
"""Apply the one additional Hungarian correction found in expanded closure context."""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
HU = ROOT / "Translations/hu"
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import check_value  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def require(test, message):
    if not test:
        raise ValueError(message)


def atomic(path, payload):
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def inputs():
    plan = json.loads((HERE / "adjudicated-plan.json").read_text())
    old = HU / "semantic-correction-cycle-02"
    require(plan["supersedesPlanSha256"] == digest(old / "adjudicated-plan.json") and
            plan["supersededClosureManifestSha256"] == digest(old / "evidence/closure-manifest.json") and
            len(plan["rows"]) == 15, "Previous author cycle changed")
    pins = {"sourceInventorySha256": ROOT / "Source/localization-inventory-v3/strings.jsonl",
            "staticInventorySha256": ROOT / "Source/localization-inventory-v3/static-text.jsonl",
            "preserveExactManifestSha256": ROOT / "Source/preserve-exactly-v4.json",
            "approvedGlossaryLayerSha256": ROOT / "Documentation/glossary-translations/hu/layer.json",
            "canonicalGlossarySha256": Path("/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary.json")}
    for key, path in pins.items():
        require(plan[key] == digest(path), "Input changed: " + key)
    prior_files = json.loads((old / "evidence/after-authored-files.json").read_text())["files"]
    for row in prior_files:
        require(digest(ROOT / row["path"]) == row["sha256"],
                "Author cycle02 file changed: " + row["path"])
    additional = json.loads((HERE / "additional-closure-read.json").read_text())
    require(additional["candidateCount"] == 41 and additional["objectiveAdditionalCorrections"] == 1 and
            additional["previousAuthorClosureSha256"] == plan["supersededClosureManifestSha256"],
            "Additional bounded read changed")
    return plan


def prepare():
    plan = inputs()
    row = plan["rows"][-1]
    key = row["stableId"]
    path = ROOT / row["authoredFile"]
    doc = json.loads(path.read_text())
    matches = [entry for entry in doc["entries"] if
               key == "string:444ff14f1967f5a4c8eb9e4cf4c913f1:" + str(entry["id"])]
    require(len(matches) == 1 and matches[0]["target"] == row["currentTarget"] and
            digest(path) == row["beforeAuthoredFileSha256"], "Amendment target differs")
    source = next(r for r in (json.loads(line) for line in
                  (ROOT / "Source/localization-inventory-v3/strings.jsonl").open())
                  if r["stableId"] == key)
    require(source["source"] == row["source"] and source["key"] == row["key"],
            "Amendment source differs")
    preserve = json.loads((ROOT / "Source/preserve-exactly-v4.json").read_text())
    rules = {r["stableId"]: r for r in preserve["tableRows"] + preserve["staticRows"]}
    check_value(rules[key], row["finalTarget"])
    matches[0]["target"] = row["finalTarget"]
    targets = {}
    pattern = re.compile(r"(?:dialogue|ui|checks)-batch-\d{3}\.json$")
    for file in HU.glob("*-batch-*.json"):
        if not pattern.fullmatch(file.name):
            continue
        batch = doc if file == path else json.loads(file.read_text())
        guid = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
                "UI": "0cbd8a7a4f543344bb95659de87f67a5",
                "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}[batch["collection"]]
        for entry in batch["entries"]:
            sid = f"string:{guid}:{entry['id']}"
            require(sid not in targets, "Duplicate ID")
            targets[sid] = entry["target"]
    for entry in json.loads((HU / "static-text-draft.json").read_text())["entries"]:
        require(entry["stableId"] not in targets, "Duplicate static ID")
        targets[entry["stableId"]] = entry["target"]
    require(set(targets) == set(rules) and len(targets) == 16538,
            "Accepted ID set changed")
    for sid, rule in rules.items():
        check_value(rule, targets[sid])
    stage = HERE / "staged"
    preflight = HERE / "preflight.json"
    require(not stage.exists() and not preflight.exists(), "Preflight exists")
    stage.mkdir()
    payload = encode(doc)
    staged = stage / path.name
    atomic(staged, payload)
    report = {"schemaVersion": 1, "locale": "hu", "acceptedUnits": 16538,
              "status": "complete virtual exact preflight; amendment not yet applied",
              "planSha256": digest(HERE / "adjudicated-plan.json"),
              "additionalClosureReadSha256": digest(HERE / "additional-closure-read.json"),
              "changedId": key, "beforeSha256": digest(path),
              "afterSha256": hashlib.sha256(payload).hexdigest(),
              "path": str(path.relative_to(ROOT)), "stagedPath": str(staged.relative_to(ROOT)),
              "virtualPreserveExact": "passed", "applicationBoundary": "single-file atomic replacement"}
    atomic(preflight, encode(report))
    print(json.dumps({"preflightSha256": digest(preflight), "accepted": 16538,
                      "changedId": key}))


def apply_or_verify(apply):
    report = json.loads((HERE / "preflight.json").read_text())
    require(report["planSha256"] == digest(HERE / "adjudicated-plan.json") and
            report["additionalClosureReadSha256"] == digest(HERE / "additional-closure-read.json") and
            report["virtualPreserveExact"] == "passed", "Preflight changed")
    path, staged = ROOT / report["path"], ROOT / report["stagedPath"]
    payload = staged.read_bytes()
    require(hashlib.sha256(payload).hexdigest() == report["afterSha256"] and
            digest(path) in (report["beforeSha256"], report["afterSha256"]),
            "Staged or current file changed")
    if apply and digest(path) != report["afterSha256"]:
        atomic(path, payload)
    if not apply:
        require(digest(path) == report["afterSha256"], "Amendment not applied")
    print(json.dumps({"mode": "apply" if apply else "verify", "changedId": report["changedId"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "apply", "verify"))
    mode = parser.parse_args().mode
    if mode == "prepare":
        prepare()
    else:
        apply_or_verify(mode == "apply")
