#!/usr/bin/env python3
"""Transfer authored Greek lines to stable dialogue IDs in one pinned source range."""

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / "Source/localization-inventory-v3/strings.jsonl"
GLOSSARY = ROOT / "Documentation/glossary-translations/el/layer.json"


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
    authored = args.authored.resolve()
    output = args.output.resolve()
    require(authored.parent == HERE and output.parent == HERE, "Greek files only")
    require(authored.exists() and output.exists() == args.verify, "Output state differs")
    plan = json.loads(authored.read_text())
    require(plan["schemaVersion"] == 1 and plan["locale"] == "el" and
            plan["sourceLocale"] == "ru" and plan["gameVersion"] == "1.3.19" and
            plan["collection"] == "Dialogs", "Unsupported batch")
    require(plan["sourceInventorySha256"] == digest(SOURCE), "Source changed")
    require(plan["glossaryFingerprint"] == digest(GLOSSARY), "Glossary changed")
    rows = [json.loads(line) for line in SOURCE.open() if '"collection":"Dialogs"' in line]
    start, end = plan["startIndex"], plan["endIndex"]
    require(isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(rows),
            "Invalid source range")
    prior = set()
    for path in HERE.glob("dialogue-batch-[0-9][0-9][0-9].json"):
        if path == output:
            continue
        batch = json.loads(path.read_text())
        require(batch["locale"] == "el" and
                batch["sourceInventorySha256"] == plan["sourceInventorySha256"],
                "Prior batch differs")
        for entry in batch["entries"]:
            require(entry["id"] not in prior, "Prior batches overlap")
            prior.add(entry["id"])
    expected = {index for index in range(start, end)
                if int(rows[index]["stableId"].rsplit(":", 1)[1]) not in prior}
    targets = {}
    for item in plan["targets"]:
        index, target = item
        require(isinstance(index, int) and index in expected and index not in targets,
                "Unknown, covered, or duplicate source index")
        require(isinstance(target, str) and target.strip(), "Empty target")
        targets[index] = target
    require(set(targets) == expected, "Uncovered source index in range")
    entries = [{"id": int(rows[index]["stableId"].rsplit(":", 1)[1]),
                "target": targets[index]} for index in sorted(targets)]
    batch = {"schemaVersion": 1, "locale": "el", "sourceLocale": "ru",
             "gameVersion": "1.3.19", "collection": "Dialogs",
             "sourceInventorySha256": plan["sourceInventorySha256"],
             "glossaryFingerprint": plan["glossaryFingerprint"],
             "authoredMapSha256": digest(authored),
             "status": "authored-draft; editorial and runtime acceptance pending",
             "entries": entries}
    content = json.dumps(batch, ensure_ascii=False, indent=2) + "\n"
    if args.verify:
        require(output.read_text() == content, "Generated batch differs")
    else:
        output.write_text(content)
    print(json.dumps({"output": str(output.relative_to(ROOT)), "sourceRange": [start, end],
                      "rows": len(entries), "result": "verified" if args.verify else "written"}))


if __name__ == "__main__":
    main()
