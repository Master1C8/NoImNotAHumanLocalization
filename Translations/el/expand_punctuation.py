#!/usr/bin/env python3
"""Expand pinned, untranslated speaker pause marks into Greek dialogue IDs."""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / "Source/localization-inventory-v3/strings.jsonl"
GLOSSARY = ROOT / "Documentation/glossary-translations/el/layer.json"
PAUSE = re.compile(r"[A-Za-z0-9]+: (?:…|\.\.\.)\Z")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("authored", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    authored, output = args.authored.resolve(), args.output.resolve()
    require(authored.parent == HERE and output.parent == HERE, "Greek files only")
    require(authored.is_file() and output.exists() == args.verify, "Output state differs")
    plan = json.loads(authored.read_text())
    require(plan["schemaVersion"] == 1 and plan["locale"] == "el" and
            plan["sourceLocale"] == "ru" and plan["gameVersion"] == "1.3.19" and
            plan["collection"] == "Dialogs" and plan["remainingOnly"] is True,
            "Unsupported plan")
    require(plan["sourceInventorySha256"] == digest(SOURCE) and
            plan["glossaryFingerprint"] == digest(GLOSSARY), "Pinned input changed")
    phrases = {}
    for item in plan["phrases"]:
        source = item["source"]
        require(source not in phrases and PAUSE.fullmatch(source) and
                item["target"] == source and
                isinstance(item["expectedRows"], int) and item["expectedRows"] > 0,
                "Non-punctuation or duplicate plan item")
        phrases[source] = item["expectedRows"]
    prior = set()
    for path in HERE.glob("dialogue-batch-[0-9][0-9][0-9].json"):
        if path == output:
            continue
        batch = json.loads(path.read_text())
        require(batch["sourceInventorySha256"] == plan["sourceInventorySha256"],
                "Prior source differs")
        for entry in batch["entries"]:
            require(entry["id"] not in prior, "Prior batches overlap")
            prior.add(entry["id"])
    counts, entries = Counter(), []
    for line in SOURCE.open():
        row = json.loads(line)
        if row["collection"] != "Dialogs" or row["source"] not in phrases:
            continue
        identifier = int(row["stableId"].rsplit(":", 1)[1])
        if identifier in prior:
            continue
        require(all(span["reason"] == "Yarn speaker/service prefix" and
                    row["source"].startswith(span["value"])
                    for span in row["exactSpans"]), "Unexpected protected span")
        counts[row["source"]] += 1
        entries.append({"id": identifier, "target": row["source"]})
    require(dict(counts) == phrases and entries, "Source count changed")
    batch = {"schemaVersion": 1, "locale": "el", "sourceLocale": "ru",
             "gameVersion": "1.3.19", "collection": "Dialogs",
             "sourceInventorySha256": plan["sourceInventorySha256"],
             "glossaryFingerprint": plan["glossaryFingerprint"],
             "authoredMapSha256": digest(authored),
             "status": "exact punctuation passthrough; editorial and runtime acceptance pending",
             "entries": entries}
    content = json.dumps(batch, ensure_ascii=False, indent=2) + "\n"
    if args.verify:
        require(output.read_text() == content, "Generated batch differs")
    else:
        output.write_text(content)
    print(json.dumps({"output": str(output.relative_to(ROOT)), "rows": len(entries),
                      "result": "verified" if args.verify else "written"}))


if __name__ == "__main__":
    main()
