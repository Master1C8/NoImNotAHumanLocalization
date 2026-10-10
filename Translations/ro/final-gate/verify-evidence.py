#!/usr/bin/env python3
"""Read-only verification of the Romanian offline final text handoff.

Verifies pinned files, first-pass rows, all correction plans, current targets,
review03's clean decision, unique mandatory regressions, static/credits
derivation, exact/structural receipts, repeat expansion and integration set.
It does not grant editorial acceptance or write to the checkout.
"""

import hashlib
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[3]
LOCALE = ROOT / "Translations/ro"
GATE = LOCALE / "final-gate"
GUIDS = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
         "UI": "0cbd8a7a4f543344bb95659de87f67a5",
         "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def checked(descriptors):
    seen = set()
    for desc in descriptors:
        path = (ROOT / desc["path"]).resolve()
        assert path.is_relative_to(ROOT) and path.exists(), desc["path"]
        rel = str(path.relative_to(ROOT))
        assert rel not in seen and sha(path) == desc["sha256"], rel
        seen.add(rel)
    return seen


def current_authored():
    values, paths = {}, set()
    for path in sorted(LOCALE.glob("*-batch-???.json")) + [LOCALE / "static-text-draft.json"]:
        data = read(path)
        paths.add(str(path.relative_to(ROOT)))
        for entry in data["entries"]:
            sid = entry.get("stableId") or f"string:{GUIDS[data['collection']]}:{entry['id']}"
            assert sid not in values
            values[sid] = entry["target"]
    assert len(values) == 16538 and len(paths) == 415
    return values, paths


def verify():
    handoff = read(GATE / "root-handoff.json")
    assert handoff["locale"] == "ro"
    assert handoff["acceptedUnits"] == handoff["firstSemanticPassUnits"] == 16538
    assert handoff["unresolvedObjectiveFindings"] == 0
    assert handoff["independentClean"] is True
    assert handoff["independentReviewer"] == "/root/ro_independent_review_03"
    assert handoff["currentHashesUnchanged"] is True
    assert handoff["structural"] == {"rows": 16538, "result": "passed"}
    assert handoff["derivedStatic"] == {"rows": 178, "result": "passed"}
    evidence_paths = checked(handoff["evidenceFiles"])
    authored_paths = checked(handoff["authoredFiles"])
    values, current_paths = current_authored()
    assert authored_paths == current_paths
    exact_desc = handoff["preserveExactReport"]
    assert checked([exact_desc])
    exact = read(ROOT / exact_desc["path"])
    assert exact["locale"] == "ro" and exact["checkedRows"] == 16538
    assert exact["exactResult"] == "passed"
    assert {x["path"]: x["sha256"] for x in exact["inputFiles"]} == \
        {x["path"]: x["sha256"] for x in handoff["authoredFiles"]}
    assert exact["manifestSha256"] == sha(ROOT / "Source/preserve-exactly-v4.json")
    corpus = read(GATE / "full-corpus.json")
    assert corpus["locale"] == "ro" and corpus["rows"] == 16538
    assert corpus["structuralResult"] == corpus["exactResult"] == "passed"
    assert corpus["validatorSha256"] == sha(ROOT / "Scripts/validate_locale_corpus.py")
    assert corpus["inputLoaderSha256"] == sha(ROOT / "Scripts/locale_text_inputs.py")
    assert corpus["authoredFiles"] == exact["inputFiles"]
    # The original complete semantic pass is historical evidence. Its current
    # authored-file pins need not match after three correction cycles; its
    # immutable source/row/finding receipts must still match.
    progress = read(LOCALE / "semantic-review-progress.json")
    assert progress["acceptedUnits"] == progress["reviewedUnits"] == 16538
    assert progress["sourceInventorySha256"] == sha(ROOT / "Source/localization-inventory-v3/strings.jsonl")
    assert progress["staticInventorySha256"] == sha(ROOT / "Source/localization-inventory-v3/static-text.jsonl")
    assert progress["approvedGlossarySha256"] == sha(ROOT / "Documentation/glossary-translations/ro/layer.json")
    first_rows = []
    for desc in progress["reviewSegments"]:
        assert sha(ROOT / desc["path"]) == desc["sha256"]
        first_rows.extend(json.loads(line) for line in (ROOT / desc["path"]).read_text().splitlines())
    assert [r["ordinal"] for r in first_rows] == list(range(16538))
    assert len({r["stableId"] for r in first_rows}) == 16538
    findings = 0
    for desc in progress["findingsBatches"]:
        assert sha(ROOT / desc["path"]) == desc["sha256"]
        part = read(ROOT / desc["path"])
        assert len(part["findings"]) == desc["findingCount"]
        findings += len(part["findings"])
    assert findings == progress["totalProposedFindings"] == 71
    source = {}
    for name in ("strings.jsonl", "static-text.jsonl"):
        for line in (ROOT / "Source/localization-inventory-v3" / name).read_text().splitlines():
            record = json.loads(line)
            assert record["stableId"] not in source
            source[record["stableId"]] = record["source"]
    # The static inventory also records out-of-scope TMP rows; the accepted
    # first-pass set is the exact 16,538-ID subset.
    assert len(source) >= 16538
    assert {r["stableId"] for r in first_rows} <= set(source)
    target = {r["stableId"]: r["target"] for r in first_rows}
    for row in first_rows:
        assert source[row["stableId"]] == row["source"]
    for item in read(LOCALE / "correction-cycle-001-plan.json")["corrections"]:
        assert target[item["stableId"]] == item["before"]
        target[item["stableId"]] = item["after"]
    for item in read(LOCALE / "remedial-cycle-002-plan.json")["decisions"]:
        assert target[item["stableId"]] == item["before"]
        target[item["stableId"]] = item["after"]
    for item in read(LOCALE / "correction-cycle-003-plan.json")["decisions"]:
        assert target[item["stableId"]] == item["before"]
        target[item["stableId"]] = item["after"]
    assert target == values
    for rel in ("correction-cycle-001-closure-v3/manifest.json",
                "remedial-cycle-002-closure-v2/manifest.json",
                "correction-cycle-003-closure/manifest.json"):
        assert str((LOCALE / rel).relative_to(ROOT)) in evidence_paths
    review = read(LOCALE / "independent-review-03/review-result.json")
    assert sha(LOCALE / "independent-review-03/review-result.json") == \
        "480ceae1d296baa780f8f7f2ad2f274cad27925cb916e2c506bfe579dd6db015"
    assert sha(LOCALE / "independent-review-03/audit-manifest.json") == \
        "9afaa875b7b19588f8a254358659b1b5364452372460fe42051eb5fe5dacd353"
    assert review["status"] == "clean-independent-exact-delta"
    assert review["objectiveFindings"] == 0 and review["freshDeltaReads"] == 5
    assert review["freshSupplementalContextReads"] == 43
    assert review["unchangedPriorDecisionsVerified"] == 4493
    audit = read(LOCALE / "independent-review-03/audit-manifest.json")
    checked(audit["files"])
    pins = read(LOCALE / "independent-review-03/input-pins.json")
    assert len(pins["pins"]) == 676 and pins["authoredFiles"] == 415
    for desc in pins["pins"]:
        pinned_path = pathlib.Path(desc["path"])
        path = pinned_path if pinned_path.is_absolute() else ROOT / pinned_path
        assert path.exists() and sha(path) == desc["sha256"], desc["path"]
    # Every regression class is checked by its own exact list hash; count
    # unique IDs across overlapping classes, never sum row counts.
    catalog = read(LOCALE / "independent-review-03/mandatory-catalog.json")
    assert len(catalog["classes"]) == 16
    union = set()
    for cls in catalog["classes"]:
        path = ROOT / cls["path"]
        assert sha(path) == cls["sha256"]
        members = set(path.read_text().splitlines())
        assert len(members) == cls["rows"]
        union |= members
    assert len(union) == catalog["unionIds"] == 3334
    fresh = set()
    for name in ("per-id-decisions.jsonl", "supplemental-context-decisions.jsonl"):
        for line in (LOCALE / "independent-review-03" / name).read_text().splitlines():
            row = json.loads(line)
            assert row["fullSourceAndCurrentTargetRead"] is True
            assert row["sourceSha256"] == text_sha(source[row["stableId"]])
            assert row["targetSha256"] == text_sha(values[row["stableId"]])
            fresh.add(row["stableId"])
    assert len(fresh) == 48 and fresh <= union
    prior = read(LOCALE / "independent-review-03/prior-decision-applicability.json")
    prior_ids = set()
    for row in prior["rows"]:
        assert row["sourceSha256"] == text_sha(source[row["stableId"]])
        assert row["targetSha256"] == text_sha(values[row["stableId"]])
        prior_ids.add(row["stableId"])
    assert len(prior_ids) == 4493 and union - fresh <= prior_ids
    regression = handoff["mandatoryRegression"]
    assert regression == {"count": 3334, "freshReads": 48,
                          "reusedUnchangedIndependentDecisions": 3286,
                          "result": "passed"}
    unique = read(GATE / "mandatory-regression-unique.json")
    assert set(unique["freshIdList"]) == fresh
    assert set(unique["reusedIdList"]) == union - fresh
    assert unique["uniqueIds"] == 3334
    static = read(LOCALE / "static-text-draft.json")
    assert len(static["entries"]) == 178
    credits = read(LOCALE / "credits-role-map.json")
    original = source[credits["stableId"]]
    replacements = {item["source"]: item["target"] for item in credits["replacements"]}
    assert len(replacements) == len(credits["replacements"])
    pattern = re.compile("|".join(re.escape(s) for s in sorted(replacements, key=len, reverse=True)))
    assert pattern.sub(lambda match: replacements[match.group()], original) == values[credits["stableId"]]
    derived = read(GATE / "derived-static.json")
    assert derived["rows"] == 178 and derived["result"] == "passed"
    assert derived["creditsRoleMapSha256"] == sha(LOCALE / "credits-role-map.json")
    repeat = read(GATE / "repeat-expansion.json")
    assert repeat["result"] == "passed" and repeat["rows"] == 2828 and repeat["transferRows"] == 245
    assert repeat["mapSha256"] == sha(LOCALE / "dialogue-repeats-001.authored.json")
    assert repeat["generatedBatchSha256"] == sha(LOCALE / "dialogue-batch-001.json")
    result = subprocess.run([str(ROOT / ".venv/bin/python"),
                             str(ROOT / "Scripts/expand_exact_text_batch.py"),
                             str(LOCALE / "dialogue-repeats-001.authored.json"),
                             str(LOCALE / "dialogue-batch-001.json"), "--verify"],
                            cwd=ROOT, capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)["result"] == "verified"
    previous = read(GATE / "ro-text-progress.pre-final.json")
    assert previous["correctionCycle003"]["closureManifestSha256"] == \
        sha(LOCALE / "correction-cycle-003-closure/manifest.json")
    limits = handoff["remainingLimits"]
    assert any("historical" in item.lower() and "unverified" in item.lower() for item in limits)
    assert any("runtime" in item.lower() for item in limits)
    integration_path = GATE / "proposed-integration.json"
    if integration_path.exists():
        integration = read(integration_path)
        listed = checked(integration["files"])
        assert integration["includedFiles"] == len(listed)
        assert integration["rootHandoffSha256"] == sha(GATE / "root-handoff.json")
        assert integration["checkpointSha256"] == sha(ROOT / "Documentation/ro-text-progress.json")
        excluded = {item["path"] for item in integration["excludedFromProposal"]}
        assert excluded == {
            "Translations/ro/independent-review-01/source-character-domains.json",
            "Translations/ro/independent-review-01/source-character-domains-v2.json"}
        actual = {str(path.relative_to(ROOT)) for path in LOCALE.rglob("*")
                  if path.is_file() and path != integration_path} - excluded
        actual.add("Documentation/ro-text-progress.json")
        assert listed == actual
    print(json.dumps({"result": "verified", "locale": "ro", "acceptedUnits": 16538,
                      "closure": 4498, "mandatoryUniqueIds": 3334,
                      "freshReads": 48, "reusedUnchangedIndependentDecisions": 3286,
                      "independentReviewer": review["reviewer"]}))


if __name__ == "__main__":
    verify()
