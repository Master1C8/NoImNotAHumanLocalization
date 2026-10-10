"""Reconcile actually-read evidence, adjudicated proposals and immutable inputs."""
import hashlib,json,re,sys,datetime
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parent))
import context_batch_v3 as c
E=c.EVIDENCE;ROOT=c.ROOT;A=ROOT/'Translations/sw/semantic-correction-cycle-01'
sha=lambda b:hashlib.sha256(b).hexdigest()
def filehash(p):return sha(p.read_bytes())
def save(n,obj):
 with (E/n).open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
def jsonl(n,rows):
 with (E/n).open('x') as f:
  for r in rows:f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
withdraw={2:'Russian Вы and Swahili polite/plural address require a locale policy and cannot be treated as an objective error here. No mandated singular address policy is in the glossary.',3:'Formal/plural address to one player can be a polite choice; no objective policy violation established.',12:'Inanimate possessors use -ake even for plural antecedents: maana yake is valid. Proposed maana yao would incorrectly impose animate plural possession.',48:'Possessive lake agrees with the possessed noun tabaka, not meno. The existing phrase is valid; explicit repetition of meno would be stylistic.',71:'Nayo is a recoverable conversational fragment in this speaker voice; expanding it to ninayo does not establish an objective semantic correction.',81:'The implicit object can be nywele in a shaving statement. Explicit makwapa would improve clarity but does not establish an objective correction.',89:'Possessive zake and agreement nazo zinakaribia follow plural siku. The draft replacement incorrectly singularized siku and is withdrawn.'}
normal={16:'Vigilante: Wewe mpuuzi! Wewe ni Mgeni, ulidhani unaweza kunidanganya?',19:'Kuniamini kuhusu nini?',54:'Unstable: Makwapa. Ya kawaida. Tu.'}
allsource=[json.loads(x) for x in (ROOT/'Source/localization-inventory-v3/strings.jsonl').read_text().splitlines()]
source_by_id={x['stableId']:x for x in allsource}
source_by_collection_number={(x['collection'],int(x['stableId'].rsplit(':',1)[1])):x for x in allsource}
assert len(source_by_collection_number)==len(allsource)
manifest=json.loads((A/'final-payload-manifest.json').read_text())
authored={};accepted=[]
for a in manifest['artifacts']:
 p=ROOT/a['path'];assert filehash(p)==a['sha256']
 d=json.loads(p.read_text())
 for entry in d['entries']:
  if 'stableId' in entry:stable=entry['stableId']
  else:
   stable=source_by_collection_number[d['collection'],entry['id']]['stableId']
  assert stable not in authored
  authored[stable]={'path':a['path'],'sha256':a['sha256'],'target':entry['target']};accepted.append(stable)
assert len(authored)==16538
static_scope=json.loads((ROOT/'Documentation/static-text-scope-v2.json').read_text())
expected={r['stableId'] for r in allsource if r['collection'] in ('Dialogs','UI')}
expected.update(r['stableId'] for r in allsource if r['collection']=='ChecksDialogs' and r['key']=='line:Esenin_Armpit_0a58dc6')
expected.update(r['stableId'] for r in static_scope['rows'] if r['source'] and (not r['localizedStringBindings'] or any(x['sourceStableId'] is None for x in r['localizedStringBindings'])))
assert len(expected)==16538 and set(authored)==expected
record_files=[E/'read-rows-01.jsonl']+sorted(E.glob('context-reviewed-*.jsonl'))+[E/'surface-reviewed-01.jsonl']
provenance={};context_provenance={}
for p in record_files:
 for line in p.read_text().splitlines():
  r=json.loads(line);i=r['closureIndexZeroBased'];row=c.closure[i]
  assert r['stableId']==row['stableId']
  assert r['sourceSha256']==sha(row['source'].encode()) and r['targetSha256']==sha(row['target'].encode())
  provenance.setdefault(i,[]).append(p.name)
  if p.name!='read-rows-01.jsonl':context_provenance.setdefault(i,[]).append(p.name)
assert set(provenance)==set(range(5211))
assert set(context_provenance)==set(range(5211))
findings=[];adjudications=[]
for p in sorted(E.glob('findings-*.json')):
 for draft in json.loads(p.read_text())['findings']:
  n=int(draft['findingId'].rsplit('-',1)[1]); f=dict(draft)
  stable=f['stableId'];s=source_by_id[stable];a=authored[stable]
  assert s['source']==f['source'] and a['target']==f['currentTarget']
  if n in withdraw:
   adjudications.append({'originEvidence':p.name,'originFindingId':f['findingId'],'stableId':stable,'closureIndexZeroBased':f.get('closureIndexZeroBased'),'decision':'withdraw; retain current target','reason':withdraw[n]});continue
  f['findingId']=f'sw-independent-{n:04d}'
  if n in normal:
   adjudications.append({'originEvidence':p.name,'originFindingId':draft['findingId'],'stableId':stable,'decision':'retain objective issue; normalize proposed full unit','oldDraftProposal':draft['proposedFullTarget'],'finalProposal':normal[n],'reason':'0016 preserves current Visitor identity and past thought using ulidhani; 0019 preserves the source open-ended trust echo and changes only the trust direction; 0054 uses standard li/ya kwapa/makwapa and preserves three spoken fragments.'})
   f['proposedFullTarget']=normal[n]
  new=f['proposedFullTarget'];old=f['currentTarget'];assert new!=old
  for pattern in [r'\{[^{}]+\}|<[^<>]+>',r'\d+',r'\r\n|\r|\n']:
   assert Counter(re.findall(pattern,new))==Counter(re.findall(pattern,old)),(f['findingId'],pattern)
  assert re.search(r'[ \t\r\n]*$',new).group()==re.search(r'[ \t\r\n]*$',old).group()
  for x in s['exactSpans']:
   if x['reason']=='Yarn speaker/service prefix':assert new.startswith(x['value'])
  f.update({'originEvidence':p.name,'originFindingId':draft['findingId'],'key':s['key'],'collection':s['collection'],'authoredPath':a['path'],'authoredSha256':a['sha256'],'sourceSha256':sha(f['source'].encode()),'currentTargetSha256':sha(old.encode()),'proposedTargetSha256':sha(new.encode()),'swGlossarySha256':filehash(ROOT/'Documentation/glossary-translations/sw/layer.json'),'compiledConsumers':c.consumers.get(s['key'],[]),'sourceNodeNames':s.get('nodeNames',[]),'adjudication':'objective correction proposed after complete assigned closure reading','replacementChecks':'full unit independently reread against source and containing node; speaker, participants, chronology, certainty, facts and source syntax checked; protected token, digit, newline and trailing-space equality passed; no new plot facts or earlier revelations introduced','scope':'proposal only; authored inputs unchanged'})
  if n==19:f['objectiveReason']='Theorist asks whether he can trust the player. The player echo must ask about being trusted, not state that the player will trust Theorist. Kuniamini preserves the open-ended echo without assuming a physical handover.'
  if n==32:f['objectiveReason']='Galaxies are inanimate plural possessors; use -ake with class-10 kanuni, producing zake. Zao denotes animate plural possessors. See lexical-evidence-02.json.'
  if n==83:f['clockFactCheck']='Russian nine in the morning is Swahili saa tatu asubuhi, verified in University of Georgia primary teaching material; four-hour duration unchanged. Clock number words encode the same hour rather than being copied literally.'
  findings.append(f)
assert len({f['stableId'] for f in findings})==len(findings)
findings.sort(key=lambda f:(f.get('closureIndexZeroBased') is None,f.get('closureIndexZeroBased',0) or 0,f['stableId']))
by_stable={f['stableId']:f for f in findings}
save('final-adjudication-01.json',{'reviewer':'/root/sw_independent_review','draftUnitProposals':len(findings)+sum(x['decision'].startswith('withdraw') for x in adjudications),'retainedObjectiveGroups':len({f['findingId'] for f in findings}),'retainedObjectiveUnits':len(findings),'decisions':adjudications,'lexicalEvidence':['lexical-evidence-01.json','lexical-evidence-02.json']})
save('final-findings-01.json',{'schemaVersion':1,'reviewer':'/root/sw_independent_review','independentOfAuthor':True,'completeAssignedClosureReading':True,'closureRowsActuallyRead':5211,'verdict':'changes requested; no editorial acceptance','findingGroups':len({f['findingId'] for f in findings}),'findingUnits':len(findings),'closureFindingUnits':sum(f.get('closureIndexZeroBased') is not None for f in findings),'supplementaryContextFindingUnits':sum(f.get('closureIndexZeroBased') is None for f in findings),'findings':findings})
rows=[]
text_scope=json.loads((ROOT/'Documentation/text-source-scope-v7.json').read_text())
for i,r in enumerate(c.closure):
 consumers=c.consumers.get(r['key'],[]) if r['collection']=='Dialogs' else []
 if r['collection']=='Dialogs':
  context=('Containing compiled nodes: full ordered source-target dialogue, option order/destinations, semantic function calls/state/conditions read. Internal visited-counter plumbing omitted by v5 presentation.' if consumers else 'Supplemental accepted source-table row read; no containing current compiled consumer or source node metadata exists. No active reachability claim. Repetition/referent context evaluated using available source catalog and the containing correction closure.')
 elif r['collection']=='ChecksDialogs':context='Accepted ChecksDialogs source text read with serialized references to Esenin assetPathId 2637 and Rocker 2668, keyId 21377524158749; matchingCurrentDialogId 110504451968671746. Source acknowledgment and target retained; no runtime use claim.'
 else:context='UI/static source-target text and surface-reviewed-01.jsonl consumer metadata read; managed UI consumers and actual static ancestry/initial-state/bindings inspected. Credits 204 paired lines reused from the initial completed comparison.'
 f=by_stable.get(r['stableId'])
 rows.append({'closureIndexZeroBased':i,'sourceIndex':r['sourceIndex'],'stableId':r['stableId'],'key':r['key'],'collection':r['collection'],'authoredPath':r['authoredPath'],'authoredSha256':authored[r['stableId']]['sha256'],'sourceSha256':sha(r['source'].encode()),'targetSha256':sha(r['target'].encode()),'actuallyRead':True,'readEvidence':provenance[i],'contextEvidence':context_provenance[i],'compiledConsumers':consumers,'sourceNodeNames':r.get('nodeNames',[]),'contextEvaluated':context,'decision':('objective correction proposed: '+f['findingId']) if f else 'retain; no objective issue found in compared text and available context','findingId':f['findingId'] if f else None,'consumerReachability':'not claimed','checksApplied':['factual meaning','voice','address and participant number','concept referents','repetitions','dynamic binding and branch order where present','spoiler timing','exact syntax'],'glossarySha256':filehash(ROOT/'Documentation/glossary-translations/sw/layer.json')})
jsonl('final-reviewed-rows-01.jsonl',rows)
cat=json.loads((A/'mandatory-regression-catalog-v2.json').read_text());categories=[];members={}
for name,ref in cat['categories'].items():
 p=ROOT/ref['path'];assert filehash(p)==ref['sha256'];d=json.loads(p.read_text());ids=d['stableIds'];assert len(ids)==ref['count']==len(set(ids))
 for stable in ids:members.setdefault(stable,[]).append(name)
 categories.append({'category':name,**ref,'actuallyReadCount':len(ids),'objectiveFindingUnits':sum(x in by_stable for x in ids),'semanticResult':'changes requested' if any(x in by_stable for x in ids) else 'no objective issue found in compared text and available context'})
assert len(members)==1592 and set(members)<=set(r['stableId'] for r in rows)
jsonl('mandatory-regression-reviewed-01.jsonl',[{**r,'regressionCategories':members[r['stableId']]} for r in rows if r['stableId'] in members])
save('mandatory-regression-result-01.json',{'catalogPath':str((A/'mandatory-regression-catalog-v2.json').relative_to(ROOT)),'catalogSha256':filehash(A/'mandatory-regression-catalog-v2.json'),'uniqueIdsActuallyRead':1592,'missingIds':[],'categories':categories,'fullStructuralGateEvidence':'structural-recheck-01.json','runtime':'not-run-per-owner','excluded':'images/textures; RTL not applicable to Swahili Latin','semanticAcceptance':'changes requested; all catalog IDs compared, not accepted from subset or validator'})
# Independently reconcile exact authored phrase-map expansions, including remaining-only maps.
map_results=[];earlier_source=set()
for p in sorted((ROOT/'Translations/sw').glob('dialogue-repeat-map-*.json')):
 d=json.loads(p.read_text());phrases=[]
 for phrase in d['phrases']:
  matches=[s for s in allsource if s['collection']=='Dialogs' and s['source']==phrase['source'] and (not d.get('remainingOnly') or s['stableId'] not in earlier_source)]
  assert len(matches)==phrase['expectedRows'],(p.name,phrase['source'],len(matches),phrase['expectedRows'])
  assert all(authored[s['stableId']]['target']==phrase['target'] for s in matches)
  earlier_source.update(s['stableId'] for s in matches)
  phrases.append({'source':phrase['source'],'expectedRows':phrase['expectedRows'],'matchedRows':len(matches),'targetSha256':sha(phrase['target'].encode())})
 map_results.append({'path':str(p.relative_to(ROOT)),'sha256':filehash(p),'remainingOnly':d.get('remainingOnly',False),'phrases':phrases})
save('accepted-ids-and-expansions-01.json',{'acceptedSourceDecisionSha256':filehash(ROOT/'Documentation/text-source-acceptance-v1.json'),'manifestSha256':filehash(A/'final-payload-manifest.json'),'uniqueAuthoredIds':16538,'exactAcceptedIdEquality':True,'duplicateIds':[],'missingIds':[],'extraIds':[],'phraseMapExpansions':map_results,'creditsRoleMap':'Canonical static validator independently regenerated the full target from the pinned role map in structural-recheck-01.json.'})
# Final input rehash, including contextual inputs and exact executing validator versions.
old=json.loads((E/'input-verification-03.json').read_text())['checkedFiles'];checks=[]
for r in old:
 p=Path(r['path']);p=p if p.is_absolute() else ROOT/p
 actual=filehash(p);assert actual==r['sha256'],str(p)
 checks.append({'path':r['path'],'sha256':actual})
extra=['Documentation/static-text-scope-v2.json','Documentation/text-source-scope-v7.json','scripts/validate_game_text_batch.py','scripts/validate_static_text_draft.py','scripts/probe_assets.py']
for n in extra:
 if n not in {x['path'] for x in checks}:checks.append({'path':n,'sha256':filehash(ROOT/n),'addedContextOrMechanismPin':True})
save('input-verification-04.json',{'reviewer':'/root/sw_independent_review','verifiedAtUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'allPrevious414PinsUnchanged':True,'checkedFileCount':len(checks),'checkedFiles':checks,'authoredMutation':'none','runtime':'not-run-per-owner'})
print(json.dumps({'closureActuallyRead':len(rows),'mandatoryActuallyRead':len(members),'objectiveGroups':len({f['findingId'] for f in findings}),'objectiveUnits':len(findings),'closureFindingUnits':sum(f.get('closureIndexZeroBased') is not None for f in findings),'supplementaryFindingUnits':sum(f.get('closureIndexZeroBased') is None for f in findings),'withdrawnUnits':sum(x['decision'].startswith('withdraw') for x in adjudications),'pins':len(checks),'missing':[]}))
