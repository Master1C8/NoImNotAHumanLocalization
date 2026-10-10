#!/usr/bin/env python3
"""Reconcile review 02 and preflight one consolidated Hebrew correction batch."""

import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CYCLE = Path(__file__).resolve().parent
HE = CYCLE.parent
PRIOR = HE / "semantic-correction-cycle-02"
IR = HE / "independent-review-02"
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import check_value
from authored_wording import WORDING

GUID = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
        "UI": "0cbd8a7a4f543344bb95659de87f67a5",
        "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def once(path, data):
    if path.exists():
        assert path.read_bytes() == data, f"immutable evidence differs: {path}"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def encoded(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode()


def ids_bytes(ids, order):
    return ("\n".join(sorted(ids, key=order.__getitem__)) + "\n").encode() if ids else b""


def main():
    gp = HE / "progress.json"
    sp = HE / "semantic-review-progress.json"
    gb, sb = gp.read_bytes(), sp.read_bytes()
    g, s = json.loads(gb), json.loads(sb)
    review = json.loads((IR / "final-review.json").read_text())
    findings = json.loads((IR / "final-findings.json").read_text())["findings"]
    decision_doc = json.loads((IR / "complete-review-decisions.json").read_text())
    decisions = decision_doc["decisions"]
    prior_manifest = json.loads((PRIOR / "closure-manifest.json").read_text())
    assert review["verdict"] == "corrections required" and review["editorialAcceptance"] is False
    assert review["acceptedUnits"] == s["acceptedUnits"] == s["reviewedUnits"] == 16538
    assert review["deltaReviewUnits"] == len(decisions) == 194 and len(findings) == 7
    assert sha(IR / "final-findings.json") == review["findings"]["sha256"]
    assert sha(IR / "complete-review-decisions.json") == review["decisions"]["sha256"]
    assert sha(PRIOR / "closure-manifest.json") == review["closureManifestSha256"]
    assert sha(PRIOR / "delta-review-rows.jsonl") == review["deltaRowsSha256"]
    assert prior_manifest["deltaIds"]["count"] == 194
    assert sha(PRIOR / "closure-ids.txt") == prior_manifest["closureIds"]["sha256"]
    assert sha(sp) == g["validation"]["semanticReviewProgressSha256"]
    assert s["postCorrection"]["cycle"] == 2
    assert sha(PRIOR / "independent-review-handoff.json") == s["postCorrection"]["handoffSha256"]
    assert len(s["firstPassFindings"]) == 120
    assert all(sha(ROOT / x["path"]) == x["sha256"] for x in g["files"])
    src = g["sourceInventory"]
    for key, hkey, reportkey in (("stringsPath", "stringsSha256", "sourceInventorySha256"),
                                 ("staticPath", "staticSha256", "staticInventorySha256"),
                                 ("preserveExactPath", "preserveExactSha256", "preserveExactSha256")):
        assert sha(ROOT / src[key]) == src[hkey] == review[reportkey]
    assert sha(Path(g["glossary"]["path"])) == g["glossary"]["sha256"] == review["glossarySha256"]
    rows = [json.loads(x) for x in (PRIOR / "delta-review-rows.jsonl").read_text().splitlines()]
    assert len(rows) == len(decisions)
    for i, (row, d) in enumerate(zip(rows, decisions)):
        assert row["stableId"] == d["stableId"] and d["deltaOrdinalZeroBased"] == i
        assert d["sourceValueSha256"] == digest(row["source"].encode())
        assert d["currentTargetValueSha256"] == digest(row["after"].encode())
        assert row["components"] == d["components"] and row["deltaReasons"] == d["deltaReasons"]
        assert d["protectedSyntax"] == "pass" and d["fullPairRead"] is True
    linked = {d["findingId"] for d in decisions if d["findingId"]}
    assert linked == {f["findingId"] for f in findings}
    for f in findings:
        d = decisions[f["deltaOrdinalZeroBased"]]
        assert d["stableId"] == f["stableId"] and d["findingId"] == f["findingId"]
        assert rows[f["deltaOrdinalZeroBased"]]["after"] == f["currentTarget"]
        assert digest(f["source"].encode()) == f["sourceValueSha256"]
        assert digest(f["currentTarget"].encode()) == f["currentTargetValueSha256"]
        assert digest(f["proposedFullTarget"].encode()) == f["proposedTargetValueSha256"]
        assert sha(ROOT / f["path"]) == f["authoredFileSha256"]
    once(CYCLE / "baseline-progress.json", gb)
    once(CYCLE / "baseline-semantic-review-progress.json", sb)
    pins = {"schemaVersion": 1, "status": "all review-02 inputs reconciled before authored edits",
        "gameVersion": "1.3.19", "sourceLocale": "ru", "locale": "he", "acceptedUnits": 16538,
        "sourceInventory": {k: src[k] for k in ("stringsPath", "stringsSha256", "staticPath", "staticSha256", "preserveExactPath", "preserveExactSha256")},
        "glossary": g["glossary"], "priorProgressSha256": digest(gb),
        "priorSemanticProgressSha256": digest(sb),
        "priorClosureManifestSha256": sha(PRIOR / "closure-manifest.json"),
        "priorClosureIdsSha256": sha(PRIOR / "closure-ids.txt"),
        "priorDeltaRowsSha256": sha(PRIOR / "delta-review-rows.jsonl"),
        "independentFinalReviewSha256": sha(IR / "final-review.json"),
        "independentFinalFindingsSha256": sha(IR / "final-findings.json"),
        "independentDecisionsSha256": sha(IR / "complete-review-decisions.json"),
        "authoredWordingSha256": sha(CYCLE / "authored_wording.py")}
    once(CYCLE / "input-pins.json", encoded(pins))
    once(CYCLE / "reviewer-decision-reconciliation.json", encoded({
        "schemaVersion": 1, "status": "194/194 reviewed source/target/decision hashes reconciled",
        "inputPinsSha256": sha(CYCLE / "input-pins.json"), "reviewedRows": 194,
        "sourceValueHashMatches": 194, "targetValueHashMatches": 194,
        "componentAndDeltaMatches": 194, "findingLinks": 7,
        "valueHashConvention": "SHA-256 of raw UTF-8 string value"}))
    rules = json.loads((ROOT / src["preserveExactPath"]).read_text())
    accepted = rules["tableRows"] + rules["staticRows"]
    order = {r["stableId"]: i for i, r in enumerate(accepted)}
    by_rule = {r["stableId"]: r for r in accepted}
    assert len(order) == 16538
    source = {r["stableId"]: r for r in map(json.loads, (ROOT / src["stringsPath"]).open())}
    source.update({r["stableId"]: r for r in map(json.loads, (ROOT / src["staticPath"]).open())})
    assert set(order) <= set(source)
    findings_by_id = {f["stableId"]: f for f in findings}
    changes = defaultdict(dict)
    adjudications = []
    # Locate every directly authored unit by stable ID, preserving batch offsets.
    current = {}
    for x in g["files"]:
        rel = x["path"]
        if not re.search(r"(?:dialogue|ui|checks)-batch-\d{3}\.json$", rel):
            continue
        obj = json.loads((ROOT / rel).read_text())
        for offset, row in enumerate(obj["entries"]):
            sid = f"string:{GUID[obj['collection']]}:{row['id']}"
            assert sid not in current
            current[sid] = {"path": rel, "offset": offset, "id": row["id"], "target": row["target"]}
    assert len(current) == 16360
    for number, target in WORDING.items():
        sid = f"string:{GUID['Dialogs']}:{number}"
        assert sid in order and sid in current
        row = current[sid]
        source_value = source[sid]["source"]
        assert target != row["target"]
        assert target.startswith(source_value.split(":", 1)[0] + ": ")
        check_value(by_rule[sid], target)
        finding = findings_by_id.get(sid)
        if finding:
            assert finding["currentTarget"] == row["target"] and finding["source"] == source_value
            category = "independent-review-02"
            reason = finding["reason"]
        elif source_value.startswith("Nun: "):
            category = "bounded-nun-single-householder-address"
            reason = "The compiled Nun branch addresses the one male householder; Russian formal Вы/imperative was incorrectly rendered as Hebrew plural. Distinct third-party plurals are retained."
        else:
            assert source_value.startswith("Bald: ") and re.search(r"(?i)пизд|хуй|хер", source_value)
            category = "bounded-bald-coarse-register"
            reason = "Explicit Russian profanity in Bald's established coarse voice was neutralized; restore a coarse full-unit assessment while retaining all other facts."
        assert row["id"] not in changes[row["path"]]
        changes[row["path"]][row["id"]] = target
        adjudications.append({"stableId": sid, "category": category,
            "findingId": finding["findingId"] if finding else None,
            "source": source_value, "before": row["target"], "after": target,
            "reviewerProposal": finding["proposedFullTarget"] if finding else None,
            "path": row["path"], "offset": row["offset"], "id": row["id"],
            "reason": reason, "nodeNames": source[sid].get("nodeNames", []),
            "sourceValueSha256": digest(source_value.encode()),
            "beforeValueSha256": digest(row["target"].encode()),
            "afterValueSha256": digest(target.encode())})
    assert len(adjudications) == len(WORDING) == 71
    assert sum(a["category"] == "independent-review-02" for a in adjudications) == 7
    assert sum(a["category"] == "bounded-nun-single-householder-address" for a in adjudications) == 61
    assert sum(a["category"] == "bounded-bald-coarse-register" for a in adjudications) == 3
    # Stage byte-preserving replacement of only target values.
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
        old_obj, new_obj = json.loads(before), json.loads(after)
        assert old_obj.keys() == new_obj.keys()
        assert len(old_obj["entries"]) == len(new_obj["entries"])
        for a, b in zip(old_obj["entries"], new_obj["entries"]):
            assert a["id"] == b["id"] and b["target"] == replacements.get(a["id"], a["target"])
        once(CYCLE / "before-authored" / path.name, before)
        once(CYCLE / "after-authored" / path.name, after)
        rendered[rel] = {"beforeSha256": digest(before), "afterSha256": digest(after),
                         "changedIds": sorted(replacements), "authoredRows": len(new_obj["entries"])}
    targets = {}
    for x in g["files"]:
        rel = x["path"]
        if not re.search(r"(?:dialogue|ui|checks)-batch-\d{3}\.json$", rel):
            continue
        path = CYCLE / "after-authored" / Path(rel).name if rel in rendered else ROOT / rel
        batch = json.loads(path.read_text())
        assert batch["locale"] == "he"
        for row in batch["entries"]:
            sid = f"string:{GUID[batch['collection']]}:{row['id']}"
            assert sid in order and sid not in targets
            targets[sid] = row["target"]
    for row in json.loads((HE / "static-text-draft.json").read_text())["entries"]:
        sid = row["stableId"]
        assert sid in order and sid not in targets
        targets[sid] = row["target"]
    assert len(targets) == len(order) == 16538 and set(targets) == set(order)
    for sid, value in targets.items():
        check_value(by_rule[sid], value)
    changed = {x["stableId"] for x in adjudications}
    once(CYCLE / "changed-ids.txt", ids_bytes(changed, order))
    once(CYCLE / "adjudications.json", encoded({"schemaVersion": 1,
        "status": "all 71 objective full-unit corrections accepted and preflighted; application pending",
        "inputPinsSha256": sha(CYCLE / "input-pins.json"),
        "reviewerFindings": 7, "boundedNunFindings": 61, "boundedBaldFindings": 3,
        "records": sorted(adjudications, key=lambda x: order[x["stableId"]])}))
    once(CYCLE / "preflight.json", encoded({"schemaVersion": 1,
        "status": "passed before authored application", "acceptedUnits": 16538,
        "acceptedCorrections": 71, "changedAuthoredFiles": len(rendered),
        "protectedRuntimeSyntax": "preserve_exact.check_value passed on all 16538 staged targets",
        "sourceTargetLinks": "7 reviewer links and 64 bounded remedial links verified against source/current authored values",
        "files": rendered, "inputPinsSha256": sha(CYCLE / "input-pins.json"),
        "adjudicationsSha256": sha(CYCLE / "adjudications.json"),
        "changedIdsSha256": sha(CYCLE / "changed-ids.txt")}))
    print(json.dumps({"result": "preflight-passed", "acceptedUnits": len(targets),
                      "corrections": len(changed), "changedFiles": len(rendered),
                      "preflightSha256": sha(CYCLE / "preflight.json")}))


if __name__ == "__main__":
    main()
