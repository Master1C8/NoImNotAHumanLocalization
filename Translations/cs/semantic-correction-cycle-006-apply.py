#!/usr/bin/env python3
"""Apply the preflighted Czech cycle-006 full-unit replacements, safely resumable."""

import hashlib
import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BEFORE = HERE / "semantic-correction-cycle-006-before.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    evidence = json.loads(BEFORE.read_text())
    assert evidence["changedCount"] == len(evidence["rows"]) == 4
    groups = defaultdict(list)
    for row in evidence["rows"]:
        groups[row["authoredFile"]].append(row)
    pending = []
    for relative, rows in groups.items():
        path = ROOT / relative
        batch = json.loads(path.read_text())
        entries = {str(entry["id"]): entry for entry in batch["entries"]}
        states = []
        for row in rows:
            value = entries[row["stableId"].rsplit(":", 1)[1]]["target"]
            assert value in (row["before"], row["after"]), row["stableId"]
            states.append(value == row["after"])
        assert len(set(states)) == 1, f"Mixed state within {relative}"
        if states[0]:
            continue
        assert digest(path) == evidence["allAuthoredFileHashesBefore"][relative], relative
        for row in rows:
            entries[row["stableId"].rsplit(":", 1)[1]]["target"] = row["after"]
        pending.append((path, json.dumps(batch, ensure_ascii=False, indent=2) + "\n"))
    # All files and values are checked before the first replacement. A later
    # interruption can resume: each file must be wholly before or wholly after.
    for path, value in pending:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix=".cs-cycle-006-", delete=False) as temp:
            temp.write(value)
            temporary = Path(temp.name)
        os.replace(temporary, path)
    for relative, rows in groups.items():
        batch = json.loads((ROOT / relative).read_text())
        entries = {str(entry["id"]): entry for entry in batch["entries"]}
        for row in rows:
            assert entries[row["stableId"].rsplit(":", 1)[1]]["target"] == row["after"]
    print(json.dumps({"changedRows": 4, "changedFiles": len(groups),
                      "newlyWrittenFiles": len(pending)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
