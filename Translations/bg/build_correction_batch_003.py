#!/usr/bin/env python3
"""Preflight the single review-02 Bulgarian correction batch against cycle 002."""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BG = ROOT / "Translations/bg"
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import check_value  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


# A full line is selected only after reading its Russian source, current Bulgarian,
# compiled scene/branch and the bounded referent and voice dependencies.
REVISED = {
    3: "Anger: Или да спукам някого от бой.",
    9: "Fugitive: Щом видях тия лайна, веднага разбрах каква е работата и реших — трябва да се омитам.",
    11: "Anger: Те просто седят и чакат да ги спукат от бой, да им изтръгнат зъбите или да им направят нещо друго.",
    12: "Я се омитай, докато е с добро",
    13: "Я се омитай, докато е с добро",
    23: "Rocker: За какъв чеп изобщо да се старая и да се бъхтя повече?..",
    24: "Rocker: Сега с тези Гости и палещото слънце е същото — просто нов кръг от шибания кошмар, а аз вече съм свикнал с него.",
    25: "Unstable: Все пак благодаря. Отдъхнах си и мога пак да се бъхтя по пътя два дни без почивка.",
    28: "Esenin: Моля те, разкарай се, мамка му. Не ми е добре.",
    33: "Bald: На лекар, разбира се, няма да отида, защото, както се казва: „Дребната шибана простотия минава, а голямата шибана беда не се лекува“.",
    36: "Rocker: Правих си тунели в ушите. После… мамка му, просто ми писна.",
}
DISMISSED = {
    10: "The existing idiomatic 'спукам някого от бой' already conveys a coarse beating; a trailing generic oath weakens this terse line.",
    14: "'Писна до гуша' is a strong, natural idiom in this choice; inserting a generic oath disrupts the question without a semantic gain.",
    29: "'Да се омете' carries the vulgar source's abrupt abandonment in this reflective confession; the added oath intrudes on the scene's tone.",
}
EXTRA = {
    "string:444ff14f1967f5a4c8eb9e4cf4c913f1:110504455680630785": (
        "Unstable: Абе, хич не знам какво се опитвам да кажа, мамка му.",
        "The six newly selected voice rows include one neutralized 'хз'; restore Unstable's coarse, disoriented register."),
}


def main():
    findings_path = BG / "independent-review-02/findings.json"
    review_path = BG / "independent-review-02/review.json"
    final_path = BG / "independent-review-02/final-verification.json"
    selector_finding = BG / "independent-review-02/selector-findings.json"
    selector = BG / "voice-risk-selector-v5.json"
    candidates = BG / "voice-remedial-candidates-v5.json"
    baseline_path = BG / "correction-batch-002-result.json"
    inputs = [findings_path, review_path, final_path, selector_finding, selector,
              candidates, baseline_path, BG / "semantic-closure-cycle-002.json",
              BG / "semantic-delta-cycle-002.json"]
    baseline = load(baseline_path)
    assert baseline["changedIdCount"] == 147
    for record in baseline["allAuthoredFiles"]:
        assert sha(ROOT / record["path"]) == record["sha256"], record["path"]
    for relpath, expected in load(selector)["pinnedInputs"].items():
        assert sha(ROOT / relpath) == expected, relpath
    assert load(candidates)["selectorSha256"] == sha(selector)
    assert load(final_path).get("status") != "clean"
    targets = {}
    for record in baseline["allAuthoredFiles"]:
        for row in load(ROOT / record["path"])["entries"]:
            sid = row.get("stableId")
            if sid is None:
                guid = {"UI": "0cbd8a7a4f543344bb95659de87f67a5",
                        "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6",
                        "Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1"}[record["collection"]]
                sid = f"string:{guid}:{row['id']}"
            assert sid not in targets
            targets[sid] = (row["target"], record["path"], record["collection"])
    assert len(targets) == 16538
    sources = {}
    for path in (ROOT / "Source/localization-inventory-v3/strings.jsonl",
                 ROOT / "Source/localization-inventory-v3/static-text.jsonl"):
        for line in path.open():
            row = json.loads(line)
            if row["stableId"] in targets:
                sources[row["stableId"]] = row["source"]
    rules = load(ROOT / "Source/preserve-exactly-v4.json")
    exact = {r["stableId"]: r for r in rules["tableRows"] + rules["staticRows"]}
    assert len(sources) == len(exact) == len(targets)

    adjudications = []
    decisions = []
    findings = load(findings_path)["findings"]
    assert len(findings) == 43
    for index, finding in enumerate(findings, 1):
        sid = finding["stableId"]
        current, path, collection = targets[sid]
        assert finding["source"] == sources[sid] and finding["currentFullTarget"] == current
        assert finding["authoredPath"] == path
        final = current if index in DISMISSED else REVISED.get(index, finding["proposedFullTarget"])
        disposition = "dismissed" if index in DISMISSED else ("revised" if index in REVISED else "accepted")
        reason = DISMISSED.get(index, "Full Russian unit, Bulgarian target, compiled scene and bounded dependencies support this repair.")
        if index in REVISED:
            reason = "Reviewer issue accepted; full-unit wording revised to preserve natural Bulgarian, the source facts and scene register."
        row = {"findingId": finding["findingId"], "stableId": sid, "source": sources[sid],
               "currentFullTarget": current, "reviewerProposedFullTarget": finding["proposedFullTarget"],
               "disposition": disposition, "acceptedFullTarget": final if final != current else None,
               "reason": reason, "sceneNodes": finding["sceneNodes"], "batchPath": path}
        adjudications.append(row)
        if final != current:
            check_value(exact[sid], final)
            decisions.append({"stableId": sid, "collection": collection, "batchPath": path,
                              "source": sources[sid], "currentFullTarget": current,
                              "acceptedFullTarget": final, "basis": finding["findingId"]})
    voice_ids = {x["stableId"] for x in load(candidates)["candidates"]}
    for sid, (final, reason) in EXTRA.items():
        assert sid in voice_ids and sid not in {x["stableId"] for x in decisions}
        current, path, collection = targets[sid]
        check_value(exact[sid], final)
        adjudications.append({"findingId": "bg-selector-02-extra-001", "stableId": sid,
                              "source": sources[sid], "currentFullTarget": current,
                              "reviewerProposedFullTarget": None, "disposition": "additional bounded correction",
                              "acceptedFullTarget": final, "reason": reason,
                              "sceneNodes": ["Unstable_Entrance_2"], "batchPath": path})
        decisions.append({"stableId": sid, "collection": collection, "batchPath": path,
                          "source": sources[sid], "currentFullTarget": current,
                          "acceptedFullTarget": final, "basis": "bg-selector-02-extra-001"})
    assert len(decisions) == 41 and len({d["stableId"] for d in decisions}) == 41
    pins = [{"path": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in inputs]
    common = {"schemaVersion": 1, "locale": "bg", "gameVersion": "1.3.19",
              "sourceSha256": sha(ROOT / "Source/localization-inventory-v3/strings.jsonl"),
              "staticSourceSha256": sha(ROOT / "Source/localization-inventory-v3/static-text.jsonl"),
              "preserveExactlySha256": sha(ROOT / "Source/preserve-exactly-v4.json"),
              "bgGlossarySha256": sha(ROOT / "Documentation/glossary-translations/canonical-reviews/artifacts/bg/layer.json"),
              "sourceGlossarySha256": sha(Path("/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary.json")),
              "pinnedInputs": pins, "baselineAuthoredFiles": baseline["allAuthoredFiles"]}
    plan = dict(common, status="preflight passed; single consolidated correction003 ready",
                acceptedUnits=16538, reviewerProposalCount=43,
                reviewerAcceptedCount=40, reviewerDismissedCount=3,
                additionalDependencyCount=1, decisionCount=len(decisions), decisions=decisions)
    evidence = dict(common, status="review-02 author adjudication; no independent clean or editorial acceptance",
                    proposalCount=43, acceptedOrRevisedCount=40, dismissedCount=3,
                    additionalDependencyCount=1, adjudications=adjudications)
    for name, value in (("correction-batch-003.json", plan),
                        ("independent-review-02-author-adjudication.json", evidence)):
        path = BG / name
        payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
        if path.exists():
            assert path.read_bytes() == payload, name + " drift"
        else:
            path.write_bytes(payload)
    print(json.dumps({"reviewerProposals": 43, "dismissed": 3, "changedIds": 41,
                      "changedFiles": len({d["batchPath"] for d in decisions}),
                      "planSha256": sha(BG / "correction-batch-003.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
