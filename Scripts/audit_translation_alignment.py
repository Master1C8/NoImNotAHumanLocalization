#!/usr/bin/env python3
"""Flag implausible Thai draft lengths and print their neighboring stable IDs.

This is a triage aid. A clean result is not a semantic review.
"""

import argparse
import json
import re
from pathlib import Path

from probe_assets import ROOT, digest, require


BATCH_NAME = re.compile(r"(?:dialogue|ui|checks)-batch-\d{3}\.json")
PREFIX = re.compile(r"^[A-Za-z]+: ?")
CYRILLIC = re.compile(r"[А-Яа-яЁё]")


def suspicious(source, target):
    source = PREFIX.sub("", source)
    target = PREFIX.sub("", target)
    if len(source) < 35 or not CYRILLIC.search(source):
        return False
    ratio = len(target) / len(source)
    return ratio < 0.35 or ratio > 2.0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("locale")
    parser.add_argument("--context", type=int, default=4)
    args = parser.parse_args()
    require(args.context >= 0, "Context must be nonnegative")

    inventory = ROOT / "Source/localization-inventory-v3/strings.jsonl"
    scope = json.loads((ROOT / "Documentation/text-source-scope-v7.json").read_text())
    supplemental = {row["stableId"] for row in scope["selectedSupplementalStringRows"]}
    source = {}
    for line in inventory.open():
        row = json.loads(line)
        if row["collection"] in ("Dialogs", "UI") or row["stableId"] in supplemental:
            key = (row["collection"], int(row["stableId"].rsplit(":", 1)[1]))
            require(key not in source, "Duplicate source ID")
            source[key] = row["source"]

    root = ROOT / "Translations" / args.locale
    require(root.is_dir(), "Unknown locale directory")
    batches = sorted(path for path in root.glob("*batch-*.json") if BATCH_NAME.fullmatch(path.name))
    require(batches, "No authored batches")
    findings = []
    reviewed = set()
    for path in batches:
        batch = json.loads(path.read_text())
        collection = batch["collection"]
        entries = batch["entries"]
        for index, entry in enumerate(entries):
            key = (collection, entry["id"])
            require(key in source, "Batch ID is absent from source")
            require(key not in reviewed, "Duplicate authored ID")
            reviewed.add(key)
            if not suspicious(source[key], entry["target"]):
                continue
            neighbors = []
            for nearby in entries[max(0, index - args.context):index + args.context + 1]:
                nearby_key = (collection, nearby["id"])
                neighbors.append({"id": nearby["id"], "source": source[nearby_key],
                                  "target": nearby["target"]})
            findings.append({"batch": str(path.relative_to(ROOT)), "batchSha256": digest(path),
                             "id": entry["id"], "neighbors": neighbors})
    print(json.dumps({"locale": args.locale, "inventorySha256": digest(inventory),
                      "reviewedRows": len(reviewed), "outlierCount": len(findings),
                      "findings": findings}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
