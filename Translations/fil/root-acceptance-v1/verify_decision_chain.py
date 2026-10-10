"""Trace exact Filipino independent decisions to their full-pair readings.

This reads immutable review evidence. It does not grant editorial acceptance
or establish that an older review still applies to today's authored text.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LOCALE = ROOT / "Translations/fil"
CLEAN = {
    "accepted-as-is-for-this-closure-review",
    "accepted-as-is-for-this-delta",
    "prior supplemental independent decision applicable",
    "applicable-independent-reviewed-unit",
    "accepted-independent-reviewed-unit",
    "exact-prior-independent-decision-reused",
}
_files = {}
_hashes = {}
_checked = set()
_leaves = Counter()


def digest(path):
    path = path.resolve()
    assert path.is_relative_to(LOCALE)
    if path not in _hashes:
        _hashes[path] = hashlib.sha256(path.read_bytes()).hexdigest()
    return _hashes[path]


def indexed(path):
    path = path.resolve()
    assert path.is_relative_to(LOCALE)
    if path not in _files:
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        result = {r["stableId"]: r for r in rows}
        assert len(result) == len(rows), path
        _files[path] = result
    return _files[path]


def same_pair(left, right):
    for key in ("stableId", "acceptedOrdinal", "sourceSha256", "targetSha256"):
        assert left[key] == right[key], (left["stableId"], key)
    for key in ("key", "nodeNames", "consumerIdentitySha256"):
        if key in left and key in right:
            assert left[key] == right[key], (left["stableId"], key)


def trace(path, stable_id, expected=None, active=None):
    path = path.resolve()
    marker = (path, stable_id)
    active = set() if active is None else active
    assert marker not in active, (path, stable_id, "cyclic decision provenance")
    row = indexed(path)[stable_id]
    if expected is not None:
        same_pair(row, expected)
    assert row["decision"] in CLEAN and row.get("findingId") is None, (path, stable_id, "not a clean independent decision")
    if marker in _checked:
        return
    active.add(marker)
    prior = row.get("priorDecisionEvidence")
    prior_hash = row.get("priorDecisionFileSha256")
    if not prior and row.get("priorEvidenceSha256"):
        number = int(path.parent.name.rsplit("-", 1)[1])
        prior = str((LOCALE / f"independent-review-{number - 1:02}" /
                     "closure-decision-applicability.jsonl").relative_to(ROOT))
        prior_hash = row["priorEvidenceSha256"]
    if not prior:
        prior = row.get("decisionEvidence")
    if (not prior and path.name == "closure-decision-applicability.jsonl" and
            row["decision"] == "accepted-independent-reviewed-unit"):
        assert row["evidenceMode"].startswith("fresh-"), (path, stable_id)
        prior = str((path.parent / "fresh-decisions.jsonl").relative_to(ROOT))
    if prior:
        previous = (ROOT / prior).resolve()
        assert previous != path, (path, stable_id, "self-referential decision evidence")
        if prior_hash:
            assert digest(previous) == prior_hash, previous
        trace(previous, stable_id, row, active)
    else:
        # The supplemental receipt itself records an independent complete-pair
        # reconsideration; its prior recipe receipt is contextual provenance.
        assert path.name in {"decisions.jsonl", "fresh-decisions.jsonl",
                             "supplemental-applicability-decisions.jsonl"}, path
        if path.name == "supplemental-applicability-decisions.jsonl":
            assert "reconsideration" in row["evidenceMode"]
            assert (ROOT / row["priorEvidence"]).is_file()
        _leaves[str(path.relative_to(ROOT))] += 1
    active.remove(marker)
    _checked.add(marker)


def verify(number):
    directory = LOCALE / f"independent-review-{number:02}"
    path = directory / "closure-decision-applicability.jsonl"
    rows = indexed(path)
    findings = []
    for stable_id, row in rows.items():
        if row["decision"] not in CLEAN or row.get("findingId") is not None:
            findings.append({"stableId": stable_id, "acceptedOrdinal": row["acceptedOrdinal"],
                             "findingId": row.get("findingId"), "decision": row["decision"]})
        else:
            trace(path, stable_id)
    return {"locale": "fil", "review": number,
            "result": "exact clean decision provenance passed; unresolved findings listed",
            "closureDecisions": len(rows), "cleanDecisions": len(rows) - len(findings),
            "unresolvedFindings": findings, "distinctTracedRecords": len(_checked),
            "distinctIndependentLeafReads": dict(_leaves),
            "evidenceFiles": [{"path": str(p.relative_to(ROOT)), "sha256": digest(p)}
                              for p in sorted(_files)],
            "boundary": "Exact source/target/ordinal decision ancestry, and key/node/consumer identity wherever represented; final current corpus and consumer applicability require a separate root check.",
            "editorialAcceptance": "not granted", "runtime": "not-run"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", type=int, required=True)
    args = parser.parse_args()
    assert args.review >= 6
    print(json.dumps(verify(args.review), ensure_ascii=False, indent=2))
