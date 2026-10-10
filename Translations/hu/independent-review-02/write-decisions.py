#!/usr/bin/env python3
"""Serialize this reviewer's completed full-unit decisions; never edit targets."""
import collections, hashlib, itertools, json, re, runpy, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).resolve().parent
CUR=ROOT/'Translations/hu/semantic-correction-cycle-03/evidence'; OLD=ROOT/'Translations/hu/independent-review-01'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
rows=lambda p:[json.loads(x) for x in p.read_text().splitlines()]
def write(name,value,jsonl=False):
 p=OUT/name;assert not p.exists(),p
 p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in value) if jsonl else json.dumps(value,ensure_ascii=False,indent=2)+'\n')
recipe=runpy.run_path(str(CUR.parent/'build-closure.py'))
plan,spec,prior,verdict,preserve,order,rules,source,after,ownership,hashes,changed,remedial=recipe['corpus']()
sys.path.insert(0,str(ROOT/'Scripts'))
import preserve_exact
for key in order:preserve_exact.check_value(rules[key],after[key])
write('preserve-exact.json',{'checkedRows':len(order),'result':'passed','problems':0,'manifestSha256':sha(ROOT/'Source/preserve-exactly-v4.json'),'validatorSha256':sha(ROOT/'Scripts/preserve_exact.py'),'authoredHashesSha256':sha(OUT/'input-verification.json'),'scope':'All accepted authored values: grammar, protected prefixes, exact literals, numeric/slot/tag/linebreak contracts. Static validation does not exercise game insertion or rendering.'})
delta=rows(CUR/'next-review-delta.jsonl');context={r['stableId']:r for r in load(OUT/'compiled-delta-context.json')['rows']}
gap=load(OLD/'catalog-risk-surface-gaps.json')
previous=set((ROOT/'Translations/hu/semantic-correction-cycle-01/evidence/closure-ids.txt').read_text().splitlines())
for group,data in gap.items():
 if not isinstance(data,dict) or 'regex' not in data:continue
 found={k for k in order if re.search(data['regex'],source[k]['source'],re.I)}-previous
 assert found==set(data['missingFromClosure']),group
child_indices={12,27,56,57,63,64,65,66,67,68,69,100,152,153,154,157,214,229,230,231,244,259,260}
catalog_map={r['stableId']:r for r in remedial['rows']}
classification=[];decisions=[]
special={
20:'Fülzsír restores earwax in the metaphorical TV report; bells and comparative quantity remain.',
21:'Fülzsír restores the earwax referent without replacing the accompanying dirty-thoughts metaphor.',
33:'Lánytestvérem retains a female sibling without asserting younger birth order; uncertainty and distress remain.',
34:'Two people resemble their parents; the female sibling and her state remain, with no unsupported birth order.',
35:'These two residents worsen the female sibling’s state; participant number, condition and apprehension remain.',
36:'The resident is expected to condemn the female sibling; no unsupported younger-sister relation remains.',
45:'Compiled preceding line negates reacting to others; the Russian infinitive inherits that negation. The Hungarian explicit negative restores that scope.',
72:'Hungarian locative van is present with {0}; this source template is absent from the saved compiled program, so no active-runtime claim.',
83:'Full alternative source unit retains disgust, submission and resident slot; van repairs the locative clause. This alternate ID is absent from saved compilation.',
93:'Retain the infinitive fragment Vagy szétverni valakit: actual compiled predecessor is a negative finite promise, so the fragment inherits its scope.',
105:'Nincs melege is the natural negative possessive temperature construction; suspicion, clothes and oblique species reference remain.',
111:'Nincs melege preserves lack of heat in clothes; the explicit subsequent Vendég interpretation remains a question.',
115:'Rodnáya refers to clothing in the preceding exchange; családtag expresses its familiar/cherished relation without inventing a female relative.',
147:'Nominative feleségem supplies the subject of fütyül; possession of her own mother and mocking tone remain.',
162:'Common father establishes a half sibling; the denial of full siblinghood remains without changing parental relation.',
169:'Dad has not fled; remained where needed remains his requested explanation, with no reachability claim for the absent compiled ID.',
184:'Babki means money in investment-advice context; it is not a grandmother reference.',
185:'Babki means money; the self-corrected fivefold-to-tenfold return and scheme claim remain.',
212:'The first-person armpit reference and shame remain; nothing particular there avoids inventing a general claim about shame.',
227:'Retain the source branch’s why-should-I-not-shave question; it is a separate IsImposter branch from why-should-I-shave.',
234:'The immediately preceding maternal eye alternation supplies the object of one; the father chooses one eye, with no changed relative identity.',
254:'Babki in this grandmother-photo exchange does refer to the grandmother; both absent photo and deceased/absent grandmother remain.',
261:'Ear-cleaning context supports fülzsírdugó as an earwax plug; remains a possibility, not a diagnosis.',
262:'Wishlist action is Kívánságlistára; the unrelated desired-place sense is removed.',
263:'Publisher’s complete proper name CRITICAL REFLEX is retained alongside the exclamation.'}
for i,r in enumerate(delta):
 key=r['stableId'];groups=catalog_map.get(key,{}).get('catalogGroups',[])
 if i in (184,185):cls='money-homonym; retained as catalog false-positive control';reason=special[i]
 elif i in (96,189):cls='divine-judge metaphor; not a human occupation';reason='Isten retains divine judgment and the correct object; no human judicial profession is asserted.'
 elif i in child_indices:cls='childhood, child-related object, setting or plural children';reason='The complete unit preserves the child-related setting, object or plural children. It does not add a specific character age or identity.'
 else:cls='applicable personal referent or other selected semantic dependency';reason='The complete source/target unit retains its referents, agency, negation, quantity, condition and register; Hungarian grammar and approved terminology are acceptable.'
 reason=special.get(i,reason)
 if i<3:reason='Retain the standalone refrigerator UI label. It is excluded from LocalizeItem consumer candidates; its display translation remains valid.'
 elif 3<=i<=9:reason='Retain the approved consumable name and source distinction. This accepted UI key is in the actual LocalizeItem naming domain.'
 if key in catalog_map:classification.append({'stableId':key,'key':r['key'],'catalogGroups':groups,'independentClassification':cls,'semanticDecision':'retain','reason':reason,'sourceSha256':hashlib.sha256(r['source'].encode()).hexdigest(),'targetSha256':hashlib.sha256(r['after'].encode()).hexdigest(),'authorClassificationReadOnlyReference':catalog_map[key]['classification']})
 decisions.append({**r,'sourceSha256':hashlib.sha256(r['source'].encode()).hexdigest(),'targetSha256':hashlib.sha256(r['after'].encode()).hexdigest(),'fullUnitRead':True,'reader':'/root/hu_independent_review_02','decision':'retain-current-target','reason':reason,'compiledOccurrences':[{k:v for k,v in hit.items() if k!='window'} for hit in context[key]['occurrences']],'contextEvidence':'compiled-delta-context.json','contextLimit':'Saved static source program and glossary; absent compiled IDs do not imply game reachability. No runtime/layout claim.'})
assert len(classification)==196 and len(decisions)==264
write('full-unit-decisions.jsonl',decisions,True)
write('catalog-extension-decisions.json',{'reader':'/root/hu_independent_review_02','sourceRiskGapRegexSetsRecomputedExactly':True,'rows':classification,'method':'Every listed full pair was read independently. Author classifications were adjudicated only after the full pair read; they do not provide independent coverage. Nonpersonal lexical matches stay as regression controls.'})
catalog=(CUR/'mandatoryRegression-ids.txt').read_text().splitlines();prevapp={r['stableId']:r for r in load(OUT/'prior-applicability.json')['rows']}
bydelta={r['stableId']:r for r in decisions}
write('mandatory-catalog-decisions.jsonl',[{'stableId':key,'decision':'passed-static-editorial','basis':'independent-review-02/full-unit-decisions.jsonl' if key in bydelta else 'verified-independent-review-01/full-pair-read-evidence.jsonl','previousEvidenceReusable':key not in bydelta,'reader':'/root/hu_independent_review_02' if key in bydelta else '/root/hu_independent_review_01','currentTargetSha256':hashlib.sha256(after[key].encode()).hexdigest()} for key in catalog],True)
items=load(CUR/'item-name-domain.json')['entries'];names=load(CUR/'resident-name-domain.json')['entries'];runtime=load(CUR/'runtime-consumer-context.json');assemblies=rows(CUR/'assembled-consumer-context.jsonl')
expected=[];template_decisions=[]
for t in runtime['templates']:
 domain=items if t['candidateDomain']=='item-name-domain.json' else names
 pairs=(p for p in itertools.product(domain,repeat=2) if p[0]['stableId']!=p[1]['stableId']) if '{1}' in t['source'] else ((v,) for v in domain)
 count=0
 for pair in pairs:
  sr=t['source'];tr=t['target']
  for j,v in enumerate(pair):sr=sr.replace('{'+str(j)+'}',v['source']);tr=tr.replace('{'+str(j)+'}',v['target'])
  expected.append({'templateStableId':t['stableId'],'candidateStableIds':[v['stableId'] for v in pair],'sourceAssembled':sr,'targetAssembled':tr});count+=1
 template_decisions.append({'stableId':t['stableId'],'candidateDomain':t['candidateDomain'],'assemblyCount':count,'compiledOccurrence':t['compiledOccurrence'],'decision':'static-composition-valid','grammar':'Bare quoted resident labels or a quantified label are inserted as nominative noun phrases; clauses require no candidate-dependent suffix or gender inflection. Singular existential van accepts a Hungarian numeral phrase. Two-name enumeration retains conjunction and each label. Item noun labels stand alone before the unchanged offer.'})
assert expected==assemblies and len(assemblies)==3491
consumer=load(OLD/'consumer-il.json');binary=Path(consumer['assemblyPath']);assert sha(binary)==consumer['assemblySha256']
assert load(OLD/'consumer-il-expanded.json')['assemblySha256']==consumer['assemblySha256']
write('assembled-consumer-verification.json',{'assembliesChecked':3491,'eachSerializedSourceTargetAndCandidateTupleCompared':True,'sourceAssemblySha256':consumer['assemblySha256'],'sourceAssemblyCurrentFileHashMatches':True,'consumerIlSha256':sha(OLD/'consumer-il.json'),'expandedConsumerIlSha256':sha(OLD/'consumer-il-expanded.json'),'itemLabelsRead':7,'residentLabelsRead':57,'templatesRead':8,'itemBobeerActualOutput':'Sör','fridgeBobeerStandaloneOutput':'Bober Cserni','assemblySha256':sha(CUR/'assembled-consumer-context.jsonl'),'templateDecisions':template_decisions,'semanticMethod':'Read all seven actual item labels, all 57 resident labels and all eight complete templates; inspect instantiated boundaries and both singular/plural label behavior; exhaustively compare all 3491 emitted tuples to independently assembled compositions. This is compositional static review, not 3491 independent story contexts or runtime-state observations.','unverified':['DeficitConsumables configuration and actual selected enum values','Character-place configuration, current occupants and admissible pairs','Reachability of the one absent compiled template','Fonts, layout, dialogue advancement, package insertion and game execution'],'probeHistory':['An initial read of consumer-il-expanded.json expected assemblyPath and raised KeyError after the primary assembly hash successfully matched; inspected its actual schema and verified its assemblySha256 against the primary verified binary. No external request or game mutation.']})
write('objective-findings.json',{'reviewedFullDeltaUnits':264,'objectiveFindings':[],'proposedCorrections':[],'completeForAssignedDelta':True,'excluded':'Images/textures, full fresh corpus reread, runtime/visual/package verification.'})
print(json.dumps({'fullUnitDecisions':264,'catalogDecisions':len(catalog),'independentGapClassifications':196,'assembliesCompared':3491,'preserveExact':len(order),'objectiveFindings':0}))
