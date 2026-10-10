#!/usr/bin/env python3
"""Apply the preflighted cycle003 target-only batch once with before/after evidence."""
import hashlib, json, os, pathlib, shutil, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
HI = ROOT / "Translations/hi"
PLAN = HI / "semantic-cycle-003-application-plan.json"
BEFORE = HI / "semantic-cycle-003-before-files"
AFTER = HI / "semantic-cycle-003-after-files"

def sha(path): return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def digest(value): return hashlib.sha256(value.encode()).hexdigest()
def read(path): return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
def dump(value): return json.dumps(value, ensure_ascii=False, indent=2) + "\n"
def atomic(path, value):
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=".hi-cycle003-", delete=False) as f:
        f.write(value); temp = pathlib.Path(f.name)
    os.replace(temp, path)

def main():
    assert not PLAN.exists() and not BEFORE.exists() and not AFTER.exists()
    adj = read(HI / "semantic-cycle-003-adjudication.json")
    pre = read(HI / "semantic-cycle-003-preflight.json")
    assert len(adj["items"]) == pre["reviewedUnits"] == 18
    assert pre["status"] == "complete 18-unit preflight passed before authored application"
    assert pre["adjudicationSha256"] == sha(HI / "semantic-cycle-003-adjudication.json")
    previous = read(HI / "semantic-cycle-002-structural-gate.json")
    old_files = {entry["path"]: entry for entry in previous["files"]}
    grouped = {}
    for item in adj["items"]: grouped.setdefault(item["authoredPath"], []).append(item)
    planned = []
    for name, items in sorted(grouped.items()):
        path = ROOT / name
        assert sha(path) == old_files[name]["sha256"]
        before = path.read_text(encoding="utf-8")
        after = before
        if before == dump(read(path)):
            obj = read(path)
            by_id = {str(entry["id"]): entry for entry in obj["entries"]}
            for item in items:
                key = item["stableId"].rsplit(":", 1)[1]
                assert by_id[key]["target"] == item["before"]
                by_id[key]["target"] = item["acceptedFullTarget"]
            after = dump(obj)
        else:
            for item in items:
                key = item["stableId"].rsplit(":", 1)[1]
                old = '"id": ' + key + ', "target": ' + json.dumps(item["before"], ensure_ascii=False)
                new = '"id": ' + key + ', "target": ' + json.dumps(item["acceptedFullTarget"], ensure_ascii=False)
                assert after.count(old) == 1, (name, key)
                after = after.replace(old, new, 1)
        old_obj, new_obj = json.loads(before), json.loads(after)
        assert {k:v for k,v in old_obj.items() if k != "entries"} == {k:v for k,v in new_obj.items() if k != "entries"}
        old_by = {str(e["id"]): e for e in old_obj["entries"]}
        new_by = {str(e["id"]): e for e in new_obj["entries"]}
        assert old_by.keys() == new_by.keys()
        assert {key for key in old_by if old_by[key] != new_by[key]} == {item["stableId"].rsplit(":",1)[1] for item in items}
        for key in old_by:
            assert {k:v for k,v in old_by[key].items() if k != "target"} == {k:v for k,v in new_by[key].items() if k != "target"}
        validation = path.with_suffix(".validation.json")
        planned.append({"path": name, "beforeSha256": sha(path), "afterSha256": digest(after),
                        "changedIds": [item["stableId"] for item in items],
                        "beforeValidationPath": str(validation.relative_to(ROOT)), "beforeValidationSha256": sha(validation),
                        "afterText": after})
    plan = {"schemaVersion":1, "locale":"hi", "gameVersion":"1.3.19", "status":"immutable pre-application plan",
            "adjudicationSha256": sha(HI / "semantic-cycle-003-adjudication.json"),
            "preflightSha256": sha(HI / "semantic-cycle-003-preflight.json"),
            "previousClosureSha256": sha(HI / "semantic-cycle-002-closure.json"),
            "changedCount":18, "fileCount":len(planned),
            "files":[{k:v for k,v in row.items() if k != "afterText"} for row in planned],
            "writeBoundary":"Each authored file is atomically replaced. Multi-file application is not a transaction; plan and snapshots allow exact reconciliation."}
    BEFORE.mkdir(); AFTER.mkdir()
    for row in planned:
        shutil.copy2(ROOT / row["path"], BEFORE / pathlib.Path(row["path"]).name)
        shutil.copy2(ROOT / row["beforeValidationPath"], BEFORE / pathlib.Path(row["beforeValidationPath"]).name)
    PLAN.write_text(dump(plan), encoding="utf-8")
    for row in planned:
        path = ROOT / row["path"]
        assert sha(path) == row["beforeSha256"]
        atomic(path, row["afterText"])
        assert sha(path) == row["afterSha256"]
        shutil.copy2(path, AFTER / path.name)
    print("applied", 18, "full units in", len(planned), "authored files")

if __name__ == "__main__": main()
