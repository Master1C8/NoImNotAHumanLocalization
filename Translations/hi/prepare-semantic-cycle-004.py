#!/usr/bin/env python3
"""Preflight the one objective cycle004 correction and 22-use mycelium repair."""
import hashlib, importlib.util, json, pathlib, re, sys

ROOT=pathlib.Path(__file__).resolve().parents[2]
HI=ROOT/'Translations/hi'
RV=HI/'independent-review-03'
ADJ=HI/'semantic-cycle-004-adjudication.json'
PREF=HI/'semantic-cycle-004-preflight.json'
PATTERN=r'(?i)\bмицели(?:й|я|ю|и|ем)\b'

def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def hs(text):return hashlib.sha256(text.encode()).hexdigest()
def read(path):return json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
def dump(obj):return json.dumps(obj,ensure_ascii=False,indent=2)+'\n'
def lines(path):return [json.loads(x) for x in pathlib.Path(path).read_text().splitlines()]

def main():
 assert not ADJ.exists() and not PREF.exists()
 pins=read(RV/'final-unchanged-input-pins.json')
 assert len(pins['pins'])==705 and len(pins['additionalVerifiedInputs'])==58
 for group in ('pins','additionalVerifiedInputs'):
  assert all(sha(ROOT/name)==digest for name,digest in pins[group].items()),group
 manifest=read(RV/'final-artifact-manifest.json')
 assert len(manifest['artifacts'])==26
 assert all(sha(ROOT/row['path'])==row['sha256'] for row in manifest['artifacts'])
 findings=read(RV/'consolidated-final-full-unit-findings.json')
 assert sha(RV/'consolidated-final-full-unit-findings.json')=='f3723bc029d72210f530d4928193e5d5fdd3ea8741bd96be68b7f6ff5c01a8ba'
 assert {x['findingId'] for x in findings}=={'HI-R03-DEP-001','HI-R03-SEM-001'}
 f=next(x for x in findings if x['findingId']=='HI-R03-SEM-001')
 snap=read(HI/'semantic-cycle-004-pre-edit-snapshot.json')
 for name,digest in snap['files'].items():
  assert sha(ROOT/name)==digest
  assert sha(HI/'semantic-cycle-004-before-files'/pathlib.Path(name).name)==digest
 assert snap['review03FindingsSha256']==sha(RV/'consolidated-final-full-unit-findings.json')
 assert snap['previousClosureSha256']==sha(HI/'semantic-cycle-003-closure.json')
 assert snap['previousSelectorSha256']==sha(HI/'build-semantic-cycle-003-closure.py')
 source=lines(ROOT/'Source/localization-inventory-v3/strings.jsonl')
 by_sid={r['stableId']:r for r in source}
 r=by_sid[f['stableId']]
 assert r['key']==f['key'] and r['source']==f['source'] and sha(ROOT/'Source/localization-inventory-v3/strings.jsonl')==read(HI/'semantic-cycle-003-closure.json')['sourceInventorySha256']
 assert hs(r['source'])==f['sourceSha256']
 path=ROOT/'Translations/hi/dialogue-batch-080.json'
 batch=read(path)
 e=next(x for x in batch['entries'] if str(x['id'])==f['stableId'].rsplit(':',1)[1])
 assert e['target']==f['currentTarget'] and hs(e['target'])==f['currentTargetSha256']
 assert hs(f['proposedFullTarget'])==f['proposedTargetSha256']
 sys.path.insert(0,str(ROOT/'Scripts'))
 spec=importlib.util.spec_from_file_location('preserve_exact',ROOT/'Scripts/preserve_exact.py')
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 exact=read(ROOT/'Source/preserve-exactly-v4.json')
 rule=next(x for x in exact['tableRows'] if x['stableId']==f['stableId'])
 mod.check_value(rule,f['proposedFullTarget'])
 assert r['source']=='И чем больше грибы...' and f['currentTarget']=='और मशरूम जितने ज़्यादा...' and f['proposedFullTarget']=='और मशरूम जितने बड़े...'
 actual=read(RV/'mycelium-inflection-closure-finding-evidence.json')
 node=actual['actualCompiledNodes']['Mushroom_end_2']
 assert [x['strings'][0] for x in node if x['opcode']==2]==['line:Mushroom_end_2_0bbb282','line:Mushroom_end_2_0f27bf6','line:Mushroom_end_2_039b8e9','line:Mushroom_end_2_02a5ab8','line:Mushroom_end_2_0699a5b']
 hits=[row for row in source if row['stableId'].startswith('string:444ff14f') and re.search(PATTERN,row['source'])]
 family=actual['completeSourceFamily']
 assert len(hits)==len(family)==22 and {row['stableId'] for row in hits}=={row['stableId'] for row in family}
 prev=read(HI/'semantic-cycle-003-closure.json')
 prev_ids={row['stableId'] for row in prev['reviewRows']}
 missing={row['stableId'] for row in family if not row['inCycle003Closure']}
 assert len(missing)==6 and missing=={row['stableId'] for row in hits if row['stableId'] not in prev_ids}
 supplemental=lines(RV/'outside-delta-six-independent-decisions.jsonl')
 assert {row['stableId'] for row in supplemental}==missing
 for row in supplemental:
  assert row['sourceSha256']==hs(by_sid[row['stableId']]['source'])
  assert row['glossarySha256']==sha(ROOT/'Documentation/glossary-translations/hi/layer.json')
  assert row['compiledBindingSha256']==sha(ROOT/'Source/glossary-corpus-v2/runtime-bindings.json')
  assert row['fullRussianAndCurrentHindiRead'] is True and row['findingIds']==['HI-R03-DEP-001']
  assert row['result'].startswith('no-objective-wording-finding')
 adj={'schemaVersion':1,'locale':'hi','gameVersion':'1.3.19','status':'complete one-unit author adjudication; no authored edit',
      'sourceInventorySha256':sha(ROOT/'Source/localization-inventory-v3/strings.jsonl'),
      'staticInventorySha256':sha(ROOT/'Source/localization-inventory-v3/static-text.jsonl'),
      'glossaryLayerSha256':sha(ROOT/'Documentation/glossary-translations/hi/layer.json'),
      'compiledRuntimeBindingsSha256':sha(ROOT/'Source/glossary-corpus-v2/runtime-bindings.json'),
      'preserveExactManifestSha256':sha(ROOT/'Source/preserve-exactly-v4.json'),
      'review03FinalReportSha256':sha(RV/'final-report.md'),
      'review03FinalFindingsSha256':sha(RV/'consolidated-final-full-unit-findings.json'),
      'review03FinalManifestSha256':sha(RV/'final-artifact-manifest.json'),
      'review03FinalCoverageSha256':sha(RV/'final-coverage-and-regression-proof.json'),
      'previousClosureSha256':sha(HI/'semantic-cycle-003-closure.json'),
      'previousSelectorSha256':sha(HI/'build-semantic-cycle-003-closure.py'),
      'preEditSnapshotSha256':sha(HI/'semantic-cycle-004-pre-edit-snapshot.json'),
      'myceliumSourcePattern':PATTERN,'myceliumFamilyCount':22,
      'myceliumFamilyIds':[row['stableId'] for row in source if row in hits],
      'sixSupplementalCleanIds':[row['stableId'] for row in supplemental],
      'supplementalIndependentEvidenceSha256':sha(RV/'outside-delta-six-independent-decisions.jsonl'),
      'item':{'stableId':f['stableId'],'key':f['key'],'source':r['source'],'sourceSha256':hs(r['source']),
              'authoredPath':'Translations/hi/dialogue-batch-080.json','before':e['target'],'beforeSha256':hs(e['target']),
              'acceptedFullTarget':f['proposedFullTarget'],'acceptedFullTargetSha256':hs(f['proposedFullTarget']),
              'reason':f['reason'],'findingId':f['findingId'],'compiledNode':'Mushroom_end_2','compiledInstructionIndex':0},
      'selectorFinding':'Cover all 22 actual accepted Russian inflection forms, source-ID selection only; six supplemental units are unchanged Hindi and have exact independent clean reads.'}
 pre={'schemaVersion':1,'locale':'hi','status':'complete one-unit preflight passed before authored edit',
      'adjudicationSha256':hs(dump(adj)),'oldAuthoredFileSha256':sha(path),
      'oldHistoricalSidecarSha256':sha(path.with_suffix('.validation.json')),
      'protectedSyntax':'passed with pinned preserve-exact grammar; ASCII ellipsis preserved',
      'semanticDecision':'Russian nominative plural грибы means larger mushrooms, not more mushrooms; compiled growth/malice/cap sequence supports बड़े.',
      'assembledDynamicConsumer':'none; no placeholders or runtime substitution in this unit',
      'sourceAndCurrentHashesMatch':True,'myceliumInflectedUses':22,'sixSupplementalCleanUses':6,
      'derivedInputs':'static phrase map, credits map and three common-option recipes unchanged'}
 ADJ.write_text(dump(adj),encoding='utf-8');PREF.write_text(dump(pre),encoding='utf-8')
 print('preflighted one full-unit correction; 22 mycelium source uses, six clean supplemental')

if __name__=='__main__':main()
