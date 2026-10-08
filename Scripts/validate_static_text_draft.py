#!/usr/bin/env python3
"""Validate authored static TMP text against the pinned source inventory."""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from probe_assets import ROOT, digest, require


DIGITS = re.compile(r"\d+")
TOKEN = re.compile(r"\{[^{}]+\}|<[^<>]+>")
INVENTORY = ROOT / "Source/localization-inventory-v3/static-text.jsonl"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path)
    args = parser.parse_args()
    path = args.draft.resolve()
    require(path.is_relative_to(ROOT / "Translations"), "Draft must be in Translations")
    draft = json.loads(path.read_text())
    state = json.loads((ROOT / "Documentation/localization-state.json").read_text())
    require(draft["schemaVersion"] == 1 and draft["gameVersion"] == state["gameVersion"],
            "Game version changed")
    require(draft["sourceLocale"] == state["sourceLocale"], "Source locale changed")
    locale = draft["locale"]
    row = next((row for row in state["localeRows"] if row["locale"] == locale), None)
    require(row is not None and draft["glossaryFingerprint"] == row["glossaryFingerprint"],
            "Approved glossary changed")
    require(draft["sourceInventoryStaticSha256"] == digest(INVENTORY),
            "Static source inventory changed")
    source = {row["stableId"]: row for row in
              (json.loads(line) for line in INVENTORY.open())}
    seen = set()
    for entry in draft["entries"]:
        key = entry["stableId"]
        require(key in source and key not in seen, "Unknown or duplicate static text ID")
        seen.add(key)
        original = source[key]["source"]
        target = entry["target"]
        require(isinstance(original, str) and original.strip() and
                isinstance(target, str) and target.strip(), "Empty static text")
        require(Counter(DIGITS.findall(target)) == Counter(DIGITS.findall(original)),
                "Numeric value mismatch: " + key)
        require(Counter(TOKEN.findall(target)) == Counter(TOKEN.findall(original)),
                "Placeholder or markup mismatch: " + key)
        require(re.findall(r"\r\n|\r|\n", target) == re.findall(r"\r\n|\r|\n", original),
                "Line break mismatch: " + key)
        require(re.search(r"[ \t\r\n]*$", target).group() ==
                re.search(r"[ \t\r\n]*$", original).group(),
                "Trailing whitespace mismatch: " + key)
    coverage = draft.get("coverage")
    require(coverage in ("partial-unbound-v2", "all-nonempty-unbound-v2"),
            "Unknown static draft coverage contract")
    scope_path = ROOT / "Documentation/static-text-scope-v2.json"
    require(draft["staticScopeSha256"] == digest(scope_path),
            "Static text scope audit changed")
    scope = json.loads(scope_path.read_text())
    require(scope["staticInventorySha256"] == digest(INVENTORY),
            "Static scope source inventory changed")
    expected = {row["stableId"] for row in scope["rows"]
                if row["source"] and
                (not row["localizedStringBindings"] or
                 any(link["sourceStableId"] is None
                     for link in row["localizedStringBindings"]))}
    require(seen <= expected, "Static draft contains a table-bound source field")
    if coverage == "all-nonempty-unbound-v2":
        require(seen == expected,
                "Static draft must cover every nonempty unbound TMP source row")
    credits_id = "tmp:level5:59:m_text"
    if credits_id in seen:
        credits_map = ROOT / "Translations" / locale / "credits-role-map.json"
        require(credits_map.exists(), "Missing authored credits role map")
        role_map = json.loads(credits_map.read_text())
        require(role_map["schemaVersion"] == 1 and
                role_map["stableId"] == credits_id and
                role_map["sourceInventoryStaticSha256"] == digest(INVENTORY),
                "Credits role map source changed")
        pairs = role_map["replacements"]
        replacements = {pair["source"]: pair["target"] for pair in pairs}
        require(len(replacements) == len(pairs) and all(replacements.values()),
                "Duplicate or empty credits role translation")
        original = source[credits_id]["source"]
        require(all(original.count(phrase) for phrase in replacements),
                "Credits role phrase absent from source")
        role_pattern = re.compile("|".join(re.escape(phrase)
                                           for phrase in sorted(replacements, key=len,
                                                                reverse=True)))
        regenerated = role_pattern.sub(lambda match: replacements[match.group()], original)
        target = next(entry["target"] for entry in draft["entries"]
                      if entry["stableId"] == credits_id)
        require(regenerated == target, "Credits target differs from authored role map")
    report = {"schemaVersion": 1, "draft": str(path.relative_to(ROOT)),
              "draftSha256": digest(path), "sourceInventoryStaticSha256": digest(INVENTORY),
              "locale": locale, "rows": len(seen), "candidateRows": len(expected),
              "coverage": coverage,
              "structuralResult": "passed",
              "semanticReview": "pending", "rendererAndRuntime": "not-run"}
    path.with_suffix(".validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
