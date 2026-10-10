#!/usr/bin/env python3
"""Prepare, apply, and verify the pinned Hungarian semantic correction batch.

This recipe transfers authored wording from adjudicated-plan.json. It does not
translate text. Each output is replaced atomically; the file set is not a
transaction, so --apply accepts only the recorded before or after hash and can
resume after an interruption.
"""

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
LOCALE = ROOT / "Translations/hu"
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import check_value  # noqa: E402


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    return sha(path.read_bytes())


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def relative(path):
    return str(path.relative_to(ROOT))


def atomic_write(path, data):
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def batch_paths():
    pattern = re.compile(r"(?:dialogue|ui|checks)-batch-\d{3}\.json$")
    return sorted(p for p in LOCALE.glob("*-batch-*.json") if pattern.fullmatch(p.name))


def stable_id(batch, entry):
    guid = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
            "UI": "0cbd8a7a4f543344bb95659de87f67a5",
            "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}[batch["collection"]]
    return "string:" + guid + ":" + str(entry["id"])


def inputs():
    plan_path = HERE / "adjudicated-plan.json"
    plan = json.loads(plan_path.read_text())
    progress = json.loads((LOCALE / "semantic-review-progress.json").read_text())
    manifest_path = ROOT / "Source/preserve-exactly-v4.json"
    manifest = json.loads(manifest_path.read_text())
    require(plan["firstPassProgressSha256"] == digest(LOCALE / "semantic-review-progress.json"),
            "First-pass checkpoint changed")
    require(plan["firstPassErrataSha256"] == digest(LOCALE / "semantic-review-evidence-errata-01.json"),
            "First-pass erratum changed")
    require(plan["proposalBatchSha256"] == digest(LOCALE / "semantic-correction-batch-01.json"),
            "Proposal evidence changed")
    pins = {"sourceInventorySha256": ROOT / "Source/localization-inventory-v3/strings.jsonl",
            "staticInventorySha256": ROOT / "Source/localization-inventory-v3/static-text.jsonl",
            "acceptedScopeSha256": ROOT / "Documentation/text-source-acceptance-v1.json",
            "preserveExactManifestSha256": manifest_path,
            "approvedGlossaryLayerSha256": ROOT / "Documentation/glossary-translations/hu/layer.json",
            "canonicalGlossarySha256": Path("/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary.json")}
    for field, path in pins.items():
        require(plan[field] == progress[field] == digest(path), "Pinned input changed: " + field)
    require(plan["acceptedUnits"] == 16538 and len(plan["rows"]) == 118,
            "Correction plan count changed")
    return plan, progress, manifest


def render(plan, progress, manifest):
    """Build the entire intended output set in memory before any authored write."""
    paths = batch_paths()
    batches = {p: json.loads(p.read_text()) for p in paths}
    by_id = {}
    for path, batch in batches.items():
        for entry in batch["entries"]:
            sid = stable_id(batch, entry)
            require(sid not in by_id, "Duplicate baseline ID: " + sid)
            by_id[sid] = (path, entry)
    rules = {row["stableId"]: row for row in manifest["tableRows"] + manifest["staticRows"]}
    source = {row["stableId"]: row for row in
              (json.loads(line) for line in (ROOT / "Source/localization-inventory-v3/strings.jsonl").open())}
    planned_ids = set()
    changes = {}
    for row in plan["rows"]:
        sid = row["stableId"]
        require(sid not in planned_ids and sid in by_id and sid in source and sid in rules,
                "Duplicate or unknown planned ID: " + sid)
        planned_ids.add(sid)
        path, entry = by_id[sid]
        require(relative(path) == row["authoredFile"] and
                progress["reviewedFileHashes"][relative(path)] == row["authoredFileSha256"] and
                source[sid]["source"] == row["source"] and
                source[sid]["sourceSha256"] == row["sourceSha256"] and
                entry["target"] == row["currentTarget"] and
                row["finalTarget"] != row["currentTarget"],
                "Source/target alignment changed: " + sid)
        check_value(rules[sid], row["finalTarget"])
        changes[sid] = row["finalTarget"]
    require(len(planned_ids) == 118, "Planned ID count changed")

    map_path = LOCALE / "common-options-002.authored.json"
    phrase_map = json.loads(map_path.read_text())
    for phrase in phrase_map["phrases"]:
        if phrase["source"] == "Мне надо вас проверить":
            require(phrase["expectedRows"] == 13 and phrase["target"] == "Meg kell vizsgálnom",
                    "Formal examination recipe changed")
            phrase["target"] = "Meg kell vizsgálnom önt"
        elif phrase["source"] == "Лучше уйдите":
            require(phrase["expectedRows"] == 3 and phrase["target"] == "Jobb, ha elmegy",
                    "Twins departure recipe changed")
            phrase["target"] = "Jobb, ha elmentek"
        elif phrase["source"] == "Вам лучше уйти":
            require(phrase["expectedRows"] == 8, "Plural rejection recipe changed")
            phrase["expectedRows"] = 4
        elif phrase["source"] == "Проходите":
            require(phrase["expectedRows"] == 9, "Plural invitation recipe changed")
            phrase["expectedRows"] = 5
    map_data = encode(phrase_map)
    generated_path = LOCALE / "dialogue-batch-003.json"
    require(generated_path in batches, "Missing generated common-options batch")
    moved = {sid for sid in planned_ids if by_id[sid][0] == generated_path and
             source[sid]["source"] in ("Вам лучше уйти", "Проходите")}
    require(len(moved) == 8, "Plural split is not eight IDs")
    new_path = LOCALE / "dialogue-batch-474.json"
    require(not new_path.exists(), "New branch-specific batch already exists")
    order = {row["stableId"]: i for i, row in enumerate(manifest["tableRows"])}
    moved_entries = sorted(({"id": int(sid.rsplit(":", 1)[1]), "target": changes[sid]}
                            for sid in moved), key=lambda x: order["string:444ff14f1967f5a4c8eb9e4cf4c913f1:" + str(x["id"])])
    generated = batches[generated_path]
    generated["entries"] = [e for e in generated["entries"] if stable_id(generated, e) not in moved]
    generated["authoredMapSha256"] = sha(map_data)
    new_batch = {"schemaVersion": 1, "locale": "hu", "sourceLocale": "ru",
                 "gameVersion": "1.3.19", "collection": "Dialogs",
                 "sourceInventorySha256": plan["sourceInventorySha256"],
                 "glossaryFingerprint": plan["approvedGlossaryLayerSha256"],
                 "status": "authored-draft; editorial and runtime acceptance pending",
                 "entries": moved_entries}
    for path, batch in batches.items():
        for entry in batch["entries"]:
            sid = stable_id(batch, entry)
            if sid in changes:
                entry["target"] = changes[sid]
    batches[new_path] = new_batch

    # Reproduce the shared exact-phrase generator with the branch-specific IDs
    # already owned by the new explicit batch. This catches future recipe drift.
    phrases = {x["source"]: x for x in phrase_map["phrases"]}
    prior = {entry["id"] for path, batch in batches.items() if path != generated_path and
             batch["collection"] == "Dialogs" for entry in batch["entries"]}
    expected_entries = []
    counts = Counter()
    for source_row in (json.loads(line) for line in
                       (ROOT / "Source/localization-inventory-v3/strings.jsonl").open()):
        if source_row["collection"] != "Dialogs" or source_row["source"] not in phrases:
            continue
        number = int(source_row["stableId"].rsplit(":", 1)[1])
        if number in prior:
            continue
        expected_entries.append({"id": number, "target": phrases[source_row["source"]]["target"]})
        counts[source_row["source"]] += 1
    require(all(counts[s] == p["expectedRows"] for s, p in phrases.items()) and
            expected_entries == generated["entries"], "Expanded phrase recipe differs")

    target = {}
    for batch in batches.values():
        for entry in batch["entries"]:
            sid = stable_id(batch, entry)
            require(sid not in target, "Duplicate planned ID: " + sid)
            target[sid] = entry["target"]
    static = json.loads((LOCALE / "static-text-draft.json").read_text())
    for entry in static["entries"]:
        sid = entry["stableId"]
        require(sid not in target, "Duplicate static ID: " + sid)
        target[sid] = entry["target"]
    require(len(target) == len(rules) == 16538 and set(target) == set(rules),
            "Planned accepted ID set differs")
    for sid, rule in rules.items():
        check_value(rule, target[sid])
    outputs = {path: encode(batch) for path, batch in batches.items()
               if path == new_path or any(by_id[sid][0] == path for sid in planned_ids)}
    outputs[map_path] = map_data
    require(len(outputs) == len({by_id[sid][0] for sid in planned_ids}) + 2,
            "Unexpected output file count")
    return outputs, moved, target


def prepare():
    plan, progress, manifest = inputs()
    outputs, moved, _ = render(plan, progress, manifest)
    stage = HERE / "staged"
    report_path = HERE / "preflight.json"
    require(not stage.exists() and not report_path.exists(), "Immutable preflight already exists")
    stage.mkdir()
    files = []
    for path, data in sorted(outputs.items()):
        before = digest(path) if path.exists() else None
        if path.exists():
            require(path == LOCALE / "common-options-002.authored.json" or
                    before == progress["reviewedFileHashes"][relative(path)],
                    "Authored before hash changed: " + relative(path))
        staged = stage / path.name
        require(not staged.exists(), "Staging name collision")
        atomic_write(staged, data)
        files.append({"path": relative(path), "beforeSha256": before,
                      "afterSha256": sha(data), "stagedPath": relative(staged)})
    report = {"schemaVersion": 1, "locale": "hu", "gameVersion": "1.3.19",
              "status": "complete virtual plan preflight; authored outputs not yet applied",
              "planSha256": digest(HERE / "adjudicated-plan.json"),
              "firstPassProgressSha256": plan["firstPassProgressSha256"],
              "sourceInventorySha256": plan["sourceInventorySha256"],
              "approvedGlossaryLayerSha256": plan["approvedGlossaryLayerSha256"],
              "preserveExactManifestSha256": plan["preserveExactManifestSha256"],
              "changedIds": len(plan["rows"]), "pluralBranchIdsMoved": len(moved),
              "virtualAcceptedIds": 16538, "virtualPreserveExact": "passed",
              "phraseRecipeExpansion": "passed", "fileCount": len(files), "files": files,
              "applicationBoundary": "per-file atomic replacement; no multi-file transaction"}
    atomic_write(report_path, encode(report))
    print(json.dumps({"preflight": relative(report_path), "sha256": digest(report_path),
                      "changedIds": 118, "files": len(files), "virtualPreserveExact": "passed"}))


def apply_or_verify(apply):
    plan, progress, manifest = inputs()
    report_path = HERE / "preflight.json"
    report = json.loads(report_path.read_text())
    require(report["planSha256"] == digest(HERE / "adjudicated-plan.json") and
            report["firstPassProgressSha256"] == plan["firstPassProgressSha256"] and
            report["virtualPreserveExact"] == "passed", "Preflight changed")
    for item in report["files"]:
        path = ROOT / item["path"]
        staged = ROOT / item["stagedPath"]
        data = staged.read_bytes()
        require(sha(data) == item["afterSha256"], "Staged output changed: " + item["path"])
        current = digest(path) if path.exists() else None
        require(current in (item["beforeSha256"], item["afterSha256"]),
                "Output differs from both pinned states: " + item["path"])
        if apply and current != item["afterSha256"]:
            atomic_write(path, data)
        if not apply:
            require(current == item["afterSha256"], "Output not applied: " + item["path"])
    if apply:
        print(json.dumps({"appliedFiles": len(report["files"]),
                          "boundary": report["applicationBoundary"]}))
    else:
        require(all(digest(ROOT / x["path"]) == x["afterSha256"] for x in report["files"]),
                "Output verification failed")
        print(json.dumps({"verifiedFiles": len(report["files"]), "changedIds": 118}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "apply", "verify"))
    mode = parser.parse_args().mode
    if mode == "prepare":
        prepare()
    else:
        apply_or_verify(mode == "apply")
