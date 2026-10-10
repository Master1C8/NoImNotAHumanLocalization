#!/usr/bin/env python3
"""Pin and preflight the one consolidated Hindi review02 correction batch."""
import hashlib, importlib.util, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HI = ROOT / "Translations/hi"
REVIEW = HI / "independent-review-02"
ADJ = HI / "semantic-cycle-003-adjudication.json"
PREFLIGHT = HI / "semantic-cycle-003-preflight.json"

def sha(path): return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def textsha(value): return hashlib.sha256(value.encode()).hexdigest()
def read(path): return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
def dump(value): return json.dumps(value, ensure_ascii=False, indent=2) + "\n"

def main():
    assert not ADJ.exists() and not PREFLIGHT.exists()
    pins = read(REVIEW / "final-unchanged-input-pins.json")["pins"]
    assert len(pins) == 693
    assert all(sha(ROOT / path) == digest for path, digest in pins.items())
    findings = read(REVIEW / "consolidated-full-unit-findings.json")["items"]
    assert len(findings) == 17
    final = [json.loads(line) for line in (REVIEW / "per-id-final-decisions.jsonl").read_text().splitlines()]
    assert len(final) == 5133 and sum(row.get("deltaOrdinal0") is not None for row in final) == 4429
    closure = read(HI / "semantic-cycle-002-closure.json")
    assert len(closure["reviewRows"]) == 5133
    assert read(REVIEW / "final-coverage-and-closure-proof.json")["currentClosureCount"] == 5133
    source_rows = [json.loads(line) for line in (ROOT / "Source/localization-inventory-v3/strings.jsonl").read_text().splitlines()]
    by_sid = {row["stableId"]: row for row in source_rows}
    by_collection_id = {(row["collection"], row["stableId"].rsplit(":", 1)[1]): row for row in source_rows}
    by_key = {row.get("key"): row for row in source_rows if row["collection"] == "Dialogs" and row.get("key")}
    authored = {}
    for path in sorted(HI.glob("dialogue-batch-[0-9][0-9][0-9].json")):
        obj = read(path)
        for entry in obj["entries"]:
            row = by_collection_id[(obj["collection"], str(entry["id"]))]
            authored[row["stableId"]] = {"target": entry["target"], "path": str(path.relative_to(ROOT))}
    extra_row = by_key["line:phone_psychics_7_01d9005"]
    assert extra_row["stableId"] in authored
    extra = {"findingId": "HI-AUTHOR-R02-BOUNDED-001", "stableId": extra_row["stableId"],
             "key": extra_row["key"], "source": extra_row["source"],
             "before": authored[extra_row["stableId"]]["target"],
             "proposedFullTarget": "Phone: उससे आपके भीतर माइसीलियम उगता है। उसकी मदद से आत्मा आपको कठपुतली की तरह आसानी से नियंत्रित कर सकेगी।",
             "reason": "The adjacent psychic hotline claim also names мицелий. The approved mycelium entry requires माइसीलियम while retaining this speaker's unqualified assertion.",
             "context": "Compiled phone_psychics_7 precedes conditional phone_psychics_8; the speaker's epistemic scope differs, but the named substance is the same.",
             "authoredPath": authored[extra_row["stableId"]]["path"]}
    assert extra["before"] == "Phone: उससे आपके भीतर कवकजाल उगता है। उसकी मदद से आत्मा आपको कठपुतली की तरह आसानी से नियंत्रित कर सकेगी।"
    items = []
    manifest = read(ROOT / "Source/preserve-exactly-v4.json")
    rules = {row["stableId"]: row for row in manifest["tableRows"] + manifest["staticRows"]}
    sys.path.insert(0, str(ROOT / "Scripts"))
    spec = importlib.util.spec_from_file_location("preserve_exact", ROOT / "Scripts/preserve_exact.py")
    preserve = importlib.util.module_from_spec(spec); spec.loader.exec_module(preserve)
    for candidate in findings + [extra]:
        sid = candidate["stableId"]
        src = by_sid[sid]
        current = authored[sid]
        assert src["source"] == candidate["source"]
        assert current["target"] == candidate["before"]
        assert current["path"] == candidate["authoredPath"]
        if "sourceSha256" in candidate: assert textsha(src["source"]) == candidate["sourceSha256"]
        if "currentTargetSha256" in candidate: assert textsha(current["target"]) == candidate["currentTargetSha256"]
        replacement = candidate["proposedFullTarget"]
        assert replacement != current["target"]
        preserve.check_value(rules[sid], replacement)
        items.append({"stableId": sid, "key": src.get("key"), "source": src["source"],
                      "sourceSha256": textsha(src["source"]), "authoredPath": current["path"],
                      "before": current["target"], "beforeSha256": textsha(current["target"]),
                      "acceptedFullTarget": replacement, "acceptedFullTargetSha256": textsha(replacement),
                      "reason": candidate["reason"], "findingId": candidate["findingId"],
                      "sceneContext": candidate["context"]})
    assert len(items) == len({row["stableId"] for row in items}) == 18
    order = {row["stableId"]: i for i, row in enumerate(closure["reviewRows"])}
    # Review02 found one adjacent TV unit outside its assigned closure/delta.
    assert {item["findingId"] for item in items if item["stableId"] not in order} == {"HI-R02-002", "HI-AUTHOR-R02-BOUNDED-001"}
    # Whole-source/target enumeration for every risk exposed by the findings.
    accepted = {row["stableId"] for row in closure["reviewRows"]}
    searches = {
        "earwax_source": r"(?i)\bсер[аы]\b|ушн\w*\s+сер\w*",
        "psychic_mycelium_source": r"(?i)мицелий",
        "kinship_remarriage_source": r"(?i)ма и ба|мам\w*.*бабушк|за другого хахаля|жена.*вышла",
        "exam_agency_source": r"(?i)делая.*обследован",
        "theft_source": r"(?i)всё пиздить",
        "firefighter_timing_source": r"(?i)я бы хотел тушить|погибну",
        "sustained_recovery_source": r"(?i)придёт в себя",
        "vibration_source": r"(?i)вибрац",
        "speaker_reveal_source": r"(?i)как мою…|новую веру",
    }
    risk = {}
    for name, pattern in searches.items():
        matcher = re.compile(pattern)
        matches = [row for row in source_rows if row["stableId"] in authored and matcher.search(row["source"])]
        risk[name] = [{"stableId": row["stableId"], "key": row.get("key"), "source": row["source"],
                       "target": authored[row["stableId"]]["target"]} for row in matches]
    target_terms = {}
    for term in ("कवकजाल", "गंधक", "माँ-बाप", "होश आए", "जाँच कराकर"):
        target_terms[term] = [sid for sid, val in authored.items() if term in val["target"]]
    assert len(target_terms["कवकजाल"]) == 2 and len(target_terms["गंधक"]) == 2
    assert set(target_terms["कवकजाल"]) | set(target_terms["गंधक"]) <= {item["stableId"] for item in items}
    # Exact repeated source content outside the 18-unit set would require another decision.
    normalized = lambda s: re.sub(r"\s+", " ", re.sub(r"^[A-Za-z][A-Za-z0-9_]*: ", "", s)).replace("ё", "е").strip()
    affected = {normalized(item["source"]) for item in items}
    repeat = [row for row in source_rows if row["stableId"] in authored and normalized(row["source"]) in affected]
    assert {row["stableId"] for row in repeat} == {item["stableId"] for item in items}
    adj = {"schemaVersion": 1, "locale": "hi", "gameVersion": "1.3.19", "status": "complete author-adjudicated 18-unit proposal; no authored edit",
           "sourceInventorySha256": sha(ROOT / "Source/localization-inventory-v3/strings.jsonl"),
           "staticInventorySha256": sha(ROOT / "Source/localization-inventory-v3/static-text.jsonl"),
           "glossaryLayerSha256": sha(ROOT / "Documentation/glossary-translations/hi/layer.json"),
           "compiledRuntimeBindingsSha256": sha(ROOT / "Source/glossary-corpus-v2/runtime-bindings.json"),
           "preserveExactManifestSha256": sha(ROOT / "Source/preserve-exactly-v4.json"),
           "review02FinalReportSha256": sha(REVIEW / "final-report.md"),
           "review02FindingsSha256": sha(REVIEW / "consolidated-full-unit-findings.json"),
           "review02FinalDecisionsSha256": sha(REVIEW / "per-id-final-decisions.jsonl"),
           "review02FinalCoverageSha256": sha(REVIEW / "final-coverage-and-closure-proof.json"),
           "previousClosureSha256": sha(HI / "semantic-cycle-002-closure.json"),
           "independentFindingCount": 17, "additionalBoundedFindingCount": 1,
           "dismissedContextCandidatesSha256": sha(REVIEW / "contextual-candidate-dispositions.json"),
           "boundedRemedialRead": {"sourceSearchPatterns": searches,
                                   "sourceFamilyRows": risk, "targetTermIds": target_terms,
                                   "exactRepeatedSourceIds": [row["stableId"] for row in repeat],
                                   "method": "Pinned authored corpus enumeration plus complete context reads of reviewer findings; retain prior contextual candidate dismissals."},
           "items": items}
    pre = {"schemaVersion": 1, "locale": "hi", "status": "complete 18-unit preflight passed before authored application",
           "adjudicationSha256": textsha(dump(adj)), "reviewedUnits": 18, "protectedSyntaxFailures": 0,
           "sourceAndBeforeMatch": True, "allFullReplacementsRead": True,
           "factsAgencyTimingReveal": "Reviewer proposals adopted with Russian and compiled scene context; one additional psychic term use corrected; no preference edits.",
           "dynamicConsumer": "No replacement contains a variable slot; no new dynamic join is introduced. Existing compiled supplier domain evidence remains pinned.",
           "derivedInputs": "Only dialogue-batch authored values change; static phrase map, credits map and common-option authored templates are unchanged.",
           "items": [{"stableId": x["stableId"], "sourceSha256": x["sourceSha256"],
                      "beforeSha256": x["beforeSha256"], "replacementSha256": x["acceptedFullTargetSha256"],
                      "protectedSyntax": "passed", "sceneContext": x["sceneContext"]} for x in items]}
    ADJ.write_text(dump(adj), encoding="utf-8")
    PREFLIGHT.write_text(dump(pre), encoding="utf-8")
    print("prepared and preflighted", len(items), "full units")

if __name__ == "__main__": main()
