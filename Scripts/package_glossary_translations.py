#!/usr/bin/env python3
"""Package coordinator-accepted, hash-pinned glossary artifacts.

This is a structural copier. It cannot perform or award semantic reviews.
It writes only this checkout; the coordinator separately integrates SiteForMods.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "Documentation/glossary-translations"
SOURCE = ROOT / "Documentation/glossary-research/final-v1/glossary.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".pending")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def copy_immutable(source, destination):
    """Preserve read-only evidence; never open an existing snapshot for write."""
    source, destination = Path(source), Path(destination)
    if destination.is_file() and destination.read_bytes() == source.read_bytes():
        return str(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".glossary-copy-", dir=destination.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copy2(source, temporary)
        if temporary.read_bytes() != source.read_bytes():
            raise ValueError("Evidence copy differs: " + str(source))
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return str(destination)


def bounded_path(relative):
    path = (BASE / relative).resolve()
    if not path.is_relative_to(BASE.resolve()):
        raise ValueError("Evidence path leaves the glossary project")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--complete", action="store_true", help="Require all authorized targets before replacing the export")
    args = parser.parse_args()
    manifest = read(BASE / "acceptance-manifest.json")
    if digest(SOURCE) != manifest["sourceRawSha256"]:
        raise ValueError("Approved source changed")
    entries = read(SOURCE)["entries"]
    ids = [row["id"] for row in entries]
    locales = manifest["authorizedLocales"]
    accepted = manifest["accepted"]
    if args.complete and set(accepted) != set(locales):
        raise ValueError("Not all targets have coordinator acceptance")
    prepared = {}
    # Validate all inputs before writes. Reviews are human/model evidence,
    # recorded by the coordinator; existence and hashes do not prove quality.
    for code, item in accepted.items():
        layer_path = BASE / code / "layer.json"
        authored_path = BASE / code / "authored.json"
        if digest(layer_path) != item["layerRawSha256"] or digest(authored_path) != item["authoredRawSha256"]:
            raise ValueError(f"{code}: accepted content changed")
        layer = read(layer_path)
        authored = read(authored_path)
        if list(layer) != ids or [row[0] for row in authored] != ids:
            raise ValueError(f"{code}: source order/IDs differ")
        if layer != {row[0]: {"term": row[1], "meaning": row[2]} for row in authored}:
            raise ValueError(f"{code}: authored/layer mismatch")
        for value in layer.values():
            if set(value) != {"term", "meaning"} or any(not isinstance(x, str) or not x.strip() for x in value.values()):
                raise ValueError(f"{code}: malformed field")
        for source_entry in entries:
            for field in ("term", "meaning"):
                expected_tags = re.findall(r"<sprite=[^>]+>", source_entry[field])
                actual_tags = re.findall(r"<sprite=[^>]+>", layer[source_entry["id"]][field])
                if actual_tags != expected_tags:
                    raise ValueError(f"{code}: sprite literals differ in {source_entry['id']}.{field}")
        for relative, expected in item["evidenceSha256"].items():
            if digest(bounded_path(relative)) != expected:
                raise ValueError(f"{code}: review evidence changed: {relative}")
        prepared[code] = layer
    reviews = BASE / "canonical-reviews"
    for code, item in accepted.items():
        if item.get("reuseCanonicalPackage"):
            existing = read(reviews / f"{code}.json")
            if existing["layerRawSha256"] != item["layerRawSha256"]:
                raise ValueError(f"{code}: existing canonical package mismatch")
            continue
        author_destination = reviews / "artifacts" / code
        shutil.copytree(BASE / code, author_destination, dirs_exist_ok=True, copy_function=copy_immutable)
        independent_destination = reviews / "independent" / code
        independent_destination.mkdir(parents=True, exist_ok=True)
        for relative in item["independentArtifacts"]:
            source_path = bounded_path(relative)
            copy_immutable(source_path, independent_destination / source_path.name)
        receipt = bounded_path(item["independentReceipt"])
        record = {
            "schemaVersion": 1, "game": "no-im-not-a-human", "version": "1.3.19",
            "locale": code, "mode": "STANDARD", "status": "editorially-accepted-canonical",
            "sourceRawSha256": manifest["sourceRawSha256"],
            "sourceParsedFingerprint": manifest["sourceParsedFingerprint"],
            "layerRawSha256": item["layerRawSha256"], "authoredRawSha256": item["authoredRawSha256"],
            "entryCount": len(ids), "exactSourceIdsAndOrder": True, "fields": ["term", "meaning"],
            "structuralValidation": "Exact ordered IDs, nonempty fields and authored/layer equality; not semantic proof.",
            "consecutiveCleanFullAudits": 3, "selfAudits": 2, "independentFinalColdAudits": 1,
            "authorReview": f"artifacts/{code}/review.json",
            "authoredArtifact": f"artifacts/{code}/authored.json", "layerArtifact": f"artifacts/{code}/layer.json",
            "selfAuditEvidence": [f"artifacts/{relative}" for relative in item["selfAuditEvidence"]],
            "independentReview": f"independent/{code}/{receipt.name}",
            "acceptanceManifest": "Coordinator acceptance is bound to all evidence hashes in the game checkout acceptance-manifest.json.",
            "historicalArtifactContext": "Original author statuses and history are preserved. Author-relative paths resolve within artifacts/<locale>/. Independent final receipt and its immutable snapshots resolve within independent/<locale>/; historical game-checkout links retain their original provenance.",
            "unresolvedFindings": [], "rendererReadiness": "unverified; standalone glossary scope",
            "gameTextTranslation": "not started", "publication": "not authorized",
            "model": "gpt-6.1-sol", "reasoningEffort": "high",
            "tokenAccounting": "Measured group usage is recorded separately; do not multiply assignment totals by locale count."
        }
        save(reviews / f"{code}.json", record)
    if args.complete:
        save(BASE / "glossary-translations.json", {code: prepared[code] for code in locales})
    print(f"Packaged {len(accepted)} accepted locales; export replaced: {args.complete}. No editorial credit awarded by this script.")


if __name__ == "__main__":
    main()
