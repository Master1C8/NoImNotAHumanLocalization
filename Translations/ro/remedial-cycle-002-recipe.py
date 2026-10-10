#!/usr/bin/env python3
"""Reproduce the Romanian remedial correction plan and apply its authored values.

This locale-owned recipe never edits source, glossary, shared state or Git.
"""

import hashlib
import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[2]
LOCALE = ROOT / "Translations/ro"
REVIEW = LOCALE / "independent-review-01"
PLAN = LOCALE / "remedial-cycle-002-plan.json"
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import check_value  # noqa: E402

GUIDS = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
         "UI": "0cbd8a7a4f543344bb95659de87f67a5",
         "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}
REJECTED = {16310: "Russian impersonal «некому напоминать» has an absent reminding agent in this clause. The children remain at home; the present Romanian says nobody is there to remind them. The proposal reverses agency and is not supported by this branch."}
REWORDED = {
    15056: "Raskolnikov: Dar într-o zi un bătăuș mi-a scos un dinte cu o lovitură și atunci mi-am promis: dacă nu pot fi puternic, măcar voi fi fără cusur.",
    15060: "Raskolnikov: Dar într-o zi un bătăuș mi-a scos un dinte cu o lovitură. Și ce crezi că am făcut?",
}
ADDITIONAL = {
    14692: ("Buddy: Așa că l-am îmbrățișat. L-am liniștit.", "The established generic câine referent is grammatically masculine in Romanian; the two feminine object clitics refer to the same dog without evidence of biological sex."),
    14693: ("Buddy: Odată, în apropiere au început să bubuie artificiile. Câinele meu a început să tremure, să se lipească de podea și să vină cât mai aproape de mine. Sărmanul era tare speriat.", "Russian собачка and бедняжка are affectionate forms, not biological-sex evidence. Replace the explicit female dog with generic câine while retaining the fear and tenderness."),
    14724: ("Buddy: Hai, amice. Vreau să cred că există ceva după moarte și că ne vom revedea undeva acolo, eu și câinele meu drag…", "The same dog is not canonically sexed; Romanian cățelușa asserts female. Generic câine with drag retains the source's affectionate diminutive tone."),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def verify_inputs():
    pins = load(REVIEW / "input-pins.json")
    for item in pins["files"] + pins["authoredFiles"]:
        assert sha(ROOT / item["path"]) == item["sha256"], item["path"]
    review = load(REVIEW / "review-result.json")
    assert review["readUnitCount"] == 3090 and review["proposalCount"] == 276
    assert review["itemTransferBindingChecksPassed"] == 245
    assert review["authoredEdits"] == 0
    source = {}
    for name in ("strings.jsonl", "static-text.jsonl"):
        for line in (ROOT / "Source/localization-inventory-v3" / name).read_text().splitlines():
            row = json.loads(line)
            assert row["stableId"] not in source
            source[row["stableId"]] = row
    manifest = load(ROOT / "Source/preserve-exactly-v4.json")
    rules = {row["stableId"]: row for row in manifest["tableRows"] + manifest["staticRows"]}
    assert len(rules) == 16538
    return pins, source, rules


def authored():
    files, values, locations = {}, {}, {}
    for path in sorted(LOCALE.glob("*-batch-???.json")) + [LOCALE / "static-text-draft.json"]:
        data = load(path)
        rel = str(path.relative_to(ROOT))
        files[rel] = data
        for i, entry in enumerate(data["entries"]):
            sid = entry.get("stableId") or f"string:{GUIDS[data['collection']]}:{entry['id']}"
            assert sid not in values
            values[sid] = entry["target"]
            locations[sid] = (rel, i)
    assert len(values) == 16538
    return files, values, locations


def current_rows():
    progress = load(LOCALE / "semantic-review-progress.json")
    rows = {}
    for item in progress["reviewSegments"]:
        assert sha(ROOT / item["path"]) == item["sha256"]
        for line in (ROOT / item["path"]).read_text().splitlines():
            row = json.loads(line)
            rows[row["ordinal"]] = row
    assert len(rows) == 16538
    return rows


def build_decisions():
    pins, source, rules = verify_inputs()
    files, values, locations = authored()
    rows = current_rows()
    findings = load(REVIEW / "consolidated-findings.json")["findings"]
    assert len(findings) == 276 and len({f["stableId"] for f in findings}) == 276
    transfer = load(REVIEW / "item-transfer-contract-verification.json")
    assert transfer["checkedBindings"] == 245 and transfer["allExpectedGuardAndTransfer"]
    transfer_ids = {r["stableId"] for r in transfer["rows"]}
    assert len(transfer_ids) == 245
    decisions = []
    for f in findings:
        sid, ordinal = f["stableId"], f["ordinal"]
        assert source[sid]["source"] == f["source"] == rows[ordinal]["source"]
        assert rows[ordinal]["stableId"] == sid
        assert values[sid] == f["currentTarget"] and locations[sid][0] == f["authoredPath"]
        if f["defectGroup"] == "existing-item-transfer":
            assert sid in transfer_ids and f["source"] == "Выдать явку в КЧС"
        accepted = ordinal not in REJECTED
        after = REWORDED.get(ordinal, f["proposedTarget"]) if accepted else f["currentTarget"]
        decisions.append({"ordinal": ordinal, "stableId": sid, "key": f["key"],
                          "source": f["source"], "before": f["currentTarget"],
                          "after": after, "defectGroup": f["defectGroup"],
                          "decision": "accepted-reworded" if ordinal in REWORDED else
                          "accepted" if accepted else "rejected",
                          "reason": f["reason"] if accepted else REJECTED[ordinal],
                          "reviewFindingId": f["findingId"],
                          "authoredPath": locations[sid][0], "entryIndex": locations[sid][1]})
    for ordinal, (after, reason) in ADDITIONAL.items():
        row = rows[ordinal]
        sid = row["stableId"]
        assert sid not in {d["stableId"] for d in decisions}
        assert values[sid] == row["target"] and source[sid]["source"] == row["source"]
        decisions.append({"ordinal": ordinal, "stableId": sid, "key": row["key"],
                          "source": row["source"], "before": values[sid], "after": after,
                          "defectGroup": "dog-referent", "decision": "accepted-connected-addition",
                          "reason": reason, "reviewFindingId": None,
                          "authoredPath": locations[sid][0], "entryIndex": locations[sid][1]})
    decisions.sort(key=lambda d: d["ordinal"])
    assert len(decisions) == 279
    accepted = [d for d in decisions if d["decision"].startswith("accepted")]
    assert len(accepted) == 278 and len({d["stableId"] for d in accepted}) == 278
    for d in accepted:
        assert d["before"] != d["after"]
        check_value(rules[d["stableId"]], d["after"])
        values[d["stableId"]] = d["after"]
    assert set(values) == set(rules)
    for sid, rule in rules.items():
        check_value(rule, values[sid])
    # The 245 transfer labels derive from one authored phrase, not 245 edits to
    # generated rows. Project the map and verify the exact source multiplicity.
    map_path = LOCALE / "dialogue-repeats-001.authored.json"
    repeat_map = load(map_path)
    phrase = next(x for x in repeat_map["phrases"] if x["source"] == "Выдать явку в КЧС")
    assert phrase["expectedRows"] == 245 and phrase["target"] == "Emite un ordin de prezentare la Comitet"
    transfer_targets = {d["after"] for d in accepted if d["defectGroup"] == "existing-item-transfer"}
    assert transfer_targets == {"Înmânează ordinul de prezentare la Comitet"}
    assert {d["stableId"] for d in accepted if d["defectGroup"] == "existing-item-transfer"} == transfer_ids
    # All admissible static same-place values are assembled with the projected
    # target label; unknown/self cells retain their explicit source limits.
    domain = load(REVIEW / "occupied-room-inputs.json")
    assert domain["sourceDomainCount"] == len(domain["samePlaceSourceDomain"]) == 13
    occupied = next(r for r in rows.values() if r["ordinal"] == 2586)
    template = values[occupied["stableId"]]
    assert template.count("{0}") == 1
    assembled = []
    for item in domain["samePlaceSourceDomain"]:
        sid = item["stableId"]
        target = values[sid] if sid else None
        assembled.append({"objectId": item["objectId"], "sourceName": item["name"],
                          "stableId": sid, "target": target,
                          "assembled": template.replace("{0}", target) if target else None})
    return pins, decisions, files, assembled


def make_plan():
    assert not PLAN.exists(), "Preserve immutable remedial plan"
    pins, decisions, files, assembled = build_decisions()
    result = {"schemaVersion": 1, "locale": "ro", "cycle": 2,
              "status": "consolidated author adjudication and projected exact preflight passed; not yet applied",
              "reviewResultSha256": sha(REVIEW / "review-result.json"),
              "consolidatedFindingsSha256": sha(REVIEW / "consolidated-findings.json"),
              "perIdLedgerSha256": sha(REVIEW / "per-id-decisions-final.jsonl"),
              "itemTransferContractSha256": sha(REVIEW / "item-transfer-contract-verification.json"),
              "previousClosureManifestSha256": sha(LOCALE / "correction-cycle-001-closure-v3/manifest.json"),
              "sourceInventorySha256": sha(ROOT / "Source/localization-inventory-v3/strings.jsonl"),
              "staticInventorySha256": sha(ROOT / "Source/localization-inventory-v3/static-text.jsonl"),
              "preserveExactManifestSha256": sha(ROOT / "Source/preserve-exactly-v4.json"),
              "approvedGlossarySha256": sha(ROOT / "Documentation/glossary-translations/ro/layer.json"),
              "beforeAuthoredFiles": [{"path": rel, "sha256": sha(ROOT / rel)} for rel in sorted(files)],
              "beforeRepeatMapSha256": sha(LOCALE / "dialogue-repeats-001.authored.json"),
              "proposals": 276, "connectedAdditions": 3, "acceptedChanges": 278,
              "rejectedProposals": 1, "projectedExactRows": 16538,
              "dynamicSamePlaceSourceCases": assembled,
              "dogGenericPluralRetained": "Ordinals 9181 and 9196 describe pets in general; Romanian ele may refer to generic animalele. No compelled sex-specific correction is made.",
              "preimageBoundary": "The four cycle-001 reformatted files have original hashes and complete first-pass target values, but no verified original bytes for non-target field comparison. The prior apply recipe assigned only entry.target; this is evidence of method, not an independently recovered preimage.",
              "decisions": decisions}
    PLAN.write_text(dump(result))
    print(json.dumps({"plan": str(PLAN.relative_to(ROOT)), "sha256": sha(PLAN),
                      "proposals": 276, "accepted": 278, "rejected": 1,
                      "projectedExact": 16538, "assembledCases": len(assembled)}))


def apply():
    plan = load(PLAN)
    assert plan["status"] == "consolidated author adjudication and projected exact preflight passed; not yet applied"
    assert plan["reviewResultSha256"] == sha(REVIEW / "review-result.json")
    assert plan["consolidatedFindingsSha256"] == sha(REVIEW / "consolidated-findings.json")
    assert plan["previousClosureManifestSha256"] == sha(LOCALE / "correction-cycle-001-closure-v3/manifest.json")
    assert plan["beforeRepeatMapSha256"] == sha(LOCALE / "dialogue-repeats-001.authored.json")
    assert all(sha(ROOT / x["path"]) == x["sha256"] for x in plan["beforeAuthoredFiles"])
    _, decisions, files, assembled = build_decisions()
    assert decisions == plan["decisions"] and assembled == plan["dynamicSamePlaceSourceCases"]
    accepted = [d for d in decisions if d["decision"].startswith("accepted")]
    touched = set()
    for d in accepted:
        rel = d["authoredPath"]
        entry = files[rel]["entries"][d["entryIndex"]]
        assert entry["target"] == d["before"]
        entry["target"] = d["after"]
        touched.add(rel)
    repeat_path = LOCALE / "dialogue-repeats-001.authored.json"
    repeat_map = load(repeat_path)
    phrase = next(x for x in repeat_map["phrases"] if x["source"] == "Выдать явку в КЧС")
    assert phrase["target"] == "Emite un ordin de prezentare la Comitet"
    phrase["target"] = "Înmânează ordinul de prezentare la Comitet"
    map_bytes = dump(repeat_map).encode()
    files["Translations/ro/dialogue-batch-001.json"]["authoredMapSha256"] = hashlib.sha256(map_bytes).hexdigest()
    assert "Translations/ro/dialogue-batch-001.json" in touched
    # Complete intended output is prepared before any replacement. Each file
    # replacement is atomic; the multi-file sequence is not a transaction.
    outputs = {ROOT / rel: dump(files[rel]).encode() for rel in touched}
    outputs[repeat_path] = map_bytes
    for path, payload in outputs.items():
        assert json.loads(payload)
    temp_paths = {}
    for path, payload in outputs.items():
        temp = path.with_name(path.name + ".cycle-002-temp")
        assert not temp.exists()
        temp.write_bytes(payload)
        temp_paths[path] = temp
    order = [repeat_path] + sorted(path for path in outputs if path != repeat_path)
    for path in order:
        temp_paths[path].replace(path)
    print(json.dumps({"appliedIds": len(accepted), "authoredFiles": len(touched),
                      "repeatMap": str(repeat_path.relative_to(ROOT)),
                      "planSha256": sha(PLAN)}))


if __name__ == "__main__":
    assert len(sys.argv) == 2 and sys.argv[1] in {"plan", "apply"}
    {"plan": make_plan, "apply": apply}[sys.argv[1]]()
