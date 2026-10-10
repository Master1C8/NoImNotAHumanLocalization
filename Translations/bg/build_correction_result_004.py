#!/usr/bin/env python3
"""Freeze cycle004 from the owning one-parse full-locale guard; no batch pools."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];BG=ROOT/'Translations/bg'
load=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();th=lambda t:hashlib.sha256(t.encode()).hexdigest()
def freeze(p,obj):
 raw=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()
 if p.exists():assert p.read_bytes()==raw,str(p)+' drift'
 else:p.write_bytes(raw)
def main():
 plan=load(BG/'correction-batch-004.json');baseline=load(BG/'correction-batch-003-result.json');corpuspath=BG/'locale-corpus-cycle-004.json';corpus=load(corpuspath)
 assert plan['decisionCount']==len(plan['decisions'])==3
 assert corpus['rows']==16538 and corpus['structuralResult']==corpus['exactResult']=='passed'
 assert sha(ROOT/'Scripts/validate_locale_corpus.py')==corpus['validatorSha256'] and sha(ROOT/'Scripts/locale_text_inputs.py')==corpus['inputLoaderSha256']
 for n,h in corpus['owningValidators'].items():assert sha(ROOT/'Scripts'/n)==h
 current={r['path']:r['sha256'] for r in corpus['authoredFiles']}
 affected={d['batchPath'] for d in plan['decisions']};snapshots=load(BG/'correction-cycle-004-baseline/manifest.json')
 snap={r['path']:r for r in snapshots['physicalSnapshots']};files=[];pairs=[]
 for b in baseline['allAuthoredFiles']:
  rec=dict(b);p=ROOT/b['path'];side=ROOT/b['validationPath']
  assert sha(p)==current[b['path']]
  rec['sha256']=sha(p)
  if b['path'] in affected:
   # Sidecar is a current derived receipt, not a claim of rerunning a batch parser.
   old=load(ROOT/snap[b['validationPath']]['snapshotPath']);assert sha(ROOT/snap[b['validationPath']]['snapshotPath'])==b['validationSha256']
   receipt=dict(old,batchSha256=rec['sha256'],structuralResult='passed',semanticReview='cycle004 bounded author correction; separate independent delta pending')
   receipt['validationMethod']='owning full locale corpus guard; no individual batch parse or pool'
   receipt['fullCorpusReceipt']={'path':str(corpuspath.relative_to(ROOT)),'sha256':sha(corpuspath),'rows':16538,'result':'passed'}
   raw=(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode()
   assert side.read_bytes() in ((ROOT/snap[b['validationPath']]['snapshotPath']).read_bytes(),raw),str(side)+' unexpected sidecar'
   side.write_bytes(raw)
   data=load(p);entries={str(e['id']):e for e in data['entries']}
   pre=load(ROOT/snap[b['path']]['snapshotPath']);preentries={str(e['id']):e for e in pre['entries']}
   changedhere={d['stableId'].rsplit(':',1)[1]:d for d in plan['decisions'] if d['batchPath']==b['path']}
   for i,e in entries.items():
    if i not in changedhere:assert e==preentries[i]
    else:
     d=changedhere[i];assert e['target']==d['acceptedFullTarget'] and preentries[i]['target']==d['currentFullTarget']
     assert {k:v for k,v in e.items() if k!='target'}=={k:v for k,v in preentries[i].items() if k!='target'}
     pairs.append(dict(d,sourceSha256=th(d['source']),beforeTargetSha256=th(d['currentFullTarget']),afterTargetSha256=th(d['acceptedFullTarget']),beforeBatchSha256=b['sha256'],afterBatchSha256=rec['sha256']))
  else:assert rec['sha256']==b['sha256'] and sha(side)==b['validationSha256']
  rec['validationSha256']=sha(side);files.append(rec)
 assert len(files)==411 and len(pairs)==3 and len(affected)==3
 preserve={'schemaVersion':1,'locale':'bg','gameVersion':'1.3.19','manifestSha256':snapshots['sourceAndConfigurationPins']['Source/preserve-exactly-v4.json'],
   'sourceInventorySha256':corpus['sourceInventorySha256'],'staticInventorySha256':corpus['staticInventorySha256'],'inputFiles':corpus['authoredFiles'],'checkedRows':16538,'exactResult':'passed',
   'evidenceMethod':'Derived receipt of the owning full locale corpus guard including check_value/preserve-exact grammar, not a separate validator invocation.',
   'fullCorpusReceiptPath':str(corpuspath.relative_to(ROOT)),'fullCorpusReceiptSha256':sha(corpuspath),'semanticReview':'first complete pass preserved; bounded correction author review only','runtime':'not-run'}
 freeze(BG/'preserve-exact-cycle-004.json',preserve)
 freeze(BG/'correction-cycle-004-sourcepairs.json',{'schemaVersion':1,'locale':'bg','pairs':sorted(pairs,key=lambda p:next(k for k,d in enumerate(plan['decisions']) if d['stableId']==p['stableId'])),'pairCount':3,'sourceUnchanged':True,'unchangedAuthoredFiles':408,'unchangedRows':16535,'beforeSnapshotManifestSha256':sha(BG/'correction-cycle-004-baseline/manifest.json')})
 result={'schemaVersion':1,'locale':'bg','gameVersion':'1.3.19','status':'three full-unit author corrections applied together; full 16538-unit owning structural/exact/derived gates passed; independent delta pending',
  'planPath':'Translations/bg/correction-batch-004.json','planSha256':sha(BG/'correction-batch-004.json'),'baselineResultPath':'Translations/bg/correction-batch-003-result.json','baselineResultSha256':sha(BG/'correction-batch-003-result.json'),
  'changedIds':[d['stableId'] for d in plan['decisions']],'changedIdCount':3,'changedFiles':[f for f in files if f['path'] in affected],'changedFileCount':3,'allAuthoredFiles':files,'allAuthoredFileCount':411,
  'localeCorpus':{'path':str(corpuspath.relative_to(ROOT)),'sha256':sha(corpuspath),'rows':16538,'result':'passed'},
  'preserveExactly':{'path':'Translations/bg/preserve-exact-cycle-004.json','sha256':sha(BG/'preserve-exact-cycle-004.json'),'checkedRows':16538,'result':'passed'},
  'sourcepairs':{'path':'Translations/bg/correction-cycle-004-sourcepairs.json','sha256':sha(BG/'correction-cycle-004-sourcepairs.json')},
  'sidecarBoundary':'Only three affected sidecars refreshed from one whole-locale gate; immutable original bytes in baseline snapshots; no per-batch pools.',
  'derivedArtifacts':'No expansion/UI/check/static authored values changed. Credits-role map and static credits expansion identical and rechecked by current_text in full corpus guard.',
  'independentDiffReview':'pending separate reviewer; no clean verdict or editorial acceptance'}
 freeze(BG/'correction-batch-004-result.json',result)
 print(json.dumps({'changedIds':3,'changedFiles':3,'unchangedFiles':408,'resultSha256':sha(BG/'correction-batch-004-result.json'),'corpusSha256':sha(corpuspath)}))
if __name__=='__main__':main()
