#!/usr/bin/env python3
"""Prepare, preflight, then apply Dutch semantic corrections from pass 1.

Run `prepare` and inspect its immutable evidence before running `apply`.
This recipe is locale-owned; it never stages files or reads the game fixture.
"""

import argparse
import hashlib
import importlib.util
import json
import sys
import types
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FINDINGS = ROOT / "Translations/nl/semantic-findings-pass1.json"
PASS = ROOT / "Translations/nl/semantic-review-progress.json"
ROWS = ROOT / "Translations/nl/semantic-review-rows-pass1.jsonl"
MANIFEST = ROOT / "Source/preserve-exactly-v4.json"
PREPARED = HERE / "adjudicated-corrections.json"
PREFLIGHT = HERE / "complete-batch-preflight.json"
BEFORE = HERE / "before-rows.jsonl"
AFTER = HERE / "after-rows.jsonl"

# Full-unit wording refined after the scene and glossary check. All other
# findings use their recorded proposedTarget verbatim.
REFINEMENTS = {
    44: "Courier: Goed, je zou geloof ik je bestelling in ontvangst nemen. Neem je die aan?",
    76: "Raskolnikov: Waarschijnlijk kun je zelfs met je blote handen doden wie gedood moet worden.",
    90: "Mijn handen trillen nog steeds als ik eraan denk door dat raam te kijken.",
    124: "Bald: Naar de dokter ga ik zeker niet. Zoals ze zeggen: “Een kutkwaaltje gaat vanzelf over, maar de echte ellende is ongeneeslijk.”",
}

SCENE_NOTES = {
    6: "Embassy phone answer: the staff cannot physically carry him home and tells the caller to take him instead.",
    15: "For Rest supplies food and consumables; it is not limited to prepared meals.",
    16: "The neighbour suggests For Rest after discussing stored food; the service still has broader stock.",
    32: "TV advertisement contrasts walking to shop with phoning to order; preserve the walking-to-calling turn.",
    39: "Fairytaller says the landlord used unemployment as a pretext and moved step relatives in.",
    44: "Courier offers the order again; the adjacent player choice is to take the order.",
    47: "The occupied-house referent is selected dynamically; do not assign a male identity in Dutch.",
    53: "The next line calls attention to a rhyme; binnenlaat/vrijlaat retains that local joke and the free-space requirement.",
    56: "Miner refuses to descend because the player cannot pull him up, and offers to belay the player from above.",
    66: "The player's admission to SuperFake leaves removal method deliberately unstated.",
    88: "Prophet means both the person and their cat must enter.",
    90: "Collapsed-house ending recalls looking through a particular window; direction outside/inside is not stated.",
    94: "New KChS recruitment scene speculates about rotating shift duty, not length of shifts.",
    95: "FunnyGuy owns a rental flat; his occupants are tenants, as his next mortgage line confirms.",
    99: "The earlier player choice compares people to vegetables; the radish insult pays it off.",
    107: "GraveDigger's theory is about remembered people returning, not ordinary current thought.",
    109: "Luka audibly self-corrects the absent person's pronoun from male to female.",
    118: "FortuneTeller's adjacent clause says she closed her eyes and imagined her dream.",
    124: "Bald's doctor joke contrasts a passing minor ailment with incurable disaster; preserve coarse register.",
    126: "Experienced repeats the radish insult from the earlier vegetable exchange.",
    129: "Former KChS worker speaks about materials his own team failed to prepare.",
    132: "Scammer's preceding line says the marks must keep paying.",
    134: "Buddy_Ears scene; the following line identifies ordinary ears.",
    135: "Fugitive's quarantine line uses cleaning as a purge euphemism against tooth cleaning.",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_new(path, data):
    assert not path.exists(), f"Immutable evidence already exists: {path}"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def serialize_batch(doc, style):
    if style == "indented":
        return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    separators = (", ", ": ") if style == "compact-spaced" else (",", ":")
    lines = ["{"]
    for key, value in doc.items():
        if key == "entries":
            lines.append('  "entries": [')
            lines.extend("    " + json.dumps(entry, ensure_ascii=False, separators=separators) +
                         ("," if index < len(value) - 1 else "")
                         for index, entry in enumerate(value))
            lines.append("  ]")
        else:
            lines.append("  " + json.dumps(key) + ": " + json.dumps(value, ensure_ascii=False) + ",")
    lines.append("}")
    return "\n".join(lines) + "\n"


def original_style(doc, expected_hash):
    matches = [style for style in ("indented", "compact-spaced", "compact-tight")
               if hashlib.sha256(serialize_batch(doc, style).encode("utf-8")).hexdigest() == expected_hash]
    assert len(matches) == 1, "Cannot reproduce authored batch formatting"
    return matches[0]


def load_exact_validator():
    # preserve_exact's pure grammar checker imports probe_assets, whose module
    # imports UnityPy. Supply only its three trivial utility bindings to run
    # the unchanged shared checker without loading the game or its assets.
    module = types.ModuleType("probe_assets")
    module.ROOT = ROOT
    module.digest = sha
    def require(condition, message):
        if not condition:
            raise ValueError(message)
    module.require = require
    old = sys.modules.get("probe_assets")
    sys.modules["probe_assets"] = module
    try:
        spec = importlib.util.spec_from_file_location("nl_preserve_exact", ROOT / "Scripts/preserve_exact.py")
        script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(script)
    finally:
        if old is None:
            del sys.modules["probe_assets"]
        else:
            sys.modules["probe_assets"] = old
    return script


def evidence():
    review = json.loads(PASS.read_text())
    assert review["acceptedUnits"] == review["reviewedUnits"] == 16538
    assert review["nextId"] is None
    for pin in review["pins"].values():
        path = Path(pin["path"])
        if not path.is_absolute():
            path = ROOT / path
        assert sha(path) == pin["sha256"], f"Input changed: {path}"
    for item in review["reviewedFileHashes"]:
        assert sha(ROOT / item["path"]) == item["sha256"], f"Authored row changed: {item['path']}"
    assert sha(FINDINGS) == review["findings"]["sha256"]
    assert sha(ROWS) == review["reviewRows"]["sha256"]
    manifest = json.loads(MANIFEST.read_text())
    assert sha(MANIFEST) == review["pins"]["preserveExactManifest"]["sha256"]
    rowlist = [json.loads(line) for line in ROWS.open()]
    assert len(rowlist) == 16538
    findings = json.loads(FINDINGS.read_text())
    assert findings["reviewedThroughOrdinal"] == 16538 and len(findings["findings"]) == 138
    return review, manifest, rowlist, findings["findings"]


def prepare():
    review, manifest, rows, findings = evidence()
    rules = {r["stableId"]: r for r in manifest["tableRows"] + manifest["staticRows"]}
    inventory = {r["stableId"]: r for r in
                 (json.loads(line) for line in (ROOT / "Source/localization-inventory-v3/strings.jsonl").open())}
    exact = load_exact_validator()
    records = []
    seen = set()
    for number, item in enumerate(findings, 1):
        ordinal, sid = item["ordinal"], item["stableId"]
        assert sid not in seen and sid == rows[ordinal - 1]["stableId"]
        seen.add(sid)
        row = rows[ordinal - 1]
        assert row["source"] == item["source"] and row["target"] == item["currentTarget"]
        assert sha_text(row["source"]) == row["sourceSha256"]
        assert sha_text(row["target"]) == row["targetSha256"]
        after = REFINEMENTS.get(number, item["proposedTarget"])
        assert after != row["target"]
        exact.check_value(rules[sid], after)
        source_record = inventory.get(sid, {})
        records.append({
            "findingNumber": number, "ordinal": ordinal, "stableId": sid,
            "authoredPath": row["authoredPath"], "source": row["source"],
            "before": row["target"], "after": after,
            "reason": item["reason"],
            "decision": "accept with full-unit refinement" if number in REFINEMENTS else "accept proposed full unit",
            "sceneNote": SCENE_NOTES.get(number, "The pass-1 finding identifies a concrete source/target divergence in this unit."),
            "nodeNames": source_record.get("nodeNames", []), "key": source_record.get("key"),
            "protectedExact": "passed shared preserve_exact.check_value on the entire replacement",
        })
    assert len(records) == len(seen) == 138
    paths = sorted({r["authoredPath"] for r in records})
    before_hashes = [{"path": p, "sha256": sha(ROOT / p)} for p in paths]
    assert all(next(x for x in review["reviewedFileHashes"] if x["path"] == h["path"])["sha256"] == h["sha256"] for h in before_hashes)
    payload = {
        "schemaVersion": 1, "locale": "nl", "cycle": 1,
        "status": "all 138 objective findings adjudicated and accepted; independent review pending",
        "reviewPassSha256": sha(PASS), "reviewRowsSha256": sha(ROWS),
        "findingFileSha256": sha(FINDINGS), "pins": review["pins"],
        "beforeAuthoredHashes": before_hashes, "corrections": records,
    }
    write_new(PREPARED, payload)
    write_new(PREFLIGHT, {
        "schemaVersion": 1, "locale": "nl", "cycle": 1,
        "adjudicationSha256": sha(PREPARED), "sourceManifestSha256": sha(MANIFEST),
        "checkedFullReplacementUnits": len(records), "checkedUniqueStableIds": len(seen),
        "protectedSyntax": "passed unchanged shared preserve_exact.check_value for every proposed full replacement",
        "sourceTargetIdentity": "passed against immutable pass-1 rows, source and authored hashes",
        "runtimeConsumerEvidence": "inventory key/node and scene-note evidence recorded per correction; dynamic format slots checked; game runtime not launched",
        "approvedToApply": True,
    })
    print(f"Prepared and structurally preflighted {len(records)} corrections in {len(paths)} authored files")


def apply():
    assert PREPARED.exists() and PREFLIGHT.exists()
    data = json.loads(PREPARED.read_text())
    check = json.loads(PREFLIGHT.read_text())
    assert check["approvedToApply"] and check["adjudicationSha256"] == sha(PREPARED)
    assert check["sourceManifestSha256"] == sha(MANIFEST)
    for pin in data["pins"].values():
        path = Path(pin["path"])
        assert sha(path if path.is_absolute() else ROOT / path) == pin["sha256"]
    for h in data["beforeAuthoredHashes"]:
        assert sha(ROOT / h["path"]) == h["sha256"], f"Authored input changed: {h['path']}"
    assert not BEFORE.exists() and not AFTER.exists()
    by_path = {}
    for row in data["corrections"]:
        by_path.setdefault(row["authoredPath"], {})[row["stableId"]] = row
    before_rows, after_rows = [], []
    writes = []
    exact = load_exact_validator()
    rules = {r["stableId"]: r for r in json.loads(MANIFEST.read_text())["tableRows"]}
    guids = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
             "UI": "0cbd8a7a4f543344bb95659de87f67a5",
             "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}
    original_hashes = {h["path"]: h["sha256"] for h in data["beforeAuthoredHashes"]}
    for path, changes in by_path.items():
        doc = json.loads((ROOT / path).read_text())
        style = original_style(doc, original_hashes[path])
        guid = guids[doc["collection"]]
        encountered = set()
        for entry in doc["entries"]:
            sid = f"string:{guid}:{entry['id']}"
            if sid not in changes:
                continue
            row = changes[sid]
            assert entry["target"] == row["before"]
            exact.check_value(rules[sid], row["after"])
            encountered.add(sid)
            before_rows.append({"ordinal": row["ordinal"], "stableId": sid, "path": path,
                                "source": row["source"], "target": entry["target"],
                                "targetSha256": sha_text(entry["target"])})
            entry["target"] = row["after"]
            after_rows.append({"ordinal": row["ordinal"], "stableId": sid, "path": path,
                               "source": row["source"], "target": entry["target"],
                               "targetSha256": sha_text(entry["target"])})
        assert encountered == set(changes), f"Missing authored IDs in {path}"
        writes.append((ROOT / path, serialize_batch(doc, style)))
    before_rows.sort(key=lambda r: r["ordinal"])
    after_rows.sort(key=lambda r: r["ordinal"])
    assert len(before_rows) == len(after_rows) == len(data["corrections"]) == 138
    BEFORE.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in before_rows))
    AFTER.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in after_rows))
    for path, content in writes:
        path.write_text(content)
    print(f"Applied {len(after_rows)} preflighted full-unit corrections to {len(writes)} authored files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "apply"])
    args = parser.parse_args()
    prepare() if args.action == "prepare" else apply()
