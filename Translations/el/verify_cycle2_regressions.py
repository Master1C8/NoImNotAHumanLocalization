#!/usr/bin/env python3
"""Verify repaired Greek selector cases and assembled item text against pinned evidence."""

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    plan = json.loads((HERE / "correction-cycle-002-adjudication.json").read_text())
    spec = json.loads((HERE / "correction-cycle-002-selectors.json").read_text())
    selector = json.loads((HERE / "independent-review-01/selector-completeness.json").read_text())
    assembled = json.loads((HERE / "independent-review-01/dynamic-assembled-evidence.json").read_text())
    closure = set((HERE / "correction-cycle-002-closure-ids.txt").read_text().splitlines())
    old_closure = set((HERE / "correction-cycle-001-closure-ids.txt").read_text().splitlines())
    targets = {}
    guids = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
             "UI": "0cbd8a7a4f543344bb95659de87f67a5",
             "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}
    for path in HERE.glob("*-batch-[0-9][0-9][0-9].json"):
        batch = json.loads(path.read_text())
        for entry in batch["entries"]:
            sid = f"string:{guids[batch['collection']]}:{entry['id']}"
            assert sid not in targets
            targets[sid] = entry["target"]
    for entry in json.loads((HERE / "static-text-draft.json").read_text())["entries"]:
        assert entry["stableId"] not in targets
        targets[entry["stableId"]] = entry["target"]
    assert len(targets) == 16538

    for row in plan["corrections"]:
        assert targets[row["stableId"]] == row["after"]
        assert row["stableId"] in closure
    findings = json.loads((HERE / "independent-review-01/findings-v3.json").read_text())["findings"]
    assert len(findings) == 23
    assert {row["reviewFindingId"] for row in plan["corrections"] if row["reviewFindingId"]} == {
        row["findingId"] for row in findings}
    day12 = next(row for row in plan["corrections"] if row["reviewFindingId"] == "EL-IR01-023")
    assert day12["source"].count("…") == day12["after"].count("…") == 4
    assert next(row for row in findings if row["findingId"] == "EL-IR01-016")["glossaryIds"] == ["babushka"]
    glossary = json.loads((ROOT / "Documentation/glossary-translations/el/layer.json").read_text())
    assert glossary["babushka"]["term"] == "Τρομακτική γριά"

    anchors = selector["mandatoryUnknownGenderCanonicalAnchors"]
    callbacks = selector["kilotonCallbacks"]
    assert len(anchors) == len(spec["canonicalUnknownRoleStableIds"]) == 25
    assert sum(not row["selected"] for row in anchors) == 20
    assert {row["stableId"] for row in anchors} == set(spec["canonicalUnknownRoleStableIds"])
    assert {row["stableId"] for row in anchors} <= closure
    assert len(callbacks) == len(spec["kilotonCallbackStableIds"]) == 3
    assert {row["stableId"] for row in callbacks} == set(spec["kilotonCallbackStableIds"])
    assert {row["stableId"] for row in callbacks} <= closure
    assert sum(row["stableId"] not in old_closure for row in callbacks) == 2
    callback_pattern = re.compile("килотонн", re.IGNORECASE)
    assert all(callback_pattern.search(row["source"]) for row in callbacks)

    old_rows = [json.loads(line) for line in
                (HERE / "correction-cycle-001-closure-review.jsonl").open()]
    examples = assembled["bribeExamples"]
    assert len(examples) == 18
    for example in examples:
        sid = old_rows[example["closureIndex"]]["stableId"]
        current = targets[sid]
        assert current.count("{0}") == 1
        assert current.replace("{0}", example["localizedDictionaryLabel"]) == example["proposedAssembled"]
    assert len(assembled["deficitConsumableEnumNames"]) == 6
    assert len(assembled["localizedNames"]) == 7
    assert len(assembled["itemHintExamples"]) == 14
    assert all("<color=" in example["assembled"] and " x1 " in example["assembled"]
               for example in assembled["itemHintExamples"])

    report = {"schemaVersion": 1, "locale": "el", "cycle": 2, "result": "passed",
              "adjudicationSha256": digest(HERE / "correction-cycle-002-adjudication.json"),
              "selectorSha256": digest(HERE / "correction-cycle-002-selectors.json"),
              "reviewSelectorEvidenceSha256": digest(HERE / "independent-review-01/selector-completeness.json"),
              "assembledEvidenceSha256": digest(HERE / "independent-review-01/dynamic-assembled-evidence.json"),
              "closureManifestSha256": digest(HERE / "correction-cycle-002-closure-manifest.json"),
              "cases": {"acceptedReviewProposals": 23, "additionalCorrections": 3,
                        "unknownRoleAnchors": 25, "previouslyMissingUnknownRoleAnchors": 20,
                        "kilotonCallbacks": 3, "previouslyMissingKilotonCallbacks": 2,
                        "deficitItemNames": 6, "acceptedItemLabels": 7,
                        "assembledBribeExamples": 18, "itemHintExamples": 14,
                        "day12InterruptedSpans": 4, "NotTrueCanonicalGlossaryId": "babushka"},
              "limit": "Deterministic source/translation and serialized/compiled assembly checks; no game runtime or independent semantic acceptance."}
    out = HERE / "correction-cycle-002-regressions.validation.json"
    content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.verify:
        assert out.read_text() == content
    else:
        assert not out.exists()
        out.write_text(content)
    print(json.dumps({"result": "passed", "reportSha256": digest(out)}))


if __name__ == "__main__":
    main()
