#!/usr/bin/env python3
"""Rebuild the Persian cycle-1 dependency closure from pinned accepted IDs."""

import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[3]
CYCLE = pathlib.Path(__file__).resolve().parent
LOCALE = ROOT / "Translations/fa"
GUID = {
    "UI": "0cbd8a7a4f543344bb95659de87f67a5",
    "Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
    "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


def id_bytes(ids):
    return "".join(identifier + "\n" for identifier in ids).encode()


def immutable(path, data):
    if path.exists():
        assert path.read_bytes() == data, f"immutable evidence changed: {path}"
    else:
        path.write_bytes(data)


def main():
    manifest_path = ROOT / "Source/preserve-exactly-v4.json"
    source_path = ROOT / "Source/localization-inventory-v3/strings.jsonl"
    static_path = ROOT / "Source/localization-inventory-v3/static-text.jsonl"
    glossary_path = ROOT / "Documentation/glossary-translations/fa/layer.json"
    manifest = read(manifest_path)
    first_path = CYCLE / "first-pass.snapshot.json"
    first = read(first_path)
    plan_path = CYCLE / "correction-plan.json"
    plan = read(plan_path)
    delta_path = CYCLE / "file-delta-manifest.json"
    delta = read(delta_path)
    spec_path = CYCLE / "selector-spec.json"
    spec = read(spec_path)
    assert digest(first_path.read_bytes()) == plan["firstPassSnapshotSha256"]
    assert digest(plan_path.read_bytes()) == delta["correctionPlanSha256"]
    assert digest(manifest_path.read_bytes()) == first["pins"]["preserveExactlyManifestSha256"]
    assert digest(source_path.read_bytes()) == first["pins"]["sourceStringsSha256"]
    assert digest(static_path.read_bytes()) == first["pins"]["sourceStaticSha256"]
    assert digest(glossary_path.read_bytes()) == first["pins"]["persianGlossaryLayerSha256"]
    order = [row["stableId"] for row in manifest["tableRows"] + manifest["staticRows"]]
    assert len(order) == len(set(order)) == first["acceptedUnits"] == 16538
    accepted = set(order)
    source = {}
    for path in (source_path, static_path):
        for line in path.open():
            row = json.loads(line)
            source[row["stableId"]] = row
    assert accepted <= set(source)
    target = {}
    location = {}
    for path in sorted(LOCALE.glob("*batch-*.json")):
        if not re.fullmatch(r"(?:ui|dialogue|checks)-batch-\d{3}\.json", path.name):
            continue
        batch = read(path)
        for entry in batch["entries"]:
            sid = f"string:{GUID[batch['collection']]}:{entry['id']}"
            assert sid in accepted and sid not in target
            target[sid] = entry["target"]
            location[sid] = str(path.relative_to(ROOT))
    static_draft = LOCALE / "static-text-draft.json"
    for entry in read(static_draft)["entries"]:
        sid = entry["stableId"]
        assert sid in accepted and sid not in target
        target[sid] = entry["target"]
        location[sid] = str(static_draft.relative_to(ROOT))
    assert set(target) == accepted
    changed = {row["stableId"] for row in plan["rows"]}
    assert len(changed) == 76
    for row in plan["rows"]:
        assert source[row["stableId"]]["source"] == row["source"]
        assert target[row["stableId"]] == row["acceptedTarget"]
        assert location[row["stableId"]] == row["path"]
    for item in delta["files"]:
        assert digest((ROOT / item["path"]).read_bytes()) == item["afterSha256"]
        before = CYCLE / "before" / pathlib.Path(item["path"]).name
        after = CYCLE / "after" / pathlib.Path(item["path"]).name
        assert digest(before.read_bytes()) == item["beforeSha256"]
        assert digest(after.read_bytes()) == item["afterSha256"]

    nodes = set()
    for sid in changed:
        nodes.update(source[sid].get("nodeNames", []))
    family = tuple(spec["contextNodeFamilyPrefixes"])
    context = {sid for sid in accepted if
               nodes.intersection(source[sid].get("nodeNames", [])) or
               any(node.startswith(family) for node in source[sid].get("nodeNames", []))}
    changed_sources = {source[sid]["source"] for sid in changed}
    changed_before = {row["before"] for row in plan["rows"]}
    changed_after = {row["acceptedTarget"] for row in plan["rows"]}
    repetition = {sid for sid in accepted if
                  source[sid]["source"] in changed_sources or
                  target[sid] in changed_before or target[sid] in changed_after}
    source_patterns = [re.compile(value, re.IGNORECASE) for value in spec["sourceConceptPatterns"]]
    fragments = tuple(spec["targetConceptFragments"])
    glossary = {sid for sid in accepted if
                any(pattern.search(source[sid]["source"]) for pattern in source_patterns) or
                any(fragment in target[sid] for fragment in fragments)}
    runtime = {sid for sid in accepted if
               re.search(r"\{[^{}]+\}|<[^<>]+>", source[sid]["source"]) or
               any("_Occupied" in node for node in source[sid].get("nodeNames", []))}
    exact = {row["stableId"] for row in manifest["tableRows"] + manifest["staticRows"]
             if row.get("wholeTextExact")}
    mandatory = {sid for sid in accepted if
                 sid.startswith("tmp:") or sid.startswith("string:" + GUID["UI"] + ":") or
                 sid in exact or re.search(r"\{[^{}]+\}|<[^<>]+>", source[sid]["source"])}
    watchlist = {item["stableId"] for item in first["contextWatchlist"]}
    assert len(watchlist) == 4 and watchlist <= accepted
    components = {
        "changed": changed,
        "context": context,
        "repetition": repetition,
        "glossaryReferent": glossary,
        "runtimeBinding": runtime,
        "mandatoryRegression": mandatory,
        "contextWatchlist": watchlist,
    }
    closure = set().union(*components.values())
    assert changed <= closure <= accepted
    ordered = {name: [sid for sid in order if sid in values] for name, values in components.items()}
    ordered["closure"] = [sid for sid in order if sid in closure]
    assert set(ordered["closure"]) == closure
    for name, ids in ordered.items():
        immutable(CYCLE / f"{name}-ids.txt", id_bytes(ids))
    hashes = {name: {"count": len(ids), "sha256": digest(id_bytes(ids))}
              for name, ids in ordered.items()}
    rows = [{"stableId": sid, "path": location[sid], "source": source[sid]["source"],
             "target": target[sid], "nodeNames": source[sid].get("nodeNames", []),
             "components": [name for name, values in components.items() if sid in values]}
            for sid in ordered["closure"]]
    compiled = ROOT / "Source/glossary-corpus-v1/sharedassets0.assets-2743.json"
    result = {
        "schemaVersion": 1, "locale": "fa", "cycle": 1,
        "phase": "independent-review-handoff; editorial-acceptance-pending",
        "acceptedUnits": len(order), "sourceManifestSha256": digest(manifest_path.read_bytes()),
        "sourceInventorySha256": digest(source_path.read_bytes()),
        "staticInventorySha256": digest(static_path.read_bytes()),
        "glossaryLayerSha256": digest(glossary_path.read_bytes()),
        "compiledYarnAssetSha256": digest(compiled.read_bytes()),
        "firstPassSnapshotSha256": digest(first_path.read_bytes()),
        "correctionPlanSha256": digest(plan_path.read_bytes()),
        "fileDeltaManifestSha256": digest(delta_path.read_bytes()),
        "selectorSpecSha256": digest(spec_path.read_bytes()),
        "componentHashes": hashes, "missingAcceptedIds": [], "extraUnacceptedIds": [],
        "reviewRows": rows,
        "runtimeContext": {
            "note": "Compiled Yarn source and node metadata are pinned; runtime resident value enumeration is unavailable without game execution.",
            "dynamicIds": [sid for sid in order if sid in changed and "{0}" in source[sid]["source"]],
        },
    }
    data = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode()
    immutable(CYCLE / "closure.json", data)
    print(json.dumps({"acceptedUnits": len(order), "changed": len(changed),
                      "closure": len(closure), "componentHashes": hashes,
                      "closureSha256": digest(data)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
