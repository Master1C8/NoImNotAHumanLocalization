#!/usr/bin/env python3
"""Assemble corrected occupied-room continuations over actual resident domains."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CYCLE = Path(__file__).resolve().parent
HE = CYCLE.parent
IR1 = HE / "independent-review-01"
IR2 = HE / "independent-review-02"

CASES = {"Greatmother_Entrance_Occupied": "Greatmother",
         "Fan_Entrance_Occupied": "Fan",
         "Luka_Entrance_Occupied": "Luka",
         "Nun_Entrance_Occupied": "Nun"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def once(path, obj):
    data = (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode()
    if path.exists():
        assert path.read_bytes() == data
    else:
        path.write_bytes(data)


def main():
    pins = json.loads((CYCLE / "input-pins.json").read_text())
    src = {r["key"]: r for r in map(json.loads, (ROOT / pins["sourceInventory"]["stringsPath"]).open())
           if r.get("key")}
    targets = {}
    for path in sorted(HE.glob("*-batch-[0-9][0-9][0-9].json")):
        staged = CYCLE / "after-authored" / path.name
        batch = json.loads((staged if staged.exists() else path).read_text())
        guid = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
                "UI": "0cbd8a7a4f543344bb95659de87f67a5",
                "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}[batch["collection"]]
        for row in batch["entries"]:
            sid = f"string:{guid}:{row['id']}"
            assert sid not in targets
            targets[sid] = row["target"]
    char_domain = json.loads((IR1 / "character-consumer-domain.json").read_text())
    by_char = {x["name"]: x for x in char_domain["characters"]}
    compiled = json.loads((IR2 / "compiled-scene-context.json").read_text())
    reports = []
    for node, caller in CASES.items():
        place = by_char[caller]["place"]
        residents = [x for x in char_domain["placeDomains"][str(place)] if x != caller]
        instructions = compiled["nodes"][node]
        line_keys = [x["operands"][0] for x in instructions if x["opcode"] == 2]
        assert len(line_keys) >= 2
        line_rows = [src[key] for key in line_keys if key in src]
        assert len(line_rows) >= 2 and "{0}" in line_rows[0]["source"]
        assert all(row["stableId"] in targets for row in line_rows)
        assembled = []
        for name in residents:
            label_key = "characterName_" + name
            assert label_key in src, (node, label_key)
            label_sid = src[label_key]["stableId"]
            label = targets[label_sid]
            display = [targets[row["stableId"]].replace("{0}", label) for row in line_rows]
            assert all("{0}" not in x for x in display)
            assembled.append({"resident": name, "labelId": label_sid,
                              "label": label, "displayInCompiledOrder": display})
        reports.append({"node": node, "caller": caller, "place": place,
                        "sourceLineIdsInCompiledOrder": [x["stableId"] for x in line_rows],
                        "residentAlternatives": residents, "assembled": assembled})
    # The fixed Russian masculine in Fan/Luka and the current Hebrew masculine
    # in Greatmother are context conflicts, not evidence that female residents
    # change gender. The staged continuations retain neutral referents.
    by_node = {x["node"]: x for x in reports}
    assert "Alt" in by_node["Fan_Entrance_Occupied"]["residentAlternatives"]
    assert "Teacher" in by_node["Greatmother_Entrance_Occupied"]["residentAlternatives"]
    assert {"Greatmother", "Teacher"} <= set(by_node["Luka_Entrance_Occupied"]["residentAlternatives"])
    for node in ("Greatmother_Entrance_Occupied", "Fan_Entrance_Occupied", "Luka_Entrance_Occupied"):
        for variant in by_node[node]["assembled"]:
            joined = "\n".join(variant["displayInCompiledOrder"])
            assert not any(x in joined for x in ("לגרש אותו", "במקומו", "הצל שלו", "הוא עצמו", "הכופר!", "אולי הוא זקוק"))
    once(CYCLE / "consumer-preflight.json", {"schemaVersion": 1,
        "status": "actual compiled occupied-room branches assembled before authored application",
        "compiledSceneContextSha256": sha(IR2 / "compiled-scene-context.json"),
        "characterDomainSha256": sha(IR1 / "character-consumer-domain.json"),
        "branchCount": len(reports), "assembledVariants": sum(len(x["assembled"]) for x in reports),
        "branches": reports,
        "sourceDomainConflict": "Russian fixed masculine in Fan/Luka conflicts with configured female alternatives. Neutral Hebrew describes the actual occupant without assigning canonical gender.",
        "runtime": "not-run; static compiled/configured evidence only"})
    print(json.dumps({"branches": len(reports),
                      "assembledVariants": sum(len(x["assembled"]) for x in reports),
                      "sha256": sha(CYCLE / "consumer-preflight.json")}))


if __name__ == "__main__":
    main()
