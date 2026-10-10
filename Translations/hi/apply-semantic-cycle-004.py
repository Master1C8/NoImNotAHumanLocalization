#!/usr/bin/env python3
"""Apply the single preflighted Hindi cycle004 full-unit correction once."""
import hashlib,json,os,pathlib,shutil,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
HI=ROOT/'Translations/hi'
PLAN=HI/'semantic-cycle-004-application-plan.json'
AFTER=HI/'semantic-cycle-004-after-files'
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def hs(text):return hashlib.sha256(text.encode()).hexdigest()
def read(path):return json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
def dump(obj):return json.dumps(obj,ensure_ascii=False,indent=2)+'\n'
def main():
 assert not PLAN.exists() and not AFTER.exists()
 adj=read(HI/'semantic-cycle-004-adjudication.json');pre=read(HI/'semantic-cycle-004-preflight.json');snap=read(HI/'semantic-cycle-004-pre-edit-snapshot.json')
 assert pre['adjudicationSha256']==sha(HI/'semantic-cycle-004-adjudication.json')
 assert pre['status']=='complete one-unit preflight passed before authored edit'
 item=adj['item'];path=ROOT/item['authoredPath'];val=path.with_suffix('.validation.json')
 assert sha(path)==pre['oldAuthoredFileSha256']==snap['files'][item['authoredPath']]
 assert sha(val)==pre['oldHistoricalSidecarSha256']==snap['files'][str(val.relative_to(ROOT))]
 assert sha(HI/'semantic-cycle-004-before-files'/path.name)==sha(path)
 before=path.read_text(encoding='utf-8');old=json.loads(before)
 key=item['stableId'].rsplit(':',1)[1]
 old_token='"id": '+key+', "target": '+json.dumps(item['before'],ensure_ascii=False)
 new_token='"id": '+key+', "target": '+json.dumps(item['acceptedFullTarget'],ensure_ascii=False)
 assert before.count(old_token)==1
 after=before.replace(old_token,new_token,1);new=json.loads(after)
 assert {k:v for k,v in old.items() if k!='entries'}=={k:v for k,v in new.items() if k!='entries'}
 old_rows={str(e['id']):e for e in old['entries']};new_rows={str(e['id']):e for e in new['entries']}
 assert old_rows.keys()==new_rows.keys()
 assert {k for k in old_rows if old_rows[k]!=new_rows[k]}=={key}
 assert old_rows[key]['target']==item['before'] and new_rows[key]['target']==item['acceptedFullTarget']
 assert {k:v for k,v in old_rows[key].items() if k!='target'}=={k:v for k,v in new_rows[key].items() if k!='target'}
 plan={'schemaVersion':1,'locale':'hi','gameVersion':'1.3.19','status':'immutable pre-application plan',
       'adjudicationSha256':sha(HI/'semantic-cycle-004-adjudication.json'),
       'preflightSha256':sha(HI/'semantic-cycle-004-preflight.json'),
       'snapshotSha256':sha(HI/'semantic-cycle-004-pre-edit-snapshot.json'),
       'previousClosureSha256':sha(HI/'semantic-cycle-003-closure.json'),
       'changedIds':[item['stableId']],'changedCount':1,
       'file':{'path':item['authoredPath'],'beforeSha256':sha(path),'afterSha256':hs(after),
               'historicalSidecarPath':str(val.relative_to(ROOT)),'historicalSidecarSha256':sha(val)},
       'writeBoundary':'One authored file atomically replaced; historical validation sidecar is preserved, and a fresh locale-only corpus receipt follows.'}
 PLAN.write_text(dump(plan),encoding='utf-8')
 AFTER.mkdir()
 with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=path.parent,prefix='.hi-cycle004-',delete=False) as f:
  f.write(after);temp=pathlib.Path(f.name)
 os.replace(temp,path)
 assert sha(path)==plan['file']['afterSha256'] and sha(val)==plan['file']['historicalSidecarSha256']
 shutil.copy2(path,AFTER/path.name)
 print('applied one full-unit target correction; historical sidecar unchanged')
if __name__=='__main__':main()
