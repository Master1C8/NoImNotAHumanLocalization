#!/usr/bin/env python3
"""Expand model-authored, context-stable phrases to exact source IDs.

This transfers supplied target wording only. It never creates or edits translations.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from probe_assets import ROOT, digest, require


SOURCE = ROOT / "Source/localization-inventory-v3/strings.jsonl"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("authored", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--verify", action="store_true", help="Compare the existing batch without writing")
    args = parser.parse_args()
    authored = args.authored.resolve()
    output = args.output.resolve()
    require(authored.is_file() and authored.is_relative_to(ROOT / "Translations"),
            "Authored map must be in Translations")
    require(output.parent == authored.parent and output.exists() == args.verify,
            "Output must be new for generation or existing for verification")
    plan = json.loads(authored.read_text())
    locale = plan["locale"]
    require(authored.parent.name == locale, "Locale directory mismatch")
    require(plan["schemaVersion"] == 1 and plan["sourceLocale"] == "ru" and
            plan["gameVersion"] == "1.3.19" and plan["collection"] == "Dialogs",
            "Unsupported source or collection")
    require(digest(SOURCE) == plan["sourceInventorySha256"], "Source inventory changed")
    glossary = ROOT / "Documentation/glossary-translations" / locale / "layer.json"
    require(digest(glossary) == plan["glossaryFingerprint"], "Glossary changed")
    glossary_terms = json.loads(glossary.read_text())

    phrases = {}
    for item in plan["phrases"]:
        source, target = item["source"], item["target"]
        require(isinstance(source, str) and source and source not in phrases,
                "Duplicate or empty authored source phrase")
        require(isinstance(target, str) and target.strip() and
                isinstance(item["expectedRows"], int) and item["expectedRows"] > 0,
                "Incomplete authored phrase")
        if "glossaryId" in item:
            term = glossary_terms[item["glossaryId"]]["term"]
            require(target in term or term in target,
                    "Target and approved glossary term differ: " + source)
        phrases[source] = item

    prior_ids = set()
    for path in authored.parent.glob("*-batch-???.json"):
        if path == output:
            continue
        batch = json.loads(path.read_text())
        if batch.get("collection") != plan["collection"]:
            continue
        require(batch["sourceInventorySha256"] == plan["sourceInventorySha256"],
                "Existing batch uses another source inventory")
        for entry in batch["entries"]:
            require(entry["id"] not in prior_ids, "Existing batches overlap")
            prior_ids.add(entry["id"])

    counts = Counter()
    entries = []
    selected_ids = set()
    remaining_only = plan.get("remainingOnly", False)
    require(isinstance(remaining_only, bool), "remainingOnly must be boolean")
    for line in SOURCE.open():
        row = json.loads(line)
        if row["collection"] != plan["collection"] or row["source"] not in phrases:
            continue
        identifier = int(row["stableId"].rsplit(":", 1)[1])
        if remaining_only and identifier in prior_ids:
            continue
        require(not row["exactSpans"], "Authored phrase has protected spans")
        require(identifier not in prior_ids and identifier not in selected_ids,
                "Authored phrase overlaps another batch or repeats an ID")
        selected_ids.add(identifier)
        counts[row["source"]] += 1
        entries.append({"id": identifier, "target": phrases[row["source"]]["target"]})

    for source, item in phrases.items():
        require(counts[source] == item["expectedRows"],
                "Source phrase count changed: " + source)
    require(entries, "No matching source rows")
    batch = {
        "schemaVersion": 1,
        "locale": locale,
        "sourceLocale": plan["sourceLocale"],
        "gameVersion": plan["gameVersion"],
        "collection": plan["collection"],
        "sourceInventorySha256": plan["sourceInventorySha256"],
        "glossaryFingerprint": plan["glossaryFingerprint"],
        "authoredMapSha256": digest(authored),
        "status": "authored-draft; editorial and runtime acceptance pending",
        "entries": entries,
    }
    expected = json.dumps(batch, ensure_ascii=False, indent=2) + "\n"
    if args.verify:
        require(output.read_text() == expected, "Generated batch differs from authored map")
    else:
        output.write_text(expected)
    print(json.dumps({"output": str(output.relative_to(ROOT)), "rows": len(entries),
                      "phrases": dict(counts), "result": "verified" if args.verify else "written"},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
