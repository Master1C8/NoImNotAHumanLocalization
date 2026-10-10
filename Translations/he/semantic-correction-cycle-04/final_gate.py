#!/usr/bin/env python3
"""Verify cycle-04 selector controls, mandatory regressions, and handoff pins."""

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CYCLE = Path(__file__).resolve().parent
HE = CYCLE.parent
IR = HE / "independent-review-03"
PRIOR = HE / "semantic-correction-cycle-03"
sys.path.insert(0, str(CYCLE))
sys.path.insert(0, str(ROOT / "Scripts"))
from workflow import sha, encoded, once, ref, current_values
from preserve_exact import check_value

FORMS = {
    "110504457400295426": ["ахуитительных", "ахуеешь"],
    "110504455806459912": ["хуесосили"],
    "110504453986131971": ["гнида"],
    "110504453977743370": ["писос"],
    "110504453977743369": ["обосрался"],
    "110504453965160450": ["Чёрт"],
    "110504453960966154": ["пересрись"],
    "110504453960966151": ["хрен", "обосрался"],
}


def main():
    manifest = json.loads((CYCLE / "closure-manifest.json").read_text())
    handoff = json.loads((CYCLE / "independent-review-handoff.json").read_text())
    structural = json.loads((CYCLE / "full-structural-diff.json").read_text())
    baseline = json.loads((CYCLE / "baseline-progress.json").read_text())
    values, _ = current_values(baseline)
    source = {x["stableId"]: x for x in map(json.loads, (ROOT / baseline["sourceInventory"]["stringsPath"]).open())}
    source.update({x["stableId"]: x for x in map(json.loads, (ROOT / baseline["sourceInventory"]["staticPath"]).open())})
    rules = json.loads((ROOT / baseline["sourceInventory"]["preserveExactPath"]).read_text())
    by_rule = {x["stableId"]: x for x in rules["tableRows"] + rules["staticRows"]}
    changed = set((CYCLE / "changed-ids.txt").read_text().splitlines())
    old = set((PRIOR / "closure-ids.txt").read_text().splitlines())
    current = set((CYCLE / "closure-ids.txt").read_text().splitlines())
    new = set((CYCLE / "new-closure-ids.txt").read_text().splitlines())
    invalidated = set((CYCLE / "explicitly-invalidated-ids.txt").read_text().splitlines())
    retired = set((CYCLE / "retired-ids.txt").read_text().splitlines())
    delta = set((CYCLE / "delta-ids.txt").read_text().splitlines())
    assert new == current - old and retired == old - current
    assert delta == changed | new | invalidated and invalidated <= old
    assert len(changed) == 14 and len(current) == 2407 and len(new) == 25
    assert len(invalidated) == 37 and len(delta) == 72 and not retired
    assert handoff["deltaReviewCount"] == len(delta)
    for key in ("changedIds", "previousClosureIds", "closureIds", "newClosureIds",
                "explicitlyInvalidatedIds", "retiredIds", "deltaIds", "reviewRows", "deltaReviewRows", "runtimeContext"):
        x = manifest[key]
        assert sha(ROOT / x["path"]) == x["sha256"]
    for x in manifest["components"].values():
        assert sha(ROOT / x["path"]) == x["sha256"]
    assert sha(CYCLE / "close.py") == manifest["selectorScriptSha256"]
    assert sha(CYCLE / "workflow.py") == manifest["workflowScriptSha256"]
    controls = json.loads((IR / "selector-controls.json").read_text())["rows"]
    assert len(controls) == len(FORMS) == 8
    examples = []
    for x in controls:
        sid = x["stableId"]
        number = sid.rsplit(":", 1)[1]
        forms = FORMS[number]
        assert all(form in source[sid]["source"] for form in forms)
        assert sid in current and sid in delta
        assert source[sid]["source"] == x["source"]
        assert x["currentTarget"] == next(z["targetBefore"] for z in json.loads((CYCLE / "bald-voice-roster-ledger.json").read_text())["rows"] if z["stableId"] == sid)
        expected_changed = x["decision"] == "objective correction required"
        assert (sid in changed) == expected_changed
        examples.append({"stableId": sid, "sourceForms": forms, "source": x["source"],
                         "before": x["currentTarget"], "after": values[sid],
                         "review03Decision": x["decision"],
                         "previousClosure": sid in old, "currentClosure": sid in current,
                         "currentDelta": sid in delta,
                         "sourceValueSha256": x["sourceValueSha256"],
                         "beforeValueSha256": x["currentTargetValueSha256"],
                         "afterValueSha256": hashlib.sha256(values[sid].encode()).hexdigest()})
    assert sum(x["previousClosure"] for x in examples) == 1
    assert sum(x["review03Decision"] == "objective correction required" for x in examples) == 5
    once(CYCLE / "selector-regression-spec.json", encoded({
        "schemaVersion": 1,
        "status": "all eight missed-variant controls now selected by complete 132-row source-voice ledger",
        "sourceInventorySha256": baseline["sourceInventory"]["stringsSha256"],
        "rosterLedger": ref(CYCLE / "bald-voice-roster-ledger.json", acceptedSpeakerRows=132, riskSelected=39),
        "previousClosure": ref(PRIOR / "closure-ids.txt", count=2382),
        "currentClosure": ref(CYCLE / "closure-ids.txt", count=2407),
        "currentDelta": ref(CYCLE / "delta-ids.txt", count=72),
        "regressionRule": "Verify all 132 source speaker values and per-row classes against the pinned inventory; these eight spellings and forms must remain selected, with 5 corrected and 3 retained targets. A changed roster/value requires reclassification rather than a regex-only pass.",
        "examples": examples}))
    mandatory = (CYCLE / "components/mandatory-regressions-ids.txt").read_text().splitlines()
    assert len(mandatory) == 549
    mandatory_rows = []
    for sid in mandatory:
        check_value(by_rule[sid], values[sid])
        mandatory_rows.append({"stableId": sid, "currentTargetSha256": hashlib.sha256(values[sid].encode()).hexdigest(),
                               "inExactDelta": sid in delta, "changed": sid in changed})
    once(CYCLE / "mandatory-regression-evidence.json", encoded({
        "schemaVersion": 1, "status": "549 current target values pass preserve-exact contract; semantic decisions remain for distinct reviewer",
        "catalog": ref(CYCLE / "components/mandatory-regressions-ids.txt", count=549),
        "currentTargetHashes": mandatory_rows,
        "changedCatalogRows": sum(x["changed"] for x in mandatory_rows),
        "deltaCatalogRows": sum(x["inExactDelta"] for x in mandatory_rows)}))
    prior_rows = [json.loads(x) for x in (PRIOR / "delta-review-rows.jsonl").read_text().splitlines()]
    assert len(prior_rows) == 269
    unchanged = 0
    for x in prior_rows:
        sid = x["stableId"]
        if sid not in changed:
            assert values[sid] == x["after"]
            unchanged += 1
    assert unchanged == 260
    for x in structural["authoredFiles"]:
        assert sha(ROOT / x["path"]) == x["sha256"]
    for x in structural["sidecars"]:
        assert sha(ROOT / x["path"]) == x["sha256"]
    assert len(structural["authoredFiles"]) == len(structural["sidecars"]) == 337
    scan = subprocess.run([str(ROOT / ".venv/bin/python"), str(ROOT / "Scripts/report_locale_readiness.py"),
                           "--exact", "--compact"], cwd=ROOT, capture_output=True, text=True)
    assert scan.returncode == 0, scan.stderr
    hebrew = next(x for x in scan.stdout.splitlines() if re.match(r"^he\s", x))
    assert "16538/16538 (100.000%)" in hebrew and "problems=0" in hebrew
    once(CYCLE / "final-gate.json", encoded({"schemaVersion": 1,
        "status": "author structural and dependency gate passed; independent verdict pending",
        "sourceInventorySha256": baseline["sourceInventory"]["stringsSha256"],
        "approvedGlossarySha256": baseline["glossary"]["sha256"],
        "review03EvidenceManifest": ref(IR / "final-evidence-manifest.json"),
        "closureManifest": ref(CYCLE / "closure-manifest.json", closureIds=2407, deltaIds=72),
        "selectorRegressionSpec": ref(CYCLE / "selector-regression-spec.json", examples=8),
        "mandatoryRegressionEvidence": ref(CYCLE / "mandatory-regression-evidence.json", units=549),
        "fullStructuralDiff": ref(CYCLE / "full-structural-diff.json", files=337),
        "preserveExact": ref(CYCLE / "preserve-exact-v4.json", units=16538),
        "unchangedReview03DeltaTargets": unchanged,
        "readinessScan": hebrew,
        "runtime": "not-run per owner instruction", "editorialAcceptance": False}))
    evidence_files = sorted(x for x in CYCLE.rglob("*") if x.is_file()
                            and x.name not in {"final-evidence-manifest.json", "review-handoff-index.json"}
                            and "__pycache__" not in x.parts)
    once(CYCLE / "final-evidence-manifest.json", encoded({
        "schemaVersion": 1,
        "status": "immutable authored cycle-04 evidence; independent review pending",
        "files": [ref(x, bytes=x.stat().st_size) for x in evidence_files]}))
    once(CYCLE / "review-handoff-index.json", encoded({
        "schemaVersion": 1, "locale": "he", "acceptedUnits": 16538,
        "status": "hash-bound cycle-04 handoff; 72 exact delta units await independent review",
        "handoff": ref(CYCLE / "independent-review-handoff.json", deltaUnits=72),
        "finalGate": ref(CYCLE / "final-gate.json"),
        "completeEvidenceManifest": ref(CYCLE / "final-evidence-manifest.json"),
        "deltaReviewRows": ref(CYCLE / "delta-review-rows.jsonl", count=72),
        "firstDeltaId": (CYCLE / "delta-ids.txt").read_text().splitlines()[0],
        "instruction": "Root should assign a distinct independent Hebrew reviewer to the exact 72-ID delta and mandatory regression catalog. Author work and bounded source reads are not an independent clean verdict or editorial acceptance."}))
    print(json.dumps({"status": "author-gate-passed", "delta": 72,
                      "finalGateSha256": sha(CYCLE / "final-gate.json"),
                      "handoffIndexSha256": sha(CYCLE / "review-handoff-index.json")}))


if __name__ == "__main__":
    main()
