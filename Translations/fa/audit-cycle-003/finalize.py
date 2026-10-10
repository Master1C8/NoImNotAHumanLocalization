#!/usr/bin/env python3
"""Verify cycle-3 correction evidence and write the immutable reviewer handoff."""

import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[3]
CYCLE = pathlib.Path(__file__).resolve().parent
FA = ROOT / "Translations/fa"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def once(path, payload):
    if path.exists():
        assert path.read_bytes() == payload, path
    else:
        path.write_bytes(payload)


def main():
    pre = read(CYCLE / "preflight.json")
    plan = read(CYCLE / "correction-plan.json")
    delta = read(CYCLE / "file-delta-manifest.json")
    closure = read(CYCLE / "closure.json")
    review = read(FA / "independent-review-02/review-verdict.json")
    assert sha(FA / "independent-review-02/review-verdict.json") == plan["reviewVerdictSha256"]
    assert sha(CYCLE / "correction-plan.json") == pre["correctionPlanSha256"] == delta["correctionPlanSha256"]
    assert len(plan["rows"]) == len(delta["correctedIds"]) == 1
    item = delta["files"][0]
    before = read(CYCLE / "before/dialogue-batch-348.json")
    after = read(CYCLE / "after/dialogue-batch-348.json")
    current = read(ROOT / item["path"])
    assert after == current and sha(ROOT / item["path"]) == item["afterSha256"]
    assert sha(CYCLE / "before/dialogue-batch-348.json") == item["beforeSha256"]
    b_entries, a_entries = before["entries"], after["entries"]
    assert len(b_entries) == len(a_entries) == 21
    differing = [(a, b) for a, b in zip(b_entries, a_entries) if a != b]
    row = plan["rows"][0]
    assert len(differing) == 1
    assert differing[0] == ({"id": int(row["stableId"].rsplit(":", 1)[1]), "target": row["before"]},
                            {"id": int(row["stableId"].rsplit(":", 1)[1]), "target": row["acceptedTarget"]})
    assert {k: v for k, v in before.items() if k != "entries"} == {k: v for k, v in after.items() if k != "entries"}
    once(CYCLE / "after/dialogue-batch-348.validation.json", (FA / "dialogue-batch-348.validation.json").read_bytes())
    sidecar = read(FA / "dialogue-batch-348.validation.json")
    assert sidecar["batchSha256"] == item["afterSha256"] and sidecar["structuralResult"] == "passed"
    assert sidecar["authoredRows"] == 21
    diff = {"schemaVersion": 1, "locale": "fa", "cycle": 3,
            "changedStableIds": [row["stableId"]], "changedAuthoredFiles": [item["path"]],
            "beforeSha256": item["beforeSha256"], "afterSha256": item["afterSha256"],
            "unchangedEntries": 20, "changedEntries": 1,
            "unchangedBatchMetadata": True, "sourceAndProtectedSyntax": "passed by preflight and full corpus gate",
            "recipeDependency": "none; direct dialogue entry, common-options/static/credits recipes unchanged",
            "authorReviewOnly": True}
    once(CYCLE / "diff-audit.json", encoded(diff))
    batches, sidecars, rows = 0, 0, 0
    for path in sorted(FA.glob("*batch-*.json")):
        if not re.fullmatch(r"(?:ui|dialogue|checks)-batch-\d{3}\.json", path.name):
            continue
        batch = read(path)
        side = read(path.with_suffix(".validation.json"))
        assert side["batchSha256"] == sha(path) and side["structuralResult"] == "passed"
        assert side["authoredRows"] == len(batch["entries"])
        batches += 1
        sidecars += 1
        rows += len(batch["entries"])
    assert (batches, sidecars, rows) == (418, 418, 16360)
    once(CYCLE / "structural-sidecar-gate.json", encoded({
        "schemaVersion": 1, "locale": "fa", "cycle": 3,
        "batches": batches, "matchingPassedSidecars": sidecars,
        "tableRows": rows, "staticRows": 178, "totalAccepted": 16538,
        "affectedBatchSidecarSha256": sha(FA / "dialogue-batch-348.validation.json"),
        "fullPreserveExact": "Translations/fa/audit-cycle-003/deterministic-gate.json",
        "localeReadinessExact": "16538/16538 validated, observed 16538, problems 0 using .venv/bin/python Scripts/report_locale_readiness.py --exact --compact"}))
    old = set((FA / "audit-cycle-002/closure-ids.txt").read_text().splitlines())
    components = {name: set((CYCLE / (name + "-ids.txt")).read_text().splitlines())
                  for name in ("changed", "context", "repetition", "glossaryReferent",
                               "runtimeBinding", "mandatoryRegression", "contextWatchlist",
                               "closure", "newlySelected", "invalidatedPrior", "retiredPrior",
                               "nextReviewDelta")}
    assert components["closure"] == set().union(*(components[k] for k in
           ("changed", "context", "repetition", "glossaryReferent", "runtimeBinding",
            "mandatoryRegression", "contextWatchlist")))
    assert components["newlySelected"] == components["closure"] - old
    assert components["retiredPrior"] == old - components["closure"]
    assert components["nextReviewDelta"] == components["changed"] | components["newlySelected"] | components["invalidatedPrior"]
    assert (len(old), len(components["closure"]), len(components["newlySelected"]),
            len(components["invalidatedPrior"]), len(components["retiredPrior"]),
            len(components["nextReviewDelta"])) == (2701, 946, 2, 16, 1757, 18)
    for key, value in closure["componentHashes"].items():
        assert value == {"count": len(components[key]), "sha256": sha(CYCLE / (key + "-ids.txt"))}
    assert review["reviewedDeltaFullUnits"] == 1408 and review["objectiveProposals"] == 1
    handoff = f"""# Persian cycle 3 author handoff

The complete first semantic pass remains 16,538/16,538 on pinned source and glossary. Independent review02 read its exact 1,408-ID cycle02 delta, passed all five cycle02 corrections, and raised one objective aunt-side error. No universal restart condition was found. This author cycle accepts that one full-unit replacement; independent editorial acceptance remains pending.

The changed ID is `{row['stableId']}`. Russian `своей тётки` identifies one aunt without maternal or paternal side. The old Persian `خاله‌ام` asserted the maternal side. The complete replacement uses `عمه یا خاله‌ام` and retains the gambling loss of her house, prior consequence, photo comparison, speaker prefix and ellipsis. The pinned compiled `Scammer_Photo_Gun` order and both choices were checked. The accepted source inventory has exactly one aunt inflection and the prior/current Persian corpus has exactly one aunt term. Source `лететь` is excluded by the word boundary. The actual encounter context has 17 accepted IDs including the death branch.

Preparation: `preflight.json` SHA-256 `{sha(CYCLE / 'preflight.json')}`; selector `selector-spec.json` SHA-256 `{sha(CYCLE / 'selector-spec.json')}`; enumeration `aunt-enumeration.json` SHA-256 `{sha(CYCLE / 'aunt-enumeration.json')}`. Reviewer02 evidence index has 14 matching files and all 456 verdict pins matched before application. Source, glossary and compiled Yarn remain unchanged. The direct authored row has no dependent expansion, phrase/static map or credits recipe; their hashes are pinned in preflight and the full gate. `before/` and `after/` retain exact authored and validator bytes; `diff-audit.json` verifies one changed target among 21 entries.

Current closure: **946** IDs, SHA-256 `{sha(CYCLE / 'closure-ids.txt')}`. Prior independently reviewed cycle02 closure: **2,701** IDs, SHA-256 `{sha(FA / 'audit-cycle-002/closure-ids.txt')}`. Corrected: 1; newly selected: 2; explicit prior IDs invalidated by the changed authored file: 16; retired resolved dependencies: 1,757. The exact next delta is **18** IDs, SHA-256 `{sha(CYCLE / 'nextReviewDelta-ids.txt')}`. Formula: corrected ∪ (current closure − prior independently reviewed closure) ∪ explicit invalidated prior IDs. The two new IDs are the actual `Scammer_Death` branch. The 16 invalidated IDs are the prior reviewed rows in `dialogue-batch-348.json`. `closure.json` and `next-review-delta.json` contain canonical-order full source/target pairs, separate component hashes and zero unexplained missing/extra IDs. Historical photo/cousin dependencies are retired because review02 passed them on unchanged hashes; the stable mandatory catalog (544 IDs), runtime bindings and four first-pass watchlist IDs remain selected.

Affected validator: `.venv/bin/python Scripts/validate_game_text_batch.py Translations/fa/dialogue-batch-348.json` passed 21 rows. All 418 current batch sidecars match their authored SHA-256 and 16,360 table rows. The full `.venv/bin/python Scripts/report_locale_readiness.py --exact --compact` gate returned fa 16,538/16,538 validated, observed 16,538, problems 0. `cycle.py closure` independently reran `preserve_exact.check_value` for every accepted unit. `.venv/bin/python Scripts/expand_exact_text_batch.py --verify Translations/fa/common-options-001.authored.json Translations/fa/dialogue-batch-001.json` reproduced 2,841 unchanged expansion rows. `deterministic-gate.json` SHA-256 `{sha(CYCLE / 'deterministic-gate.json')}`; sidecar gate SHA-256 `{sha(CYCLE / 'structural-sidecar-gate.json')}`. These are structural checks, not Persian meaning or runtime proof.

Distinct reviewer next: verify pinned cycle03 inputs, reproduce closure with `.venv/bin/python Translations/fa/audit-cycle-003/cycle.py closure`, read all 18 full source/target delta pairs and the stable mandatory regression catalog. Resolve the two previously recorded source/context watchlist questions only if new evidence exists; unchanged prior wording decisions remain. Do not claim author self-review as independent acceptance. Runtime, Persian shaping/ZWNJ, bidi, fonts and visual layout remain unrun under the no-game instruction. Images/textures are excluded. No Git/index/shared state was changed by this author cycle.
"""
    once(CYCLE / "reviewer-handoff.md", handoff.encode())
    print(json.dumps({"closure": len(components["closure"]),
                      "nextDelta": len(components["nextReviewDelta"]),
                      "sidecars": sidecars, "handoffSha256": sha(CYCLE / "reviewer-handoff.md")}))


if __name__ == "__main__":
    main()
