#!/usr/bin/env python3
"""Pin, adjudicate, preflight, then apply Dutch independent-review-02 corrections."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PRIOR = ROOT / "Translations/nl/semantic-cycle-2/closure/closure-manifest.json"
REVIEW = ROOT / "Translations/nl/independent-review-02"
ADJ = HERE / "adjudicated-corrections-v2.json"
PREFLIGHT = HERE / "complete-batch-preflight-v2.json"

REFINEMENTS = {
    "NL-IR02-003": "Fairytaller: Maar ik vrees dat ik me ongemakkelijk zal voelen zolang ik met deze persoon in één ruimte zit: {0}.",
    "NL-IR02-009": "Experienced: Deze persoon staat me niet aan: {0}.",
    "NL-IR02-012": "Twins: Ik vrees dat hier al iemand bij u zit: {0}.",
    "NL-IR02-020": "Foreigner: (Het lijkt erop dat hij dit gezelschap niet mag: {0}. Hij wijst naar hem, dan naar zichzelf en daarna weer naar hem.)",
    "NL-IR02-023": "Cold: Bedankt… O, er is hier al iemand. Ik kom niet binnen zolang er hier al gezelschap is: {0}.",
    "NL-IR02-025": "Fanatic: Mens! De ZON gebiedt me niet binnen te gaan zolang er in je huis iemand schuilhoudt: {0}.",
    "NL-IR02-030": "Teacher: Neem me niet kwalijk, ik zie dat u gezelschap hebt. Wie is het — {0}?",
    "NL-IR02-036": "Fugitive: Dat kan ik niet… Vriend, ik ben zulke mensen wel eens tegengekomen. Kijk wie er bij jou in huis is: {0}.",
    "NL-IR02-037": "Nun: Zo, wie is hier bij u — {0}?",
}

NOTES = {
    "NL-IR02-003": "The source names shared room occupancy; retain the room while introducing the descriptor independently.",
    "NL-IR02-009": "The source expresses personal dislike, not an objective defect in the occupant.",
    "NL-IR02-012": "The Alkonost occupied line says someone is already sitting there; retain sitting rather than implying residence.",
    "NL-IR02-020": "The source reports dislike and pointing, but does not establish residence. Keep that observation and the male pointing pronoun while separating the descriptor.",
    "NL-IR02-023": "The speaker refuses to enter while the occupant is there; preserve refusal and location without implying the speaker entered.",
    "NL-IR02-025": "The source says someone is hiding in the house; retain the hiding action, house, and SUN command.",
    "NL-IR02-030": "The source says the teacher sees an occupant but asks for confirmation; preserve both observation and question.",
    "NL-IR02-036": "The source says someone is in the player's house, without establishing residence; retain location only.",
    "NL-IR02-037": "The source asks who is there, without establishing residence; use idiomatic Dutch while keeping the label attached to the question.",
    "NL-IR02-032": "The offered object is an inducement, not the shooting instrument. The player's gun remains the instrument.",
    "NL-IR02-039": "Accepted inventory text only: this exact key is absent from the pinned compiled program; live reachability is unverified.",
    "NL-IR02-040": "Accepted inventory text only: this exact key is absent from the pinned compiled program; live reachability is unverified.",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_new(path, content):
    assert not path.exists(), f"Immutable output exists: {path}"
    path.write_text(content)


def recipe():
    path = ROOT / "Translations/nl/semantic-cycle-1/prepare-and-apply.py"
    spec = importlib.util.spec_from_file_location("nl_cycle1_recipe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_inputs():
    previous = json.loads(PRIOR.read_text())
    evidence = json.loads((REVIEW / "evidence-manifest.json").read_text())
    findings = json.loads((REVIEW / "findings.json").read_text())
    assert evidence["sourceClosureManifestSha256"] == sha(PRIOR)
    assert evidence["sourceDeltaRowsSha256"] == sha(ROOT / previous["deltaReviewRowsPath"])
    assert evidence["reviewedPairs"] == findings["reviewedPairCount"] == 367
    assert findings["closureManifestSha256"] == sha(PRIOR)
    assert findings["deltaReviewRowsSha256"] == evidence["sourceDeltaRowsSha256"]
    assert evidence["findings"] == len(findings["findings"]) == 40
    for name, expected in evidence["files"].items():
        assert sha(REVIEW / name) == expected, name
    for item in previous["pins"].values():
        path = Path(item["path"])
        assert sha(path if path.is_absolute() else ROOT / path) == item["sha256"], item["path"]
    assert sha(ROOT / previous["consumerContextPath"]) == previous["consumerContextSha256"]
    assert sha(ROOT / previous["reviewRowsPath"]) == previous["reviewRowsSha256"]
    for item in previous["manual"]["authoredBatches"]:
        assert sha(ROOT / item["path"]) == item["sha256"], item["path"]
    for item in previous["components"].values():
        assert sha(ROOT / item["path"]) == item["sha256"], item["path"]
    decisions = [json.loads(line) for line in (REVIEW / "review-decisions.jsonl").open()]
    delta = [json.loads(line) for line in (ROOT / previous["deltaReviewRowsPath"]).open()]
    assert len(decisions) == len(delta) == 367
    assert [item["stableId"] for item in decisions] == [item["stableId"] for item in delta]
    for decision, row in zip(decisions, delta):
        assert decision["sourceSha256"] == row["sourceSha256"]
        assert decision["targetSha256"] == row["targetSha256"]
    return previous, evidence, findings["findings"], {row["stableId"]: row for row in delta}, decisions


def prepare():
    previous, evidence, findings, rows, decisions = verify_inputs()
    exact = recipe().load_exact_validator()
    manifest = json.loads((ROOT / "Source/preserve-exactly-v4.json").read_text())
    rules = {row["stableId"]: row for row in manifest["tableRows"] + manifest["staticRows"]}
    consumer = json.loads((REVIEW / "consumer-context.json").read_text())
    assert sha(ROOT / consumer["bindingPath"]) == consumer["bindingSha256"]
    unbound = set(consumer["unboundDeltaRows"])
    samples = json.loads((REVIEW / "dynamic-label-examples.json").read_text())["samples"]
    sample_by_id = {}
    for sample in samples:
        sample_by_id.setdefault(sample["stableId"], []).append(sample)
    records, previews = [], []
    assert len({f["stableId"] for f in findings}) == 40
    for finding in findings:
        sid = finding["stableId"]
        row = rows[sid]
        assert all(finding[key] == row[key] for key in ("source", "target", "sourceSha256", "targetSha256", "authoredPath", "key"))
        assert text_sha(finding["source"]) == finding["sourceSha256"]
        assert text_sha(finding["target"]) == finding["targetSha256"]
        assert text_sha(finding["proposedReplacement"]) == finding["proposedReplacementSha256"]
        assert any(d["stableId"] == sid and d["findingId"] == finding["findingId"] for d in decisions)
        after = REFINEMENTS.get(finding["findingId"], finding["proposedReplacement"])
        assert after != finding["target"] and after.split(": ", 1)[0] == finding["source"].split(": ", 1)[0]
        exact.check_value(rules[sid], after)
        assert after.count("{0}") == finding["target"].count("{0}")
        if sid in unbound:
            assert finding["findingId"] in ("NL-IR02-039", "NL-IR02-040")
        elif "{0}" in after:
            assert finding["consumerBindings"]
        record = {
            "findingId": finding["findingId"], "ordinal": finding["ordinal"], "stableId": sid,
            "authoredPath": finding["authoredPath"], "collection": finding["collection"],
            "key": finding["key"], "nodeNames": finding["nodeNames"],
            "source": finding["source"], "sourceSha256": finding["sourceSha256"],
            "before": finding["target"], "beforeSha256": finding["targetSha256"],
            "reviewProposal": finding["proposedReplacement"], "reviewProposalSha256": finding["proposedReplacementSha256"],
            "after": after, "afterSha256": text_sha(after),
            "decision": "accept with full-unit refinement" if finding["findingId"] in REFINEMENTS else "accept full-unit proposal",
            "objectiveReason": finding["reason"],
            "contextAdjudication": NOTES.get(finding["findingId"], "Russian full unit and bound scene preserve the occupant, action, address, and register; exact UI descriptor is introduced after a colon or dash."),
            "consumer": "accepted inventory text; compiled reachability unverified" if sid in unbound else "pinned compiled scene and exact article-free GetCharacterOnPlace UI label" if "{0}" in after else "pinned compiled bribe and gun scene",
            "protectedValueCheck": "passed unchanged shared preserve_exact.check_value",
        }
        records.append(record)
        for sample in sample_by_id.get(sid, []):
            previews.append({"stableId": sid, "labelKey": sample["labelKey"], "labelTarget": sample["labelTarget"],
                             "assembledAfter": after.replace("{0}", sample["labelTarget"])})
    assert records == sorted(records, key=lambda r: r["ordinal"])
    paths = sorted({r["authoredPath"] for r in records})
    old_hashes = [{"path": path, "sha256": sha(ROOT / path)} for path in paths]
    adjudication = {
        "schemaVersion": 1, "locale": "nl", "cycle": 3, "acceptedUnits": 16538,
        "previousClosurePath": str(PRIOR.relative_to(ROOT)), "previousClosureSha256": sha(PRIOR),
        "reviewEvidencePath": str((REVIEW / "evidence-manifest.json").relative_to(ROOT)),
        "reviewEvidenceSha256": sha(REVIEW / "evidence-manifest.json"),
        "reviewFindingsSha256": sha(REVIEW / "findings.json"),
        "reviewDecisionsSha256": sha(REVIEW / "review-decisions.jsonl"),
        "supersedesInitialAdjudicationSha256": sha(HERE / "adjudicated-corrections.json"),
        "supersedesInitialPreflightSha256": sha(HERE / "complete-batch-preflight.json"),
        "consumerContextSha256": sha(REVIEW / "consumer-context.json"),
        "pins": previous["pins"], "beforeAuthoredHashes": old_hashes,
        "corrections": records,
        "status": "40 full-unit corrections accepted after source, glossary, and consumer adjudication; independent delta pending",
    }
    write_new(ADJ, json.dumps(adjudication, ensure_ascii=False, indent=2) + "\n")
    preflight = {
        "schemaVersion": 1, "locale": "nl", "cycle": 3,
        "adjudicationSha256": sha(ADJ), "acceptedFullUnits": len(records),
        "changedAuthoredFiles": len(paths), "allProtectedValuesPassed": True,
        "allSourceAndTargetHashesMatched": True,
        "all367IndependentDecisionsMatched": True,
        "reviewerProposalsAcceptedExact": len(records) - len(REFINEMENTS),
        "reviewerProposalsAcceptedWithRefinement": len(REFINEMENTS),
        "sampleBoundary": "Exact label substitution illustrations; do not assert sample label is admissible for each scene or unbound key is live.",
        "assembledSamples": previews,
        "semanticBoundary": "Full Russian units and pinned compiled scene/consumer evidence adjudicated; static examples and syntax checks do not themselves establish semantics.",
    }
    write_new(PREFLIGHT, json.dumps(preflight, ensure_ascii=False, indent=2) + "\n")
    print(f"Preflighted {len(records)} full units in {len(paths)} batches; {len(previews)} assembled samples")


def apply():
    previous, _, _, _, _ = verify_inputs()
    adj = json.loads(ADJ.read_text())
    preflight = json.loads(PREFLIGHT.read_text())
    assert adj["previousClosureSha256"] == sha(PRIOR)
    assert preflight["adjudicationSha256"] == sha(ADJ) and preflight["allProtectedValuesPassed"]
    records = adj["corrections"]
    by_path = {}
    for record in records:
        by_path.setdefault(record["authoredPath"], {})[record["stableId"]] = record
    old_hashes = {item["path"]: item["sha256"] for item in adj["beforeAuthoredHashes"]}
    guids = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
             "UI": "0cbd8a7a4f543344bb95659de87f67a5",
             "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}
    helper = recipe()
    before, after, writes = [], [], []
    for path, changes in by_path.items():
        assert sha(ROOT / path) == old_hashes[path]
        doc = json.loads((ROOT / path).read_text())
        style = helper.original_style(doc, old_hashes[path])
        found = set()
        for entry in doc["entries"]:
            sid = f"string:{guids[doc['collection']]}:{entry['id']}"
            if sid not in changes:
                continue
            record = changes[sid]
            assert entry["target"] == record["before"]
            found.add(sid)
            before.append({"ordinal": record["ordinal"], "stableId": sid, "path": path,
                           "source": record["source"], "target": record["before"], "targetSha256": record["beforeSha256"]})
            entry["target"] = record["after"]
            after.append({"ordinal": record["ordinal"], "stableId": sid, "path": path,
                          "source": record["source"], "target": record["after"], "targetSha256": record["afterSha256"]})
        assert found == set(changes)
        writes.append((ROOT / path, helper.serialize_batch(doc, style)))
    assert len(before) == len(after) == 40
    before.sort(key=lambda r: r["ordinal"])
    after.sort(key=lambda r: r["ordinal"])
    write_new(HERE / "before-rows.jsonl", "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in before))
    write_new(HERE / "after-rows.jsonl", "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in after))
    for path, data in writes:
        path.write_text(data)
    print(f"Applied {len(after)} full-unit corrections to {len(writes)} authored batches")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "apply"])
    args = parser.parse_args()
    prepare() if args.action == "prepare" else apply()
