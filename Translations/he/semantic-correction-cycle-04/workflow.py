#!/usr/bin/env python3
"""Reproducible Hebrew review-03 correction, preflight, and delta evidence.

Run prepare, apply, then close. Each phase verifies its predecessor's hashes.
The Bald voice ledger enumerates the entire accepted speaker roster; the
classification is an editorial source read, not a regex used as proof.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CYCLE = Path(__file__).resolve().parent
HE = CYCLE.parent
PRIOR = HE / "semantic-correction-cycle-03"
IR = HE / "independent-review-03"
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import check_value, validate

GUID = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
        "UI": "0cbd8a7a4f543344bb95659de87f67a5",
        "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}

# Positions in the canonical, source-inventory-order 132-line Bald speaker roster.
# Every position, including the 93 noncoarse controls, is pinned below in the
# ledger. The 39 marked positions encompass literal, slang-spelled, inflected,
# euphemistic, and curse variants observed during the complete roster read.
COARSE_POSITIONS = {1, 4, 8, 11, 12, 18, 21, 23, 25, 28, 32, 33, 34, 35,
                    45, 47, 48, 49, 52, 53, 56, 74, 75, 79, 85, 88, 90,
                    91, 92, 94, 95, 104, 105, 107, 118, 119, 121, 122, 124}
CONTROL_POSITIONS = {11, 56, 74, 91, 92, 118, 121, 122}
LOSS_POSITIONS = {11, 56, 91, 92, 122}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(Path(path).read_bytes())


def encoded(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode()


def once(path, data):
    if path.exists():
        assert path.read_bytes() == data, f"immutable evidence differs: {path}"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def lines(ids, order):
    return ("\n".join(sorted(ids, key=order.__getitem__)) + "\n").encode() if ids else b""


def ref(path, **extra):
    return {"path": str(path.relative_to(ROOT)), "sha256": sha(path), **extra}


def load():
    progress = json.loads((HE / "progress.json").read_text())
    semantic = json.loads((HE / "semantic-review-progress.json").read_text())
    review = json.loads((IR / "final-review.json").read_text())
    findings = json.loads((IR / "final-findings.json").read_text())["findings"]
    decisions = json.loads((IR / "complete-review-decisions.json").read_text())["decisions"]
    controls = json.loads((IR / "selector-controls.json").read_text())["rows"]
    prior_manifest = json.loads((PRIOR / "closure-manifest.json").read_text())
    rules = json.loads((ROOT / progress["sourceInventory"]["preserveExactPath"]).read_text())
    accepted = rules["tableRows"] + rules["staticRows"]
    order = {x["stableId"]: i for i, x in enumerate(accepted)}
    source = {x["stableId"]: x for x in map(json.loads, (ROOT / progress["sourceInventory"]["stringsPath"]).open())}
    source.update({x["stableId"]: x for x in map(json.loads, (ROOT / progress["sourceInventory"]["staticPath"]).open())})
    assert len(accepted) == len(order) == 16538 and set(order) <= set(source)
    return progress, semantic, review, findings, decisions, controls, prior_manifest, accepted, order, source


def current_values(progress):
    values = {}
    positions = {}
    for entry in progress["files"]:
        rel = entry["path"]
        if not re.search(r"(?:dialogue|ui|checks)-batch-\d{3}\.json$", rel):
            continue
        batch = json.loads((ROOT / rel).read_text())
        for offset, row in enumerate(batch["entries"]):
            sid = f"string:{GUID[batch['collection']]}:{row['id']}"
            assert sid not in values
            values[sid] = row["target"]
            positions[sid] = {"path": rel, "offset": offset, "id": row["id"]}
    assert len(values) == 16360
    for row in json.loads((HE / "static-text-draft.json").read_text())["entries"]:
        sid = row["stableId"]
        assert sid not in values
        values[sid] = row["target"]
    assert len(values) == 16538
    return values, positions


def reconcile():
    p, s, r, findings, decisions, controls, pm, accepted, order, source = load()
    assert r["verdict"] == "corrections required" and not r["editorialAcceptance"]
    assert s["reviewedUnits"] == s["acceptedUnits"] == r["acceptedUnits"] == 16538
    assert s["postCorrection"]["cycle"] == 3
    assert sha(PRIOR / "independent-review-handoff.json") == s["postCorrection"]["handoffSha256"]
    assert sha(PRIOR / "closure-manifest.json") == r["closureManifestSha256"]
    assert sha(PRIOR / "delta-review-rows.jsonl") == r["deltaRowsSha256"]
    assert sha(IR / "final-findings.json") == r["findings"]["sha256"]
    assert sha(IR / "complete-review-decisions.json") == r["decisions"]["sha256"]
    manifest = json.loads((IR / "final-evidence-manifest.json").read_text())
    assert all(sha(ROOT / x["path"]) == x["sha256"] for x in manifest["files"])
    src = p["sourceInventory"]
    for key, rv in (("stringsPath", "sourceInventorySha256"),
                    ("staticPath", "staticInventorySha256"),
                    ("preserveExactPath", "preserveExactSha256")):
        assert sha(ROOT / src[key]) == r[rv]
    assert sha(ROOT / p["glossary"]["path"]) == p["glossary"]["sha256"] == r["glossarySha256"]
    assert all(sha(ROOT / x["path"]) == x["sha256"] for x in p["files"])
    rows = [json.loads(x) for x in (PRIOR / "delta-review-rows.jsonl").read_text().splitlines()]
    assert len(rows) == len(decisions) == 269 and len(findings) == 14 and len(controls) == 8
    for i, (row, d) in enumerate(zip(rows, decisions)):
        assert row["stableId"] == d["stableId"] and i == d["deltaOrdinalZeroBased"]
        assert digest(row["source"].encode()) == d["sourceValueSha256"]
        assert digest(row["after"].encode()) == d["currentTargetValueSha256"]
        assert d["fullPairRead"] and d["protectedSyntax"] == "pass"
    vals, pos = current_values(p)
    assert set(vals) == set(order)
    for f in findings:
        sid = f["stableId"]
        assert source[sid]["source"] == f["source"] and vals[sid] == f["currentTarget"]
        assert pos[sid]["path"] == f["path"] and pos[sid]["offset"] == f["offset"]
        assert sha(ROOT / f["path"]) == f["authoredFileSha256"]
        assert digest(f["proposedFullTarget"].encode()) == f["proposedTargetValueSha256"]
    for c in controls:
        sid = c["stableId"]
        assert source[sid]["source"] == c["source"] and vals[sid] == c["currentTarget"]
        assert digest(vals[sid].encode()) == c["currentTargetValueSha256"]
    assert pm["closureIds"]["count"] == 2382
    assert sha(PRIOR / "closure-ids.txt") == pm["closureIds"]["sha256"]
    return p, s, r, findings, decisions, controls, pm, accepted, order, source, vals, pos


def bald_ledger(source, vals, order, controls):
    roster = [x for x in source.values() if x.get("collection") == "Dialogs"
              and x["source"].startswith("Bald: ") and x["stableId"] in order]
    roster.sort(key=lambda x: order[x["stableId"]])
    assert len(roster) == 132 and max(COARSE_POSITIONS | CONTROL_POSITIONS) <= len(roster)
    control_by = {x["stableId"]: x for x in controls}
    result = []
    for i, x in enumerate(roster, 1):
        sid = x["stableId"]
        row = {"rosterPosition": i, "stableId": sid, "nodeNames": x.get("nodeNames", []),
               "source": x["source"], "targetBefore": vals[sid],
               "sourceSha256": digest(x["source"].encode()),
               "targetBeforeSha256": digest(vals[sid].encode()),
               "sourceVoiceClass": "coarse/slang register" if i in COARSE_POSITIONS else "no coarse-register dependency",
               "dependencySelected": i in COARSE_POSITIONS,
               "review03Control": i in CONTROL_POSITIONS,
               "review03ControlDecision": ("objective correction required" if i in LOSS_POSITIONS else
                                           "register retained") if i in CONTROL_POSITIONS else None}
        if i in CONTROL_POSITIONS:
            assert sid in control_by
            assert (control_by[sid]["decision"] == "objective correction required") == (i in LOSS_POSITIONS)
        result.append(row)
    assert len(control_by) == 8
    assert sum(x["dependencySelected"] for x in result) == 39
    return result


def prepare():
    p, s, r, findings, decisions, controls, pm, accepted, order, source, vals, pos = reconcile()
    assert not (CYCLE / "application.json").exists(), "already applied"
    once(CYCLE / "baseline-progress.json", (HE / "progress.json").read_bytes())
    once(CYCLE / "baseline-semantic-review-progress.json", (HE / "semantic-review-progress.json").read_bytes())
    pins = {"schemaVersion": 1, "status": "review-03 and current source/author pins reconciled before edit",
            "sourceInventory": p["sourceInventory"], "glossary": p["glossary"],
            "priorProgressSha256": sha(HE / "progress.json"),
            "priorSemanticProgressSha256": sha(HE / "semantic-review-progress.json"),
            "priorClosureManifestSha256": sha(PRIOR / "closure-manifest.json"),
            "priorClosureIdsSha256": sha(PRIOR / "closure-ids.txt"),
            "priorDeltaRowsSha256": sha(PRIOR / "delta-review-rows.jsonl"),
            "review03Sha256": sha(IR / "final-review.json"),
            "review03FindingsSha256": sha(IR / "final-findings.json"),
            "review03DecisionsSha256": sha(IR / "complete-review-decisions.json"),
            "review03EvidenceManifestSha256": sha(IR / "final-evidence-manifest.json"),
            "review03SelectorControlsSha256": sha(IR / "selector-controls.json"),
            "authoredFileCount": len(p["files"]), "reviewedDeltaPairs": 269,
            "reviewerFindings": 14, "additionalControls": 8}
    once(CYCLE / "input-pins.json", encoded(pins))
    once(CYCLE / "reviewer-decision-reconciliation.json", encoded({
        "schemaVersion": 1, "status": "all 269 reviewer decisions, 14 findings and 8 controls matched current values and SHA-256 pins",
        "inputPinsSha256": sha(CYCLE / "input-pins.json"), "reviewedPairs": 269,
        "findings": 14, "controls": 8, "objectiveFindingLinks": 9,
        "valueHashConvention": "SHA-256 of raw UTF-8 string value"}))
    roster = bald_ledger(source, vals, order, controls)
    once(CYCLE / "bald-voice-roster-ledger.json", encoded({
        "schemaVersion": 1, "status": "complete bounded author source/target voice reconciliation; not independent review",
        "sourceInventorySha256": r["sourceInventorySha256"], "acceptedBaldSpeakerRows": 132,
        "coarseOrSlangSourceRows": 39, "review03Controls": 8, "review03ControlCorrections": 5,
        "classificationRule": "Every one of 132 accepted Bald speaker source and target values read in canonical source order; explicit per-row editorial class, including misspellings, inflections, euphemisms and curse forms. New inventory or value hashes require a new ledger.",
        "rows": roster}))
    by_rule = {x["stableId"]: x for x in accepted}
    changes = defaultdict(dict)
    records = []
    for f in findings:
        sid = f["stableId"]
        target = f["proposedFullTarget"]
        assert target != vals[sid]
        check_value(by_rule[sid], target)
        assert target.startswith(source[sid]["source"].split(":", 1)[0] + ": ") if source[sid]["source"].startswith(("Bald: ", "Nun: ")) else True
        location = pos[sid]
        assert location["id"] not in changes[location["path"]]
        changes[location["path"]][location["id"]] = target
        records.append({"stableId": sid, "findingId": f["findingId"], "path": location["path"],
                        "offset": location["offset"], "id": location["id"],
                        "source": source[sid]["source"], "before": vals[sid], "after": target,
                        "reason": f["reason"], "nodeNames": source[sid].get("nodeNames", []),
                        "sourceValueSha256": digest(source[sid]["source"].encode()),
                        "beforeValueSha256": digest(vals[sid].encode()),
                        "afterValueSha256": digest(target.encode()),
                        "decision": "accepted objective full-unit correction after source, glossary and compiled-node adjudication"})
    assert len(records) == 14 and len(changes) == 5
    records.sort(key=lambda x: order[x["stableId"]])
    once(CYCLE / "adjudications.json", encoded({"schemaVersion": 1,
        "status": "14/14 objective full-unit findings accepted; eight selector controls reconciled; other Bald roster rows unchanged",
        "inputPinsSha256": sha(CYCLE / "input-pins.json"),
        "baldVoiceLedgerSha256": sha(CYCLE / "bald-voice-roster-ledger.json"),
        "records": records}))
    once(CYCLE / "changed-ids.txt", lines({x["stableId"] for x in records}, order))
    rendered = {}
    entry_re = re.compile(r'"id"\s*:\s*(\d+)\s*,\s*"target"\s*:\s*')
    for rel, replacements in changes.items():
        path = ROOT / rel
        before = path.read_bytes()
        content = before.decode()
        seen, spans = set(), []
        for m in entry_re.finditer(content):
            identifier = int(m.group(1))
            if identifier in replacements:
                assert identifier not in seen
                seen.add(identifier)
                old, n = json.JSONDecoder().raw_decode(content[m.end():])
                assert isinstance(old, str)
                spans.append((m.end(), m.end() + n, json.dumps(replacements[identifier], ensure_ascii=False)))
        assert seen == set(replacements)
        for start, end, new in sorted(spans, reverse=True):
            content = content[:start] + new + content[end:]
        after = content.encode()
        a, b = json.loads(before), json.loads(after)
        assert list(a) == list(b) and len(a["entries"]) == len(b["entries"])
        for x, y in zip(a["entries"], b["entries"]):
            assert x["id"] == y["id"] and y["target"] == replacements.get(x["id"], x["target"])
        once(CYCLE / "before-authored" / path.name, before)
        once(CYCLE / "after-authored" / path.name, after)
        rendered[rel] = {"beforeSha256": digest(before), "afterSha256": digest(after),
                         "changedIds": sorted(replacements), "authoredRows": len(b["entries"])}
    staged_values = dict(vals)
    for x in records:
        staged_values[x["stableId"]] = x["after"]
    assert len(staged_values) == 16538
    for sid, value in staged_values.items():
        check_value(by_rule[sid], value)
    once(CYCLE / "preflight.json", encoded({"schemaVersion": 1,
        "status": "passed before authored application", "acceptedUnits": 16538,
        "acceptedCorrections": 14, "changedAuthoredFiles": len(rendered),
        "sourceAndScene": "Full 14 Russian units, approved glossary and actual compiled nodes adjudicated; unchanged facts retained",
        "protectedRuntimeSyntax": "preserve_exact.check_value passed on all 16538 staged values",
        "consumerPreflight": "No corrected unit has a format slot; compiled options and continuations were checked as whole displayed units",
        "inputPinsSha256": sha(CYCLE / "input-pins.json"),
        "adjudicationsSha256": sha(CYCLE / "adjudications.json"),
        "changedIdsSha256": sha(CYCLE / "changed-ids.txt"), "files": rendered}))
    checked = []
    for rel in sorted(rendered):
        path = CYCLE / "after-authored" / Path(rel).name
        result = subprocess.run([str(ROOT / ".venv/bin/python"), str(ROOT / "Scripts/validate_game_text_batch.py"), str(path)],
                                cwd=ROOT, text=True, capture_output=True)
        assert result.returncode == 0, (rel, result.stdout, result.stderr)
        report = json.loads(result.stdout)
        assert report["batchSha256"] == sha(path) and report["structuralResult"] == "passed"
        checked.append({"path": str(path.relative_to(ROOT)), "sha256": sha(path),
                        "sidecarSha256": sha(path.with_suffix(".validation.json"))})
    once(CYCLE / "staged-validation-summary.json", encoded({"schemaVersion": 1,
        "status": "passed before authored application", "validatedStagedFiles": len(checked),
        "files": checked, "preflightSha256": sha(CYCLE / "preflight.json")}))
    print(json.dumps({"phase": "prepare", "corrections": 14, "changedFiles": len(rendered),
                      "stagedValidation": len(checked), "preflightSha256": sha(CYCLE / "preflight.json")}))


def apply():
    pre = json.loads((CYCLE / "preflight.json").read_text())
    pins = json.loads((CYCLE / "input-pins.json").read_text())
    staged = json.loads((CYCLE / "staged-validation-summary.json").read_text())
    consumer = json.loads((CYCLE / "compiled-consumer-preflight.json").read_text())
    assert pre["status"] == staged["status"] == "passed before authored application"
    assert pre["acceptedCorrections"] == 14 and staged["validatedStagedFiles"] == len(pre["files"])
    assert consumer["status"] == "passed before authored application" and consumer["changedCompiledUnits"] == 14
    assert sha(HE / "progress.json") == pins["priorProgressSha256"]
    assert sha(HE / "semantic-review-progress.json") == pins["priorSemanticProgressSha256"]
    assert sha(CYCLE / "preflight.json") == staged["preflightSha256"]
    for key, path in (("review03Sha256", IR / "final-review.json"),
                      ("review03FindingsSha256", IR / "final-findings.json"),
                      ("review03DecisionsSha256", IR / "complete-review-decisions.json"),
                      ("priorClosureManifestSha256", PRIOR / "closure-manifest.json")):
        assert sha(path) == pins[key]
    baseline = json.loads((CYCLE / "baseline-progress.json").read_text())
    for x in baseline["files"]:
        rel = x["path"]
        if rel not in pre["files"]:
            assert sha(ROOT / rel) == x["sha256"]
        else:
            assert sha(ROOT / rel) in (pre["files"][rel]["beforeSha256"], pre["files"][rel]["afterSha256"])
    for rel, x in pre["files"].items():
        assert sha(CYCLE / "before-authored" / Path(rel).name) == x["beforeSha256"]
        assert sha(CYCLE / "after-authored" / Path(rel).name) == x["afterSha256"]
    for x in staged["files"]:
        path = ROOT / x["path"]
        assert sha(path) == x["sha256"] and sha(path.with_suffix(".validation.json")) == x["sidecarSha256"]
    applied = 0
    for rel, x in sorted(pre["files"].items()):
        path = ROOT / rel
        if sha(path) == x["afterSha256"]:
            continue
        temp = path.with_name(path.name + ".he-cycle04-tmp")
        assert not temp.exists()
        temp.write_bytes((CYCLE / "after-authored" / path.name).read_bytes())
        assert sha(temp) == x["afterSha256"]
        os.replace(temp, path)
        assert sha(path) == x["afterSha256"]
        applied += 1
    receipt = {"schemaVersion": 1, "status": "applied", "changedStableIds": 14,
               "changedAuthoredFiles": len(pre["files"]), "appliedThisRun": applied,
               "preflightSha256": sha(CYCLE / "preflight.json"),
               "stagedValidationSummarySha256": sha(CYCLE / "staged-validation-summary.json"),
               "compiledConsumerPreflightSha256": sha(CYCLE / "compiled-consumer-preflight.json"),
               "files": pre["files"],
               "commitBoundary": "Each authored file was atomically replaced; the multi-file set was not a transaction. All after hashes verified before this receipt."}
    once(CYCLE / "application.json", encoded(receipt))
    print(json.dumps({"phase": "apply", "appliedFiles": applied,
                      "applicationSha256": sha(CYCLE / "application.json")}))


def consumer():
    pre = json.loads((CYCLE / "preflight.json").read_text())
    assert pre["status"] == "passed before authored application"
    records = json.loads((CYCLE / "adjudications.json").read_text())["records"]
    progress = json.loads((CYCLE / "baseline-progress.json").read_text())
    src = {x["stableId"]: x for x in map(json.loads, (ROOT / progress["sourceInventory"]["stringsPath"]).open())}
    by_key = {x["key"]: x for x in src.values() if x.get("key")}
    compiled = {}
    files = [IR / "compiled-scene-context.json", IR / "additional-compiled-scene-context.json"]
    for path in files:
        compiled.update(json.loads(path.read_text())["nodes"])
    output = []
    for x in records:
        source_row = src[x["stableId"]]
        assert source_row["source"] == x["source"]
        key = source_row["key"]
        nodes = []
        for node in source_row["nodeNames"]:
            operations = compiled.get(node)
            assert operations is not None, (x["stableId"], node)
            matches = [i for i, op in enumerate(operations)
                       if op["opcode"] in (2, 4) and op["operands"][0] == key]
            assert len(matches) == 1, (x["stableId"], node, matches)
            index = matches[0]
            neighbors = []
            for op in operations[max(0, index - 2): index + 3]:
                if op["opcode"] in (2, 4) and op["operands"][0] in by_key:
                    row = by_key[op["operands"][0]]
                    neighbors.append({"stableId": row["stableId"], "source": row["source"]})
            nodes.append({"node": node, "opcode": operations[index]["opcode"],
                          "operationIndex": index, "key": key, "nearbySource": neighbors})
        assert nodes
        assert not re.search(r"\{\d+\}|<[^<>]+>", x["after"])
        output.append({"stableId": x["stableId"], "source": x["source"],
                       "beforeDisplayed": x["before"], "afterDisplayed": x["after"],
                       "nodes": nodes, "displayMode": "complete compiled line or option; no dynamic token in changed unit"})
    once(CYCLE / "compiled-consumer-preflight.json", encoded({
        "schemaVersion": 1, "status": "passed before authored application",
        "changedCompiledUnits": len(output), "compiledContextHashes": [ref(x) for x in files],
        "sourceInventorySha256": sha(ROOT / progress["sourceInventory"]["stringsPath"]),
        "scope": "Actual compiled opcode-2 lines and opcode-4 player choices with adjacent source context; no changed format-slot assembly",
        "nodes": output}))
    print(json.dumps({"phase": "consumer", "compiledUnits": len(output),
                      "sha256": sha(CYCLE / "compiled-consumer-preflight.json")}))


if __name__ == "__main__":
    assert len(sys.argv) == 2 and sys.argv[1] in {"prepare", "consumer", "apply"}
    {"prepare": prepare, "consumer": consumer, "apply": apply}[sys.argv[1]]()
