#!/usr/bin/env python3
"""Adjudicate review01 and preflight the bounded Greek cycle-2 correction batch."""

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import check_value  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main():
    review = HERE / "independent-review-01"
    findings = json.loads((review / "findings-v3.json").read_text())["findings"]
    manifest = json.loads((ROOT / "Source/preserve-exactly-v4.json").read_text())
    source = {}
    for path in (ROOT / "Source/localization-inventory-v3/strings.jsonl",
                 ROOT / "Source/localization-inventory-v3/static-text.jsonl"):
        for line in path.open():
            row = json.loads(line)
            source[row["stableId"]] = row
    accepted = manifest["tableRows"] + manifest["staticRows"]
    ordinal = {row["stableId"]: i for i, row in enumerate(accepted)}
    rules = {row["stableId"]: row for row in accepted}
    by_key = {row.get("key"): row for row in source.values() if row.get("key")}
    additions = {
        "line:phone_phoneroulette_05e3bc8": (
            "Phone: Γεια σας, καλέσατε την Τηλεφωνική ρουλέτα. Θα σας βρούμε αμέσως το ιδανικό άτομο για κουβέντα. Παρακαλώ περιμένετε.",
            "Undisclosed future caller; masculine prospective role assigns a sex."),
        "line:radio_5_09b3a2c": (
            "Καλέστε τώρα στο 891-533 και θα βρούμε το ιδανικό άτομο για κουβέντα.",
            "Same prospective caller in the radio advertisement; preserve 891-533."),
        "line:radio_1_0d6b913": (
            "— Εμπρός, εδώ μιλά το άτομο που συντονίζει την υπηρεσία διάσωσης. Πώς μπορώ να βοηθήσω; — Άνθρωποι… καίγονται.",
            "Source identifies a rescue dispatcher; current target attributes speech to the service organization. Restore the neutral individual."),
    }
    rows = [{"stableId": f["stableId"], "reviewFindingId": f["findingId"],
             "source": f["source"], "before": f["before"],
             "after": f["proposedTarget"], "reason": f["reason"]} for f in findings]
    for key, (after, reason) in additions.items():
        src = by_key[key]
        rows.append({"stableId": src["stableId"], "reviewFindingId": None,
                     "source": src["source"], "after": after, "reason": reason})
    batches = {}
    for path in sorted(HERE.glob("*-batch-[0-9][0-9][0-9].json")):
        data = json.loads(path.read_text())
        for entry in data["entries"]:
            assert entry["id"] not in batches
            batches[entry["id"]] = (path, entry)
    static = json.loads((HERE / "static-text-draft.json").read_text())
    static_entries = {entry["stableId"]: entry for entry in static["entries"]}
    lexicon = json.loads((HERE / "static-lexicon-001.authored.json").read_text())
    lexicon_entries = {entry["source"]: entry for entry in lexicon["lexicon"]}
    for row in rows:
        sid = row["stableId"]
        src = source[sid]
        assert sid in ordinal and src["source"] == row["source"]
        row["ordinal"] = ordinal[sid]
        row["key"] = src.get("key")
        row["sourceSha256"] = text_digest(row["source"])
        if sid.startswith("tmp:"):
            target_file = HERE / "static-text-draft.json"
            entry = static_entries[sid]
            authored = HERE / "static-lexicon-001.authored.json"
            assert lexicon_entries[row["source"]]["target"] == entry["target"]
        else:
            target_file, entry = batches[int(sid.rsplit(":", 1)[1])]
            authored = HERE / f"dialogue-ordered-{target_file.stem[-3:]}.authored.json"
            if not authored.exists():
                authored = target_file
            else:
                targets = json.loads(authored.read_text())["targets"]
                assert entry["target"] in [value for _, value in targets]
        row["authoredInput"] = str(authored.relative_to(ROOT))
        row["targetFile"] = str(target_file.relative_to(ROOT))
        row["before"] = row.get("before", entry["target"])
        assert row["before"] == entry["target"], sid
        row["beforeSha256"] = text_digest(row["before"])
        row["afterSha256"] = text_digest(row["after"])
        row["authoredInputBeforeSha256"] = digest(authored)
        row["targetFileBeforeSha256"] = digest(target_file)
        check_value(rules[sid], row["after"])
    assert len(rows) == 26 and len({row["stableId"] for row in rows}) == 26
    rows.sort(key=lambda row: row["ordinal"])
    plan = {
        "schemaVersion": 1, "locale": "el", "cycle": 2,
        "status": "adjudicated and preserve-exact preflight passed; authored application pending",
        "acceptedUnits": 16538, "review01FindingsAdjudicated": 23,
        "review01FindingsAccepted": 23, "boundedAdditionalCorrections": 3,
        "correctionCount": len(rows),
        "sourceInventorySha256": digest(ROOT / "Source/localization-inventory-v3/strings.jsonl"),
        "sourceStaticSha256": digest(ROOT / "Source/localization-inventory-v3/static-text.jsonl"),
        "approvedGlossarySha256": digest(ROOT / "Documentation/glossary-translations/el/layer.json"),
        "firstPassProgressSha256": digest(HERE / "semantic-review-progress.json"),
        "review01FindingsSha256": digest(review / "findings-v3.json"),
        "review01EvidenceManifestSha256": digest(review / "evidence-manifest-v3.json"),
        "review01DecisionsSha256": digest(review / "decisions.jsonl"),
        "previousClosureManifestSha256": digest(HERE / "correction-cycle-001-closure-manifest.json"),
        "boundedAudit": {
            "unknownRoleAnchors": "25 canonical anchors checked (20 absent from the prior closure); six review proposals and two additional anchor corrections, plus one associated radio advertisement correction; other anchors retain neutral or source-supported wording",
            "kilotonCallbacks": "Three source occurrences; one previously selected and two omitted callbacks; no further objective wording correction after compiled scene review",
            "humanInhumane": "Six source нелюд substring cases inspected; one ontological/moral mismatch is review finding 014",
            "ratMouse": "Three source крысы cases inspected; one mismatch is review finding 015",
            "Death": "Named and lowercase entity occurrences inspected in cult dialogue; one omitted reveal is review finding 013",
            "dynamicDeficit": "Six serialized deficit enum values, seven accepted labels, 18 assembled bribe cases and 14 item-hint cases checked; findings 008-010 remove invalid article/plural agreement",
            "reachabilityLimit": "29 prior closure dialogue keys without compiled occurrences remain a limit; no runtime claim"},
        "corrections": rows}
    out = HERE / "correction-cycle-002-adjudication.json"
    assert not out.exists(), "Preserve immutable adjudication"
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"preflight": "passed", "corrections": len(rows),
                      "planSha256": digest(out)}))


if __name__ == "__main__":
    main()
