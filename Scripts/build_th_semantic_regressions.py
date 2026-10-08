#!/usr/bin/env python3
"""Pin high-risk source IDs for repeated Thai editorial regression review."""

import hashlib
import json
import re

from probe_assets import ROOT, digest, require


PAIRED = ROOT / "outputs/th-semantic-audit-input-v3/paired.jsonl"
OUTPUT = ROOT / "Documentation/th-semantic-regressions-v1.json"
SPECS = {
    "uiAndSystem": {"reason": "Menus, language selection, save/load, HUD and labels.",
                    "predicate": lambda row: row["collection"] == "UI"},
    "serializedDisplayFields": {"reason": "Static labels, credits and potentially unbound text.",
                                "predicate": lambda row: row["stableId"].startswith("tmp:")},
    "familyAndIdentity": {"reason": "Kinship, gender, hidden identity and address.",
                          "sourceRegex": r"(?iu)(сестр|брат|матер|мать|мам|отец|пап|доч|сын|ж[её]н|муж|бабуш|дедуш|девуш|парен|женщин|мужчин|\b(?:он|она|его|её|ее|ему|ей|им|них|ними)\b)"},
    "guestAndHuman": {"reason": "World terms, person-versus-object status and reveal timing.",
                      "sourceRegex": r"(?iu)(гост[ьи]|человек|люд[ией]|нечеловек|фема|FEMA|визит[её]р)"},
    "profanityAndWordplay": {"reason": "Preserve vulgarity, humor and recurring insults.",
                             "sourceRegex": r"(?iu)(бля|нахуй|нахер|ху[йяеюи]|говн|жоп|пизд|[её]б|долбо|сука|шутк|смешн)"},
    "formatAndMarkup": {"reason": "Numbered format slots and TMP rich text.",
                        "sourceRegex": r"\{[0-9]+\}|<[^<>]+>"},
    "inputAndLocale": {"reason": "Controller prompts and locale selection or names.",
                       "predicate": lambda row: row["collection"] == "UI" and
                       bool(re.search(r"(?i)(control|language|locale|key|button|fullscreen)",
                                      row["key"] or ""))},
    "credits": {"reason": "Names, roles, tags and line breaks in final credits.",
                "predicate": lambda row: row["stableId"] == "tmp:level5:59:m_text"},
}


def main():
    require(not OUTPUT.exists(), "Preserve previous regression catalog")
    rows = [json.loads(line) for line in PAIRED.open()]
    require(len(rows) == 16538, "Paired source scope changed")
    groups = []
    for name, spec in SPECS.items():
        predicate = spec.get("predicate")
        pattern = re.compile(spec["sourceRegex"]) if "sourceRegex" in spec else None
        selected = [row["stableId"] for row in rows
                    if (predicate(row) if predicate else bool(pattern.search(row["source"]))) ]
        require(selected, "Empty mandatory regression group: " + name)
        canonical = "".join(stable_id + "\n" for stable_id in selected)
        groups.append({"name": name, "reason": spec["reason"],
                       "selector": spec.get("sourceRegex", "explicit predicate in pinned recipe"),
                       "count": len(selected),
                       "idsSha256": hashlib.sha256(canonical.encode()).hexdigest(),
                       "ids": selected})
    result = {"schemaVersion": 1, "gameVersion": "1.3.19", "locale": "th",
              "status": "mandatory editorial regressions; selection supplements full semantic read",
              "pairedSha256": digest(PAIRED), "idNewlineConvention": "UTF-8 LF, one stable ID per line",
              "groups": groups,
              "note": "Exact ID lists are pinned to the current source. Rebuild if source, inventory, selector or authored context changes; review dependencies by actual consumer topology, not literal matches alone."}
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(OUTPUT.relative_to(ROOT)),
                      "groups": {row["name"]: row["count"] for row in groups}}))


if __name__ == "__main__":
    main()
