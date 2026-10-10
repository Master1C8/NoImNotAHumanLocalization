"""Reconcile current Filipino text to the pinned complete first author pass.

This proves byte-bound author provenance and target-only recorded changes. It
does not perform semantic review, gameplay, rendering, or installation checks.
"""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
LOCALE = ROOT / "Translations/fil"
sys.path.insert(0, str(ROOT / "Scripts"))
from locale_text_inputs import current_text


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def serialize_variants(value):
    yield (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    metadata = {k: v for k, v in value.items() if k != "entries"}
    entries = ",\n".join("    " + json.dumps(e, ensure_ascii=False)
                           for e in value["entries"])
    yield (json.dumps(metadata, ensure_ascii=False, indent=2)[:-2] +
           ',\n  "entries": [\n' + entries + "\n  ]\n}\n").encode()


def entry(document, stable_id):
    identity = int(stable_id.rsplit(":", 1)[1]) if stable_id.startswith("string:") else stable_id
    found = [e for e in document["entries"]
             if e.get("id", e.get("stableId")) == identity]
    assert len(found) == 1, stable_id
    return found[0]


def verify(latest):
    first_path = LOCALE / "semantic-review-progress.json"
    assert sha(first_path.read_bytes()) == "f23b782e39dda73cfcb04bc32a7b04d96400148379c6060f77935211a2e49faa"
    first = load(first_path)
    values, authored = current_text("fil")
    assert len(values) == first["reviewedUnits"] == first["acceptedUnits"] == 16538
    assert sum(r["reviewedUnits"] for r in first["reviewedFileHashes"]) == 16538
    assert all(r["wholeFileReviewed"] and r["reviewedUnits"] == r["fileUnits"]
               for r in first["reviewedFileHashes"])
    raws = {r["path"]: (ROOT / r["path"]).read_bytes() for r in authored}
    checkpoints = []
    events = 0
    for number in range(latest, 0, -1):
        directory = LOCALE / f"semantic-correction-cycle-{number:03}"
        plan_path = (LOCALE / "semantic-correction-cycle-001.before.json"
                     if number == 1 else directory / "plan.json")
        after_path = (LOCALE / "semantic-correction-cycle-001.after.json"
                      if number == 1 else directory / "after.json")
        plan, after = load(plan_path), load(after_path)
        recorded_plan_hash = after.get("planSha256", after.get("beforeEvidenceSha256"))
        assert recorded_plan_hash == sha(plan_path.read_bytes()), number
        rows = plan.get("rows", [plan.get("row")])
        files = after.get("files", [after.get("file")])
        grouped = {}
        for row in rows:
            grouped.setdefault(row["authoredPath"], []).append(row)
        assert set(grouped) == {f.get("authoredPath", f.get("path")) for f in files}
        for record in files:
            path = record.get("authoredPath", record.get("path"))
            raw = raws[path]
            assert sha(raw) == record["afterSha256"], (number, path, "after")
            before_path = record.get("beforeSnapshotPath")
            old = load(ROOT / before_path) if before_path else copy.deepcopy(json.loads(raw))
            new = json.loads(raw)
            if before_path:
                expected = copy.deepcopy(old)
                for row in grouped[path]:
                    target = entry(expected, row["stableId"])
                    prior = row.get("beforeTarget", row.get("currentTarget", row.get("target")))
                    assert target["target"] == prior, (number, row["stableId"], "before target")
                    target["target"] = row.get("afterTarget", row.get("acceptedFullTarget"))
                assert expected == new, (number, path, "unexplained changes")
                before = (ROOT / before_path).read_bytes()
            else:
                for row in grouped[path]:
                    target = entry(old, row["stableId"])
                    assert target["target"] == row["afterTarget"]
                    target["target"] = row["beforeTarget"]
                candidates = [candidate for candidate in serialize_variants(old)
                              if sha(candidate) == record["beforeSha256"]]
                assert len(candidates) == 1, (number, path, "first cycle formatting")
                before = candidates[0]
            assert sha(before) == record["beforeSha256"], (number, path, "before")
            raws[path] = before
        events += len(rows)
        checkpoints.append({"cycle": number, "changedFiles": len(files),
                            "targetEvents": len(rows), "planSha256": sha(plan_path.read_bytes()),
                            "afterSha256": sha(after_path.read_bytes()), "result": "passed"})
    expected = {r["path"]: r["sha256"] for r in first["reviewedFileHashes"]}
    assert set(expected) == set(raws) and len(raws) == 456
    assert all(sha(raw) == expected[path] for path, raw in raws.items())
    for record in first["sourceAndGlossaryFingerprints"].values():
        assert sha((ROOT / record["path"]).read_bytes()) == record["sha256"]
    return {"locale": "fil", "result": "passed", "firstPassUnits": 16538,
            "authoredFiles": len(raws), "targetOnlyCorrectionEvents": events,
            "firstPassProgressSha256": sha(first_path.read_bytes()),
            "currentAuthoredFiles": authored, "cycles": checkpoints,
            "boundary": "Current corpus and exact recorded target-only provenance to the complete first author pass; no new semantic review.",
            "runtime": "not-run", "rendering": "not-run", "installation": "not-run"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--latest-cycle", type=int, required=True)
    args = parser.parse_args()
    assert args.latest_cycle >= 6
    print(json.dumps(verify(args.latest_cycle), ensure_ascii=False, indent=2))
