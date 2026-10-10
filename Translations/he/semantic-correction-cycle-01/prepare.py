#!/usr/bin/env python3
"""Pin and preflight the first Hebrew semantic correction cycle.

The wording below is authored editorial input. This script only applies it to
the pinned records and verifies structure; it does not translate text.
"""

import hashlib
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CYCLE = Path(__file__).resolve().parent
HE = CYCLE.parent
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import check_value  # noqa: E402


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


# These refinements replace proposed wording only after scene and consumer review.
OVERRIDES = {
    20: ("Wheelchair: רואה איך העין קופצת? ההרגל נשאר.",
         "Name the twitching eye shown by the Eyes consumer; מרצד would mean flicker."),
    31: ("Raskolnikov: פעם הייתי מהדק את אגרופיי עד שפרקי האצבעות היו מלבינים, במיוחד כשהייתי עצבני. חשבתי שאם אלמד לשלוט בגוף, גם הפחד ייסוג.",
         "מהדק את אגרופיי expresses clenching fists without the awkward מאגרף את ידיי."),
    40: ("Ballerina: חה חה חה חה חה.", "Use unambiguous written laughter."),
    42: ("Ballerina: חה חה חה חה, קדימה, תתקוף!", "Use unambiguous written laughter."),
    43: ("Ballerina: חה חה חה חה חה! קדימה, תסתכל. תריח. מה עוד אתה עושה?",
         "Use unambiguous written laughter."),
    65: ("Experienced: פראייר, למה לעזאזל שלפת את הנשק? תוריד אותו.",
         "Волына is a firearm; generic נשק avoids inventing an exact gun type."),
    66: ("Experienced: השיניים שלי הרי צהובות, אז למה שלפת נשק?",
         "The same firearm slang remains generic in the second branch."),
}


def main():
    semantic_path = HE / "semantic-review-progress.json"
    progress_path = HE / "progress.json"
    baseline = semantic_path.read_bytes()
    progress_baseline = progress_path.read_bytes()
    s = json.loads(baseline)
    g = json.loads(progress_baseline)
    assert s["acceptedUnits"] == s["reviewedUnits"] == 16538
    assert len(s["firstPassFindings"]) == 120
    assert file_sha(semantic_path) == g["validation"]["semanticReviewProgressSha256"]
    assert sum(x["units"] for x in s["reviewedFiles"]) == 16538
    assert all(file_sha(ROOT / x["path"]) == x["sha256"] for x in s["reviewedFiles"])
    assert all(file_sha(ROOT / x["path"]) == x["sha256"] for x in g["files"])
    for key, field in (("stringsPath", "stringsSha256"),
                       ("staticPath", "staticSha256"),
                       ("preserveExactPath", "preserveExactSha256")):
        assert file_sha(ROOT / g["sourceInventory"][key]) == g["sourceInventory"][field]
    assert file_sha(Path(g["glossary"]["path"])) == g["glossary"]["sha256"]
    write_once(CYCLE / "baseline-semantic-review-progress.json", baseline)
    write_once(CYCLE / "baseline-progress.json", progress_baseline)

    source = {}
    source_order = {}
    for row in map(json.loads, (ROOT / g["sourceInventory"]["stringsPath"]).open()):
        if row["collection"] in ("Dialogs", "UI", "ChecksDialogs"):
            sid = row["stableId"]
            assert sid not in source
            source_order[sid] = len(source)
            source[sid] = row
    rules = json.loads((ROOT / g["sourceInventory"]["preserveExactPath"]).read_text())
    by_rule = {r["stableId"]: r for r in rules["tableRows"] + rules["staticRows"]}
    assert len(by_rule) == 16538
    guid = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
            "UI": "0cbd8a7a4f543344bb95659de87f67a5",
            "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}
    changes = defaultdict(dict)
    adjudications = []
    for index, f in enumerate(s["firstPassFindings"]):
        path = ROOT / f["path"]
        batch = json.loads(path.read_text())
        row = batch["entries"][f["offset"]]
        sid = f"string:{guid[batch['collection']]}:{f['id']}"
        assert row == {"id": f["id"], "target": f["currentTarget"]}
        assert source[sid]["source"] == f["source"]
        assert f["status"] == "proposed for one complete first-pass correction batch; target unchanged"
        assert f["id"] not in changes[f["path"]]
        target, note = OVERRIDES.get(index, (f["proposedTarget"],
                                      "Accepted: the recorded objective issue is supported by the pinned source and scene."))
        assert target != f["currentTarget"]
        check_value(by_rule[sid], target)
        changes[f["path"]][f["id"]] = target
        adjudications.append({
            "findingIndex": index,
            "findingRecordSha256": sha(json.dumps(f, ensure_ascii=False, sort_keys=True,
                                                  separators=(",", ":")).encode()),
            "stableId": sid, "path": f["path"], "offset": f["offset"],
            "source": f["source"], "before": f["currentTarget"],
            "originalProposal": f["proposedTarget"], "after": target,
            "decision": "accepted", "adjudication": note,
            "nodeNames": source[sid]["nodeNames"],
        })
    assert len(adjudications) == 120 and len({x["stableId"] for x in adjudications}) == 120

    # Preserve the authored file layout, including batches with multi-line entries.
    rendered = {}
    entry_re = re.compile(r'"id"\s*:\s*(\d+)\s*,\s*"target"\s*:\s*')
    for rel, replacements in changes.items():
        path = ROOT / rel
        before = path.read_bytes()
        content = before.decode()
        seen = set()
        spans = []
        for match in entry_re.finditer(content):
            identifier = int(match.group(1))
            if identifier not in replacements:
                continue
            assert identifier not in seen
            seen.add(identifier)
            old_value, end = json.JSONDecoder().raw_decode(content[match.end():])
            assert isinstance(old_value, str)
            spans.append((match.end(), match.end() + end,
                          json.dumps(replacements[identifier], ensure_ascii=False)))
        assert seen == set(replacements)
        for start, end, replacement in sorted(spans, reverse=True):
            content = content[:start] + replacement + content[end:]
        after = content.encode()
        old_obj = json.loads(before)
        new_obj = json.loads(after)
        assert old_obj.keys() == new_obj.keys()
        assert len(old_obj["entries"]) == len(new_obj["entries"])
        for old, new in zip(old_obj["entries"], new_obj["entries"]):
            assert old["id"] == new["id"]
            assert new["target"] == replacements.get(old["id"], old["target"])
        write_once(CYCLE / "before-authored" / path.name, before)
        write_once(CYCLE / "after-authored" / path.name, after)
        rendered[rel] = {"beforeSha256": sha(before), "afterSha256": sha(after),
                         "changedIds": list(replacements), "authoredRows": len(new_obj["entries"])}

    # Preflight the assembled 16,538-unit candidate, including all unchanged rows.
    targets = {}
    for rel in sorted(x["path"] for x in g["files"] if re.search(r"(?:dialogue|ui|checks)-batch-\d{3}\.json$", x["path"])):
        batch = json.loads(rendered[rel] and (CYCLE / "after-authored" / Path(rel).name).read_bytes()
                           if rel in rendered else (ROOT / rel).read_bytes())
        assert batch["locale"] == "he" and batch["sourceInventorySha256"] == s["sourceInventorySha256"]
        positions = []
        for entry in batch["entries"]:
            sid = f"string:{guid[batch['collection']]}:{entry['id']}"
            assert sid in source and sid not in targets
            targets[sid] = entry["target"]
            positions.append(source_order[sid])
        assert positions == sorted(positions)
    static = json.loads((HE / "static-text-draft.json").read_text())
    for entry in static["entries"]:
        sid = entry["stableId"]
        assert sid in by_rule and sid not in targets
        targets[sid] = entry["target"]
    assert len(targets) == len(by_rule) == 16538
    assert set(targets) == set(by_rule)
    for sid, target in targets.items():
        check_value(by_rule[sid], target)

    changed = sorted((x["stableId"] for x in adjudications), key=source_order.__getitem__)
    assert len(changed) == 120
    write_once(CYCLE / "changed-ids.txt", ("\n".join(changed) + "\n").encode())
    write_once(CYCLE / "adjudications.json", (json.dumps({
        "schemaVersion": 1, "status": "accepted and preflighted; application pending",
        "sourceInventorySha256": s["sourceInventorySha256"],
        "glossarySha256": s["glossarySha256"],
        "preserveExactSha256": s["preserveExactSha256"],
        "baselineSemanticReviewSha256": sha(baseline), "findingCount": len(adjudications),
        "records": adjudications}, ensure_ascii=False, indent=2) + "\n").encode())
    write_once(CYCLE / "preflight.json", (json.dumps({
        "schemaVersion": 1, "status": "passed before authored application",
        "acceptedUnits": len(targets), "acceptedFindings": len(adjudications),
        "changedAuthoredFiles": len(rendered), "files": rendered,
        "protectedRuntimeSyntax": "preserve_exact.check_value passed for every candidate unit",
        "sourceTargetLinks": "120/120 exact source and before-target links verified",
        "stableIdsAndOrder": "complete unique accepted inventory; every batch remains in canonical source order",
        "newlineConvention": "one stable ID per line, UTF-8, final LF",
        "changedIdsSha256": file_sha(CYCLE / "changed-ids.txt"),
        "adjudicationsSha256": file_sha(CYCLE / "adjudications.json"),
    }, ensure_ascii=False, indent=2) + "\n").encode())
    print(json.dumps({"result": "preflight-passed", "units": len(targets),
                      "findings": len(adjudications), "changedFiles": len(rendered),
                      "preflightSha256": file_sha(CYCLE / "preflight.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
