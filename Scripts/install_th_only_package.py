#!/usr/bin/env python3
"""Install the verified Thai-only package in the stopped copied fixture."""

import argparse
import json
import shutil
from pathlib import Path

from install_th_text_draft import GAME, fixture_stopped
from probe_assets import ROOT, digest, require


def install(package, native_receipt, font_receipt, text_receipt, output):
    require(package.is_relative_to(ROOT / "outputs") and
            output.is_relative_to(ROOT / "outputs") and not output.exists(),
            "Use a new canonical output directory")
    report_path = package / "report.json"
    report = json.loads(report_path.read_text())
    require(report["locale"] == "th" and report["newLocaleCount"] == 1 and
            len(report["artifacts"]) == 31, "Not the complete Thai-only package")
    native = json.loads(native_receipt.read_text())
    font = json.loads(font_receipt.read_text())
    text = json.loads(text_receipt.read_text())
    require(native["allInstalledHashesVerified"] and font["completed"] and
            text["completed"], "Previous installation chain is incomplete")
    previous = {row["relativePath"]: row["after"] for row in native["files"]}
    previous.update({row["path"]: row["afterSha256"] for row in font["files"]})
    previous.update({row["relativePath"]: row["after"] for row in text["files"]})
    require(set(report["artifacts"]) <= set(previous), "Previous artifact missing")
    fixture_stopped()
    rows = []
    for relative, artifact in sorted(report["artifacts"].items()):
        source, target = package / relative, GAME / relative
        require(source.resolve().is_relative_to(package.resolve()) and
                target.resolve().is_relative_to(GAME.resolve()) and
                digest(source) == artifact["sha256"] and
                digest(target) == previous[relative],
                "Package or fixture hash mismatch: " + relative)
        rows.append({"relativePath": relative, "before": previous[relative],
                     "after": artifact["sha256"], "installed": False})
    fixture_stopped()
    output.mkdir(parents=True)
    receipt = {"packageReport": str(report_path.relative_to(ROOT)),
               "packageReportSha256": digest(report_path),
               "previousReceipts": {"native": str(native_receipt.relative_to(ROOT)),
                                    "font": str(font_receipt.relative_to(ROOT)),
                                    "text": str(text_receipt.relative_to(ROOT))},
               "files": rows, "completed": False,
               "commitBoundary": "Per-file atomic replacements in the stopped copied fixture; no multi-file transaction. Reconcile the exact backup and target hashes before launch after any interruption."}
    receipt_path = output / "receipt.json"

    def record():
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")

    record()
    replace_files(package, GAME, output, rows, receipt, receipt_path)
    require(all(digest(GAME / row["relativePath"]) == row["after"] for row in rows),
            "Final installed package mismatch")
    receipt["completed"] = True
    record()
    print(json.dumps({"receipt": str(receipt_path.relative_to(ROOT)),
                      "installedFiles": len(rows), "verified": True}))


def replace_files(package, game, output, rows, receipt, receipt_path,
                  inject_failure_after=None):
    def record():
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")

    for index, row in enumerate(rows, 1):
        relative = row["relativePath"]
        target, source = game / relative, package / relative
        backup = output / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup)
        require(digest(backup) == row["before"], "Backup mismatch: " + relative)
        temporary = target.with_name(target.name + ".thai-only-tmp")
        require(not temporary.exists(), "Prior temporary replacement requires reconciliation")
        shutil.copy2(source, temporary)
        require(digest(temporary) == row["after"], "Temporary mismatch")
        temporary.replace(target)
        require(digest(target) == row["after"], "Installed hash mismatch")
        row["installed"] = True
        record()
        if inject_failure_after == index:
            raise RuntimeError("Injected interruption after a verified file replacement")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--native-receipt", type=Path, required=True)
    parser.add_argument("--font-receipt", type=Path, required=True)
    parser.add_argument("--text-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    install(args.package.resolve(), args.native_receipt.resolve(),
            args.font_receipt.resolve(), args.text_receipt.resolve(), args.output.resolve())
