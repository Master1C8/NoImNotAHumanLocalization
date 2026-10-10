#!/usr/bin/env python3
"""Prepare the two bounded concept families from current canonical inputs."""
import hashlib,importlib.util,json,re,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];F=ROOT/'Translations/fil';C=Path(__file__).resolve().parent;R=F/'independent-review-06'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def th(s):return hashlib.sha256(s.encode()).hexdigest()
def load(p):return json.loads(p.read_text())
def put(n,d):
 p=C/n;assert not p.exists(),n;p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def main():
 chain=load(C/'prior-author-chain.json');assert chain['targetOnlyCorrectionEvents']==143 and sha(ROOT/chain['verifierPath'])==chain['verifierSha256']
 manifest=load(R/'completion-manifest.json')
 for pin in manifest['files']+manifest['currentInputPins']:assert sha(ROOT/pin['path'])==pin['sha256'],pin['path']
 G={'UI':'0cbd8a7a4f543344bb95659de87f67a5','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1'};targets={};paths={}
 for pin in chain['currentAuthoredFiles']:
  p=ROOT/pin['path'];assert sha(p)==pin['sha256'];doc=load(p)
  for e in doc['entries']:
   sid=e['stableId'] if p.name=='static-text-draft.json' else f"string:{G[doc['collection']]}:{e['id']}";assert sid not in targets;targets[sid]=e['target'];paths[sid]=pin['path']
 inv=[json.loads(s) for s in (ROOT/'Source/localization-inventory-v3/strings.jsonl').read_text().splitlines()];source={r['stableId']:r for r in inv if r['stableId'] in targets};source.update({r['stableId']:r for r in (json.loads(s) for s in (ROOT/'Source/localization-inventory-v3/static-text.jsonl').read_text().splitlines()) if r['stableId'] in targets})
 order=[r['stableId'] for col in ['UI','ChecksDialogs','Dialogs'] for r in inv if r['collection']==col and r['stableId'] in targets]+[e['stableId'] for e in load(F/'static-text-draft.json')['entries']];assert len(order)==len(source)==16538;rank={s:i+1 for i,s in enumerate(order)}
 patterns={'exclusive-underground-group':r'(?i)^Miner:(?=.*\b(?:мы|нас|нам|нами|наш(?:а|е|и|его|ему|им|ей|их|ими|у|ем)?)\b)(?=.*\b(?:тут|здесь|внизу|подзем[а-яё]*|подвал[а-яё]*)\b)','household-work-totality':r'(?i)(?:\bвс[её]\b.{0,24}\bпо дому\b|\bпо дому\b.{0,24}\bвс[её]\b)'}
 families={n:[s for s in order if re.search(p,source[s]['source'])] for n,p in patterns.items()};assert list(map(len,families.values()))==[9,1],{n:len(v) for n,v in families.items()}
 decoder=F/'independent-review-04/bytecode_decoder.py';sp=importlib.util.spec_from_file_location('cycle007_decoder',decoder);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);bykey={r['key']:r for r in source.values() if r.get('key')};cons={};nodes={};windows=[];contexts=set();selected=set().union(*map(set,families.values()))
 for name,node in m.actual.items():
  textidx=[i['index'] for i in node['instructions'] if i['op'] in ['RunLine','AddOption']]
  for i in node['instructions']:
   r=bykey.get(i['operands'][0]) if i['op'] in ['RunLine','AddOption'] else None
   if not r:continue
   sid=r['stableId'];cons.setdefault(sid,[]).append(dict(node=name,instruction=i['index'],opcode=i['op'],operands=i['operands']))
   if sid not in selected:continue
   k=textidx.index(i['index']);chosen=textidx[max(0,k-2):k+3];nodes[name]=node;window=[]
   for x in node['instructions'][min(chosen):max(chosen)+1]:
    sr=bykey.get(x['operands'][0]) if x['op'] in ['RunLine','AddOption'] else None
    if sr:contexts.add(sr['stableId'])
    window.append(dict(x,sourceStableId=sr['stableId'] if sr else None,source=sr['source'] if sr else None,target=targets[sr['stableId']] if sr else None))
   windows.append(dict(stableId=sid,node=name,consumerInstruction=i['index'],windowInstructions=window))
 rows=[]
 for sid in order:
  if sid not in selected:continue
  s=source[sid];ci=dict(compiledProgramSha256=hashlib.sha256(m.raw).hexdigest(),key=s.get('key'),nodeNames=s.get('nodeNames',[]),sites=cons.get(sid,[]))
  rows.append(dict(acceptedOrdinal=rank[sid],stableId=sid,collection=s.get('collection','static'),key=s.get('key'),nodeNames=s.get('nodeNames',[]),source=s['source'],sourceSha256=th(s['source']),target=targets[sid],targetSha256=th(targets[sid]),authoredPath=paths[sid],consumerIdentity=ci,consumerIdentitySha256=th(json.dumps(ci,sort_keys=True,ensure_ascii=False,separators=(',',':'))),conceptSelectors=[n for n,v in families.items() if sid in v]))
 put('bounded-author-inputs.json',dict(sourceRegex=patterns,families=families,rows=rows,compiledProgramSha256=hashlib.sha256(m.raw).hexdigest(),decoderPath=str(decoder.relative_to(ROOT)),decoderSha256=sha(decoder),nodes=nodes,windows=windows,boundedContextStableIds=[s for s in order if s in contexts],boundary='Only corrected units and actual underground-group/household-totality dependencies; nearest2 actual text instructions; no full semantic pass.'))
 put('preimage-pins.json',dict(review06CompletionManifestSha256=sha(R/'completion-manifest.json'),review06VerdictSha256=sha(R/'final-verdict.json'),review06FilesSha256={Path(x['path']).name:x['sha256'] for x in manifest['files']},verifiedReview06CurrentInputPins=len(manifest['currentInputPins']),cycle006CompletionManifestSha256=sha(F/'semantic-correction-cycle-006/completion-manifest.json'),previousClosureSha256=sha(F/'semantic-correction-cycle-006/closure.json'),previousPairedSha256=sha(F/'semantic-correction-cycle-006/closure-paired.jsonl'),sourceAndGlossaryFingerprints=load(F/'semantic-correction-cycle-006/plan.json')['sourceAndGlossaryFingerprints'],preserveExactManifestSha256=sha(ROOT/'Source/preserve-exactly-v4.json'),firstPassProgressSha256=sha(F/'semantic-review-progress.json'),authoredFiles=chain['currentAuthoredFiles'],beforeProgressSha256=sha(F/'progress.json'),boundedInputsSha256=sha(C/'bounded-author-inputs.json'),priorAuthorChainSha256=sha(C/'prior-author-chain.json'),copiedHelpers={n:dict(originalPath='Translations/fil/semantic-correction-cycle-006/'+n,sha256=sha(C/n)) for n in ['json_target_spans.py','source_predicates.py','validate_affected.py']}))
 (C/'before-progress.json').write_bytes((F/'progress.json').read_bytes())
 print(json.dumps({'concepts':{n:len(v) for n,v in families.items()},'nodes':len(nodes),'contexts':len(contexts)}))
if __name__=='__main__':main()
