#!/usr/bin/env python3
"""Archive a verified Thai-only preview and compare its extracted bytes in memory."""

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from probe_assets import ROOT, digest, require


def archive(package, destination):
    require(package.is_relative_to(ROOT / "outputs") and
            destination.is_relative_to(ROOT / "dist") and
            not destination.exists(), "Use a new canonical dist archive")
    report = json.loads((package / "report.json").read_text())
    verification = json.loads((package / "verification.json").read_text())
    require(report["locale"] == "th" and verification["result"] == "passed" and
            verification["reportSha256"] == digest(package / "report.json"),
            "Thai-only package is not verified")
    expected = {relative: row["sha256"] for relative, row in report["artifacts"].items()}
    require(len(expected) == 31, "Unexpected package file count")
    members = sorted(["report.json", "verification.json", *expected])
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, "w", compression=ZIP_DEFLATED, compresslevel=6) as zipped:
        for member in members:
            source = package / member
            require(source.resolve().is_relative_to(package.resolve()) and source.is_file(),
                    "Missing package member")
            zipped.write(source, member)
    with ZipFile(destination) as zipped:
        require(zipped.namelist() == members and zipped.testzip() is None,
                "Archive members or CRC differ")
        for member, expected_sha in expected.items():
            require(hashlib.sha256(zipped.read(member)).hexdigest() == expected_sha,
                    "Archived artifact differs: " + member)
        require(hashlib.sha256(zipped.read("report.json")).hexdigest() ==
                verification["reportSha256"], "Archived report differs")
    result = {"archive": str(destination.relative_to(ROOT)),
              "sha256": digest(destination), "archivedArtifacts": len(expected),
              "newLocales": ["th"], "status": "verified local preview; full runtime gate pending"}
    destination.with_suffix(destination.suffix + ".json").write_text(
        json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    archive(args.package.resolve(), args.destination.resolve())
