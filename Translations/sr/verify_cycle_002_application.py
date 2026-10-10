#!/usr/bin/env python3
"""Prove cycle 002 changed only its 17 authored values across JSON formatting."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SR = ROOT / "Translations/sr"
OUT = SR / "semantic-cycle-002-application-verification.json"


def read(path):
    return json.loads(path.read_text())


def sha_bytes(contents):
    return hashlib.sha256(contents).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def encoded(document, style):
    if style == "pretty-entries":
        return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode()
    header = json.dumps({key: value for key, value in document.items()
                         if key != "entries"}, ensure_ascii=False, indent=2)[:-2]
    if style == "compact-dialogue-entries":
        entries = ",\n".join("    { \"id\": " + str(entry["id"]) +
                              ", \"target\": " + json.dumps(entry["target"], ensure_ascii=False) +
                              " }" for entry in document["entries"])
    elif style == "compact-ui-entries":
        entries = ",\n".join("    " + json.dumps(entry, ensure_ascii=False)
                              for entry in document["entries"])
    else:
        raise ValueError(style)
    return (header + ",\n  \"entries\": [\n" + entries + "\n  ]\n}\n").encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    prior = read(SR / "semantic-cycle-001-closure.json")
    current = read(SR / "semantic-cycle-002-corrections.json")
    plan = read(SR / "semantic-cycle-002-adjudication.json")
    prior_files = {row["path"]: row["sha256"] for row in prior["currentAuthoredFileHashes"]}
    current_files = {row["path"]: row["sha256"] for row in current["currentAuthoredFileHashes"]}
    require(set(prior_files) == set(current_files) and len(prior_files) == 341,
            "Authored file membership changed")
    by_file = defaultdict(list)
    for finding in plan["entries"]:
        by_file[finding["targetFile"]].append(finding)
    require(len(by_file) == 13, "Changed file count differs")
    proof = []
    for name in sorted(prior_files):
        path = ROOT / name
        contents = path.read_bytes()
        require(sha_bytes(contents) == current_files[name], "Current file hash differs")
        if name not in by_file:
            require(prior_files[name] == current_files[name], "Unrelated authored file changed")
            continue
        document = json.loads(contents)
        for finding in by_file[name]:
            identifier = int(finding["stableId"].rsplit(":", 1)[1])
            matching = [row for row in document["entries"] if row.get("id") == identifier]
            require(len(matching) == 1 and matching[0]["target"] == finding["acceptedTarget"],
                    "Applied target differs")
            matching[0]["target"] = finding["currentTarget"]
        styles = [style for style in ("pretty-entries", "compact-dialogue-entries",
                                       "compact-ui-entries")
                  if sha_bytes(encoded(document, style)) == prior_files[name]]
        require(len(styles) == 1, "Prior bytes cannot be reconstructed from value-only delta")
        proof.append({"path": name, "priorSha256": prior_files[name],
                      "currentSha256": current_files[name], "priorRowStyle": styles[0],
                      "changedIds": [r["stableId"] for r in by_file[name]],
                      "jsonFormattingNormalized": styles[0] != "pretty-entries"})
    require(len(proof) == 13 and sum(len(row["changedIds"]) for row in proof) == 17,
            "Application proof count differs")
    result = {"schemaVersion": 1, "locale": "sr", "cycle": "002",
              "status": "prior authored bytes reconstructed from current JSON after reversing exactly the accepted targets",
              "priorAuthoredFileSetSha256": prior["currentAuthoredFileSetSha256"],
              "currentAuthoredFileSetSha256": current["currentAuthoredFileSetSha256"],
              "unchangedFilesByteIdentical": 328,
              "changedFiles": 13, "changedTargetValues": 17,
              "jsonFormattingNormalizedFiles": sum(row["jsonFormattingNormalized"] for row in proof),
              "files": proof}
    content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if OUT.exists():
        require(OUT.read_text() == content, "Immutable application proof differs")
    else:
        require(args.write, "Application proof missing")
        OUT.write_text(content)
    print(json.dumps({"result": "written" if args.write else "verified",
                      "changedFiles": len(proof), "changedTargets": 17,
                      "unchangedFiles": 328,
                      "formattingNormalizedFiles": result["jsonFormattingNormalizedFiles"],
                      "sha256": sha_bytes(OUT.read_bytes())}))


if __name__ == "__main__":
    main()
