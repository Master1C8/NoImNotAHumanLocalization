#!/usr/bin/env python3
"""Validate model-authored rows and export one locale without generating wording."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("locale")
    parser.add_argument("--complete", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    state = json.loads((root / "Documentation/localization-state.json").read_text())
    if args.locale not in state["targetLocales"]:
        raise ValueError("Locale is outside the authorized target list")
    source = root / "Documentation/glossary-research/final-v1/glossary.json"
    expected = state["standaloneSourceGlossary"]["sourceFileSha256"]
    if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
        raise ValueError("Reviewed source bytes changed")
    entries = json.loads(source.read_text())["entries"]
    directory = root / "Documentation/glossary-translations" / args.locale
    rows = json.loads((directory / "authored.json").read_text())
    ids = [row[0] for row in rows]
    if ids != [entry["id"] for entry in entries[:len(rows)]]:
        raise ValueError("Authored IDs must be unique and match the source prefix in order")
    if len(rows) > len(entries) or any(len(row) != 3 for row in rows):
        raise ValueError("Invalid authored row shape/count")
    for row in rows:
        for value in row:
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Empty/non-string authored field")
            if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
                raise ValueError("Invalid Unicode surrogate")
    if args.complete and len(rows) != len(entries):
        raise ValueError("Complete export requires all source entries")
    layer = {row[0]: {"term": row[1], "meaning": row[2]} for row in rows}
    output = directory / "layer.json"
    output.write_text(json.dumps(layer, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"locale": args.locale, "entries": len(rows), "total": len(entries),
                      "sourceRawSha256": expected,
                      "layerRawSha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                      "complete": len(rows) == len(entries), "editorial": "not inferred"}))


if __name__ == "__main__":
    main()
