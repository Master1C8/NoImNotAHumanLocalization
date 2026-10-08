#!/usr/bin/env python3
"""Reinstall the exact Thai ZIP on clean data in the stopped copied fixture.

The diagnostic Wine loader is disabled for the next runtime check. Use
``--restore-loader`` only after that check and after the fixture has stopped.
"""

import argparse
import json
import shutil
from pathlib import Path
from zipfile import ZipFile

from install_th_text_draft import GAME, fixture_stopped
from probe_assets import DEFAULT_GAME, ROOT, digest, require
from rehearse_th_archive_install import apply_archive

ARCHIVE = ROOT / "dist/NoImNotAHuman-th-preview-v1.zip"
PREFLIGHT = ROOT / "outputs/th-fresh-install-preflight-v3/report.json"
ARCHIVE_SHA256 = "300a409c6e0f6eae576bda12b20cb40e81f52d3998988ad23aa3f7d242cef24a"
LOADER_SHA256 = "8c6cdbc38836dee87e3368f5de1994d7c0ccebf29e4ce7aba3c0981f9375412c"
MODULE_SHA256 = "ff89d7ed545ec6a0d4268f67193e297890d5ffc2b50249c7d0e2e05f8d4a1f80"


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def expected():
    preflight = json.loads(PREFLIGHT.read_text())
    require(preflight["result"] == "passed-read-only-preflight" and
            preflight["archiveSha256"] == digest(ARCHIVE) == ARCHIVE_SHA256 and
            Path(preflight["game"]) == DEFAULT_GAME and
            len(preflight["originalFileHashes"]) == 31, "Preflight or archive changed")
    with ZipFile(ARCHIVE) as zipped:
        require(zipped.testzip() is None, "Archive CRC failed")
        report = json.loads(zipped.read("report.json"))
    packaged = {key: value["sha256"] for key, value in report["artifacts"].items()}
    originals = preflight["originalFileHashes"]
    require(set(packaged) == set(originals) and len(packaged) == 31,
            "Archive and original file sets differ")
    return originals, packaged


def prepare(output):
    require(output.is_relative_to(ROOT / "outputs") and not output.exists(),
            "Use a new canonical output directory")
    require(GAME.resolve().is_relative_to((ROOT / "runtime/No Human Probe.app").resolve()),
            "Fixture path escaped")
    originals, packaged = expected()
    fixture_stopped()
    require(all(digest(GAME / key) == packaged[key] for key in packaged),
            "Fixture is not the verified Thai package; reconcile it before preparing")
    require(all(digest(DEFAULT_GAME / key) == originals[key] for key in originals),
            "Original game changed since preflight")
    loader = GAME / "winhttp.dll"
    module = GAME / "BepInEx/plugins/NoHuman.TextRenderer/NoHuman.TextRenderer.dll"
    require(digest(loader) == LOADER_SHA256 and digest(module) == MODULE_SHA256,
            "Diagnostic loader or module changed")
    require(not (GAME / "BepInEx/config/nohuman-dialogue-probe.json").exists(),
            "Dialogue probe is still configured")
    output.mkdir(parents=True)
    receipt = {"phase": "restore-clean-data", "archiveSha256": ARCHIVE_SHA256,
               "fixture": str(GAME), "originalRestored": [], "overlayReceipt": None,
               "loaderDisabled": False,
               "commitBoundary": "Each data file is replaced atomically; the 31-file overlay is not a transaction. An incomplete receipt requires hash reconciliation before launch."}
    receipt_path = output / "receipt.json"
    save(receipt_path, receipt)
    for relative in sorted(originals):
        destination = GAME / relative
        temporary = destination.with_name(destination.name + ".th-clean-tmp")
        require(not temporary.exists(), "Unreconciled temporary file: " + relative)
        shutil.copy2(DEFAULT_GAME / relative, temporary)
        require(digest(temporary) == originals[relative], "Clean copy differs: " + relative)
        temporary.replace(destination)
        require(digest(destination) == originals[relative], "Clean replacement differs: " + relative)
        receipt["originalRestored"].append(relative)
        save(receipt_path, receipt)
    require(len(receipt["originalRestored"]) == 31, "Clean restore incomplete")
    receipt["phase"] = "apply-archive"
    save(receipt_path, receipt)
    overlay = apply_archive(ARCHIVE, GAME, output / "overlay", originals, packaged)
    require(overlay["completed"] and all(row["installed"] for row in overlay["files"]),
            "Archive overlay incomplete")
    receipt["overlayReceipt"] = str((output / "overlay/receipt.json").relative_to(ROOT))
    receipt["phase"] = "disable-loader"
    save(receipt_path, receipt)
    backup = output / "winhttp.dll"
    shutil.copy2(loader, backup)
    require(digest(backup) == LOADER_SHA256 and digest(loader) == LOADER_SHA256,
            "Loader backup mismatch")
    fixture_stopped()
    loader.unlink()
    require(not loader.exists() and all(digest(GAME / key) == packaged[key] for key in packaged),
            "Final fixture differs from archive without the loader")
    receipt.update(phase="ready-for-runtime", loaderDisabled=True,
                   loaderBackupSha256=digest(backup), filesMatchedArchive=31)
    save(receipt_path, receipt)
    print(json.dumps({"receipt": str(receipt_path.relative_to(ROOT)),
                      "result": receipt["phase"], "filesMatchedArchive": 31}))


def restore_loader(output):
    receipt_path = output / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    require(receipt["phase"] == "ready-for-runtime" and receipt["loaderDisabled"] and
            receipt["fixture"] == str(GAME), "Fixture preparation receipt is not complete")
    loader = GAME / "winhttp.dll"
    backup = output / "winhttp.dll"
    fixture_stopped()
    require(not loader.exists() and digest(backup) == LOADER_SHA256,
            "Loader state changed since preparation")
    temporary = loader.with_name("winhttp.dll.th-restore-tmp")
    require(not temporary.exists(), "Unreconciled loader temporary file")
    shutil.copy2(backup, temporary)
    require(digest(temporary) == LOADER_SHA256, "Loader restore copy differs")
    temporary.replace(loader)
    require(digest(loader) == LOADER_SHA256, "Loader restore mismatch")
    receipt["phase"] = "loader-restored"
    receipt["loaderDisabled"] = False
    save(receipt_path, receipt)
    print(json.dumps({"receipt": str(receipt_path.relative_to(ROOT)), "result": receipt["phase"]}))


def disable_loader(output):
    receipt_path = output / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    require(receipt["phase"] == "loader-restored" and not receipt["loaderDisabled"] and
            receipt["fixture"] == str(GAME), "Fixture loader has not been restored")
    _, packaged = expected()
    fixture_stopped()
    require(all(digest(GAME / key) == packaged[key] for key in packaged),
            "Fixture data differs from the exact Thai archive")
    loader = GAME / "winhttp.dll"
    backup = output / "winhttp.dll"
    require(digest(loader) == digest(backup) == LOADER_SHA256,
            "Diagnostic loader changed since preparation")
    loader.unlink()
    require(not loader.exists(), "Diagnostic loader remains installed")
    receipt["phase"] = "ready-for-runtime"
    receipt["loaderDisabled"] = True
    save(receipt_path, receipt)
    print(json.dumps({"receipt": str(receipt_path.relative_to(ROOT)), "result": receipt["phase"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--restore-loader", action="store_true")
    parser.add_argument("--disable-loader", action="store_true")
    args = parser.parse_args()
    target = args.output.resolve()
    require(not (args.restore_loader and args.disable_loader), "Choose one loader action")
    if args.restore_loader:
        restore_loader(target)
    elif args.disable_loader:
        disable_loader(target)
    else:
        prepare(target)
