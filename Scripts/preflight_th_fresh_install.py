#!/usr/bin/env python3
"""Check the Thai archive against an untouched game before installation."""

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from probe_assets import DEFAULT_GAME, ROOT, digest, require


def sha(data):
    return hashlib.sha256(data).hexdigest()


def preflight(archive, game, output):
    require(archive.is_relative_to(ROOT / "dist") and
            output.is_relative_to(ROOT / "outputs") and not output.exists(),
            "Use the canonical archive and a new output directory")
    native_report_path = ROOT / "outputs/th-native-base-v1/report.json"
    native = json.loads(native_report_path.read_text())
    source_inventory_path = ROOT / "Source/localization-inventory-v3/summary.json"
    source_inventory = json.loads(source_inventory_path.read_text())
    require(native["buildGuid"] == "c003ddc7de634775a85305fef3b9a0d3" and
            len(native["inputs"]) == 24, "Native source binding changed")
    require(not (game / "winhttp.dll").exists() and
            not (game / "BepInEx/plugins/NoHuman.TextRenderer/NoHuman.TextRenderer.dll").exists(),
            "Original game already contains the diagnostic runtime loader")

    with ZipFile(archive) as zipped:
        require(zipped.testzip() is None, "Archive CRC failed")
        names = zipped.namelist()
        require(len(names) == len(set(names)), "Duplicate archive member")
        report_bytes = zipped.read("report.json")
        verification = json.loads(zipped.read("verification.json"))
        report = json.loads(report_bytes)
        expected = {relative: row["sha256"] for relative, row in report["artifacts"].items()}
        require(report["locale"] == "th" and report["gameVersion"] == "1.3.19" and
                report["newLocaleCount"] == 1 and report["translatedTextValues"] == 16538 and
                len(expected) == 31 and verification["result"] == "passed" and
                verification["reportSha256"] == sha(report_bytes),
                "Archive report or verification changed")
        require(set(names) == {*expected, "report.json", "verification.json"} and
                all(relative.startswith("NoImNotAHuman_Data/") and
                    not Path(relative).is_absolute() and ".." not in Path(relative).parts
                    for relative in expected),
                "Unexpected or unsafe archive members")
        for relative, wanted in expected.items():
            require(sha(zipped.read(relative)) == wanted,
                    "Archived artifact hash mismatch: " + relative)

    pinned = dict(native["inputs"])
    for relative, value in source_inventory["staticTextSourcePins"].items():
        if relative in expected:
            require(relative not in pinned or pinned[relative] == value,
                    "Source inventory and native build disagree: " + relative)
            pinned[relative] = value
    require(set(pinned) == set(expected), "Fresh-install baseline is not fully pinned")

    baseline = {}
    changed = 0
    for relative, wanted in sorted(expected.items()):
        source = game / relative
        require(source.is_file() and source.resolve().is_relative_to(game.resolve()),
                "Original game file missing: " + relative)
        original = digest(source)
        require(original == pinned[relative],
                "Installed game differs from the pinned build: " + relative)
        baseline[relative] = original
        changed += original != wanted
    require(changed > 0, "Thai archive matches the original game unexpectedly")
    baseline_set = sha("".join(f"{key}\t{value}\n" for key, value in
                                   sorted(baseline.items())).encode())
    result = {
        "schemaVersion": 1,
        "scope": "Read-only preflight for a fresh Thai data overlay; runtime installation and plugin independence remain unverified",
        "archive": str(archive.relative_to(ROOT)),
        "archiveSha256": digest(archive),
        "game": str(game),
        "gameVersion": report["gameVersion"],
        "buildGuid": native["buildGuid"],
        "sourceReportSha256": digest(native_report_path),
        "sourceInventorySha256": digest(source_inventory_path),
        "archiveMembersVerified": len(expected) + 2,
        "originalFilesPresent": len(baseline),
        "originalDiagnosticLoaderAbsent": True,
        "pinnedOriginalHashesMatched": len(pinned),
        "filesDifferingFromOriginal": changed,
        "originalFileHashes": baseline,
        "originalSetSha256": baseline_set,
        "result": "passed-read-only-preflight",
    }
    output.mkdir(parents=True)
    (output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items()
                      if key != "originalFileHashes"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--game", type=Path, default=DEFAULT_GAME)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    preflight(args.archive.resolve(), args.game.resolve(), args.output.resolve())
