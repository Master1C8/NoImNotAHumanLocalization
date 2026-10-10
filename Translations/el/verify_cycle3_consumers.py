#!/usr/bin/env python3
"""Verify all actual Greek LocalizeItem display assemblies and neutral controls."""

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
REVIEW = HERE / "independent-review-02"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    plan = json.loads((HERE / "correction-cycle-003-adjudication.json").read_text())
    selector = json.loads((HERE / "correction-cycle-003-selectors.json").read_text())
    closure = json.loads((HERE / "correction-cycle-003-closure-manifest.json").read_text())
    corpus = json.loads((HERE / "correction-cycle-003-corpus.validation.json").read_text())
    topology = json.loads((REVIEW / "bounded-consumer-topology.json").read_text())
    checks = json.loads((REVIEW / "proposal-and-consumer-checks.json").read_text())
    assert corpus["rows"] == 16538 and closure["actualLocalizeItemConsumerCount"] == 21
    assert len(topology["consumerRows"]) == 21
    assert len(checks["deficitDomain"]) == 6 and len(checks["acceptedNameKeys"]) == 7
    assert len(checks["assembledBribeExamples"]) == 126
    assert len(checks["itemHintExamples"]) == 14
    assert selector["actualLocalizeItemConsumerSelector"]["expectedActualConsumerCount"] == 21
    targets = {}
    ui = {}
    source_by_id = {}
    for line in (ROOT / "Source/localization-inventory-v3/strings.jsonl").open():
        row = json.loads(line)
        source_by_id[row["stableId"]] = row
    for file in corpus["authoredFiles"]:
        path = ROOT / file["path"]
        batch = json.loads(path.read_text())
        if batch.get("collection") == "Dialogs":
            for entry in batch["entries"]:
                sid = f"string:444ff14f1967f5a4c8eb9e4cf4c913f1:{entry['id']}"
                targets[sid] = entry["target"]
        elif batch.get("collection") == "UI":
            for entry in batch["entries"]:
                sid = f"string:0cbd8a7a4f543344bb95659de87f67a5:{entry['id']}"
                ui[source_by_id[sid]["key"]] = entry["target"]
    consumer_ids = {row["row"]["stableId"] for row in topology["consumerRows"]}
    assert len(consumer_ids) == 21 and consumer_ids <= set(targets)
    changed = {row["stableId"] for row in plan["corrections"]}
    assert len(changed) == 6 and changed <= consumer_ids
    for key, label in checks["acceptedNameKeys"].items():
        assert ui[key] == label
    for example in checks["itemHintExamples"]:
        assert example["itemKey"] in checks["acceptedNameKeys"]
        assert checks["acceptedNameKeys"][example["itemKey"]] in example["assembled"]
        assert " x1 " in example["assembled"]
    positive, controls = 0, 0
    for example in checks["assembledBribeExamples"]:
        sid = example["stableId"]
        target = targets[sid]
        assert target.count("{0}") == 1
        assert target.replace("{0}", example["label"]) == example["proposedAssembled"]
        if sid in changed:
            positive += 1
            before = next(row["before"] for row in plan["corrections"] if row["stableId"] == sid)
            assert before.replace("{0}", example["label"]) == example["currentAssembled"]
        else:
            controls += 1
            assert example["currentAssembled"] == example["proposedAssembled"]
            assert target == next(row["row"]["currentTarget"] for row in topology["consumerRows"]
                                  if row["row"]["stableId"] == sid)
        assert "έχω Καφές" not in example["proposedAssembled"]
        assert "Πάρε Καφές" not in example["proposedAssembled"]
        assert "Σου κάνει Τσιγάρα" not in example["proposedAssembled"]
    assert positive == 36 and controls == 90
    assert sum("έχω Καφές" in row["before"] or "Πάρε Καφές" in row["before"]
               for item in plan["corrections"] for row in item["assembledVariants"]
               if row["item"] == "Coffee") == 5
    assert sum("Σου κάνει Τσιγάρα" in row["before"]
               for item in plan["corrections"] for row in item["assembledVariants"]
               if row["item"] == "Cigarette") == 1
    after = {row["findingId"]: row["after"] for row in plan["corrections"]}
    assert all("Η ποσότητα είναι μικρή" in after[key] and "σας χρησιμεύσει" in after[key]
               for key in ("EL-IR02-001", "EL-IR02-002"))
    assert "Αν χρειάζεται" in after["EL-IR02-003"] and "Σας κάνει;" in after["EL-IR02-003"]
    assert "Θες;" in after["EL-IR02-004"]
    assert all(token in after["EL-IR02-005"] for token in
               ("Πάρ' το", "κράτησέ το", "κούνησέ το", "είσοδο", "αόρατος"))
    assert "Σου κάνει αυτό;" in after["EL-IR02-006"]
    report = {"schemaVersion": 1, "locale": "el", "cycle": 3, "result": "passed",
              "adjudicationSha256": digest(HERE / "correction-cycle-003-adjudication.json"),
              "selectorSha256": digest(HERE / "correction-cycle-003-selectors.json"),
              "closureManifestSha256": digest(HERE / "correction-cycle-003-closure-manifest.json"),
              "corpusReceiptSha256": digest(HERE / "correction-cycle-003-corpus.validation.json"),
              "reviewTopologySha256": digest(REVIEW / "bounded-consumer-topology.json"),
              "reviewAssembledChecksSha256": digest(REVIEW / "proposal-and-consumer-checks.json"),
              "actualConsumers": 21, "serializedDeficitItems": 6,
              "acceptedItemLabels": 7, "assembledVariants": 126,
              "correctedPositiveVariants": positive,
              "unchangedCitationControlVariants": controls,
              "itemHintControls": 14,
              "originalObjectiveFailures": {"CoffeeCase": 5, "CigaretteNumber": 1},
              "unexplainedMissingOrExtraConsumers": 0,
              "limit": "Serialized/compiled assembly and Greek grammar checks; no gameplay or independent editorial claim."}
    out = HERE / "correction-cycle-003-consumers.validation.json"
    content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.verify:
        assert out.read_text() == content
    else:
        assert not out.exists()
        out.write_text(content)
    print(json.dumps({"result": "passed", "positive": positive,
                      "controls": controls, "reportSha256": digest(out)}))


if __name__ == "__main__":
    main()
