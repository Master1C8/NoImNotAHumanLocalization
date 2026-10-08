#!/usr/bin/env python3
"""Compose verified native Thai-only game data for an isolated fixture."""

import argparse
import json
import shutil
from pathlib import Path

from probe_assets import ROOT, digest, require


def assemble(base, text_build, output):
    require(base.is_relative_to(ROOT / "outputs") and
            text_build.is_relative_to(ROOT / "outputs") and
            output.is_relative_to(ROOT / "outputs") and not output.exists(),
            "Use a new canonical output directory")
    base_report_path = base / "report.json"
    text_report_path = text_build / "report.json"
    base_report = json.loads(base_report_path.read_text())
    text_report = json.loads(text_report_path.read_text())
    verification = json.loads((text_build / "verification.json").read_text())
    require(set(base_report["languages"]) == {"th"} and base_report["sourceUnchanged"],
            "Native base must add only Thai")
    require(text_report["baseLanguages"] == ["th"] and
            text_report["baseReportSha256"] == digest(base_report_path) and
            verification["reportSha256"] == digest(text_report_path) and
            verification["serializedValuesResult"] == "passed" and
            verification["tableRowsCompared"] == 16360 and
            verification["staticRowsCompared"] == 178 and
            verification["rtlOriginalTextRowsCompared"] == 165,
            "Thai text build or verification is stale")
    combined = {rel: (base / rel, details["sha256"], "native-base")
                for rel, details in base_report["artifacts"].items()}
    combined.update({rel: (text_build / rel, details["sha256"], "thai-text")
                     for rel, details in text_report["artifacts"].items()})
    require(len(base_report["artifacts"]) == 24 and
            len(text_report["artifacts"]) == 10 and len(combined) == 31,
            "Unexpected Thai-only artifact union")
    output.mkdir(parents=True)
    artifacts = {}
    for rel, (source, expected, layer) in sorted(combined.items()):
        require(rel.startswith("NoImNotAHuman_Data/") and
                source.resolve().is_relative_to((base if layer == "native-base"
                                                  else text_build).resolve()) and
                digest(source) == expected, "Source artifact changed: " + rel)
        target = output / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        require(digest(target) == expected, "Composed artifact changed: " + rel)
        artifacts[rel] = {"sha256": expected, "layer": layer}
    report = {"schemaVersion": 1, "locale": "th", "gameVersion": "1.3.19",
              "status": "isolated Thai-only data package; full runtime gate pending",
              "baseReportSha256": digest(base_report_path),
              "textReportSha256": digest(text_report_path),
              "textVerificationSha256": digest(text_build / "verification.json"),
              "newLocaleCount": 1, "translatedTextValues": 16538,
              "rtlOriginalTextValues": 165, "artifacts": artifacts,
              "texturesAndImagesTranslated": False,
              "originalGameUnchanged": True}
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"report": str((output / "report.json").relative_to(ROOT)),
                      "artifacts": len(artifacts), "newLocales": 1}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--text-build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assemble(args.base.resolve(), args.text_build.resolve(), args.output.resolve())
