#!/usr/bin/env python3
"""Apply the preflighted Hindi cycle-002 correction batch once, with exact snapshots."""
import hashlib,json,os,shutil,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HI=ROOT/"Translations/hi"
PLAN=HI/"semantic-cycle-002-application-plan.json"
BEFORE=HI/"semantic-cycle-002-before-files"
AFTER=HI/"semantic-cycle-002-after-files"
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def dump(x):return json.dumps(x,ensure_ascii=False,indent=2)+"\n"
def atomic(path,text):
 with tempfile.NamedTemporaryFile("w",encoding="utf-8",dir=path.parent,prefix=".hi-cycle002-",delete=False) as f:
  f.write(text);temporary=Path(f.name)
 os.replace(temporary,path)
def main():
 assert not PLAN.exists() and not BEFORE.exists() and not AFTER.exists()
 a=read(HI/"semantic-cycle-002-adjudication.json")
 pre=read(HI/"semantic-cycle-002-preflight.json")
 assert pre["status"].startswith("complete 21-unit preflight passed")
 assert pre["adjudicationSha256"]==sha(HI/"semantic-cycle-002-adjudication.json")
 gate=read(HI/"semantic-cycle-001-structural-gate.json")
 old_gate={f["path"]:f for f in gate["files"]}
 grouped={}
 for item in a["items"]:grouped.setdefault(item["authoredPath"],[]).append(item)
 assert len(a["items"])==21 and len(grouped)==16
 changes={}
 for name,items in grouped.items():
  path=ROOT/name
  assert sha(path)==old_gate[name]["sha256"],name
  before=path.read_text(encoding="utf-8")
  obj=read(path)
  if before==dump(obj):
   by_id={e.get("stableId",str(e.get("id"))):e for e in obj["entries"]}
   for item in items:
    key=item["stableId"] if item["stableId"].startswith("tmp:") else item["stableId"].rsplit(":",1)[1]
    e=by_id[key];assert e["target"]==item["before"]
    e["target"]=item["acceptedFullTarget"]
   after=dump(obj)
  else:
   after=before
   for item in items:
    number=item["stableId"].rsplit(":",1)[1]
    old_token='"id": '+number+', "target": '+json.dumps(item["before"],ensure_ascii=False)
    new_token='"id": '+number+', "target": '+json.dumps(item["acceptedFullTarget"],ensure_ascii=False)
    assert after.count(old_token)==1,(name,number)
    after=after.replace(old_token,new_token,1)
   updated=json.loads(after)
   before_by_id={str(e["id"]):e for e in obj["entries"]}
   after_by_id={str(e["id"]):e for e in updated["entries"]}
   assert before_by_id.keys()==after_by_id.keys()
   wanted={i["stableId"].rsplit(":",1)[1] for i in items}
   assert {k for k in before_by_id if before_by_id[k]!=after_by_id[k]}==wanted
   for k in wanted:
    assert set(before_by_id[k])==set(after_by_id[k])=={"id","target"}
   assert {k:obj[k] for k in obj if k!="entries"}=={k:updated[k] for k in updated if k!="entries"}
  assert len(json.loads(after)["entries"])==len(obj["entries"])
  assert before!=after
  changes[name]={"beforeText":before,"afterText":after,"items":items}
 phrase=HI/"static-phrases-authored.json"
 phrase_before=phrase.read_text(encoding="utf-8")
 assert sha(phrase)==read(HI/"semantic-review-progress.json")["reviewedInputHashes"]["Translations/hi/static-phrases-authored.json"]
 pm=read(phrase);matches=[e for e in pm["entries"] if e["source"]=="Экстрасенсы"]
 assert len(matches)==1 and matches[0]["target"]=="साइकिक्स"
 matches[0]["target"]="अतींद्रिय विशेषज्ञों की सेवा"
 phrase_after=dump(pm)
 files=[]
 for name,change in changes.items():
  path=ROOT/name
  vpath=path.with_suffix(".validation.json")
  files.append({"path":name,"beforeSha256":sha(path),"afterSha256":hashlib.sha256(change["afterText"].encode()).hexdigest(),"changedIds":[i["stableId"] for i in change["items"]],"beforeValidationPath":str(vpath.relative_to(ROOT)),"beforeValidationSha256":sha(vpath)})
 files.sort(key=lambda x:x["path"])
 plan={"schemaVersion":1,"locale":"hi","gameVersion":"1.3.19","status":"immutable pre-application plan","adjudicationSha256":sha(HI/"semantic-cycle-002-adjudication.json"),"preflightSha256":sha(HI/"semantic-cycle-002-preflight.json"),"previousClosureSha256":sha(HI/"semantic-cycle-001-closure.json"),"changedIds":[i["stableId"] for i in a["items"]],"changedCount":21,"fileCount":len(files),"files":files,"phraseMap":{"path":str(phrase.relative_to(ROOT)),"beforeSha256":sha(phrase),"afterSha256":hashlib.sha256(phrase_after.encode()).hexdigest()},"writeBoundary":"Each file is atomically replaced; the 17-file batch is not a filesystem transaction. Before copies and plan permit exact reconciliation."}
 BEFORE.mkdir();AFTER.mkdir()
 for f in files:
  path=ROOT/f["path"];vpath=ROOT/f["beforeValidationPath"]
  shutil.copy2(path,BEFORE/path.name);shutil.copy2(vpath,BEFORE/vpath.name)
 shutil.copy2(phrase,BEFORE/phrase.name)
 PLAN.write_text(dump(plan),encoding="utf-8")
 for f in files:
  path=ROOT/f["path"];atomic(path,changes[f["path"]]["afterText"])
 atomic(phrase,phrase_after)
 for f in files:
  path=ROOT/f["path"];assert sha(path)==f["afterSha256"]
  shutil.copy2(path,AFTER/path.name)
 assert sha(phrase)==plan["phraseMap"]["afterSha256"]
 shutil.copy2(phrase,AFTER/phrase.name)
 print("applied",plan["changedCount"],"targets in",len(files),"authored files plus phrase map")
if __name__=="__main__":main()
