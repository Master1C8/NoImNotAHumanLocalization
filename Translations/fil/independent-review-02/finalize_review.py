"""Persist independent model-authored findings and exact applicability evidence."""
import datetime,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent; C=ROOT/'Translations/fil/semantic-correction-cycle-002';P=ROOT/'Translations/fil/independent-review-01'
sys.path.insert(0,str(ROOT/'Scripts'))
from preserve_exact import check_value
def load(p):return json.loads(p.read_text())
def jl(p):return [json.loads(x) for x in p.read_text().splitlines()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def th(s):return hashlib.sha256(s.encode()).hexdigest()
def write(name,d):
 p=OUT/name;assert not p.exists(),p;p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def writejl(name,rows):
 p=OUT/name;assert not p.exists(),p;p.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in rows))
v=load(OUT/'input-verification.json');cl=load(C/'closure.json');pl=load(C/'plan.json');a=load(C/'after.json');gate=load(C/'full-structural-validation.json')
for p in v['pinChecks']:assert sha(ROOT/p['path'])==p['expected']
for k,path in [('commonOptionsSha256','common-options-001.authored.json'),('staticPhrasesSha256','static-phrases-001.authored.json'),('creditsRoleMapSha256','credits-role-map.authored.json'),('staticDraftSha256','static-text-draft.json')]:
 # Resolve exact canonical file names from actual gate inputs when names differ.
 candidates=[p for p in (ROOT/'Translations/fil').glob('*.json') if sha(p)==a['derivedArtifacts'][k]]
 assert len(candidates)==1,(k,candidates)
 v['pinChecks'].append(dict(path=str(candidates[0].relative_to(ROOT)),expected=a['derivedArtifacts'][k],actual=sha(candidates[0])))
cur=jl(C/'closure-paired.jsonl');cm={r['stableId']:r for r in cur};prior=jl(ROOT/'Translations/fil/semantic-correction-cycle-001.paired.jsonl');pm={r['stableId']:r for r in prior};olddec={r['stableId']:r for r in jl(P/'decisions.jsonl')};fresh=jl(C/'pending-delta-paired.jsonl');freshids={r['stableId'] for r in fresh};sup={r['stableId'] for r in pl['verifiedSupplementalIndependentReads']};delta=freshids|sup
rules={r['stableId']:r for r in load(ROOT/'Source/preserve-exactly-v4.json')['tableRows']}
proposals={
 943:dict(findingId='fil-independent-02-001',replacement='Window: Anuman ang mangyari, tiyak na sa iyo na iyon mangyayari ngayon.',reason='The conditional/subjunctive Что бы ни случилось describes any future calamity now falling on the player. Nangyari is completed aspect (whatever already happened), and rin makes the prediction a repetition of that past event. In window_12_1, the surrounding source says all nearby houses are destroyed and no one else remains to absorb the next attack. Preserve the open future contingency with mangyari.',boundary='window_12_1 instruction3, after instructions0–2 establish the only surviving house and no other recipient of an attack.'),
 10326:dict(findingId='fil-independent-02-002',replacement='Esenin: Lahat nagsasabing nilulutas nila ang mga problema, pero sa totoo, wala namang nangyayari, putangina.',reason='The source вообще нихера is a vulgar negative quantifier: absolutely nothing happens. The target attaches putangina to kahit anong as the noun for a thing/event, producing wala namang nangyayaring kahit anong putangina instead of an intelligible negative statement plus profanity. Separate the curse from the quantified event while retaining everyone saying they solve problems and the actual absence of progress.',boundary='Esenin_Asking_3_1 instruction5, between the profane complaint at4 and predicted general catastrophe at7–9.')}
findings=[]
for ordinal,p in proposals.items():
 r=next(x for x in fresh if x['acceptedOrdinal']==ordinal);check_value(rules[r['stableId']],p['replacement']);findings.append(dict(r,**p,proposedFullTarget=p['replacement'],proposedTargetSha256=th(p['replacement']),proposalProtectedSyntax='passed check_value on pinned v4 rule; no authored application',contextPath='Translations/fil/independent-review-02/additional-compiled-context.json'))
write('findings.json',dict(schemaVersion=1,status='two objective bounded full-unit corrections required; all266 fresh pairs read',reviewer='/root/fil_independent_review_02',locale='fil',sourceLocale='ru',gameVersion='1.3.19',findings=findings,acceptedCycle002Corrections=19,withdrawnPriorCandidatesStillWithdrawn=[197,249,4044,7222,7989]))
byfinding={r['stableId']:r for r in findings};dec=[]
for r in fresh:
 f=byfinding.get(r['stableId']);dec.append(dict(r,reviewer='/root/fil_independent_review_02',evidenceMode='fresh independent full Russian/Filipino unit read',decision='correction-required' if f else 'accepted-as-is-for-this-delta',findingId=f['findingId'] if f else None,reason=f['reason'] if f else 'Full-unit meaning, facts, agency, timing, referent, voice and syntax retained under approved glossary and applicable source scene; no objective replacement required.',proposedFullTarget=f['replacement'] if f else None))
writejl('fresh-decisions.jsonl',dec)
supdec=[]
for r in cur:
 if r['stableId'] in sup:supdec.append(dict(r,decision='prior supplemental independent decision applicable',reviewer='/root/fil_independent_review_02',evidenceMode='independent exact source/target/key/node verification and reconsideration of20 complete supplemental pairs',priorReviewer='/root/fil_independent_review_01',priorEvidence='Translations/fil/independent-review-01/recipe-findings.json',reason='Complete pair remains valid; exact evidence unchanged; neutral pronouns preserve established kinship/life-stage roles.'))
writejl('supplemental-applicability-decisions.jsonl',supdec)
ledger=[]
for r in cur:
 sid=r['stableId'];f=byfinding.get(sid);mode='fresh-independent-read' if sid in freshids else 'exact-supplemental-independent-reuse' if sid in sup else 'exact-prior-independent-reuse'
 ledger.append(dict(stableId=sid,acceptedOrdinal=r['acceptedOrdinal'],sourceSha256=r['sourceSha256'],targetSha256=r['targetSha256'],components=r['components'],evidenceMode=mode,decision='correction-required' if f else 'applicable-independent-reviewed-unit',findingId=f['findingId'] if f else None,decisionEvidence='Translations/fil/independent-review-02/fresh-decisions.jsonl' if sid in freshids else 'Translations/fil/independent-review-02/supplemental-applicability-decisions.jsonl' if sid in sup else 'Translations/fil/independent-review-01/decisions.jsonl'))
writejl('closure-decision-applicability.jsonl',ledger)
mandatory=set(next(x for x in cl['components'] if x['name']=='mandatoryRegression')['ids']);writejl('mandatory-regression-applicability.jsonl',[x for x in ledger if x['stableId'] in mandatory])
prevcl=load(ROOT/'Translations/fil/semantic-correction-cycle-001.closure.json'); retired=set(pm)-set(cm);retiredrows=[]
# Reconcile all retired rows against current authored target, including records outside new closure.
G={'UI':'0cbd8a7a4f543344bb95659de87f67a5','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1'};tm={}
for x in gate['batchReports']:
 d=load(ROOT/x['path'])
 for e in d['entries']:tm[f"string:{G[d['collection']]}:{e['id']}"]=e['target']
for e in load(ROOT/'Translations/fil/static-text-draft.json')['entries']:tm[e['stableId']]=e['target']
for sid in cl['retiredPreviousMinusCurrent']['ids']:
 r=pm[sid];assert r['target']==tm[sid] and r['targetSha256']==olddec[sid]['targetSha256']
 retiredrows.append(dict(stableId=sid,sourceSha256=r['sourceSha256'],targetSha256=r['targetSha256'],priorComponents=[x['name'] for x in prevcl['components'] if sid in x['ids']],decision='justified retired unchanged dependency',reason='Cycle001 dependency predicates no longer select this ID for cycle002 correction concepts, scenes, exact repeats, localized wording or mandatory catalog; current source/target unchanged and prior independent full-unit decision retained.'))
writejl('retired-dependencies.jsonl',retiredrows)
spec=load(C/'selector-specification.json');reg=[]
for t in spec['regressionExamples']:
 passed=bool(re.search(spec['mandatorySourceRegex'][t['expectedSelector']],t['source'])) and t['stableId'] in mandatory;assert passed;reg.append(dict(t,passed=True))
for t in spec['syntheticSelectorRegressions']:
 observed=bool(re.search(spec['mandatorySourceRegex'][t['selector']],t['source']));assert observed==t['mustMatch'];reg.append(dict(t,observedMatch=observed,passed=True))
# A broader independent youth probe confirms there are no real omitted молод* variants in accepted source.
source=jl(ROOT/'Source/localization-inventory-v3/strings.jsonl');accepted=set(tm);omitted=[]
for r in source:
 if r['stableId'] not in accepted:continue
 forms=re.findall(r'(?i)\bмолод[а-яё]*\b',r['source'])
 if forms and any(x.lower() not in ['молодец','молодцы'] for x in forms) and not re.search(spec['mandatorySourceRegex']['youth-life-stage'],r['source']):omitted.append(r['stableId'])
assert not omitted
write('recipe-regressions.json',dict(selectorSpecificationSha256=sha(C/'selector-specification.json'),builderSha256=sha(C/'build_closure.py'),tests=reg,realTests=22,syntheticTests=7,omittedGenuineYouthForms=omitted,components=cl['components'],componentDeltas=cl['componentDeltas'],retiredComponentNames=cl['retiredPreviousComponentNames'],newFindingBounding=[dict(ordinal=943,matchingCurrentAuthoredPhrase='Anuman ang nangyari',matches=[x for x,y in tm.items() if 'Anuman ang nangyari' in y]),dict(ordinal=10326,matchingCurrentAuthoredPhrase='kahit anong putangina',matches=[x for x,y in tm.items() if 'kahit anong putangina' in y])],fullRestartPredicateObserved=False))
correctiondec=[]
for r in pl['rows']:
 assert cm[r['stableId']]['target']==r['acceptedFullTarget'];correctiondec.append(dict(stableId=r['stableId'],acceptedOrdinal=r['acceptedOrdinal'],source=r['source'],before=r['currentTarget'],after=r['acceptedFullTarget'],decision='full correction accepted',reason='Original defect corrected; all unchanged sentences and source facts retained. Actual compiled source order verified for applicable17 nodes;15480 inventory-only repeat separately compared with compiled13483.',sourceSha256=r['sourceSha256'],targetSha256=r['acceptedFullTargetSha256']))
write('applied-correction-decisions.json',dict(corrections=correctiondec,fullUnitsChecked=19,uncompiledRepeatOrdinal=15480,compiledCounterpartOrdinal=13483,reachabilityOfUncompiledRepeat='unverified',withdrawnProposalsReopened=0))
cutoff=datetime.datetime.now(datetime.timezone.utc).isoformat();v.update(dict(finalCutoffUtc=cutoff,status='independent delta complete; two bounded objective corrections required',sourceAndAuthoredPinsUnchanged=True,fullFreshSemanticReads=266,supplementalApplicabilityDecisions=20,appliedCorrectionsAccepted=19,objectiveFindings=2,mandatoryRegressionStatus='one wording finding at943; other7232 units applicable',fullStructuralCommand='.venv/bin/python Scripts/report_locale_readiness.py --exact --compact',fullStructuralObserved='fil16538/16538 validated16538 observed16538 problems0; read-only command passed',modelTelemetry=dict(reviewer='/root/fil_independent_review_02',systemModelIdentity='GPT-6',exactDeployedModel=None,reasoningLevel=None,inputTokens=None,cachedInputTokens=None,outputTokens=None,reasoningTokens=None,totalTokens=None,reason='No agent/session per-request telemetry or counters exposed in available tools; no text-size estimate used',coordinatorAttribution='parent owns orchestration accounting; unknown to this reviewer',measurementCutoff=cutoff),fullRestartPredicateObserved=False))
write('verification.json',v)
write('evidence-manifest.json',dict(schemaVersion=1,reviewer='/root/fil_independent_review_02',cutoffUtc=cutoff,files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in sorted(OUT.iterdir()) if p.is_file()]))
print(json.dumps(dict(status=v['status'],cutoffUtc=cutoff,freshDecisions=len(dec),supplementalDecisions=len(supdec),closureApplicability=len(ledger),mandatory=len(mandatory),retired=len(retiredrows),findings=[dict(ordinal=x['acceptedOrdinal'],findingId=x['findingId'],replacement=x['replacement']) for x in findings]),ensure_ascii=False,indent=2))
