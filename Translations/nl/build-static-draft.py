#!/usr/bin/env python3
"""Rebuild the Dutch static TMP draft from authored Dutch text and credits roles."""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / "Source/localization-inventory-v3/static-text.jsonl"
SCOPE = ROOT / "Documentation/static-text-scope-v2.json"
GLOSSARY = ROOT / "Documentation/glossary-translations/nl/layer.json"
CREDITS_ID = "tmp:level5:59:m_text"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = {r["stableId"]: r["source"] for r in
              (json.loads(line) for line in SOURCE.open())}
    scope = json.loads(SCOPE.read_text())
    assert scope["staticInventorySha256"] == digest(SOURCE)
    selected = [r["stableId"] for r in scope["rows"] if r["source"] and
                (not r["localizedStringBindings"] or
                 any(link["sourceStableId"] is None
                     for link in r["localizedStringBindings"]))]
    phrases = json.loads((HERE / "static-text-map.json").read_text())
    assert set(phrases) == {source[key] for key in selected if key != CREDITS_ID}
    role_map = json.loads((HERE / "credits-role-map.json").read_text())
    assert (role_map["schemaVersion"] == 1 and
            role_map["stableId"] == CREDITS_ID and
            role_map["sourceInventoryStaticSha256"] == digest(SOURCE))
    pairs = role_map["replacements"]
    roles = {pair["source"]: pair["target"] for pair in pairs}
    assert len(roles) == len(pairs) and all(roles.values())
    original_credits = source[CREDITS_ID]
    assert all(original_credits.count(phrase) for phrase in roles)
    role_pattern = re.compile("|".join(re.escape(phrase) for phrase in
                                       sorted(roles, key=len, reverse=True)))
    credits = role_pattern.sub(lambda match: roles[match.group()], original_credits)
    entries = [{"stableId": key,
                "target": credits if key == CREDITS_ID else phrases[source[key]]}
               for key in selected]
    draft = {
        "schemaVersion": 1,
        "gameVersion": "1.3.19",
        "sourceLocale": "ru",
        "locale": "nl",
        "sourceInventoryStaticSha256": digest(SOURCE),
        "glossaryFingerprint": digest(GLOSSARY),
        "status": "authored complete static TMP draft; semantic and renderer/runtime acceptance pending",
        "coverage": "all-nonempty-unbound-v2",
        "staticScopeSha256": digest(SCOPE),
        "entries": entries,
    }
    path = HERE / "static-text-draft.json"
    path.write_text(json.dumps(draft, ensure_ascii=False, indent=2) + "\n")
    print(f"{path.relative_to(ROOT)}: {len(entries)} rows; credits role matches "
          f"{len(role_pattern.findall(original_credits))}")


if __name__ == "__main__":
    main()
