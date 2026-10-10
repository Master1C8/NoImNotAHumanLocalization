#!/usr/bin/env python3
"""Adjudicate and apply the first Dutch independent review's full-unit findings."""

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PRIOR = ROOT / "Translations/nl/semantic-cycle-1/closure-v2/closure-manifest.json"
REVIEW = ROOT / "Translations/nl/independent-review-01"
FINDINGS = REVIEW / "findings.json"
CONSUMER = REVIEW / "consumer-context.json"
CURRENT = ROOT / "Documentation/nl-text-progress.json"
PREPARED = HERE / "adjudicated-corrections-v2.json"
PREFLIGHT = HERE / "complete-batch-preflight-v2.json"
BEFORE = HERE / "before-rows.jsonl"
AFTER = HERE / "after-rows.jsonl"

# The Russian vocative is repeated twice; the review proposal's first 'toch'
# replaced the repetition rather than translating it. Retain both addresses.
REFINEMENTS = {
    "NL-IR01-006": "NotTrue: Och, lieverd, lieverd. Nou ja, kun je voor oma misschien een stoeltje naar buiten brengen?",
    "NL-IR01-014": "NotTrue: O, vriendje… wat heb je hier in huis — {0}?",
}

CONTEXT_NOTES = {
    "NL-IR01-001": "Fridge narrative and approved strange-mushroom glossary locate growth inside a potato.",
    "NL-IR01-002": "Day-8 television ear scene and approved ear-wax term establish oorsmeer.",
    "NL-IR01-003": "Same day-8 ear scene; oorsmeer is the repeated referent.",
    "NL-IR01-004": "Compiled occupied-sister branch supplies an article-free characterName UI label.",
    "NL-IR01-005": "Compiled Doctor occupied branch calls GetCharacterOnPlace; article-free characterName label follows the colon.",
    "NL-IR01-008": "Compiled NotTrue occupied-chair branch calls GetCharacterOnPlace; chair remains occupied.",
    "NL-IR01-009": "Compiled Hunter occupied branch calls GetCharacterOnPlace; label follows a colon.",
    "NL-IR01-010": "Compiled Mother occupied branch calls GetCharacterOnPlace; article-free label follows a colon.",
    "NL-IR01-011": "Compiled occupied-place choice requires freeing a place; binnenlaat/maat rhymes before the explicit rhyme comment.",
    "NL-IR01-012": "Compiled BigLebowski occupied branch supplies an article-free label for an already occupied place.",
    "NL-IR01-013": "Compiled MushroomEater scene immediately reacts to midnight; source asks for a visual time display, without specifying a wristwatch.",
    "NL-IR01-014": "Source key is absent from pinned compiled program; safe textual label introduction, live consumer remains unverified.",
    "NL-IR01-022": "Compiled post-gun ear scene has no lighting referent; idiomatic expletive is retained.",
    "NL-IR01-023": "Compiled gun response has no lighting referent; idiomatic expletive is retained.",
    "NL-IR01-024": "Russian снял их names removing the glasses; compiled scene first mentions finding them on a table. The intervening handling is not fully shown, so the literal removal is retained without inventing where they were worn.",
    "NL-IR01-038": "Firefighter contrasts ears that no longer care with a soul that still does; deafness was not asserted in source.",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_new(path, content):
    assert not path.exists(), f"Immutable evidence exists: {path}"
    path.write_text(content)


def get_recipe():
    path = ROOT / "Translations/nl/semantic-cycle-1/prepare-and-apply.py"
    spec = importlib.util.spec_from_file_location("nl_cycle1_recipe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify():
    prior = json.loads(PRIOR.read_text())
    findings = json.loads(FINDINGS.read_text())
    assert findings["closureManifestSha256"] == sha(PRIOR)
    assert findings["reviewedPairCount"] == prior["components"]["closure"]["count"] == 1440
    review_manifest = json.loads((REVIEW / "evidence-manifest.json").read_text())
    assert review_manifest["reviewedPairs"] == 1440 and review_manifest["proposedCorrectionUnits"] == 38
    for entry in review_manifest["artifacts"]:
        assert sha(ROOT / entry["path"]) == entry["sha256"], entry["path"]
    for pin in prior["pins"].values():
        path = Path(pin["path"])
        assert sha(path if path.is_absolute() else ROOT / path) == pin["sha256"]
    for entry in prior["manual"]["authoredBatches"]:
        assert sha(ROOT / entry["path"]) == entry["sha256"], entry["path"]
    current = json.loads(CURRENT.read_text())
    assert current["batchSetSha256"] == prior["manual"]["authoredSetSha256"]
    rows = {row["stableId"]: row for row in
            (json.loads(line) for line in (ROOT / prior["reviewRowsPath"]).open())}
    assert len(rows) == 1440
    consumer = json.loads(CONSUMER.read_text())
    assert sha(ROOT / consumer["bindingPath"]) == consumer["bindingSha256"]
    return prior, findings["findings"], rows, consumer


def prepare():
    prior, findings, rows, consumer = verify()
    assert len(findings) == 38 and len({f["stableId"] for f in findings}) == 38
    recipe = get_recipe()
    exact = recipe.load_exact_validator()
    manifest = json.loads((ROOT / "Source/preserve-exactly-v4.json").read_text())
    rules = {row["stableId"]: row for row in manifest["tableRows"] + manifest["staticRows"]}
    records = []
    for finding in findings:
        sid = finding["stableId"]
        row = rows[sid]
        assert finding["source"] == row["source"] and finding["target"] == row["target"]
        assert finding["sourceSha256"] == row["sourceSha256"]
        assert finding["targetSha256"] == row["targetSha256"]
        assert finding["authoredPath"] == row["authoredPath"]
        assert sha_text(finding["source"]) == finding["sourceSha256"]
        assert sha_text(finding["target"]) == finding["targetSha256"]
        after = REFINEMENTS.get(finding["findingId"], finding["proposedReplacement"])
        assert after != finding["target"]
        exact.check_value(rules[sid], after)
        records.append({
            "findingId": finding["findingId"], "ordinal": finding["ordinal"], "stableId": sid,
            "authoredPath": finding["authoredPath"], "collection": finding["collection"],
            "key": finding["key"], "nodeNames": finding["nodeNames"],
            "source": finding["source"], "before": finding["target"], "after": after,
            "objectiveReason": finding["reason"], "concept": finding["concept"],
            "decision": "accept with full-unit refinement" if finding["findingId"] in REFINEMENTS else "accept full-unit proposal",
            "contextAdjudication": CONTEXT_NOTES.get(finding["findingId"],
                "Approved babushka voice: милок → lieverd and дружок → vriendje; preserve the remaining source sentences."),
            "protectedValueCheck": "passed unchanged shared preserve_exact.check_value",
        })
    assert records == sorted(records, key=lambda item: item["ordinal"])
    paths = sorted({item["authoredPath"] for item in records})
    before_hashes = [{"path": path, "sha256": sha(ROOT / path)} for path in paths]
    samples = json.loads((REVIEW / "dynamic-label-examples.json").read_text())["samples"]
    labels = {sample["labelTarget"] for sample in samples}
    assert {"man zonder ogen", "vrouw met een kat", "twee zussen"} <= labels
    dynamic = []
    for record in records:
        if "{0}" in record["after"]:
            assert record["after"].count("{0}") == record["before"].count("{0}") == 1
            dynamic.append({"stableId": record["stableId"], "findingId": record["findingId"],
                            "consumer": "GetCharacterOnPlace → exact article-free UI characterName label" if record["findingId"] != "NL-IR01-014" else "unbound accepted source key; live consumer unverified",
                            "assembledSamples": [record["after"].replace("{0}", label)
                                                 for label in ("man zonder ogen", "vrouw met een kat", "twee zussen")]})
    payload = {
        "schemaVersion": 1, "locale": "nl", "cycle": 2,
        "status": "38 independent findings adjudicated and accepted; author corrections, independent delta pending",
        "previousClosurePath": str(PRIOR.relative_to(ROOT)), "previousClosureSha256": sha(PRIOR),
        "independentReviewEvidenceSha256": sha(REVIEW / "evidence-manifest.json"),
        "independentFindingsSha256": sha(FINDINGS), "consumerContextSha256": sha(CONSUMER),
        "pins": prior["pins"], "beforeAuthoredHashes": before_hashes,
        "corrections": records,
    }
    write_new(PREPARED, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    preflight = {
        "schemaVersion": 1, "locale": "nl", "cycle": 2,
        "adjudicationSha256": sha(PREPARED), "acceptedFullUnits": len(records),
        "changedAuthoredFiles": len(paths),
        "sourceTargetIdentity": "passed against immutable independent review rows and current authored hashes",
        "protectedSyntax": "passed unchanged shared preserve_exact.check_value for all 38 full replacements",
        "consumerPreviews": dynamic,
        "consumerExceptions": ["NL-IR01-014 is absent from pinned compiled program; no live reachability claim"],
        "branchAndMeaning": "compiled review consumer context checked for occupied labels, rhyme/free-place choice, clock, glasses, Leper and Firefighter scenes; unchanged full-unit sentences retained",
        "approvedToApply": True,
    }
    write_new(PREFLIGHT, json.dumps(preflight, ensure_ascii=False, indent=2) + "\n")
    print(f"Preflighted {len(records)} accepted full-unit corrections in {len(paths)} authored files; {len(dynamic)} dynamic templates")


def apply():
    assert PREPARED.exists() and PREFLIGHT.exists() and not BEFORE.exists() and not AFTER.exists()
    adjudication = json.loads(PREPARED.read_text())
    preflight = json.loads(PREFLIGHT.read_text())
    assert preflight["approvedToApply"] and preflight["adjudicationSha256"] == sha(PREPARED)
    for pin in adjudication["pins"].values():
        path = Path(pin["path"])
        assert sha(path if path.is_absolute() else ROOT / path) == pin["sha256"]
    for entry in adjudication["beforeAuthoredHashes"]:
        assert sha(ROOT / entry["path"]) == entry["sha256"], entry["path"]
    recipe = get_recipe()
    exact = recipe.load_exact_validator()
    rules = {row["stableId"]: row for row in json.loads((ROOT / "Source/preserve-exactly-v4.json").read_text())["tableRows"]}
    guids = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
             "UI": "0cbd8a7a4f543344bb95659de87f67a5",
             "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}
    by_path = {}
    for record in adjudication["corrections"]:
        by_path.setdefault(record["authoredPath"], {})[record["stableId"]] = record
    old_hashes = {entry["path"]: entry["sha256"] for entry in adjudication["beforeAuthoredHashes"]}
    writes, before_rows, after_rows = [], [], []
    for path, changes in by_path.items():
        doc = json.loads((ROOT / path).read_text())
        style = recipe.original_style(doc, old_hashes[path])
        found = set()
        for entry in doc["entries"]:
            sid = f"string:{guids[doc['collection']]}:{entry['id']}"
            if sid not in changes:
                continue
            record = changes[sid]
            assert entry["target"] == record["before"]
            exact.check_value(rules[sid], record["after"])
            found.add(sid)
            before_rows.append({"ordinal": record["ordinal"], "stableId": sid, "path": path,
                                "source": record["source"], "target": entry["target"],
                                "targetSha256": sha_text(entry["target"])})
            entry["target"] = record["after"]
            after_rows.append({"ordinal": record["ordinal"], "stableId": sid, "path": path,
                               "source": record["source"], "target": entry["target"],
                               "targetSha256": sha_text(entry["target"])})
        assert found == set(changes)
        writes.append((ROOT / path, recipe.serialize_batch(doc, style)))
    assert len(before_rows) == len(after_rows) == 38
    before_rows.sort(key=lambda row: row["ordinal"])
    after_rows.sort(key=lambda row: row["ordinal"])
    write_new(BEFORE, "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in before_rows))
    write_new(AFTER, "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in after_rows))
    for path, content in writes:
        path.write_text(content)
    print(f"Applied {len(after_rows)} corrections to {len(writes)} authored files")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "apply"])
    args = parser.parse_args()
    prepare() if args.action == "prepare" else apply()
