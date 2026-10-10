#!/usr/bin/env python3
"""Verify immutable Hindi cycle-002 before/after target and derived evidence."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HI=ROOT/"Translations/hi"
def read(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 plan=read(HI/"semantic-cycle-002-application-plan.json")
 adj=read(HI/"semantic-cycle-002-adjudication.json")
 receipt=read(HI/"semantic-cycle-002-applied-evidence.json")
 gate=read(HI/"semantic-cycle-002-structural-gate.json")
 assert plan["changedCount"]==adj["acceptedCount"]==receipt["changedIds"]==21
 assert plan["fileCount"]==receipt["changedAuthoredFiles"]==16
 assert receipt["applicationPlanSha256"]==sha(HI/"semantic-cycle-002-application-plan.json")
 assert receipt["adjudicationSha256"]==sha(HI/"semantic-cycle-002-adjudication.json")
 assert receipt["preflightSha256"]==sha(HI/"semantic-cycle-002-preflight.json")
 assert len(receipt["evidenceFiles"])==16
 changed={x["stableId"]:x for x in adj["items"]}
 gate_files={x["path"]:x for x in gate["files"]}
 before=HI/"semantic-cycle-002-before-files";after=HI/"semantic-cycle-002-after-files"
 for planned,verified in zip(plan["files"],receipt["evidenceFiles"]):
  assert all(planned[k]==verified[k] for k in planned)
  path=ROOT/planned["path"];bp=before/path.name;ap=after/path.name
  vp=ROOT/planned["beforeValidationPath"]
  assert sha(bp)==planned["beforeSha256"]
  assert sha(ap)==sha(path)==planned["afterSha256"]==gate_files[planned["path"]]["sha256"]
  assert sha(before/vp.name)==planned["beforeValidationSha256"]
  assert sha(after/vp.name)==sha(vp)==verified["afterValidationSha256"]==gate_files[planned["path"]]["validationSha256"]
  old=read(bp);new=read(ap)
  assert {k:v for k,v in old.items() if k!="entries"}=={k:v for k,v in new.items() if k!="entries"}
  key=lambda e:e.get("stableId") or str(e["id"])
  o={key(e):e for e in old["entries"]};n={key(e):e for e in new["entries"]}
  assert set(o)==set(n)
  wanted={sid if sid.startswith("tmp:") else sid.rsplit(":",1)[1] for sid in planned["changedIds"]}
  assert {k for k in o if o[k]!=n[k]}==wanted
  for sid in planned["changedIds"]:
   k=sid if sid.startswith("tmp:") else sid.rsplit(":",1)[1]
   assert o[k]["target"]==changed[sid]["before"]
   assert n[k]["target"]==changed[sid]["acceptedFullTarget"]
   assert {a:b for a,b in o[k].items() if a!="target"}=={a:b for a,b in n[k].items() if a!="target"}
 p=plan["phraseMap"];name=Path(p["path"]).name
 assert sha(before/name)==p["beforeSha256"]
 assert sha(after/name)==sha(ROOT/p["path"])==p["afterSha256"]==gate["phraseMapSha256"]
 old_map={e["source"]:e["target"] for e in read(before/name)["entries"]}
 new_map={e["source"]:e["target"] for e in read(after/name)["entries"]}
 assert set(old_map)==set(new_map)
 assert {k for k in old_map if old_map[k]!=new_map[k]}=={"Экстрасенсы"}
 source={r["stableId"]:r["source"] for r in (json.loads(l) for l in (ROOT/"Source/localization-inventory-v3/static-text.jsonl").read_text().splitlines())}
 for row in read(HI/"static-text-draft.json")["entries"]:
  if row["stableId"]=="tmp:level5:59:m_text":continue
  assert row["target"]==new_map[source[row["stableId"]]]
 print("verified 21 target-only corrections in 16 files, phrase map and all validation sidecars")
if __name__=="__main__":main()
