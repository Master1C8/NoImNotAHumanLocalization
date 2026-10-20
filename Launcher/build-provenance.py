#!/usr/bin/env python3
"""Build both NoHuman launchers locally and retain unsigned provenance."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def inventory(root):
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symlink material: " + str(path))
        if path.is_file():
            result[path.relative_to(root).as_posix()] = {
                "sha256": sha(path), "sizeBytes": path.stat().st_size}
    if not result:
        raise ValueError("Empty stage")
    return result


def verify(archive, stage, manifest):
    expected = {stage.name + "/" + name: row for name, row in inventory(stage).items()}
    expected[manifest.name] = {"sha256": sha(manifest), "sizeBytes": manifest.stat().st_size}
    with zipfile.ZipFile(archive) as package:
        files = [row for row in package.infolist() if not row.is_dir()]
        if len(files) != len(expected) or {row.filename for row in files} != set(expected):
            raise ValueError("Unexpected or duplicate archive files")
        for row in files:
            h = hashlib.sha256()
            with package.open(row) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    h.update(block)
            if (row.file_size != expected[row.filename]["sizeBytes"]
                    or h.hexdigest() != expected[row.filename]["sha256"]):
                raise ValueError("Archive bytes differ: " + row.filename)
    return len(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--release", required=True, type=Path)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--zig", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    payload, out, build, zig = (p.resolve() for p in
                                [args.payload, args.release, args.build, args.zig])
    if (not out.is_relative_to(root / "dist") or not build.is_relative_to(root / "outputs")
            or not payload.is_relative_to(root / "outputs") or out.exists() or build.exists()):
        raise ValueError("Use new canonical dist and outputs directories")
    if git(root, "branch", "--show-current") != "main" or git(root, "status", "--porcelain"):
        raise ValueError("Commit source on clean canonical main first")
    commit = git(root, "rev-parse", "HEAD")
    if git(root, "rev-parse", "origin/main") != commit:
        raise ValueError("Push source before building")
    repository = git(root, "remote", "get-url", "origin").removesuffix(".git")
    if repository != "https://github.com/Master1C8/NoImNotAHumanLocalization":
        raise ValueError("Unexpected canonical repository")
    if subprocess.check_output([str(zig), "version"], text=True).strip() != "0.15.2":
        raise ValueError("Use the pinned Zig 0.15.2")
    materials = inventory(payload)
    origin = payload.with_name(payload.name + "-origin.json")
    if not origin.is_file():
        raise ValueError("Retained payload origin record required")
    origin_hash = sha(origin)
    for row in (payload / "inventory.tsv").read_text().splitlines():
        name, expected = row.split("\t")
        if name not in materials or materials[name]["sha256"] != expected:
            raise ValueError("Payload inventory mismatch: " + name)
    tools = {"zig": {"sha256": sha(zig), "version": "0.15.2"}}
    for name in ["python3", "swiftc", "clang", "lipo", "codesign", "ditto"]:
        path = shutil.which(name)
        if not path:
            raise ValueError("Missing build tool: " + name)
        tools[name] = {"path": str(Path(path).resolve()), "sha256": sha(path)}
    tools["swiftVersion"] = subprocess.check_output(["swiftc", "--version"], text=True).strip()
    tools["sdkVersion"] = subprocess.check_output(["xcrun", "--show-sdk-version"], text=True).strip()
    started = datetime.now(timezone.utc).isoformat()
    out.mkdir(parents=True)
    with (out / "build.log").open("x") as log:
        subprocess.run(["python3", "Launcher/build.py", "--payload", str(payload),
                        "--out", str(build), "--zig", str(zig)], cwd=root,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
        # Fault injection is compiled only into the separate test executable.
        subprocess.run(["clang", "-target", "arm64-apple-macos14", "-O2",
                        "-DNOHUMAN_CLI", "-DNOHUMAN_TESTING", "-Wno-deprecated-declarations",
                        "Launcher/engine.c", "Launcher/vendor/zstd/zstddeclib.c", "-o",
                        str(build / "engine-testing-arm64")], cwd=root,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(["python3", "Launcher/test_engine.py", "--engine",
                        str(build / "engine-testing-arm64"), "--payload", str(payload),
                        "--out", str(build / "engine-checks")], cwd=root,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run([str(build / "engine-arm64"), str(payload),
                        str(build / "engine-checks/game"), "all"], cwd=root,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
        (out / "production-engine-verification.json").write_text(json.dumps({
            "status": "passed", "sha256": sha(build / "engine-arm64"),
            "boundary": "Uninstrumented production engine verifies and reapplies the isolated installed fixture",
            "faultInjectionBoundary": "Separate same-source executable compiled with NOHUMAN_TESTING",
            "instrumentedSha256": sha(build / "engine-testing-arm64")}, indent=2) + "\n")
    if git(root, "rev-parse", "HEAD") != commit or git(root, "status", "--porcelain"):
        raise ValueError("Source changed during build")
    if inventory(payload) != materials or sha(origin) != origin_hash:
        raise ValueError("Payload changed during build")
    records = []
    for platform, label, stage in [
        ("windows", "Windows", build / "No Human Launcher Windows"),
        ("macos", "macOS", build / "No Human Launcher.app"),
    ]:
        archive = build / ("NoHuman-Launcher-" + label + "-0.2.1.zip")
        manifest = out / "vnrevival-release.json"
        manifest.write_text(json.dumps({
            "schemaVersion": 1, "gameSlug": "no-im-not-a-human", "platform": platform,
            "version": "0.2.1", "sourceCommit": commit, "sourceTreeClean": True,
            "repositoryUrl": repository, "recipe": "Launcher/build-provenance.py",
            "payloadInventorySha256": sha(payload / "inventory.tsv"),
        }, indent=2) + "\n")
        with zipfile.ZipFile(archive, "a", compression=zipfile.ZIP_DEFLATED) as package:
            package.write(manifest, manifest.name)
        count = verify(archive, stage, manifest)
        manifest.rename(out / (platform + "-vnrevival-release.json"))
        archive.rename(out / archive.name)
        archive = out / archive.name
        if archive.stat().st_size > 100_000_000:
            raise ValueError("Archive exceeds 100 MB")
        records.append({"platform": platform, "filename": archive.name, "sha256": sha(archive),
                        "sizeBytes": archive.stat().st_size, "verifiedEntries": count})
    shutil.copyfile(build / "engine-checks/report.json", out / "engine-verification.json")
    shutil.copyfile(origin, out / "payload-origin.json")
    (out / "payload-materials.json").write_text(json.dumps(materials, indent=2) + "\n")
    (out / "source-tree.txt").write_text(git(root, "ls-tree", "-r", "--full-tree", commit) + "\n")
    (out / "SHA256SUMS").write_text("".join(r["sha256"] + "  " + r["filename"] + "\n" for r in records))
    (out / "provenance.json").write_text(json.dumps({
        "schemaVersion": 1, "source": {"repository": repository, "commit": commit,
        "tree": git(root, "rev-parse", "HEAD^{tree}")}, "version": "0.2.1",
        "build": {"method": "local macOS compilation and Windows cross-compilation",
        "recipe": "Launcher/build-provenance.py", "startedAt": started,
        "completedAt": datetime.now(timezone.utc).isoformat(), "tools": tools,
        "logSha256": sha(out / "build.log")},
        "materials": {"inventory": "payload-materials.json", "sha256": sha(out / "payload-materials.json"),
                      "origin": "payload-origin.json", "originSha256": origin_hash,
                      "availability": "Retained local payload; not distributed as public source"},
        "artifacts": records, "assurance": {"statement": "unsigned local build record",
        "publisherSignature": None, "notarization": None,
        "runtimeBoundary": "Native engine reconstruction and rollback in disposable fixtures; no new real-game run"}},
        indent=2) + "\n")
    print(json.dumps({"sourceCommit": commit, "artifacts": records}))


if __name__ == "__main__":
    main()
