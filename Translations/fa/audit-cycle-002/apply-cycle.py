#!/usr/bin/env python3
"""Apply the preflighted Persian cycle-2 full-unit correction batch."""

import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[3]
CYCLE = pathlib.Path(__file__).resolve().parent
FA = ROOT / "Translations/fa"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encode(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode()


def replace_target(raw, sid, before, after):
    if sid.startswith("tmp:"):
        lead = r'"stableId":\s*' + re.escape(json.dumps(sid, ensure_ascii=False))
    else:
        lead = r'"id":\s*' + re.escape(sid.rsplit(":", 1)[1])
    pattern = re.compile(r'(' + lead + r'\s*,\s*"target":\s*)(' +
                         re.escape(json.dumps(before, ensure_ascii=False)) + r')')
    text = raw.decode()
    assert len(pattern.findall(text)) == 1, (sid, "ambiguous or changed prior value")
    return pattern.sub(lambda match: match.group(1) + json.dumps(after, ensure_ascii=False),
                       text, count=1).encode()


def main():
    plan_path = CYCLE / "correction-plan.json"
    plan = json.loads(plan_path.read_text())["rows"]
    preflight = json.loads((CYCLE / "preflight.json").read_text())
    assert sha(plan_path.read_bytes()) == preflight["correctionPlanSha256"]
    before_hashes = preflight["beforeFileHashes"]
    desired = {}
    for path_name, pin in before_hashes.items():
        path = ROOT / path_name
        before = (CYCLE / "before" / path.name).read_bytes()
        assert sha(before) == pin and path.read_bytes() == before, path_name
        desired[path_name] = before
    for item in plan:
        if item["stableId"].startswith("tmp:"):
            continue
        path_name = item["path"]
        desired[path_name] = replace_target(desired[path_name], item["stableId"],
                                            item["before"], item["acceptedTarget"])
    # The phrase map is the recipe. Recompute every mapped static draft target from it.
    map_name = "Translations/fa/static-phrase-map.json"
    phrase_map = json.loads(desired[map_name])
    static_changes = [item for item in plan if item["stableId"].startswith("tmp:")]
    assert len(static_changes) == 2
    source = {}
    for line in (ROOT / "Source/localization-inventory-v3/static-text.jsonl").open():
        row = json.loads(line)
        source[row["stableId"]] = row["source"]
    for item in static_changes:
        phrase = source[item["stableId"]]
        matches = [row for row in phrase_map["phrases"] if row["source"] == phrase]
        assert len(matches) == 1 and matches[0]["target"] == item["before"]
        matches[0]["target"] = item["acceptedTarget"]
    desired[map_name] = encode(phrase_map)
    draft_name = "Translations/fa/static-text-draft.json"
    draft = json.loads(desired[draft_name])
    prior = {row["stableId"]: row["target"] for row in draft["entries"]}
    mapping = {row["source"]: row["target"] for row in phrase_map["phrases"]}
    assert len(mapping) == len(phrase_map["phrases"])
    updated = []
    for entry in draft["entries"]:
        sid = entry["stableId"]
        if source[sid] not in mapping:
            continue
        next_target = mapping[source[sid]]
        if next_target != prior[sid]:
            assert any(item["stableId"] == sid and item["acceptedTarget"] == next_target
                       for item in static_changes), sid
            updated.append(sid)
        entry["target"] = next_target
    assert set(updated) == {item["stableId"] for item in static_changes}
    desired[draft_name] = encode(draft)
    # Keep an immutable, reviewable after image before mutating authored inputs.
    files = []
    for path_name in sorted(desired):
        before = (CYCLE / "before" / pathlib.Path(path_name).name).read_bytes()
        after = desired[path_name]
        assert before != after
        snapshot = CYCLE / "after" / pathlib.Path(path_name).name
        snapshot.parent.mkdir(exist_ok=True)
        if snapshot.exists():
            assert snapshot.read_bytes() == after
        else:
            snapshot.write_bytes(after)
        files.append({"path": path_name, "beforeSha256": sha(before),
                      "afterSha256": sha(after)})
    # Each file replacement is atomic; the group has no cross-file transaction.
    for path_name in sorted(desired):
        path = ROOT / path_name
        temporary = path.with_name(path.name + ".cycle2-tmp")
        assert not temporary.exists()
        temporary.write_bytes(desired[path_name])
        temporary.replace(path)
    assert all(sha((ROOT / item["path"]).read_bytes()) == item["afterSha256"]
               for item in files)
    result = {"schemaVersion": 1, "locale": "fa", "cycle": 2,
              "correctionPlanSha256": sha(plan_path.read_bytes()),
              "correctionIds": [item["stableId"] for item in plan],
              "files": files,
              "boundary": "five per-file atomic replacements; no cross-file transaction",
              "staticRecipe": "all 177 accepted phrase-map matches regenerated; exactly two changed"}
    manifest = CYCLE / "file-delta-manifest.json"
    data = encode(result)
    if manifest.exists():
        assert manifest.read_bytes() == data
    else:
        manifest.write_bytes(data)
    print(json.dumps({"correctionUnits": len(plan), "changedFiles": len(files),
                      "staticRowsChanged": len(updated)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
