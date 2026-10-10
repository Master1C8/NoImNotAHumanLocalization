#!/usr/bin/env python3
"""Pin and enumerate bounded coarse-source author inputs and actual consumers."""
import hashlib,importlib.util,json,re,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];FIL=ROOT/'Translations/fil';CYCLE=Path(__file__).resolve().parent;REVIEW=FIL/'independent-review-05'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def jl(p):return [json.loads(s) for s in p.read_text().splitlines()]
def require(ok,msg):
 if not ok:raise RuntimeError(msg)
def save(p,d):require(not p.exists(),'Immutable preimage exists');p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def main():
 require(sha(REVIEW/'completion-manifest.json')=='670f0c2d0932d0aba8d09abc33a642bcc52016da430f454a5c8e2f7217d4cc3b','Review05 seal differs')
 require(sha(REVIEW/'final-verdict.json')=='4146376b871a2bd51fcde27577c5763dc12d6f22e405ba3eb95a71bfec5c75f4','Verdict differs')
 for pin in load(REVIEW/'completion-manifest.json')['files']:require(sha(ROOT/pin['path'])==pin['sha256'],'Sealed review file changed')
 for pin in load(REVIEW/'input-verification.json')['pinChecks']:require(sha(ROOT/pin['path'])==pin['sha256'],'Preimage input differs: '+pin['path'])
 receipt=load(FIL/'semantic-correction-cycle-005/full-corpus-validation.json');targets={};paths={}
 G={'UI':'0cbd8a7a4f543344bb95659de87f67a5','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1'}
 for pin in receipt['authoredFiles']:
  path=ROOT/pin['path'];require(sha(path)==pin['sha256'],'Authored preimage changed')
  doc=load(path)
  for entry in doc['entries']:
   sid=entry['stableId'] if path.name=='static-text-draft.json' else f"string:{G[doc['collection']]}:{entry['id']}"
   require(sid not in targets,'Duplicate ID');targets[sid]=entry['target'];paths[sid]=pin['path']
 inv=jl(ROOT/'Source/localization-inventory-v3/strings.jsonl');source={r['stableId']:r for r in inv if r['stableId'] in targets}
 source.update({r['stableId']:r for r in jl(ROOT/'Source/localization-inventory-v3/static-text.jsonl') if r['stableId'] in targets})
 order=[r['stableId'] for col in ['UI','ChecksDialogs','Dialogs'] for r in inv if r['collection']==col and r['stableId'] in targets]+[e['stableId'] for e in load(FIL/'static-text-draft.json')['entries']]
 require(len(order)==len(targets)==16538,'Scope differs');rank={s:i+1 for i,s in enumerate(order)}
 work=load(REVIEW/'coarse-source-dependencies.json');selected=[s for s in order if re.search(work['predicate'],source[s]['source'])]
 require(set(selected)=={r['stableId'] for r in work['rows']} and len(selected)==125,'Canonical candidate enumeration differs')
 decoder=FIL/'independent-review-04/bytecode_decoder.py';spec=importlib.util.spec_from_file_location('fil_source_decoder',decoder);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 by_key={r['key']:r for r in source.values() if r.get('key') is not None};consumer_by_id={}
 for name,node in m.actual.items():
  for ins in node['instructions']:
   if ins['op'] not in ['RunLine','AddOption']:continue
   row=by_key.get(ins['operands'][0])
   if row is not None:
    require(name in row.get('nodeNames',[]),'Consumer mapping differs');consumer_by_id.setdefault(row['stableId'],[]).append(dict(node=name,instruction=ins['index'],opcode=ins['op'],operands=ins['operands']))
 rows=[];contexts={};context_ids=set()
 for sid in selected:
  s=source[sid];existing=next(r for r in work['rows'] if r['stableId']==sid);cons=consumer_by_id.get(sid,[])
  require(cons==existing['compiledConsumers'] and s['source']==existing['source'] and hashlib.sha256(targets[sid].encode()).hexdigest()==existing['targetSha256'],'Worklist current source/target/topology differs')
  windows=[]
  for binding in cons:
   name=binding['node'];idx=binding['instruction'];raw=m.actual[name]
   # Full control topology pinned; visible context bounded to nearest2 text instructions on either side.
   text_idx=[i['index'] for i in raw['instructions'] if i['op'] in ['RunLine','AddOption']];position=text_idx.index(idx);chosen=text_idx[max(0,position-2):position+3]
   start=min(chosen);end=max(chosen)
   window=[]
   for i in raw['instructions'][start:end+1]:
    a=dict(i);r=by_key.get(i['operands'][0]) if i['op'] in ['RunLine','AddOption'] else None
    a.update(sourceStableId=r['stableId'] if r else None,source=r['source'] if r else None,target=targets[r['stableId']] if r else None)
    if r:context_ids.add(r['stableId'])
    window.append(a)
   windows.append(dict(node=name,consumerInstruction=idx,windowInstructions=window))
   contexts[name]=raw
  rows.append(dict(acceptedOrdinal=rank[sid],stableId=sid,collection=s.get('collection','static'),key=s.get('key'),nodeNames=s.get('nodeNames',[]),source=s['source'],sourceSha256=hashlib.sha256(s['source'].encode()).hexdigest(),target=targets[sid],targetSha256=hashlib.sha256(targets[sid].encode()).hexdigest(),authoredPath=paths[sid],authoredSha256=sha(ROOT/paths[sid]),compiledConsumers=cons,boundedWindows=windows))
 save(CYCLE/'bounded-author-inputs.json',{'candidatePredicate':work['predicate'],'candidateUnits':125,'candidateSemanticCredit':0,'compiledConsumerSites':sum(len(r['compiledConsumers']) for r in rows),'noConsumerUnits':[r['stableId'] for r in rows if not r['compiledConsumers']],'rows':rows})
 save(CYCLE/'actual-consumer-topology.json',{'compiledProgramSha256':hashlib.sha256(m.raw).hexdigest(),'decoderPath':str(decoder.relative_to(ROOT)),'decoderSha256':sha(decoder),'nodes':contexts,'boundedContextStableIds':[s for s in order if s in context_ids],'contextRule':'nearest2 accepted text-producing instructions on either side in actual compiled node; full control topology kept separately; no fabricated consumer for unbound accepted text'})
 save(CYCLE/'preimage-pins.json',{'review05CompletionManifestSha256':sha(REVIEW/'completion-manifest.json'),'review05VerdictSha256':sha(REVIEW/'final-verdict.json'),'review05FilesSha256':{Path(r['path']).name:r['sha256'] for r in load(REVIEW/'completion-manifest.json')['files']},'verifiedInputPaths':1157,'sourceAndGlossaryFingerprints':load(FIL/'semantic-correction-cycle-005/plan.json')['sourceAndGlossaryFingerprints'],'preserveExactManifestSha256':sha(ROOT/'Source/preserve-exactly-v4.json'),'firstPassProgressSha256':sha(FIL/'semantic-review-progress.json'),'previousClosureSha256':sha(FIL/'semantic-correction-cycle-005/closure.json'),'previousPairedSha256':sha(FIL/'semantic-correction-cycle-005/closure-paired.jsonl'),'authoredFiles':receipt['authoredFiles'],'beforeProgressSha256':sha(FIL/'progress.json'),'preparedFilesSha256':{n:sha(CYCLE/n) for n in ['bounded-author-inputs.json','actual-consumer-topology.json']}})
 (CYCLE/'before-progress.json').write_bytes((FIL/'progress.json').read_bytes())
 print(json.dumps({'candidates':125,'consumerSites':122,'nodes':len(contexts),'boundedContextIds':len(context_ids)}))
if __name__=='__main__':main()
