#!/usr/bin/env python3
"""Reproduce Filipino cycle 003 structural, exact and derived-input checks."""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CYCLE = Path(__file__).resolve().parent
FIL = ROOT / "Translations/fil"
sys.path.insert(0, str(ROOT / "Scripts"))
from locale_text_inputs import current_text  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    require(args.write != args.verify, "Choose write or verify")
    plan_path = CYCLE / "plan.json"
    plan = json.loads(plan_path.read_text())
    for item in plan["sourceAndGlossaryFingerprints"].values():
        require(sha(ROOT / item["path"]) == item["sha256"], "Source/glossary pin changed")
    require(sha(ROOT / "Source/preserve-exactly-v4.json") == plan["preserveExactManifestSha256"],
            "Preserve-exact contract changed")
    values, files = current_text("fil", require_sidecars=True)
    require(len(values) == 16538 and len(files) == 456, "Accepted set or authored file count differs")
    G = {"UI": "0cbd8a7a4f543344bb95659de87f67a5",
         "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6",
         "Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1"}
    target = {}
    for p in sorted(FIL.glob("*batch-*.json")):
        if re.fullmatch(r"(?:ui|checks|dialogue)-batch-\d{3}\.json", p.name):
            d = json.loads(p.read_text())
            for e in d["entries"]:
                target[f"string:{G[d['collection']]}:{e['id']}"] = e["target"]
    static = json.loads((FIL / "static-text-draft.json").read_text())
    target.update({e["stableId"]: e["target"] for e in static["entries"]})
    require(len(target) == 16538, "Target stable IDs differ")
    source = {r["stableId"]: r for r in
              (json.loads(line) for line in
               (ROOT / "Source/localization-inventory-v3/strings.jsonl").open())
              if r["stableId"] in target}
    source.update({r["stableId"]: r for r in
                   (json.loads(line) for line in
                    (ROOT / "Source/localization-inventory-v3/static-text.jsonl").open())
                   if r["stableId"] in target})
    require(set(source) == set(target), "Source mapping differs")
    option_recipe = FIL / "common-options-001.authored.json"
    options = json.loads(option_recipe.read_text())["phrases"]
    option_count = 0
    independent_extra = []
    for phrase in options:
        ids = [sid for sid in target if sid.startswith("string:") and
               source[sid]["source"] == phrase["source"]]
        require(all(target[sid] == phrase["target"] for sid in ids),
                "Option expansion differs: " + phrase["source"])
        if len(ids) != phrase["expectedRows"]:
            require(phrase["source"] == "Нет" and len(ids) == phrase["expectedRows"] + 1,
                    "Option occurrence count differs")
            independent_extra = [sid for sid in ids]
        option_count += len(ids)
    require(option_count == 2675 and len(independent_extra) == 19,
            "Option exact-source count differs")
    static_recipe = FIL / "static-phrases.authored.json"
    phrases = {r["source"]: r["target"] for r in json.loads(static_recipe.read_text())["phrases"]}
    require(len(phrases) == 75, "Static phrase recipe changed")
    static_rows = [sid for sid in target if sid.startswith("tmp:") and
                   sid != "tmp:level5:59:m_text"]
    require(len(static_rows) == 177 and all(source[sid]["source"] in phrases and
            target[sid] == phrases[source[sid]["source"]] for sid in static_rows),
            "Static phrase expansion differs")
    credits = json.loads((FIL / "credits-role-map.json").read_text())
    replacements = {r["source"]: r["target"] for r in credits["replacements"]}
    original = source["tmp:level5:59:m_text"]["source"]
    pattern = re.compile("|".join(re.escape(s) for s in sorted(replacements, key=len, reverse=True)))
    require(pattern.sub(lambda m: replacements[m.group()], original) ==
            target["tmp:level5:59:m_text"], "Credits derivation differs")
    before = {row["authoredPath"]: row for row in plan["beforeAuthoredFiles"]}
    changed = []
    for row in files:
        path = row["path"]
        if path not in before:
            continue
        prev = json.loads((ROOT / before[path]["snapshotPath"]).read_text())
        curr = json.loads((ROOT / path).read_text())
        require({k: v for k, v in prev.items() if k != "entries"} ==
                {k: v for k, v in curr.items() if k != "entries"},
                "Authored metadata differs")
        require(len(prev["entries"]) == len(curr["entries"]), "Entry count differs")
        for old, new in zip(prev["entries"], curr["entries"]):
            require({k: v for k, v in old.items() if k != "target"} ==
                    {k: v for k, v in new.items() if k != "target"},
                    "Authored non-target field differs")
            if old["target"] != new["target"]:
                changed.append((path, new["id"], old["target"], new["target"]))
    expected = {(row["authoredPath"], int(row["stableId"].rsplit(":", 1)[1]),
                 row["currentTarget"], row["acceptedFullTarget"]) for row in plan["rows"]}
    require(set(changed) == expected and len(changed) == 2,
            "Applied target diff differs from full-unit plan")
    prior = json.loads((FIL / "semantic-correction-cycle-002/full-structural-validation.json").read_text())
    prior_files = {r["path"]: r for r in prior["batchReports"]}
    for row in files:
        if row["path"] not in prior_files or row["path"] in before:
            continue
        require(prior_files[row["path"]]["sha256"] == row["sha256"],
                "Unaffected authored batch changed")
        sidecar = ROOT / prior_files[row["path"]]["sidecarPath"]
        require(sha(sidecar) == prior_files[row["path"]]["sidecarSha256"],
                "Unaffected batch receipt changed")
    output = {"schemaVersion": 1, "locale": "fil",
              "status": "full accepted structural and preserve-exact gate passed; semantics and runtime pending",
              "planSha256": sha(plan_path), "acceptedIds": 16538, "checkedIds": len(target),
              "missingIds": 0, "extraIds": 0, "duplicateIds": 0,
              "authoredInputs": len(files), "batches": len(files)-1,
              "allBatchSidecarsCurrent": True,
              "changedTargets": len(changed), "unexpectedFieldOrEntryChanges": 0,
              "optionRecipeSha256": sha(option_recipe), "optionExactSourceRows": option_count,
              "optionOwnedRows": sum(r["expectedRows"] for r in options),
              "independentNoRowCount": 1,
              "staticPhraseRecipeSha256": sha(static_recipe),
              "staticPhraseRows": len(static_rows),
              "creditsRoleMapSha256": sha(FIL / "credits-role-map.json"),
              "creditsRegeneratedExact": True,
              "staticDraftSha256": sha(FIL / "static-text-draft.json"),
              "preserveExactManifestSha256": plan["preserveExactManifestSha256"],
              "sourceAndGlossaryFingerprints": plan["sourceAndGlossaryFingerprints"],
              "batchReports": [{"path": r["path"], "sha256": r["sha256"],
                                "sidecarPath": str((ROOT / r["path"]).with_suffix(".validation.json").relative_to(ROOT)),
                                "sidecarSha256": sha((ROOT / r["path"]).with_suffix(".validation.json"))}
                               for r in files if r["path"].endswith(".json") and "batch-" in r["path"]]}
    raw = (json.dumps(output, ensure_ascii=False, indent=2) + "\n").encode()
    out = CYCLE / "full-structural-validation.json"
    if args.write:
        require(not out.exists(), "Immutable cycle gate exists")
        out.write_bytes(raw)
    else:
        require(out.read_bytes() == raw, "Cycle gate bytes differ")
    print(json.dumps({"gateSha256": sha(out), "checkedIds": 16538,
                      "batches": len(files)-1, "changedTargets": 2,
                      "options": option_count, "staticPhrases": len(static_rows)}))


if __name__ == "__main__":
    main()
