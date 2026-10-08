#!/usr/bin/env python3
"""Build a conservative, shared localization inventory from pinned Russian assets.

This inventories candidates. It does not decide scene reachability or authorize
translation before the remaining source and renderer gates are resolved.
"""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from probe_assets import DEFAULT_GAME, ROOT, digest, require


SOURCE = ROOT / "Source/glossary-corpus-v2"
TEXT_PATHS = ROOT / "outputs/text-path-audit-v2/report.json"
DEFAULT_OUTPUT = ROOT / "Source/localization-inventory-v3"
SUMMARY = ROOT / "Documentation/localization-source-inventory-v3.json"
SPEAKER = re.compile(r"^([A-Za-z][A-Za-z0-9_]*:)(\s+)")
PLACEHOLDER = re.compile(r"\{[^{}]+\}|<[^<>]+>")


def encoded(record):
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT / "Source"), "Output must remain in canonical Source directory")
    require(not output.exists(), "Inventory output already exists; preserve prior version")
    state = json.loads((ROOT / "Documentation/localization-state.json").read_text())
    report = json.loads((SOURCE / "report.json").read_text())
    require(state["gameVersion"] == "1.3.19" and state["sourceLocale"] == "ru", "Source version changed")
    require(digest(SOURCE / "strings.jsonl") == report["corpusSha256"], "Corpus differs from its receipt")
    for relative, expected in report["sourcePins"].items():
        actual = DEFAULT_GAME / relative
        require(actual.is_file() and digest(actual) == expected, "Source input changed: " + relative)

    records = []
    seen = set()
    collections = Counter()
    protected_count = 0
    for line in (SOURCE / "strings.jsonl").open():
        row = json.loads(line)
        identity = (row["guid"], row["id"])
        require(identity not in seen, "Duplicate source table identity")
        seen.add(identity)
        text = row["text"]
        require(isinstance(text, str) and text.strip(), "Empty source text")
        prefix = SPEAKER.match(text)
        exact = []
        if prefix:
            exact.append({"span": [0, prefix.end()], "value": prefix.group(), "reason": "Yarn speaker/service prefix"})
        for match in PLACEHOLDER.finditer(text):
            exact.append({"span": [match.start(), match.end()], "value": match.group(), "reason": "Runtime placeholder or markup"})
        protected_count += len(exact)
        record = {
            "stableId": f"string:{row['guid']}:{row['id']}",
            "surface": "Unity Localization string table",
            "collection": row["collection"],
            "tablePathId": row["tablePathId"],
            "key": row["key"],
            "source": text,
            "sourceSha256": hashlib.sha256(text.encode()).hexdigest(),
            "exactSpans": exact,
            "nodeNames": [item["nodeName"] for item in row["yarnMetadata"] if "nodeName" in item],
            "candidateStatus": "source candidate; active reachability unverified",
        }
        records.append(record)
        collections[row["collection"]] += 1
    require(len(records) == report["records"], "Corpus row count changed")

    text_audit = json.loads(TEXT_PATHS.read_text())
    require(text_audit["gameVersion"] == state["gameVersion"] and
            text_audit["count"] == len(text_audit["rows"]) == 244,
            "Text-path audit count or version changed")
    for relative, expected in text_audit["sourceFiles"].items():
        require(digest(DEFAULT_GAME / relative) == expected,
                "Static text source input changed: " + relative)
    static = text_audit["rows"]
    static_records = []
    static_seen = set()
    for row in static:
        require(row["class"] in ("RTLTextMeshPro", "TextMeshProUGUI"),
                "Unclassified text-bearing component")
        identity = (row["file"], row["id"])
        require(identity not in static_seen, "Duplicate static text identity")
        static_seen.add(identity)
        value = row.get("fields", {}).get("m_text")
        require(isinstance(value, str), "TMP component lacks serialized text")
        static_records.append({
            "stableId": f"tmp:{row['file']}:{row['id']}:m_text",
            "surface": "TextMeshPro serialized field",
            "source": value,
            "candidateStatus": "needs source-role classification",
        })
    require(len(static_records) == 244, "TMP object count changed")

    output.mkdir(parents=True)
    files = {
        "strings.jsonl": records,
        "static-text.jsonl": static_records,
    }
    for name, rows in files.items():
        (output / name).write_text("".join(encoded(row) for row in rows))
    summary = {
        "schemaVersion": 1,
        "gameVersion": state["gameVersion"],
        "sourceLocale": "ru",
        "status": "candidate inventory; source gate incomplete",
        "localizationScope": "String-table and serialized TMP text only. Owner excluded textures and images.",
        "corpusReportSha256": digest(SOURCE / "report.json"),
        "sourcePins": report["sourcePins"],
        "staticTextSourcePins": text_audit["sourceFiles"],
        "inputs": {
            "textPathAuditSha256": digest(TEXT_PATHS),
        },
        "counts": {
            "stringRows": len(records),
            "stringCollections": dict(sorted(collections.items())),
            "protectedStringSpans": protected_count,
            "staticTextObjects": len(static_records),
        },
        "outputs": {name: digest(output / name) for name in files},
        "remaining": [
            "Classify visible versus technical or unused strings and static text.",
            "Verify full source-to-inventory and preserve-exactly comparison before translation.",
            "Shared renderer feasibility remains unverified for dialogue and dense UI.",
        ],
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    if SUMMARY.exists():
        require(json.loads(SUMMARY.read_text()) == summary, "Generated summary differs from tracked source inventory")
    else:
        SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"counts": summary["counts"], "status": summary["status"]}))


if __name__ == "__main__":
    main()
