#!/usr/bin/env python3
"""Reproduce the Serbian static text draft from its two authored maps."""

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCALE = ROOT / "Translations" / "sr"
SOURCE = ROOT / "Source" / "localization-inventory-v3" / "static-text.jsonl"
SCOPE = ROOT / "Documentation" / "static-text-scope-v2.json"
GLOSSARY = ROOT / "Documentation" / "glossary-translations" / "sr" / "layer.json"
PHRASES = LOCALE / "static-authored-map.json"
CREDITS = LOCALE / "credits-role-map.json"
DRAFT = LOCALE / "static-text-draft.json"
CREDITS_ID = "tmp:level5:59:m_text"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text())


def require(condition: bool, message: str):
    if not condition:
        raise ValueError(message)


def credits_target(source: str, role_map: dict) -> str:
    pairs = role_map["replacements"]
    replacements = {pair["source"]: pair["target"] for pair in pairs}
    require(len(replacements) == len(pairs) and all(replacements.values()),
            "Duplicate or empty credits role translation")
    require(all(source.count(phrase) for phrase in replacements),
            "Credits role phrase absent from source")
    pattern = re.compile("|".join(re.escape(phrase) for phrase in
                                  sorted(replacements, key=len, reverse=True)))
    return pattern.sub(lambda match: replacements[match.group()], source)


def reproduce():
    draft = read(DRAFT)
    phrases_map = read(PHRASES)
    role_map = read(CREDITS)
    scope = read(SCOPE)
    source = {row["stableId"]: row["source"] for row in
              (json.loads(line) for line in SOURCE.open())}
    require(len(source) == sum(1 for _ in SOURCE.open()), "Duplicate static source ID")
    require(scope["staticInventorySha256"] == digest(SOURCE), "Static scope changed")
    require(phrases_map["sourceInventoryStaticSha256"] == digest(SOURCE),
            "Authored phrase map source changed")
    require(role_map["sourceInventoryStaticSha256"] == digest(SOURCE),
            "Authored credits map source changed")
    require(draft["sourceInventoryStaticSha256"] == digest(SOURCE) and
            draft["staticScopeSha256"] == digest(SCOPE) and
            draft["glossaryFingerprint"] == digest(GLOSSARY),
            "Draft input binding changed")
    phrases = {item["source"]: item["target"] for item in phrases_map["phrases"]}
    require(len(phrases) == len(phrases_map["phrases"]) and all(phrases.values()),
            "Duplicate or empty authored phrase")
    selected = [row["stableId"] for row in scope["rows"]
                if row["source"] and
                (not row["localizedStringBindings"] or
                 any(link["sourceStableId"] is None for link in
                     row["localizedStringBindings"]))]
    require(len(selected) == 178 and role_map["stableId"] == CREDITS_ID,
            "Static selection or credits ID changed")
    entries = []
    used_phrases = set()
    for stable_id in selected:
        original = source[stable_id]
        if stable_id == CREDITS_ID:
            target = credits_target(original, role_map)
        else:
            require(original in phrases, "Missing authored phrase: " + stable_id)
            target = phrases[original]
            used_phrases.add(original)
        entries.append({"stableId": stable_id, "target": target})
    require(used_phrases == set(phrases), "Unused authored static phrase")
    require(draft["entries"] == entries, "Current static wording differs from authored maps")
    draft["authoredMapSha256"] = digest(PHRASES)
    draft["creditsRoleMapSha256"] = digest(CREDITS)
    return json.dumps(draft, ensure_ascii=False, indent=2) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Refresh map fingerprints in the draft")
    args = parser.parse_args()
    expected = reproduce()
    if args.write:
        DRAFT.write_text(expected)
    else:
        require(DRAFT.read_text() == expected, "Static draft differs from authored-map regeneration")
    print(json.dumps({"result": "written" if args.write else "verified",
                      "draftSha256": digest(DRAFT), "authoredMapSha256": digest(PHRASES),
                      "creditsRoleMapSha256": digest(CREDITS)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
