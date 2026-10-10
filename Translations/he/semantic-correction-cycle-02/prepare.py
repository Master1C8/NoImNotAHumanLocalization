#!/usr/bin/env python3
"""Pin, adjudicate and preflight the second Hebrew correction cycle.

Wording in OVERRIDES is authored editorial input. This recipe never generates
translations; it verifies exact source/reviewer links and protected syntax.
"""

import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CYCLE = Path(__file__).resolve().parent
HE = CYCLE.parent
IR = HE / "independent-review-01"
PRIOR = HE / "semantic-correction-cycle-01"
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import check_value

GUID = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
        "UI": "0cbd8a7a4f543344bb95659de87f67a5",
        "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}

# These are full-unit refinements after checking actual player/item variants.
OVERRIDES = {
    3: ("Tourist: {0} כאן. אני לא בטוח שנסתדר.",
        "Slot-first clause works with definite, feminine and plural character labels."),
    6: ("Bald: יש אצלך את {0}. אולי נצליח איכשהו לגרש את מי שכאן?",
        "Keep the Russian ejection action and object without assuming the occupant's gender."),
    9: ("Wolfhound: הבית שלך כבר חם בזכות {0}? אני רואה מיד שזאת זאבה בעור כבש.",
        "Retain the source's warm-hearth agency and fixed she-wolf metaphor without gendering the variable."),
    11: ("Wheelchair: לא מכניס אותי? מיד נסדר את זה! הנה {0}. לוקחים את זה, מנופפים בזה בכניסה ו—הופ!—אתה בלתי נראה.",
         "Natural object-neutral Hebrew for every actual deficit item label."),
    12: ("NotTrue: אוי ואבוי! {0} כבר אצלך בכורסה.",
         "Slot-first clause avoids agreement and the proposed definite-marker collision."),
    14: ("Luka: הייתי שמח להיכנס, אבל {0} שם עכשיו.",
         "Slot-first clause avoids יש plus a definite character label."),
    15: ("Fatman: לעזאזל, יש אצלך… {0}. תעיף מפה את מי שכאן, קיבינימט! אני לא מוכן ללכת מכות… בשביל אמבטיה.",
         "Keep the order to evict the occupant with a neutral object; proposed תעיף מפה was incomplete."),
    16: ("Buddy: אוֹה, אחי, אני רואה שכבר נעים וחם אצלך בזכות {0}.",
         "Keep the warm-place idiom and casual voice with neutral causation."),
    18: ("BigLebowski: שיט, לא. {0} כבר במקום המגניב שלך, בקיצור.",
         "Slot-first clause handles actual definite labels without יש plus definiteness."),
}

REASONS = {
    0: "Approved jerky-man glossary term; the existing UI name differs.",
    1: "Anonymous radio speaker and subject entity require neutral wording.",
    2: "Remove masculine speaker agreement while retaining the prior entity correction.",
    4: "The item can be feminine; אפשר clause preserves the suitability question.",
    5: "The occupying character may be feminine; first-person construction preserves shared-room meaning.",
    7: "Bald's ма и ба are mother and grandmother in the scene.",
    8: "The occupant may be female; לא לטעמי preserves his dislike.",
    10: "The occupant may be female; neutral location preserves the surprised meeting.",
    13: "The occupant may be female; nominal hiding phrase avoids agreement.",
    17: "Nun addresses the one male player; singular is required.",
    19: "FortuneTeller addresses the one male player; formal Russian Вы is singular in this exchange.",
    20: "Singular player address; retain prior complex-personality correction.",
    21: "Singular player address; retain the female speaker and astrological claim.",
    22: "Gasmask recruitment branch addresses the one male player.",
    23: "Same Gasmask recruitment branch; singular player return.",
    24: "Same Gasmask recruitment branch; singular imperative and beneficiary.",
    25: "Bald's mother and grandmother are both female; object pronoun must be feminine plural.",
    26: "Как-то is a past occasion here, not a claim that he somehow managed to return.",
    27: "Tough reports his need to go home while she stayed outside; subjectless Hebrew retains agency.",
    28: "The husband addresses the one male player in the armed confrontation.",
    29: "A coarse light-based oath has no literal light referent in this inspection scene.",
    30: "Same coarse interjection during the gun confrontation; no literal light referent.",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def once(path, data):
    if path.exists():
        assert path.read_bytes() == data, f"immutable evidence differs: {path}"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def encoded(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode()


def canonical(ids, order):
    return ("\n".join(sorted(ids, key=order.__getitem__)) + "\n").encode()


def main():
    progress_bytes = (HE / "progress.json").read_bytes()
    semantic_bytes = (HE / "semantic-review-progress.json").read_bytes()
    progress, semantic = json.loads(progress_bytes), json.loads(semantic_bytes)
    report = json.loads((IR / "final-review.json").read_text())
    findings = json.loads((IR / "final-findings.json").read_text())
    prior_manifest = json.loads((PRIOR / "closure-manifest.json").read_text())
    assert report["status"].startswith("complete independent")
    assert report["closureRowsTotal"] == 2111 and findings["findingCount"] == 31
    assert report["findings"]["sha256"] == sha(IR / "final-findings.json")
    assert report["closureManifestSha256"] == sha(PRIOR / "closure-manifest.json")
    assert report["reviewRowsSha256"] == sha(PRIOR / "review-rows.jsonl")
    assert sha(PRIOR / "closure-ids.txt") == prior_manifest["closureIds"]["sha256"]
    assert sha(IR / "complete-review-decisions.json") == report["decisions"]["sha256"]
    assert sha(IR / "all-reviewed-ids.txt") == report["reviewedIds"]["sha256"]
    assert (IR / "all-reviewed-ids.txt").read_bytes() == (PRIOR / "closure-ids.txt").read_bytes()
    assert semantic["acceptedUnits"] == semantic["reviewedUnits"] == 16538
    assert len(semantic["firstPassFindings"]) == 120
    assert progress["validation"]["semanticReviewProgressSha256"] == digest(semantic_bytes)
    assert semantic["postCorrection"]["handoffSha256"] == sha(PRIOR / "independent-review-handoff.json")
    assert all(sha(ROOT / r["path"]) == r["sha256"] for r in progress["files"])
    source_info = progress["sourceInventory"]
    for key, hkey in (("stringsPath", "stringsSha256"), ("staticPath", "staticSha256"),
                      ("preserveExactPath", "preserveExactSha256")):
        assert sha(ROOT / source_info[key]) == source_info[hkey]
    assert sha(Path(progress["glossary"]["path"])) == progress["glossary"]["sha256"]
    for key, hkey in (("stringsSha256", "sourceInventorySha256"),
                      ("staticSha256", "staticInventorySha256"),
                      ("preserveExactSha256", "preserveExactSha256")):
        assert source_info[key] == report[hkey]
    assert progress["glossary"]["sha256"] == report["glossarySha256"]
    for item in report["consumerContexts"]:
        assert sha(ROOT / item["path"]) == item["sha256"]
    # Independent decisions are matched to the immutable cycle-01 row sequence.
    decision_doc = json.loads((IR / "complete-review-decisions.json").read_text())
    print("decision structure:", decision_doc.keys())
    decisions = decision_doc.get("decisions", decision_doc.get("rows"))
    assert decisions is not None and len(decisions) == 2111
    review_rows = [json.loads(s) for s in (PRIOR / "review-rows.jsonl").read_text().splitlines()]
    assert len(review_rows) == len(decisions)
    for i, (r, d) in enumerate(zip(review_rows, decisions)):
        assert d["stableId"] == r["stableId"] and d["closureOrdinalZeroBased"] == i
    once(CYCLE / "baseline-progress.json", progress_bytes)
    once(CYCLE / "baseline-semantic-review-progress.json", semantic_bytes)
    pinned = {"schemaVersion": 1, "status": "reconciled before cycle-02 edits",
              "gameVersion": "1.3.19", "sourceLocale": "ru", "locale": "he",
              "acceptedUnits": 16538, "firstSemanticPassReviewedUnits": 16538,
              "sourceInventory": {k: source_info[k] for k in ("stringsPath", "stringsSha256", "staticPath", "staticSha256", "preserveExactPath", "preserveExactSha256")},
              "glossary": progress["glossary"],
              "priorClosureManifestSha256": sha(PRIOR / "closure-manifest.json"),
              "priorClosureIdsSha256": sha(PRIOR / "closure-ids.txt"),
              "priorReviewRowsSha256": sha(PRIOR / "review-rows.jsonl"),
              "independentFinalReviewSha256": sha(IR / "final-review.json"),
              "independentFinalFindingsSha256": sha(IR / "final-findings.json"),
              "independentDecisionsSha256": sha(IR / "complete-review-decisions.json"),
              "priorProgressSha256": digest(progress_bytes),
              "priorSemanticProgressSha256": digest(semantic_bytes)}
    once(CYCLE / "input-pins.json", encoded(pinned))

    rules = json.loads((ROOT / source_info["preserveExactPath"]).read_text())
    accepted = rules["tableRows"] + rules["staticRows"]
    order = {r["stableId"]: i for i, r in enumerate(accepted)}
    by_rule = {r["stableId"]: r for r in accepted}
    assert len(order) == 16538
    source = {r["stableId"]: r for r in map(json.loads, (ROOT / source_info["stringsPath"]).open())}
    source.update({r["stableId"]: r for r in map(json.loads, (ROOT / source_info["staticPath"]).open())})
    assert set(order) <= set(source)
    prior_review = {r["stableId"]: r for r in review_rows}
    changes = defaultdict(dict)
    adjudications = []
    for index, f in enumerate(findings["findings"]):
        sid = f["stableId"]
        assert sid in order and sid in prior_review
        assert f["closureOrdinalZeroBased"] == (PRIOR / "closure-ids.txt").read_text().splitlines().index(sid)
        assert source[sid]["source"] == f["source"] == prior_review[sid]["source"]
        assert prior_review[sid]["after"] == f["currentTarget"]
        assert digest(f["source"].encode()) == f["sourceValueSha256"]
        assert digest(f["currentTarget"].encode()) == f["currentTargetValueSha256"]
        assert digest(f["proposedFullTarget"].encode()) == f["proposedTargetValueSha256"]
        path = ROOT / f["path"]
        assert sha(path) == f["authoredFileSha256"]
        batch = json.loads(path.read_text())
        row = batch["entries"][f["offset"]]
        assert row == {"id": int(sid.rsplit(":", 1)[-1]), "target": f["currentTarget"]}
        assert sid == f"string:{GUID[batch['collection']]}:{row['id']}"
        if index in OVERRIDES:
            target, note = OVERRIDES[index]
        else:
            target, note = f["proposedFullTarget"], REASONS[index]
        assert target != f["currentTarget"]
        check_value(by_rule[sid], target)
        assert row["id"] not in changes[f["path"]]
        changes[f["path"]][row["id"]] = target
        adjudications.append({"findingIndex": index, "findingId": f["findingId"],
            "findingRecordSha256": digest(json.dumps(f, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()),
            "stableId": sid, "path": f["path"], "offset": f["offset"], "source": f["source"],
            "before": f["currentTarget"], "reviewerProposal": f["proposedFullTarget"],
            "after": target, "decision": "accepted with full-unit wording adjudicated",
            "reason": note, "nodeNames": source[sid].get("nodeNames", [])})
    assert len(adjudications) == len({r["stableId"] for r in adjudications}) == 31
    assert len(changes) == len({r["path"] for r in adjudications})
    # Keep untouched JSON bytes identical and replace only the pinned target values.
    rendered = {}
    entry_re = re.compile(r'"id"\s*:\s*(\d+)\s*,\s*"target"\s*:\s*')
    for rel, replacements in changes.items():
        path = ROOT / rel
        before = path.read_bytes()
        content = before.decode()
        seen, spans = set(), []
        for m in entry_re.finditer(content):
            identifier = int(m.group(1))
            if identifier in replacements:
                assert identifier not in seen
                seen.add(identifier)
                old, n = json.JSONDecoder().raw_decode(content[m.end():])
                assert isinstance(old, str)
                spans.append((m.end(), m.end() + n, json.dumps(replacements[identifier], ensure_ascii=False)))
        assert seen == set(replacements)
        for start, end, new in sorted(spans, reverse=True):
            content = content[:start] + new + content[end:]
        after = content.encode()
        old_obj, new_obj = json.loads(before), json.loads(after)
        assert old_obj.keys() == new_obj.keys()
        assert len(old_obj["entries"]) == len(new_obj["entries"])
        for old, new in zip(old_obj["entries"], new_obj["entries"]):
            assert old["id"] == new["id"]
            assert new["target"] == replacements.get(old["id"], old["target"])
        once(CYCLE / "before-authored" / path.name, before)
        once(CYCLE / "after-authored" / path.name, after)
        rendered[rel] = {"beforeSha256": digest(before), "afterSha256": digest(after),
                         "changedIds": sorted(replacements), "authoredRows": len(new_obj["entries"])}
    # Assemble every accepted target from staged changed batches and unchanged files.
    targets = {}
    for row in progress["files"]:
        rel = row["path"]
        if re.search(r"(?:dialogue|ui|checks)-batch-\d{3}\.json$", rel):
            path = CYCLE / "after-authored" / Path(rel).name if rel in rendered else ROOT / rel
            batch = json.loads(path.read_text())
            assert batch["locale"] == "he"
            for entry in batch["entries"]:
                sid = f"string:{GUID[batch['collection']]}:{entry['id']}"
                assert sid in order and sid not in targets
                targets[sid] = entry["target"]
    for entry in json.loads((HE / "static-text-draft.json").read_text())["entries"]:
        sid = entry["stableId"]
        assert sid in order and sid not in targets
        targets[sid] = entry["target"]
    assert set(targets) == set(order)
    for sid, target in targets.items():
        check_value(by_rule[sid], target)
    changed_ids = {r["stableId"] for r in adjudications}
    once(CYCLE / "changed-ids.txt", canonical(changed_ids, order))
    once(CYCLE / "adjudications.json", encoded({"schemaVersion": 1,
        "status": "31 objective findings accepted with full-unit wording; preflight passed; application pending",
        "inputPinsSha256": sha(CYCLE / "input-pins.json"), "findingCount": 31,
        "records": adjudications}))
    once(CYCLE / "preflight.json", encoded({"schemaVersion": 1,
        "status": "passed before authored application", "acceptedUnits": 16538,
        "acceptedFindings": 31, "changedAuthoredFiles": len(rendered),
        "sourceTargetLinks": "31 exact findings, previous review rows and authored offsets verified",
        "protectedRuntimeSyntax": "preserve_exact.check_value passed for every staged target in full corpus",
        "files": rendered, "inputPinsSha256": sha(CYCLE / "input-pins.json"),
        "changedIdsSha256": sha(CYCLE / "changed-ids.txt"),
        "adjudicationsSha256": sha(CYCLE / "adjudications.json")}))
    print(json.dumps({"result": "preflight-passed", "units": len(targets),
                      "findings": len(adjudications), "changedFiles": len(rendered),
                      "preflightSha256": sha(CYCLE / "preflight.json")}))


if __name__ == "__main__":
    main()
