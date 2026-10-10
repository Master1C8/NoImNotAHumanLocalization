"""Read-only root reconciliation of Bulgarian author and independent evidence."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
BG = ROOT / "Translations/bg"
HERE = Path(__file__).parent
sys.path.insert(0, str(ROOT / "Scripts"))
from locale_text_inputs import current_text


def load(path):
    return json.loads(path.read_text())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def serialize(value, inline):
    if not inline:
        return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    metadata = {k: v for k, v in value.items() if k != "entries"}
    entries = ",\n".join("    " + json.dumps(e, ensure_ascii=False) for e in value["entries"])
    return (json.dumps(metadata, ensure_ascii=False, indent=2)[:-2] +
            ',\n  "entries": [\n' + entries + "\n  ]\n}\n").encode()


def main():
    first = load(BG / "semantic-first-pass-cycle-000.json")
    values, authored = current_text("bg")
    assert len(values) == first["reviewedUnits"] == first["acceptedUnits"] == 16538
    assert sum(r["units"] for r in first["reviewedRanges"]) == 16538
    raws = {r["path"]: (ROOT / r["path"]).read_bytes() for r in authored}
    objects = {path: json.loads(raw) for path, raw in raws.items()}
    results = {n: load(BG / f"correction-batch-{n:03}-result.json") for n in range(1, 5)}
    events = 0
    for n in range(4, 0, -1):
        result = results[n]
        plan_path = BG / f"correction-batch-{n:03}.json"
        plan = load(plan_path)
        assert sha(plan_path.read_bytes()) == result["planSha256"]
        expected = {r["path"]: r.get("sha256", r.get("afterSha256")) for r in result["allAuthoredFiles"]}
        assert set(raws) == set(expected)
        assert all(sha(raw) == expected[path] for path, raw in raws.items())
        touched = set()
        for decision in plan["decisions"]:
            sid = decision["stableId"]
            identity = int(sid.rsplit(":", 1)[1]) if sid.startswith("string:") else sid
            path = decision["batchPath"]
            entry = next(e for e in objects[path]["entries"] if e.get("id", e.get("stableId")) == identity)
            assert entry["target"] == decision["acceptedFullTarget"]
            entry["target"] = decision.get("currentFullTarget", decision.get("currentTarget"))
            touched.add(path)
        before = results[n - 1]["allAuthoredFiles"] if n > 1 else first["reviewedFiles"]
        expected_before = {r["path"]: r.get("sha256", r.get("afterSha256")) for r in before}
        for path in touched:
            matches = [serialize(objects[path], inline) for inline in (False, True)
                       if sha(serialize(objects[path], inline)) == expected_before[path]]
            assert len(matches) == 1, (n, path)
            raws[path] = matches[0]
        assert all(sha(raw) == expected_before[path] for path, raw in raws.items())
        events += len(plan["decisions"])
    assert events == 251 and len(raws) == 411
    review = BG / "independent-review-04"
    assert sha((review / "evidence-sha256.json").read_bytes()) == "96acd495f01752ce01a469283eaa65eeea085a31b636f4fcf3e8b6d8dd254f6f"
    assert sha((review / "review.json").read_bytes()) == "cdb67845f0bb8de9ba99cea0e82d7694683cb1f1b1a69e1b2e12259ef11ff3b4"
    subprocess.run([sys.executable, "-B", str(BG / "verify_cycle_004.py"), "verify"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-B", str(review / "verify_review.py"), "verify"], cwd=ROOT, check=True)
    print(json.dumps({"locale": "bg", "rootReconciliation": "passed", "firstPassUnits": 16538,
                      "authoredFiles": 411, "targetOnlyCorrectionEvents": events,
                      "runtime": "not-run", "installation": "not-run"}))


if __name__ == "__main__":
    main()
