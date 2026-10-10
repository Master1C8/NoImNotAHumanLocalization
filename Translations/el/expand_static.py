#!/usr/bin/env python3
"""Map authored Greek TMP wording to the pinned, accepted unbound source IDs."""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
INVENTORY = ROOT / "Source/localization-inventory-v3/static-text.jsonl"
SCOPE = ROOT / "Documentation/static-text-scope-v2.json"
GLOSSARY = ROOT / "Documentation/glossary-translations/el/layer.json"
CREDITS_ID = "tmp:level5:59:m_text"
ROLE_MAP = HERE / "credits-role-map.json"


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
            plan["sourceLocale"] == "ru" and plan["gameVersion"] == "1.3.19",
            "Unsupported plan")
    require(plan["sourceInventoryStaticSha256"] == digest(INVENTORY) and
            plan["staticScopeSha256"] == digest(SCOPE) and
            plan["glossaryFingerprint"] == digest(GLOSSARY), "Pinned input changed")
    scope = json.loads(SCOPE.read_text())
    rows = [row for row in scope["rows"] if row["source"] and
            (not row["localizedStringBindings"] or
             any(link["sourceStableId"] is None for link in row["localizedStringBindings"]))
            and row["stableId"] != CREDITS_ID]
    lexicon = {}
    for item in plan["lexicon"]:
        source = item["source"]
        require(source not in lexicon and isinstance(item["target"], str) and
                item["target"].strip() and isinstance(item["sourceRows"], int) and
                item["sourceRows"] > 0, "Duplicate or empty lexicon item")
        lexicon[source] = item
    counts = Counter(row["source"] for row in rows)
    require(counts == Counter({source: item["sourceRows"]
                               for source, item in lexicon.items()}),
            "Source coverage or counts changed")
    entries = [{"stableId": row["stableId"],
                "target": lexicon[row["source"]]["target"]} for row in rows]
    role_map = json.loads(ROLE_MAP.read_text())
    require(role_map["schemaVersion"] == 1 and
            role_map["stableId"] == CREDITS_ID and
            role_map["sourceInventoryStaticSha256"] == digest(INVENTORY),
            "Credits role map differs")
    replacements = {pair["source"]: pair["target"]
                    for pair in role_map["replacements"]}
    require(len(replacements) == len(role_map["replacements"]) and
            all(replacements.values()), "Invalid role map")
    credits_source = next(row["source"] for row in scope["rows"]
                          if row["stableId"] == CREDITS_ID)
    require(all(credits_source.count(phrase) for phrase in replacements),
            "Credits source role missing")
    pattern = re.compile("|".join(re.escape(phrase) for phrase in
                                  sorted(replacements, key=len, reverse=True)))
    credits_target = pattern.sub(lambda match: replacements[match.group()],
                                 credits_source)
    entries.append({"stableId": CREDITS_ID, "target": credits_target})
    draft = {"schemaVersion": 1, "gameVersion": "1.3.19", "sourceLocale": "ru",
             "locale": "el", "sourceInventoryStaticSha256": digest(INVENTORY),
             "glossaryFingerprint": digest(GLOSSARY),
             "staticScopeSha256": digest(SCOPE),
             "authoredMapSha256": digest(authored),
             "creditsRoleMapSha256": digest(ROLE_MAP),
             "status": "authored complete static TMP draft; editorial and runtime acceptance pending",
             "coverage": "all-nonempty-unbound-v2", "entries": entries}
    content = json.dumps(draft, ensure_ascii=False, indent=2) + "\n"
    if args.verify:
        require(output.read_text() == content, "Generated draft differs")
    else:
        output.write_text(content)
    print(json.dumps({"output": str(output.relative_to(ROOT)), "rows": len(entries),
                      "result": "verified" if args.verify else "written"}))


if __name__ == "__main__":
    main()
