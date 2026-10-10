#!/usr/bin/env python3
"""Pin and apply the Romanian review02 five-unit author correction batch.

Only target fields in locale-authored JSON are changed. Source, glossary,
shared scripts, historical review artifacts and Git state are read-only.
"""

import hashlib
import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
LOCALE = ROOT / "Translations/ro"
REVIEW = LOCALE / "independent-review-02"
PLAN = LOCALE / "correction-cycle-003-plan.json"
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import check_value  # noqa: E402

GUIDS = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
         "UI": "0cbd8a7a4f543344bb95659de87f67a5",
         "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}
EXPECTED = {8018, 8757, 11963, 12078, 12104}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def current():
    files, values, locations = {}, {}, {}
    for path in sorted(LOCALE.glob("*-batch-???.json")) + [LOCALE / "static-text-draft.json"]:
        rel = str(path.relative_to(ROOT))
        data = read(path)
        files[rel] = data
        for index, entry in enumerate(data["entries"]):
            sid = entry.get("stableId") or f"string:{GUIDS[data['collection']]}:{entry['id']}"
            assert sid not in values
            values[sid] = entry["target"]
            locations[sid] = (rel, index)
    assert len(values) == 16538
    return files, values, locations


def first_pass_rows():
    progress = read(LOCALE / "semantic-review-progress.json")
    assert progress["reviewedUnits"] == progress["acceptedUnits"] == 16538
    rows = []
    for desc in progress["reviewSegments"]:
        assert sha(ROOT / desc["path"]) == desc["sha256"]
        rows.extend(json.loads(line) for line in (ROOT / desc["path"]).read_text().splitlines())
    assert [r["ordinal"] for r in rows] == list(range(16538))
    return rows


def verify_review_before():
    pins = read(REVIEW / "input-pins.json")
    assert len(pins["pins"]) == 428 and pins["authoredFiles"] == 415
    for item in pins["pins"]:
        assert sha(ROOT / item["path"]) == item["sha256"], item["path"]
    audit = read(REVIEW / "audit-manifest.json")
    for item in audit["files"]:
        assert sha(ROOT / item["path"]) == item["sha256"], item["path"]
    assert sha(LOCALE / "remedial-cycle-002-closure-v2/manifest.json") == \
        "d2759f6fb0676d94e05235f0ae27916432afe81b9c9fb98eee4f35c11f39f3a2"
    return pins, audit


def compiled_adjudication(rows):
    decoder_path = LOCALE / "independent-review-01/compiled_context.py"
    spec = importlib.util.spec_from_file_location("ro_cycle3_decoder", decoder_path)
    decoder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(decoder)
    nodes, program_sha = decoder.load()
    assert program_sha == "33de1e80e55e4eb8ec2093078028aa83fc45ac8b77acc05c5a4f9477ebe92827"
    bykey = {r["key"]: r for r in rows if r["key"]}
    def operands(name):
        return [op for ins in nodes[name] for op in ins["operands"] if isinstance(op, str)]
    assert rows[8018]["key"] in operands("talk_doc_3")
    assert "Doctor_Asking_3" in operands("talk_doc_3")
    assert rows[8757]["key"] in operands("talk_couple_3")
    assert "Couple_Asking_3" in operands("talk_couple_3")
    assert rows[11963]["key"] in operands("selfcheck_armpit_imposter")
    assert rows[12078]["key"] in operands("selfcheck_armpit_imposter")
    assert rows[12104]["key"] in operands("selfcheck_hands")
    for node in ("selfcheck_armpit_imposter", "selfcheck_hands"):
        assert "selfchek_wash_armpits" in operands(node)
    assert "WashArmpits" in operands("selfchek_wash_armpits")
    assert rows[11963]["source"] == rows[12104]["source"] == "Умыться"
    for ordinal in range(6757, 6763):
        node = "FEMA_GivingPostcard_Firefighter" if ordinal <= 6759 else "FEMA_GivingPostcard"
        assert rows[ordinal]["key"] in operands(node)
    return {"programSha256": program_sha,
            "doctor": ["talk_doc_3", "Doctor_Asking_3", "Doctor_Asking_3_Backstory", "Doctor_Asking_3_Disappointed"],
            "couple": ["talk_couple_3", "Couple_Asking_3"],
            "washing": ["selfcheck_armpit_imposter", "selfcheck_hands", "selfchek_wash_armpits"],
            "transferSuccess": ["FEMA_GivingPostcard", "FEMA_GivingPostcard_Firefighter"],
            "sourcePeculiarity": "selfcheck_hands calls selfchek_wash_armpits and WashArmpits; no invented hand-wash dispatch"}


def prepare():
    pins, audit = verify_review_before()
    rows = first_pass_rows()
    files, values, locations = current()
    before = {r["stableId"]: r["target"] for r in rows}
    for item in read(LOCALE / "correction-cycle-001-plan.json")["corrections"]:
        assert before[item["stableId"]] == item["before"]
        before[item["stableId"]] = item["after"]
    for item in read(LOCALE / "remedial-cycle-002-plan.json")["decisions"]:
        assert before[item["stableId"]] == item["before"]
        before[item["stableId"]] = item["after"]
    assert all(values[sid] == target for sid, target in before.items())
    proposals = read(REVIEW / "consolidated-findings.json")["proposals"]
    assert len(proposals) == 5 and {p["ordinal"] for p in proposals} == EXPECTED
    rules = read(ROOT / "Source/preserve-exactly-v4.json")
    rules = {r["stableId"]: r for r in rules["tableRows"] + rules["staticRows"]}
    assert len(rules) == 16538
    decisions = []
    for proposal in sorted(proposals, key=lambda p: p["ordinal"]):
        ordinal = proposal["ordinal"]
        row = rows[ordinal]
        sid = row["stableId"]
        assert (sid, row["key"], row["source"]) == \
            (proposal["stableId"], proposal["key"], proposal["source"])
        assert values[sid] == proposal["currentTarget"]
        assert locations[sid] == (proposal["authoredPath"], proposal["entryIndex"])
        assert proposal["proposedTarget"] != proposal["currentTarget"]
        check_value(rules[sid], proposal["proposedTarget"])
        decisions.append({"ordinal": ordinal, "stableId": sid, "key": row["key"],
                          "source": row["source"], "before": values[sid],
                          "after": proposal["proposedTarget"], "decision": "accepted",
                          "reason": proposal["reason"], "defectGroup": proposal["defectGroup"],
                          "reviewFindingId": proposal["findingId"],
                          "authoredPath": locations[sid][0], "entryIndex": locations[sid][1]})
        values[sid] = proposal["proposedTarget"]
    for sid, rule in rules.items():
        check_value(rule, values[sid])
    context = compiled_adjudication(rows)
    return pins, audit, files, decisions, context


def plan():
    assert not PLAN.exists(), "Keep the correction plan immutable"
    pins, audit, files, decisions, context = prepare()
    result = {"schemaVersion": 1, "locale": "ro", "cycle": 3,
              "status": "five full-unit corrections adjudicated and projected over all 16538 preserve-exact values; not yet applied",
              "reviewAuditManifestSha256": sha(REVIEW / "audit-manifest.json"),
              "reviewFindingsSha256": sha(REVIEW / "consolidated-findings.json"),
              "reviewInputPinsSha256": sha(REVIEW / "input-pins.json"),
              "previousClosureManifestSha256": sha(LOCALE / "remedial-cycle-002-closure-v2/manifest.json"),
              "sourceInventorySha256": sha(ROOT / "Source/localization-inventory-v3/strings.jsonl"),
              "staticInventorySha256": sha(ROOT / "Source/localization-inventory-v3/static-text.jsonl"),
              "approvedGlossarySha256": sha(ROOT / "Documentation/glossary-translations/ro/layer.json"),
              "preserveExactManifestSha256": sha(ROOT / "Source/preserve-exactly-v4.json"),
              "beforeAuthoredFiles": [{"path": rel, "sha256": sha(ROOT / rel)} for rel in sorted(files)],
              "beforeAuthoredMaps": [{"path": str(path.relative_to(ROOT)), "sha256": sha(path)}
                                     for path in sorted(LOCALE.glob("*.authored.json"))],
              "acceptedCorrections": 5, "rejectedProposals": 0, "projectedExactRows": 16538,
              "compiledAdjudication": context,
              "retainedDecisions": {"firefighter16310": "Reviewer02 confirmed no objective correction: Russian некому + infinitive denotes absent reminding actor.",
                                    "genericPets9181And9196": "Reviewer02 confirmed Romanian ele refers to generic plural animalele."},
              "historicalPreimageLimit": "Five older reformatted batch preimages remain byte-unavailable. Reviewer02 verified current parsed schema/version/IDs/order/source and target alignment; historical whole-file non-target parity is unverified.",
              "decisions": decisions}
    PLAN.write_text(canonical(result))
    print(json.dumps({"planSha256": sha(PLAN), "accepted": len(decisions), "projectedExact": 16538,
                      "affectedFiles": len({d["authoredPath"] for d in decisions})}))


def apply():
    saved = read(PLAN)
    assert saved["status"].endswith("not yet applied")
    assert saved["reviewAuditManifestSha256"] == sha(REVIEW / "audit-manifest.json")
    assert saved["reviewFindingsSha256"] == sha(REVIEW / "consolidated-findings.json")
    assert saved["reviewInputPinsSha256"] == sha(REVIEW / "input-pins.json")
    assert all(sha(ROOT / item["path"]) == item["sha256"] for item in saved["beforeAuthoredFiles"])
    assert all(sha(ROOT / item["path"]) == item["sha256"] for item in saved["beforeAuthoredMaps"])
    _, _, files, decisions, context = prepare()
    assert decisions == saved["decisions"] and context == saved["compiledAdjudication"]
    touched = set()
    for item in decisions:
        rel = item["authoredPath"]
        entry = files[rel]["entries"][item["entryIndex"]]
        assert entry["target"] == item["before"]
        entry["target"] = item["after"]
        touched.add(rel)
    for rel in sorted(touched):
        path = ROOT / rel
        temporary = path.with_suffix(path.suffix + ".cycle-003-tmp")
        temporary.write_text(canonical(files[rel]))
        temporary.replace(path)
    print(json.dumps({"applied": len(decisions), "files": len(touched), "planSha256": sha(PLAN)}))


if __name__ == "__main__":
    assert len(sys.argv) == 2 and sys.argv[1] in {"plan", "apply"}
    {"plan": plan, "apply": apply}[sys.argv[1]]()
