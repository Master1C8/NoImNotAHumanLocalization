#!/usr/bin/env python3
"""Restore an interrupted dialogue probe only after its exact fixture has stopped."""

import argparse
import datetime
import json
import os
import shutil
import subprocess
from pathlib import Path

from fixture_preferences import FIXTURE, PREFERENCES, read_settings
from probe_assets import ROOT, digest, require


def restore(run):
    require(run.is_relative_to(ROOT / "outputs"), "Probe run escaped outputs")
    status = json.loads((run / "status.json").read_text())
    info = json.loads(subprocess.check_output([str(run / "window-info")], text=True))
    require(not info["applications"] and not info["windows"], "Fixture is open")
    lines = subprocess.check_output(["ps", "-axo", "pid,command"], text=True).splitlines()
    active = []
    for line in lines[1:]:
        fields = line.strip().split(None, 1)
        if len(fields) < 2 or int(fields[0]) in (os.getpid(), os.getppid()):
            continue
        if str(FIXTURE) in fields[1] or "NoImNotAHuman.exe" in fields[1] or "wineserver" in fields[1]:
            active.append(line)
    require(not active, "Game or Wine process remains: " + str(active[:3]))
    require(read_settings(PREFERENCES.read_text())[2] == status["probeSettings"],
            "Preferences changed since the probe; preserve owner settings")
    backup = run / "before-user.reg"
    require(digest(backup) == status["preferencesBackupSha256"], "Backup changed")
    game = FIXTURE / "Contents/SharedSupport/prefix/drive_c/KS Games/No Im not a Human"
    config = game / "BepInEx/config/nohuman-dialogue-probe.json"
    require(digest(config) == status["configSha256"], "Probe config changed")
    command = game / "BepInEx/config/nohuman-dialogue-command.json"
    require(not command.exists(), "Unexpected diagnostic command file")
    final = run / "final-recovery"
    final.mkdir(exist_ok=False)
    save = (FIXTURE / "Contents/SharedSupport/prefix/drive_c/users/Sikarugir/"
            "AppData/LocalLow/Trioskaz/NoImNotAHuman")
    for source in (game / "BepInEx/config/nohuman-dialogue-evidence.jsonl",
                   game / "BepInEx/LogOutput.log", save / "Player.log",
                   save / "Player-prev.log", config):
        if source.is_file():
            shutil.copy2(source, final / source.name)
    save_hashes = {path.name: digest(path) for path in save.iterdir() if path.is_file()}
    shutil.copy2(backup, PREFERENCES)
    require(digest(PREFERENCES) == digest(backup), "Preference restoration failed")
    config.unlink()
    report = {"restoredAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "fixtureStopped": True, "settingsRestoredExact": True,
              "diagnosticConfigRemoved": True, "saveFilesAfterProbe": save_hashes,
              "finalLogHashes": {path.name: digest(path) for path in final.iterdir()}}
    (final / "recovery.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    restore(args.run.resolve())
