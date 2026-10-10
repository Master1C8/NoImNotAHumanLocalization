"""Compose, read back and archive one accepted locale as an offline preview."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from locale_text_inputs import accepted_inputs, project_path
from probe_assets import DEFAULT_GAME, ROOT, digest, require
from verify_locale_native import verify_native
from verify_locale_text import verify as verify_text


def read(path):
    return json.loads(path.read_text())


def write_new(path, value):
    require(not path.exists(), "Preserve prior receipt: " + str(path))
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def assemble(base, text_build, output):
    require(all(p.is_relative_to(ROOT / "outputs") for p in (base, text_build, output)) and
            not output.exists(), "Use a new canonical output directory")
    native, text = read(base / "report.json"), read(text_build / "report.json")
    locale = text["locale"]
    accepted_inputs(locale, project_path(text["semanticAcceptancePath"]), project_path(text["exactReportPath"]))
    verified = read(text_build / "verification.json")
    require(set(native["languages"]) == {locale} and native["sourceUnchanged"] is True and
            text["baseLanguages"] == [locale] and text["baseReportSha256"] == digest(base / "report.json") and
            verified["reportSha256"] == digest(text_build / "report.json") and
            verified["serializedValuesResult"] == verified["allOtherOverlayFieldsResult"] == "passed" and
            (verified["tableRowsCompared"], verified["staticRowsCompared"], verified["rtlOriginalTextRowsCompared"]) == (16360, 178, 165),
            "Native/overlay acceptance or verification stale")
    combined = {rel: (base / rel, details["sha256"], "native-base") for rel, details in native["artifacts"].items()}
    combined.update({rel: (text_build / rel, details["sha256"], "locale-text") for rel, details in text["artifacts"].items()})
    require(len(native["artifacts"]) == 24 and len(text["artifacts"]) == 10 and len(combined) == 31, "Unexpected artifact union")
    for rel, (source, expected, layer) in combined.items():
        require(rel.startswith("NoImNotAHuman_Data/") and
                source.resolve().is_relative_to(base if layer == "native-base" else text_build) and
                (output / rel).resolve().is_relative_to(output) and digest(source) == expected, "Invalid source artifact")
    output.mkdir(parents=True)
    artifacts = {}
    for rel, (source, expected, layer) in sorted(combined.items()):
        target = output / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        require(digest(target) == expected, "Composed artifact differs")
        artifacts[rel] = {"sha256": expected, "layer": layer}
    report = {"schemaVersion": 1, "locale": locale, "gameVersion": "1.3.19",
              "status": "isolated one-locale offline preview; runtime and font/layout QA not run",
              "baseReportPath": str((base / "report.json").relative_to(ROOT)), "baseReportSha256": digest(base / "report.json"),
              "textReportPath": str((text_build / "report.json").relative_to(ROOT)), "textReportSha256": digest(text_build / "report.json"),
              "textVerificationSha256": digest(text_build / "verification.json"), "newLocaleCount": 1,
              "translatedTextValues": 16538, "rtlOriginalTextValues": 165, "artifacts": artifacts,
              "texturesAndImagesTranslated": False, "originalGameUnchanged": True,
              "installerIncluded": False, "runtime": "not-run", "installation": "not-run"}
    write_new(output / "report.json", report)
    print(json.dumps({"locale": locale, "package": str(output.relative_to(ROOT)), "artifacts": 31}))


def verify(package):
    require(package.is_relative_to(ROOT / "outputs"), "Package escaped canonical outputs")
    report_path = package / "report.json"
    report = read(report_path)
    locale = report["locale"]
    base_report = project_path(report["baseReportPath"])
    text_report = project_path(report["textReportPath"])
    base, text_build = base_report.parent, text_report.parent
    require(report["newLocaleCount"] == 1 and report["translatedTextValues"] == 16538 and
            report["rtlOriginalTextValues"] == 165 and len(report["artifacts"]) == 31 and
            digest(base_report) == report["baseReportSha256"] and digest(text_report) == report["textReportSha256"] and
            digest(text_build / "verification.json") == report["textVerificationSha256"], "Package layers changed")
    expected = {**read(base_report)["artifacts"], **read(text_report)["artifacts"]}
    require(set(expected) == set(report["artifacts"]), "Package added/dropped artifacts")
    for rel, row in report["artifacts"].items():
        require((package / rel).resolve().is_relative_to(package) and
                digest(package / rel) == row["sha256"] == expected[rel]["sha256"], "Delivered package hash differs")
    native_result = verify_native(base, locale)
    # Reopen delivered text assets, rather than crediting only a build-side receipt.
    text_result = verify_text(text_build, artifact_root=package, write=False)
    text = read(text_report)
    for rel, expected_sha in text["sourceGameInputs"].items():
        require(digest(DEFAULT_GAME / rel) == expected_sha, "Original game changed since build")
    result = {"schemaVersion": 1, "locale": locale, "reportSha256": digest(report_path), "result": "passed",
              "verifierSha256": digest(Path(__file__)), "nativeVerifierSha256": digest(ROOT / "Scripts/verify_locale_native.py"),
              "textVerifierSha256": digest(ROOT / "Scripts/verify_locale_text.py"), "artifactHashesCompared": 31,
              "translatedTextValuesCompared": 16538, "rtlOriginalTextValuesCompared": 165,
              "nativeObjects": native_result, "deliveredTextObjects": text_result,
              "newLocales": [locale], "newUiKeys": ["language_" + locale], "fontRolesCompared": 3,
              "runtime": "not-run", "fontRenderingLayout": "not-run", "installation": "not-run"}
    write_new(package / "verification.json", result)
    print(json.dumps({"locale": locale, "result": "passed", "translatedTextValuesCompared": 16538}))


def archive(package, destination):
    require(package.is_relative_to(ROOT / "outputs") and destination.is_relative_to(ROOT / "dist") and
            not destination.exists() and not destination.with_suffix(destination.suffix + ".json").exists(),
            "Use a new canonical dist archive and receipt")
    report, verified = read(package / "report.json"), read(package / "verification.json")
    require(verified["result"] == "passed" and verified["reportSha256"] == digest(package / "report.json") and
            verified["locale"] == report["locale"], "Package not verified")
    expected = {rel: row["sha256"] for rel, row in report["artifacts"].items()}
    expected.update({name: digest(package / name) for name in ("report.json", "verification.json")})
    require(len(expected) == 33, "Unexpected archive member count")
    for rel, sha in expected.items():
        require((package / rel).resolve().is_relative_to(package) and digest(package / rel) == sha, "Pre-archive member changed")
    partial = destination.with_suffix(destination.suffix + ".partial")
    require(not partial.exists(), "Previous partial archive requires reconciliation")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(partial, "x", compression=ZIP_DEFLATED, compresslevel=6) as zipped:
        for name in sorted(expected):
            zipped.write(package / name, name)
    with ZipFile(partial) as zipped:
        require(zipped.namelist() == sorted(expected) and zipped.testzip() is None, "ZIP members/CRC differ")
        for name, sha in expected.items():
            require(hashlib.sha256(zipped.read(name)).hexdigest() == sha, "ZIP read-back hash differs")
    require(not destination.exists(), "Archive destination appeared during verification")
    partial.rename(destination)
    result = {"archive": str(destination.relative_to(ROOT)), "sha256": digest(destination),
              "archivedArtifacts": 31, "allMembersReadBack": 33, "locale": report["locale"],
              "status": "verified local offline preview", "runtime": "not-run", "installation": "not-run",
              "fontRenderingLayout": "not-run", "imagesTextures": "excluded"}
    write_new(destination.with_suffix(destination.suffix + ".json"), result)
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    compose = commands.add_parser("assemble")
    compose.add_argument("--base", type=Path, required=True)
    compose.add_argument("--text-build", type=Path, required=True)
    compose.add_argument("--output", type=Path, required=True)
    check = commands.add_parser("verify")
    check.add_argument("--package", type=Path, required=True)
    pack = commands.add_parser("archive")
    pack.add_argument("--package", type=Path, required=True)
    pack.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "assemble":
        assemble(args.base.resolve(), args.text_build.resolve(), args.output.resolve())
    elif args.command == "verify":
        verify(args.package.resolve())
    else:
        archive(args.package.resolve(), args.destination.resolve())
