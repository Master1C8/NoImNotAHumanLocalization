#!/usr/bin/env python3
"""Install a verified Thai text build into the stopped, isolated fixture."""

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from fixture_preferences import FIXTURE
from probe_assets import DEFAULT_GAME, ROOT, digest, require

GAME = FIXTURE / "Contents/SharedSupport/prefix/drive_c/KS Games/No Im not a Human"
BASE = ROOT / "outputs/native-locale-probe-v6"
FONT = ROOT / "outputs/renderer-font-v3"


def fixture_stopped():
    lines = subprocess.run(["ps", "-axo", "pid,command"], check=True, text=True,
                           stdout=subprocess.PIPE).stdout.splitlines()
    require(not any(str(FIXTURE) in line or "NoImNotAHuman.exe" in line or
                    "wineserver" in line for line in lines),
            "Game or Wine is running; preserve the fixture")


def base_path(relative):
    if relative == "NoImNotAHuman_Data/sharedassets0.assets":
        return FONT / "sharedassets0.assets"
    if (BASE / relative).exists():
        return BASE / relative
    return DEFAULT_GAME / relative


def install(build, output, previous_receipt=None):
    require(build.is_relative_to(ROOT / "outputs") and
            output.is_relative_to(ROOT / "outputs") and not output.exists(),
            "Use a new canonical output directory")
    report_path = build / "report.json"
    report = json.loads(report_path.read_text())
    verification = json.loads((build / "verification.json").read_text())
    require(report["status"].startswith("isolated Thai text draft") and
            report["semanticReview"] == "accepted offline" and
            report["rendererFontReceiptSha256"] == digest(FONT / "receipt.json") and
            verification["reportSha256"] == digest(report_path) and
            verification["serializedValuesResult"] == "passed" and
            verification["tableRowsCompared"] == 16360 and
            verification["staticRowsCompared"] == 178 and
            verification.get("rtlOriginalTextRowsCompared") == 165 and
            verification["artifactHashesCompared"] == 10,
            "Thai build or complete verification changed")
    expected = report["artifacts"]
    require(len(expected) == 10 and all(rel.startswith("NoImNotAHuman_Data/")
                                        for rel in expected),
            "Unexpected Thai artifact set")
    require(GAME.resolve().is_relative_to(FIXTURE.resolve()), "Fixture path escaped")
    prior = None
    if previous_receipt is not None:
        prior_record = json.loads(previous_receipt.read_text())
        require(prior_record["completed"] and prior_record["fixture"] == str(FIXTURE),
                "Previous Thai install is incomplete or belongs to another fixture")
        prior = {row["relativePath"]: row["after"] for row in prior_record["files"]}
        require(set(prior) == set(expected), "Previous Thai artifact set differs")
    fixture_stopped()
    rows = []
    for rel, details in sorted(expected.items()):
        source, destination, base = build / rel, GAME / rel, base_path(rel)
        require(source.resolve().is_relative_to(build) and
                destination.resolve().is_relative_to(GAME.resolve()) and
                base.is_file() and destination.is_file(), "Artifact path mismatch")
        before = prior[rel] if prior is not None else digest(base)
        require(digest(destination) == before, "Fixture differs from expected base: " + rel)
        require(digest(source) == details["sha256"], "Thai artifact changed: " + rel)
        rows.append({"relativePath": rel, "before": before,
                     "after": details["sha256"], "installed": False})
    fixture_stopped()
    output.mkdir(parents=True)
    receipt = {"buildReport": str(report_path.relative_to(ROOT)),
               "buildReportSha256": digest(report_path), "fixture": str(FIXTURE),
               "previousReceipt": str(previous_receipt.relative_to(ROOT)) if previous_receipt else None,
               "files": rows, "completed": False,
               "commitBoundary": "Each file replaces atomically; the ten files are not a transaction. Reconcile hashes and backups after an interruption before launch."}
    receipt_path = output / "receipt.json"

    def record():
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")

    record()
    for row in rows:
        rel = row["relativePath"]
        destination = GAME / rel
        backup = output / rel
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(destination, backup)
        require(digest(backup) == row["before"], "Backup mismatch: " + rel)
        temporary = destination.with_name(destination.name + ".thai-probe-tmp")
        require(not temporary.exists(), "Previous temporary file requires reconciliation")
        shutil.copy2(build / rel, temporary)
        require(digest(temporary) == row["after"], "Temporary artifact mismatch")
        temporary.replace(destination)
        require(digest(destination) == row["after"], "Installed artifact mismatch")
        row["installed"] = True
        record()
    require(all(digest(GAME / row["relativePath"]) == row["after"] for row in rows),
            "Final fixture verification failed")
    receipt["completed"] = True
    record()
    print(json.dumps({"receipt": str(receipt_path.relative_to(ROOT)),
                      "installedFiles": len(rows), "verified": True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--previous-receipt", type=Path)
    args = parser.parse_args()
    install(args.build.resolve(), args.output.resolve(),
            args.previous_receipt.resolve() if args.previous_receipt else None)
