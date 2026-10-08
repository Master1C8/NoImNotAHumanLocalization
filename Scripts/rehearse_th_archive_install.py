#!/usr/bin/env python3
"""Rehearse the exact Thai ZIP overlay on disposable copies of its 31 game files."""

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from zipfile import ZipFile

from probe_assets import DEFAULT_GAME, ROOT, digest, require


def write_receipt(path, receipt):
    path.write_text(json.dumps(receipt, indent=2) + "\n")


def apply_archive(archive, target, output, original_hashes, target_hashes,
                  inject_failure_after=None):
    rows = [{"relativePath": relative, "before": original_hashes[relative],
             "after": target_hashes[relative], "installed": False}
            for relative in sorted(target_hashes)]
    require(all(digest(target / row["relativePath"]) == row["before"] for row in rows),
            "Target is not the pinned clean game state")
    output.mkdir()
    receipt = {"completed": False, "files": rows,
               "commitBoundary": "Per-file atomic replacement; no multi-file transaction or automatic rollback"}
    receipt_path = output / "receipt.json"
    write_receipt(receipt_path, receipt)
    with ZipFile(archive) as zipped:
        for index, row in enumerate(rows, 1):
            relative = row["relativePath"]
            destination = target / relative
            backup = output / "backup" / relative
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, backup)
            require(digest(backup) == row["before"], "Backup differs: " + relative)
            temporary = destination.with_name(destination.name + ".thai-archive-tmp")
            require(not temporary.exists(), "Prior temporary replacement requires reconciliation")
            temporary.write_bytes(zipped.read(relative))
            require(digest(temporary) == row["after"], "Temporary differs: " + relative)
            temporary.replace(destination)
            require(digest(destination) == row["after"], "Installed file differs: " + relative)
            row["installed"] = True
            write_receipt(receipt_path, receipt)
            if inject_failure_after == index:
                raise RuntimeError("Injected interruption after one verified replacement")
    require(all(digest(target / row["relativePath"]) == row["after"] for row in rows),
            "Final overlay differs")
    receipt["completed"] = True
    write_receipt(receipt_path, receipt)
    return receipt


def copy_originals(source, target, original_hashes):
    for relative, wanted in sorted(original_hashes.items()):
        original = source / relative
        require(digest(original) == wanted, "Original game changed: " + relative)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, destination)
        require(digest(destination) == wanted, "Staged original differs: " + relative)


def rehearse(archive, preflight, output):
    require(archive.is_relative_to(ROOT / "dist") and
            preflight.is_relative_to(ROOT / "outputs") and
            output.is_relative_to(ROOT / "outputs") and not output.exists(),
            "Use the canonical archive, preflight and a new output directory")
    baseline = json.loads(preflight.read_text())
    require(baseline["result"] == "passed-read-only-preflight" and
            baseline["archiveSha256"] == digest(archive) and
            baseline["pinnedOriginalHashesMatched"] == 31 and
            baseline["originalDiagnosticLoaderAbsent"],
            "Fresh-install preflight changed")
    original_hashes = baseline["originalFileHashes"]
    with ZipFile(archive) as zipped:
        package = json.loads(zipped.read("report.json"))
    target_hashes = {relative: row["sha256"] for relative, row in package["artifacts"].items()}
    require(set(original_hashes) == set(target_hashes) and len(target_hashes) == 31,
            "Preflight and archive file sets differ")
    output.mkdir()
    failure = {}
    with tempfile.TemporaryDirectory(prefix="no-human-th-interruption-") as temporary:
        stage = Path(temporary) / "game"
        copy_originals(DEFAULT_GAME, stage, original_hashes)
        try:
            apply_archive(archive, stage, Path(temporary) / "receipt", original_hashes,
                          target_hashes, inject_failure_after=1)
        except RuntimeError as error:
            require(str(error) == "Injected interruption after one verified replacement",
                    "Unexpected installation failure")
        else:
            raise AssertionError("Injected interruption did not happen")
        receipt = json.loads((Path(temporary) / "receipt/receipt.json").read_text())
        installed = [row for row in receipt["files"] if row["installed"]]
        require(not receipt["completed"] and len(installed) == 1 and
                all(digest(stage / row["relativePath"]) ==
                    (row["after"] if row["installed"] else row["before"])
                    for row in receipt["files"]) and
                digest(Path(temporary) / "receipt/backup" / installed[0]["relativePath"]) ==
                installed[0]["before"],
                "Interruption boundary differs from receipt")
        failure = {"completed": False, "installedFiles": 1,
                   "remainingOriginalFiles": 30, "firstBackupMatched": True,
                   "result": "expected partial state after injected interruption"}
    with tempfile.TemporaryDirectory(prefix="no-human-th-complete-") as temporary:
        stage = Path(temporary) / "game"
        copy_originals(DEFAULT_GAME, stage, original_hashes)
        receipt = apply_archive(archive, stage, Path(temporary) / "receipt",
                                original_hashes, target_hashes)
        require(receipt["completed"] and all(row["installed"] for row in receipt["files"]),
                "Positive overlay did not complete")
    require(all(digest(DEFAULT_GAME / relative) == wanted for relative, wanted in
                original_hashes.items()), "Original game changed during rehearsal")
    result = {"schemaVersion": 1, "archiveSha256": digest(archive),
              "preflightSha256": digest(preflight), "files": len(target_hashes),
              "interruption": failure,
              "positiveControl": "All 31 copied clean files matched the exact archive after overlay",
              "originalGameChanged": False,
              "runtime": "not run; no executable or save was copied",
              "result": "passed-offline-install-rehearsal"}
    write_receipt(output / "report.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rehearse(args.archive.resolve(), args.preflight.resolve(), args.output.resolve())
