#!/usr/bin/env python3
"""Apply or verify the immutable Serbian cycle 002 authored correction batch."""

import argparse
import hashlib
import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SR = ROOT / "Translations/sr"
PLAN = SR / "semantic-cycle-002-adjudication.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    plan = json.loads(PLAN.read_text())
    require(plan["status"].startswith("one accepted author correction batch") and
            len(plan["entries"]) == plan["changedIdsCount"] == 17,
            "Adjudication changed")
    grouped = defaultdict(list)
    for entry in plan["entries"]:
        grouped[entry["targetFile"]].append(entry)
    replacements = {}
    for name, entries in grouped.items():
        path = ROOT / name
        require(path.is_relative_to(SR) and path.exists(), "Unauthorized target path")
        document = json.loads(path.read_text())
        require(document["locale"] == "sr", "Wrong locale")
        indexed = {int(entry["id"]): entry for entry in document["entries"]}
        for entry in entries:
            identifier = int(entry["stableId"].rsplit(":", 1)[1])
            require(identifier in indexed, "Missing target ID")
            value = indexed[identifier]["target"]
            require(value in (entry["currentTarget"], entry["acceptedTarget"]),
                    "Unexpected current value: " + entry["stableId"])
            indexed[identifier]["target"] = entry["acceptedTarget"]
        encoded = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode()
        replacements[path] = encoded
    pending = [path for path, encoded in replacements.items() if path.read_bytes() != encoded]
    if pending:
        require(args.write, "Correction batch has unapplied authored files")
    for path in pending:
        descriptor, temp_name = tempfile.mkstemp(prefix=".cycle-002-", suffix=".json",
                                                  dir=path.parent)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(replacements[path])
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
    for path, encoded in replacements.items():
        require(path.read_bytes() == encoded, "Post-apply file differs")
    print(json.dumps({"status": "applied" if pending else "verified",
                      "changedIds": len(plan["entries"]), "changedFiles": len(replacements),
                      "writtenFiles": len(pending),
                      "fileHashes": [{"path": str(path.relative_to(ROOT)), "sha256": sha(path)}
                                     for path in sorted(replacements)]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
