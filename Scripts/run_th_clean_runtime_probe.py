#!/usr/bin/env python3
"""Capture the exact Thai ZIP in the copied game without the diagnostic loader."""

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from fixture_preferences import FIXTURE, PREFERENCES, read_settings, replace_language
from install_th_text_draft import GAME, fixture_stopped
from prepare_th_clean_fixture import expected
from probe_assets import ROOT, digest, require
from run_saved_locale_probe import state, stop_fixture, wait_menu

sys.path.insert(0, str(ROOT / "Scripts/visual-qa"))
import guarded_click
import run_capture

SAVE = FIXTURE / "Contents/SharedSupport/prefix/drive_c/users/Sikarugir/AppData/LocalLow/Trioskaz/NoImNotAHuman"
LOADER_LOG = GAME / "BepInEx/LogOutput.log"


def log_identity(path):
    if not path.exists():
        return None
    return {"sha256": digest(path), "mtimeNs": path.stat().st_mtime_ns,
            "size": path.stat().st_size}


def start(preparation, output):
    require(output.is_relative_to(ROOT / "outputs") and not output.exists(),
            "Use a new canonical capture directory")
    require(preparation.is_relative_to(ROOT / "outputs") and
            (preparation / "receipt.json").is_file(),
            "Use a completed preparation under canonical outputs")
    prep = json.loads((preparation / "receipt.json").read_text())
    require(prep["phase"] == "ready-for-runtime" and prep["loaderDisabled"] and
            prep["fixture"] == str(GAME), "Clean fixture preparation is incomplete")
    _, packaged = expected()
    require(not (GAME / "winhttp.dll").exists() and
            all(digest(GAME / key) == packaged[key] for key in packaged),
            "Clean runtime data differs from the exact Thai ZIP")
    fixture_stopped()
    output.mkdir(parents=True)
    frozen = output / "frozen-helpers"
    frozen.mkdir()
    for source in (ROOT / "Scripts").rglob("*"):
        if source.is_file() and source.suffix in (".py", ".swift"):
            target = frozen / source.relative_to(ROOT / "Scripts")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    run_capture.SCRIPT = frozen / "visual-qa"
    guarded_click.SCRIPT = run_capture.SCRIPT
    helper = output / "window-info"
    subprocess.run(["/usr/bin/xcrun", "swiftc", "-module-cache-path",
                    "/private/tmp/no-human-swift-cache",
                    str(run_capture.SCRIPT / "window_info.swift"), "-o", str(helper)], check=True)
    info = state(helper)
    require(not info["applications"] and not info["windows"],
            "Fixture window is in use; preserve it")
    (output / "initial-state.json").write_text(json.dumps(info, indent=2) + "\n")
    shutil.copy2(PREFERENCES, output / "before-user.reg")
    shutil.copytree(SAVE, output / "before-save-directory")
    status = {"phase": "preparing-preferences", "preparation": str(preparation.relative_to(ROOT)),
              "preparationSha256": digest(preparation / "receipt.json"),
              "preferencesBackupSha256": digest(output / "before-user.reg"),
              "installedThaiFilesMatched": 31, "diagnosticLoaderAbsent": True,
              "diagnosticLoaderLogBefore": log_identity(LOADER_LOG),
              "sourceHashes": {str(path.relative_to(frozen)): digest(path)
                               for path in frozen.rglob("*") if path.is_file()}}
    (output / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    require(digest(PREFERENCES) == status["preferencesBackupSha256"],
            "Preferences changed after backup")
    before = PREFERENCES.read_text()
    current = read_settings(before)[2]["TextSettingsData"]["SelectedLanguage"]
    changed, _ = replace_language(before, current, "th")
    temporary = PREFERENCES.with_name("user.reg.th-clean-tmp")
    require(not temporary.exists(), "Unreconciled preference temporary file")
    temporary.write_text(changed)
    temporary.replace(PREFERENCES)
    require(read_settings(PREFERENCES.read_text())[2]["TextSettingsData"]["SelectedLanguage"] == "th",
            "Saved Thai locale was not set")
    status["phase"] = "launch-request"
    (output / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    subprocess.run(["/usr/bin/open", str(FIXTURE)], check=True)
    wait_menu(helper, ROOT / "outputs/renderer-final-runtime/ru/menu/native.png",
              output / "readiness")
    run_capture.run(output / "menu", None)
    guarded_click.run(output / "menu/native.png", [580, 1580, 324, 100],
                      [372, 818], output / "new-game",
                      extra_guards=[(ROOT / "outputs/renderer-final-runtime/ru/menu/native.png",
                                     [600, 400, 300, 300], .12)])
    time.sleep(2)
    run_capture.run(output / "after-new-game", None)
    status["phase"] = "new-game-input-sent; visual-review-required"
    (output / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps({"status": status["phase"], "output": str(output.relative_to(ROOT))}))


def finish(output):
    require(output.is_relative_to(ROOT / "outputs") and (output / "status.json").is_file(),
            "Use an existing canonical capture directory")
    status_path = output / "status.json"
    status = json.loads(status_path.read_text())
    require(status["phase"] in ("preparing-preferences", "launch-request",
                                "new-game-input-sent; visual-review-required"),
            "Unexpected clean runtime phase")
    run_capture.SCRIPT = output / "frozen-helpers/visual-qa"
    helper = output / "window-info"
    info = state(helper)
    if info["applications"] or info["windows"]:
        if info["windows"]:
            try:
                run_capture.run(output / "finish-frame", None)
            except (OSError, ValueError, subprocess.CalledProcessError, SystemExit) as error:
                (output / "finish-frame-error.txt").write_text(str(error) + "\n")
        stop_fixture(helper, output / "stop.json")
    else:
        fixture_stopped()
        (output / "stop.json").write_text(json.dumps({"alreadyStopped": True}, indent=2) + "\n")
    shutil.copy2(output / "before-user.reg", PREFERENCES)
    require(digest(PREFERENCES) == status["preferencesBackupSha256"],
            "Preference restoration mismatch")
    latest_save = {str(path.relative_to(SAVE)): digest(path) for path in SAVE.rglob("*") if path.is_file()}
    initial = output / "before-save-directory"
    before_save = {str(path.relative_to(initial)): digest(path) for path in initial.rglob("*") if path.is_file()}
    if (SAVE / "Player.log").exists():
        shutil.copy2(SAVE / "Player.log", output / "Player.log")
    after_loader_log = log_identity(LOADER_LOG)
    status.update(phase="stopped-and-restored", preferencesRestored=True,
                  diagnosticLoaderAbsentAtFinish=not (GAME / "winhttp.dll").exists(),
                  diagnosticLoaderLogAfter=after_loader_log,
                  diagnosticLoaderLogUnchanged=after_loader_log == status["diagnosticLoaderLogBefore"],
                  saveDirectoryChanged=sorted(key for key in set(latest_save) | set(before_save)
                                              if latest_save.get(key) != before_save.get(key)))
    status_path.write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps({"status": status["phase"],
                      "saveDirectoryChanged": status["saveDirectoryChanged"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preparation", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--finish", action="store_true")
    args = parser.parse_args()
    destination = args.output.resolve()
    if args.finish:
        finish(destination)
    else:
        require(args.preparation is not None, "Preparation receipt required")
        start(args.preparation.resolve(), destination)
