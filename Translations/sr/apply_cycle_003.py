#!/usr/bin/env python3
"""Apply or verify the pinned Serbian cycle 003 full-unit correction."""

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SR = ROOT / "Translations/sr"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    plan_path = SR / "semantic-cycle-003-adjudication.json"
    plan = json.loads(plan_path.read_text())
    previous = json.loads((SR / "semantic-cycle-002-corrections.json").read_text())
    require(plan["priorAuthoredFileSetSha256"] == previous["currentAuthoredFileSetSha256"]
            and len(plan["entries"]) == 1, "Correction boundary differs")
    entry = plan["entries"][0]
    path = ROOT / entry["targetFile"]
    require(path.is_relative_to(SR) and path.exists(), "Target path outside locale")
    old_hash = next(row["sha256"] for row in previous["currentAuthoredFileHashes"]
                    if row["path"] == entry["targetFile"])
    raw = path.read_text()
    old_literal = json.dumps(entry["currentTarget"], ensure_ascii=False)
    new_literal = json.dumps(entry["acceptedTarget"], ensure_ascii=False)
    old_count, new_count = raw.count(old_literal), raw.count(new_literal)
    require((old_count, new_count) in ((1, 0), (0, 1)),
            "Ambiguous old/new target state")
    if old_count:
        require(digest(path) == old_hash and args.write,
                "Unapplied correction or prior bytes changed")
        replacement = raw.replace(old_literal, new_literal, 1)
        before = json.loads(raw)
        after = json.loads(replacement)
        identifier = int(entry["stableId"].rsplit(":", 1)[1])
        old_entry = next(x for x in before["entries"] if x["id"] == identifier)
        new_entry = next(x for x in after["entries"] if x["id"] == identifier)
        require(old_entry["target"] == entry["currentTarget"] and
                new_entry["target"] == entry["acceptedTarget"], "Target ID differs")
        new_entry["target"] = entry["currentTarget"]
        require(before == after, "Other parsed values changed")
        descriptor, temp_name = tempfile.mkstemp(prefix=".cycle-003-", suffix=".json",
                                                  dir=path.parent)
        try:
            with os.fdopen(descriptor, "w") as handle:
                handle.write(replacement)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
    final = json.loads(path.read_text())
    found = next(x for x in final["entries"] if x["id"] ==
                 int(entry["stableId"].rsplit(":", 1)[1]))
    require(found["target"] == entry["acceptedTarget"], "Postcondition differs")
    print(json.dumps({"result": "applied" if old_count else "verified",
                      "changedIds": 1, "changedFiles": 1,
                      "priorSha256": old_hash, "currentSha256": digest(path)},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
