#!/usr/bin/env python3
"""Build reproducible Hebrew correction-cycle review components in source order."""

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CYCLE = Path(__file__).resolve().parent
HE = CYCLE.parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(path.read_bytes())


def write_once(path, data):
    if path.exists():
        assert path.read_bytes() == data, f"Immutable evidence differs: {path}"
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def canonical_lines(ids, order):
    return ("\n".join(sorted(ids, key=order.__getitem__)) + "\n").encode()


def main():
    g = json.loads((CYCLE / "baseline-progress.json").read_text())
    a = json.loads((CYCLE / "adjudications.json").read_text())["records"]
    app = json.loads((CYCLE / "application.json").read_text())
    assert app["status"] == "applied" and len(a) == 120
    manifest = json.loads((ROOT / g["sourceInventory"]["preserveExactPath"]).read_text())
    accepted = manifest["tableRows"] + manifest["staticRows"]
    ordered_ids = [r["stableId"] for r in accepted]
    order = {sid: i for i, sid in enumerate(ordered_ids)}
    assert len(order) == len(ordered_ids) == 16538
    by_source = {r["stableId"]: r for r in
                 map(json.loads, (ROOT / g["sourceInventory"]["stringsPath"]).open())}
    by_source.update({r["stableId"]: r for r in
                      map(json.loads, (ROOT / g["sourceInventory"]["staticPath"]).open())})
    assert set(order) <= set(by_source)
    guid = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
            "UI": "0cbd8a7a4f543344bb95659de87f67a5",
            "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}
    before = {}
    after = {}
    changed_files = set(app["files"])
    for x in g["files"]:
        rel = x["path"]
        if not re.search(r"(?:dialogue|ui|checks)-batch-\d{3}\.json$", rel):
            continue
        current = ROOT / rel
        new = json.loads(current.read_text())
        old = json.loads((CYCLE / "before-authored" / current.name).read_text()) if rel in changed_files else new
        assert len(old["entries"]) == len(new["entries"])
        for b, c in zip(old["entries"], new["entries"]):
            assert b["id"] == c["id"]
            sid = f"string:{guid[new['collection']]}:{b['id']}"
            assert sid in order and sid not in before
            before[sid] = b["target"]
            after[sid] = c["target"]
    static = json.loads((HE / "static-text-draft.json").read_text())
    for x in static["entries"]:
        sid = x["stableId"]
        assert sid in order and sid not in before
        before[sid] = after[sid] = x["target"]
    assert set(before) == set(after) == set(order)
    changed = {sid for sid in order if before[sid] != after[sid]}
    assert changed == {x["stableId"] for x in a} and len(changed) == 120
    assert (CYCLE / "changed-ids.txt").read_bytes() == canonical_lines(changed, order)

    components = defaultdict(set)
    components["changed"].update(changed)
    affected_nodes = {node for x in a for node in by_source[x["stableId"]].get("nodeNames", [])}
    for sid in ordered_ids:
        if affected_nodes.intersection(by_source[sid].get("nodeNames", [])):
            components["scene-context"].add(sid)

    changed_sources = {x["source"] for x in a}
    changed_before = {x["before"] for x in a}
    changed_after = {x["after"] for x in a}
    for sid in ordered_ids:
        if (by_source[sid]["source"] in changed_sources or before[sid] in changed_before or
                after[sid] in changed_after):
            components["exact-repetitions-and-wording"].add(sid)

    # Source-side family selectors deliberately name concrete changed concepts and
    # bounded register patterns. They do not select every line by every speaker.
    lexical = re.compile(r"(?i)(?:КЧС|субъ|снегир|кинопрокат|волын|матер|АХАХ|"
                         r"ёб|ебан|заеб|съеб|доёб|охуе|хуй|хуйн|пизд|бля)")
    family_nodes = ("entrance_gasmask_15", "Couple_Asking_5", "talk_couple",
                    "talk_sirin", "talk_fortuneteller", "talk_provocateur")
    for sid in ordered_ids:
        row = by_source[sid]
        if lexical.search(row["source"]) or any(
                node.lower().startswith(prefix.lower()) for node in row.get("nodeNames", [])
                for prefix in family_nodes):
            components["glossary-referent-and-register"].add(sid)

    # All corrected non-speaker cells are complete localized Yarn display cells.
    # Branch siblings and command-bearing text stay in the scene component.
    for x in a:
        if not re.match(r"^[A-Za-z0-9]+: ", x["source"]):
            components["runtime-bindings"].add(x["stableId"])
    for sid in ordered_ids:
        row = by_source[sid]
        if row.get("collection") == "UI" and row["source"] in changed_sources:
            components["runtime-bindings"].add(sid)

    # Stable mandatory catalog: every UI, accepted static and ChecksDialogs
    # surface, plus all runtime placeholder/markup/exact-literal cells.
    for rule in accepted:
        sid = rule["stableId"]
        if (sid.startswith("tmp:") or rule.get("collection") in ("UI", "ChecksDialogs") or
                rule["formatSlots"] or rule["tmpTags"] or rule["wholeTextExact"]):
            components["mandatory-regressions"].add(sid)
    baseline_review = json.loads((CYCLE / "baseline-semantic-review-progress.json").read_text())
    for note in baseline_review["knownEditorialFollowups"]:
        for number in re.findall(r"\b\d{15,18}\b", note):
            for sid in order:
                if sid.endswith(":" + number):
                    components["mandatory-regressions"].add(sid)

    closure = set().union(*components.values())
    assert changed <= closure
    for name, ids in components.items():
        write_once(CYCLE / "components" / (name + "-ids.txt"), canonical_lines(ids, order))
    write_once(CYCLE / "closure-ids.txt", canonical_lines(closure, order))
    causes = {sid: sorted(name for name, ids in components.items() if sid in ids) for sid in closure}
    review_rows = []
    for sid in sorted(closure, key=order.__getitem__):
        row = by_source[sid]
        review_rows.append({"stableId": sid, "collection": row.get("collection", "StaticTMP"),
                            "source": row["source"], "before": before[sid], "after": after[sid],
                            "key": row.get("key"), "nodeNames": row.get("nodeNames", []),
                            "components": causes[sid]})
    write_once(CYCLE / "review-rows.jsonl", ("\n".join(
        json.dumps(x, ensure_ascii=False, separators=(",", ":")) for x in review_rows) + "\n").encode())
    component_stats = {}
    for name, ids in sorted(components.items()):
        path = CYCLE / "components" / (name + "-ids.txt")
        component_stats[name] = {"path": str(path.relative_to(ROOT)), "count": len(ids),
                                 "sha256": file_sha(path)}
    # Technical/consumer fragments are context, not added semantic units.
    runtime = {"schemaVersion": 1, "status": "context only; not additional translation IDs",
               "correctedCompleteYarnCells": 17,
               "speakerPrefixRule": "The 103 other corrected cells retain their pinned service/speaker prefixes exactly.",
               "unchangedParentheticalCue": "(מוציא את הרובה) in both corrected Couple choices",
               "mapBindings": {}}
    changed_source_set = {x["source"] for x in a}
    for name in ("action-label-map.json", "visitor-choice-map.json", "repeated-choices-map.json",
                 "repeated-ambient-map.json", "credits-replacements.json", "credits-role-map.json"):
        path = HE / name
        obj = json.loads(path.read_text())
        phrases = obj.get("phrases", obj.get("entries", obj.get("replacements", [])))
        affected = [x for x in phrases if x.get("source") in changed_source_set or
                    x.get("target") in changed_before]
        runtime["mapBindings"][name] = {"sha256": file_sha(path), "affectedPhrases": affected}
        assert not affected, name
    write_once(CYCLE / "runtime-context.json", (json.dumps(runtime, ensure_ascii=False, indent=2) + "\n").encode())
    summary = {"schemaVersion": 1, "status": "reproducible first correction closure; independent review pending",
               "algorithm": "union of changed IDs, exact Yarn scene nodes, exact source/old/new repetitions, bounded source-side concept/register/character branch selectors, corrected full display cells and mandatory regression catalog",
               "canonicalOrder": "preserve-exactly-v4 tableRows followed by staticRows; UTF-8, one stable ID per line, final LF",
               "sourceInventorySha256": file_sha(ROOT / g["sourceInventory"]["stringsPath"]),
               "staticInventorySha256": file_sha(ROOT / g["sourceInventory"]["staticPath"]),
               "preserveExactSha256": file_sha(ROOT / g["sourceInventory"]["preserveExactPath"]),
               "glossarySha256": file_sha(Path(g["glossary"]["path"])),
               "workflowSha256": file_sha(Path("/Users/antonkrutov/.codex/instructions/game-localization-audit-workflow.md")),
               "selectorScriptSha256": file_sha(Path(__file__)),
               "changedIds": {"path": str((CYCLE / "changed-ids.txt").relative_to(ROOT)),
                              "count": len(changed), "sha256": file_sha(CYCLE / "changed-ids.txt")},
               "closureIds": {"path": str((CYCLE / "closure-ids.txt").relative_to(ROOT)),
                              "count": len(closure), "sha256": file_sha(CYCLE / "closure-ids.txt")},
               "components": component_stats,
               "reviewRows": {"path": str((CYCLE / "review-rows.jsonl").relative_to(ROOT)),
                              "count": len(review_rows), "sha256": file_sha(CYCLE / "review-rows.jsonl")},
               "runtimeContext": {"path": str((CYCLE / "runtime-context.json").relative_to(ROOT)),
                                  "sha256": file_sha(CYCLE / "runtime-context.json")}}
    write_once(CYCLE / "closure-manifest.json", (json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode())
    print(json.dumps({"changed": len(changed), "closure": len(closure),
                      "components": {k: len(v) for k, v in components.items()},
                      "manifestSha256": file_sha(CYCLE / "closure-manifest.json")}))


if __name__ == "__main__":
    main()
