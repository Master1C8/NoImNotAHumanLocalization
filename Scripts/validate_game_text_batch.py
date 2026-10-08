#!/usr/bin/env python3
"""Check one authored game-text batch against the shared source inventory."""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from probe_assets import ROOT, digest, require


TOKEN = re.compile(r"\{[^{}]+\}|<[^<>]+>")
DIGITS = re.compile(r"\d+")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    args = parser.parse_args()
    path = args.batch.resolve()
    require(path.is_relative_to(ROOT / "Translations"), "Batch must be in canonical Translations directory")
    batch = json.loads(path.read_text())
    state = json.loads((ROOT / "Documentation/localization-state.json").read_text())
    inventory = json.loads((ROOT / "Documentation/localization-source-inventory-v3.json").read_text())
    require(batch["schemaVersion"] == 1 and batch["gameVersion"] == state["gameVersion"], "Batch version mismatch")
    require(batch["sourceLocale"] == state["sourceLocale"], "Source locale mismatch")
    locale = batch["locale"]
    require(locale in state["targetLocales"], "Unknown target locale")
    row = next(row for row in state["localeRows"] if row["locale"] == locale)
    require(batch["glossaryFingerprint"] == row["glossaryFingerprint"], "Approved glossary differs")
    require(batch["sourceInventorySha256"] == inventory["outputs"]["strings.jsonl"], "Source inventory differs")

    source = []
    for line in (ROOT / "Source/localization-inventory-v3/strings.jsonl").open():
        record = json.loads(line)
        if record["collection"] == batch["collection"]:
            source.append(record)
    by_id = {int(record["stableId"].rsplit(":", 1)[1]): record for record in source}
    source_positions = {identifier: index for index, identifier in enumerate(by_id)}
    require(len(by_id) == len(source), "Duplicate source ID in collection")
    seen = set()
    source_order = []
    for entry in batch["entries"]:
        identifier = entry["id"]
        require(isinstance(identifier, int) and identifier in by_id, "Unknown source ID")
        require(identifier not in seen, "Duplicate authored ID")
        seen.add(identifier)
        source_order.append(source_positions[identifier])
        target = entry["target"]
        require(isinstance(target, str) and target.strip(), "Empty target text")
        original = by_id[identifier]["source"]
        exact = Counter(span["value"] for span in by_id[identifier]["exactSpans"] if span["reason"] == "Runtime placeholder or markup")
        require(Counter(TOKEN.findall(target)) == exact, "Protected placeholder or markup mismatch: " + str(identifier))
        prefixes = [span["value"] for span in by_id[identifier]["exactSpans"] if span["reason"] == "Yarn speaker/service prefix"]
        require(not prefixes or target.startswith(prefixes[0]), "Speaker/service prefix mismatch: " + str(identifier))
        require(Counter(DIGITS.findall(target)) == Counter(DIGITS.findall(original)), "Numeric value mismatch: " + str(identifier))
        require(re.findall(r"\r\n|\r|\n", target) == re.findall(r"\r\n|\r|\n", original),
                "Line break mismatch: " + str(identifier))
        require(re.search(r"[ \t\r\n]*$", target).group() == re.search(r"[ \t\r\n]*$", original).group(),
                "Trailing whitespace mismatch: " + str(identifier))
    require(source_order == sorted(source_order), "Authored entries are out of source order")
    report = {
        "schemaVersion": 1,
        "batch": str(path.relative_to(ROOT)),
        "batchSha256": digest(path),
        "locale": locale,
        "collection": batch["collection"],
        "authoredRows": len(seen),
        "sourceCollectionRows": len(source),
        "structuralResult": "passed",
        "semanticReview": "pending",
        "rendererAndRuntime": "not-run",
    }
    sidecar = path.with_suffix(".validation.json")
    sidecar.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
