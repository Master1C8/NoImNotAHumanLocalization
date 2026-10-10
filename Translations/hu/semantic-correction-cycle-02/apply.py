#!/usr/bin/env python3
"""Preflight and apply the pinned second Hungarian author correction batch.

The full proposed corpus is checked in memory before any authored replacement.
Each file replacement is atomic; the set of files is not a transaction. Repeated
application accepts only the recorded before/after hashes, so an interrupted
application may be resumed without overwriting unrelated work.
"""

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


def encode(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode()


def require(test, message):
    if not test:
        raise ValueError(message)


def atomic(path, data):
    fd, name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def sid(batch, entry):
    guid = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
            "UI": "0cbd8a7a4f543344bb95659de87f67a5",
            "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}[batch["collection"]]
    return f"string:{guid}:{entry['id']}"


def collect():
    plan = json.loads((HERE / "adjudicated-plan.json").read_text())
    pins = {"sourceInventorySha256": ROOT / "Source/localization-inventory-v3/strings.jsonl",
            "staticInventorySha256": ROOT / "Source/localization-inventory-v3/static-text.jsonl",
            "acceptedScopeSha256": ROOT / "Documentation/text-source-acceptance-v1.json",
            "preserveExactManifestSha256": ROOT / "Source/preserve-exactly-v4.json",
            "approvedGlossaryLayerSha256": ROOT / "Documentation/glossary-translations/hu/layer.json",
            "canonicalGlossarySha256": Path("/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary.json"),
            "firstPassProgressSha256": HU / "semantic-review-progress.json",
            "reviewVerdictSha256": HU / "independent-review-01/review-verdict.json",
            "reviewProposalSha256": HU / "independent-review-01/consolidated-proposals-v2.json",
            "reviewArtifactManifestSha256": HU / "independent-review-01/artifact-manifest.json",
            "previousClosureManifestSha256": HU / "semantic-correction-cycle-01/evidence/closure-manifest.json",
            "previousReviewedRowsSha256": HU / "independent-review-01/full-pair-read-evidence.jsonl"}
    for key, path in pins.items():
        require(plan[key] == digest(path), "Input pin changed: " + key)
    review = json.loads((HU / "independent-review-01/review-verdict.json").read_text())
    require(review["status"] == "corrections-required" and review["reviewRows"] == 2902,
            "Review verdict changed")
    source = {r["stableId"]: r for name in ("strings", "static-text")
              for r in (json.loads(line) for line in
                        (ROOT / f"Source/localization-inventory-v3/{name}.jsonl").open())}
    manifest = json.loads((ROOT / "Source/preserve-exactly-v4.json").read_text())
    rules = {row["stableId"]: row for row in manifest["tableRows"] + manifest["staticRows"]}
    pattern = re.compile(r"(?:dialogue|ui|checks)-batch-\d{3}\.json$")
    files = sorted(p for p in HU.glob("*-batch-*.json") if pattern.fullmatch(p.name))
    files.append(HU / "static-text-draft.json")
    docs = {p: json.loads(p.read_text()) for p in files}
    entries = {}
    for path, doc in docs.items():
        for entry in doc["entries"]:
            key = entry["stableId"] if path.name == "static-text-draft.json" else sid(doc, entry)
            require(key not in entries, "Duplicate current ID: " + key)
            entries[key] = (path, entry)
    require(len(entries) == len(rules) == 16538 and set(entries) == set(rules),
            "Accepted IDs changed")
    require(len(plan["rows"]) == 14 and len({r["stableId"] for r in plan["rows"]}) == 14,
            "Correction rows differ")
    touched = set()
    for row in plan["rows"]:
        key = row["stableId"]
        require(key in entries and key in source, "Unknown correction ID: " + key)
        path, entry = entries[key]
        require(str(path.relative_to(ROOT)) == row["authoredFile"] and
                digest(path) == row["beforeAuthoredFileSha256"] and
                source[key]["source"] == row["source"] and
                hashlib.sha256(row["source"].encode()).hexdigest() == row["sourceSha256"] and
                entry["target"] == row["currentTarget"] and
                row["currentTarget"] != row["finalTarget"],
                "Correction alignment changed: " + key)
        check_value(rules[key], row["finalTarget"])
        entry["target"] = row["finalTarget"]
        touched.add(path)
    for key, rule in rules.items():
        check_value(rule, entries[key][1]["target"])
    require(len(touched) == 9, "Unexpected authored file count")
    return plan, {path: encode(docs[path]) for path in touched}


def prepare():
    plan, outputs = collect()
    stage = HERE / "staged"
    preflight = HERE / "preflight.json"
    require(not stage.exists() and not preflight.exists(), "Preflight already exists")
    stage.mkdir()
    records = []
    for path, payload in sorted(outputs.items()):
        saved = stage / path.name
        atomic(saved, payload)
        records.append({"path": str(path.relative_to(ROOT)), "beforeSha256": digest(path),
                        "afterSha256": hashlib.sha256(payload).hexdigest(),
                        "stagedPath": str(saved.relative_to(ROOT))})
    report = {"schemaVersion": 1, "locale": "hu", "acceptedUnits": 16538,
              "status": "complete virtual exact preflight; authored files not yet applied",
              "planSha256": digest(HERE / "adjudicated-plan.json"),
              "sourceInventorySha256": plan["sourceInventorySha256"],
              "preserveExactManifestSha256": plan["preserveExactManifestSha256"],
              "changedIds": len(plan["rows"]), "virtualAcceptedIds": 16538,
              "virtualPreserveExact": "passed", "fileCount": len(records), "files": records,
              "applicationBoundary": "per-file atomic replacement; no multi-file transaction"}
    atomic(preflight, encode(report))
    print(json.dumps({"preflightSha256": digest(preflight), "files": len(records),
                      "virtualAcceptedIds": 16538}))


def apply_or_verify(apply):
    report = json.loads((HERE / "preflight.json").read_text())
    require(report["planSha256"] == digest(HERE / "adjudicated-plan.json") and
            report["virtualPreserveExact"] == "passed", "Preflight changed")
    for item in report["files"]:
        path, saved = ROOT / item["path"], ROOT / item["stagedPath"]
        payload = saved.read_bytes()
        require(hashlib.sha256(payload).hexdigest() == item["afterSha256"],
                "Staged output changed")
        current = digest(path)
        require(current in (item["beforeSha256"], item["afterSha256"]),
                "Authored file differs from pinned states: " + item["path"])
        if apply and current != item["afterSha256"]:
            atomic(path, payload)
        if not apply:
            require(current == item["afterSha256"], "Unapplied output: " + item["path"])
    print(json.dumps({"mode": "apply" if apply else "verify", "files": len(report["files"])}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "apply", "verify"))
    mode = parser.parse_args().mode
    if mode == "prepare":
        prepare()
    else:
        apply_or_verify(mode == "apply")
