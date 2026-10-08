#!/usr/bin/env python3
"""Create an immutable paired source/Thai review corpus; does not review wording."""

import argparse
import hashlib
import json
from pathlib import Path

from build_th_text_draft import authored_tables
from probe_assets import ROOT, digest, require


STRINGS = ROOT / "Source/localization-inventory-v3/strings.jsonl"
STATIC = ROOT / "Source/localization-inventory-v3/static-text.jsonl"
MANIFEST = ROOT / "Source/preserve-exactly-v4.json"
STATIC_SCOPE = ROOT / "Documentation/static-text-scope-v2.json"
EXACT = ROOT / "Documentation/th-preserve-exact-v5.json"
SOURCE_ACCEPTANCE = ROOT / "Documentation/text-source-acceptance-v1.json"
GLOSSARY_REVIEW = ROOT / "Documentation/glossary-translations/canonical-reviews/th.json"
REGRESSIONS = ROOT / "Documentation/th-semantic-regressions-v1.json"
DEFAULT_OUTPUT = ROOT / "outputs/th-semantic-audit-input-v4"
GUIDS = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
         "UI": "0cbd8a7a4f543344bb95659de87f67a5",
         "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}


def main(output):
    require(output.is_relative_to(ROOT / "outputs") and not output.exists(),
            "Use a new canonical outputs directory")
    manifest = json.loads(MANIFEST.read_text())
    exact = json.loads(EXACT.read_text())
    accepted = json.loads(SOURCE_ACCEPTANCE.read_text())
    glossary = json.loads(GLOSSARY_REVIEW.read_text())
    regressions = json.loads(REGRESSIONS.read_text())
    require(exact["manifestSha256"] == digest(MANIFEST) and
            exact["sourceInventorySha256"] == digest(STRINGS) and
            exact["staticInventorySha256"] == digest(STATIC) and
            exact["exactResult"] == "passed", "Exact gate does not match review inputs")
    require(accepted["decision"] ==
            "accepted source-ID inventory for authored text and editorial review" and
            accepted["selectedTotalRows"] == 16538 and
            accepted["sourceStringsSha256"] == digest(STRINGS) and
            accepted["sourceStaticSha256"] == digest(STATIC),
            "Accepted source scope differs from review inputs")
    require(glossary["status"] == "editorially-accepted-canonical" and
            glossary["locale"] == "th" and
            glossary["layerRawSha256"] ==
            json.loads((ROOT / "Translations/th/static-text-draft.json").read_text())
                ["glossaryFingerprint"],
            "Approved Thai glossary differs")
    _, tables, batch_files = authored_tables()
    targets = {}
    for collection, rows in tables.items():
        for row_id, text in rows.items():
            targets[f"string:{GUIDS[collection]}:{row_id}"] = text
    static_path = ROOT / "Translations/th/static-text-draft.json"
    static = json.loads(static_path.read_text())
    for entry in static["entries"]:
        require(entry["stableId"] not in targets, "Duplicate target stable ID")
        targets[entry["stableId"]] = entry["target"]
    require(len(targets) == 16538, "Review target coverage changed")
    source = {}
    for path in (STRINGS, STATIC):
        for line in path.open():
            row = json.loads(line)
            source[row["stableId"]] = row
    scope = {row["stableId"]: row for row in
             json.loads(STATIC_SCOPE.read_text())["rows"]}
    selected = manifest["tableRows"] + manifest["staticRows"]
    require({row["stableId"] for row in selected} == set(targets),
            "Review stable-ID set differs from exact gate")
    output.mkdir(parents=True)
    pairs_path = output / "paired.jsonl"
    with pairs_path.open("w") as stream:
        for index, rule in enumerate(selected):
            stable_id = rule["stableId"]
            row = source[stable_id]
            require(hashlib.sha256(row["source"].encode("utf-8")).hexdigest() ==
                    rule["sourceSha256"],
                    "Source text changed: " + stable_id)
            pair = {"ordinal": index + 1, "stableId": stable_id,
                    "collection": rule.get("collection"),
                    "key": rule.get("key"),
                    "nodeNames": row.get("nodeNames", []),
                    "scenePath": [part["name"] for part in
                                  scope[stable_id]["sceneAncestry"]]
                                  if stable_id in scope else None,
                    "source": row["source"], "target": targets[stable_id]}
            stream.write(json.dumps(pair, ensure_ascii=False, separators=(",", ":")) + "\n")
    require(regressions["pairedSha256"] == digest(pairs_path),
            "Mandatory regression catalog differs from paired corpus")
    report = {"schemaVersion": 1,
              "status": "review input only; semantic coverage zero until manually recorded",
              "gameVersion": "1.3.19", "sourceLocale": "ru", "targetLocale": "th",
              "sourceStringsSha256": digest(STRINGS),
              "sourceStaticSha256": digest(STATIC),
              "manifestSha256": digest(MANIFEST),
              "sourceAcceptanceSha256": digest(SOURCE_ACCEPTANCE),
              "glossaryLayerFingerprint": glossary["layerRawSha256"],
              "glossaryReviewSha256": digest(GLOSSARY_REVIEW),
              "regressionCatalogSha256": digest(REGRESSIONS),
              "exactReportSha256": digest(EXACT),
              "staticScopeSha256": digest(STATIC_SCOPE),
              "authoredBatchFiles": batch_files,
              "staticDraftSha256": digest(static_path),
              "pairedPath": str(pairs_path.relative_to(ROOT)),
              "pairedSha256": digest(pairs_path),
              "rowCount": len(selected), "semanticReviewedRows": 0}
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"report": str((output / "report.json").relative_to(ROOT)),
                      "rows": len(selected), "semanticReviewedRows": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    main(args.output.resolve())
