"""Record model-authored full-unit decisions and seal the independently verified delta."""
import json,hashlib,datetime,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent;C=ROOT/'Translations/fil/semantic-correction-cycle-004'
sys.path.insert(0,str(ROOT/'Scripts'))
from preserve_exact import check_value

def load(p):return json.loads(p.read_text())
def jl(p):return [json.loads(x) for x in p.read_text().splitlines()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def th(s):return hashlib.sha256(s.encode()).hexdigest()
def write(n,d):
 p=OUT/n;assert not p.exists();p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def writejl(n,rows):
 p=OUT/n;assert not p.exists();p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows))
comments={
651:'Contrast with the preceding failed reconciliation is retained by Gayunman; present improved well-being and being with people who understand the speaker remain complete. No future condition introduced.',
1001:'Regardless of the armed man\'s uncertain motivation, the homeowner hopes not to become his enemy. Hope, negation and man-as-evaluator agency retained; no identity revealed early.',
1111:'Ongoing stabilization and cordon retain present duration; Gayunman introduces the immediately following new threat. No resolved crisis or lifting of the cordon asserted.',
1125:'Despite unresolved investigation, broadcaster expresses certainty that the Komite will resolve both this situation and the Panauhin influx. Future agency, certainty and two coordinated problems preserved.',
1152:'Contrast remains between help/evacuation and incomplete finding of suspicious escapees. Only part, completed finding and suspect status preserved.',
1161:'Regular house rounds continue unchanged despite temporary suspension of body disposal. Future continuation and unchanged manner preserved.',
1512:'Speaker still declines responsibility for the earlier café conflict; first-person self-reference and negation retained. No blame transferred to a named hidden occupant.',
3014:'Regardless of the preceding rebuke about the disciples and peace, the cult leader thanks the addressee. Gayon pa man is understandable concessive wording; no future outcome asserted. Ellipses remain separate actual instructions.',
3094:'In any case returns from the house question to the request: let the leader\'s people in and guard them. Speaker possession, plural followers, imperative requests and protective agency preserved.',
5006:'Thanks persist despite refusal, specifically for listening. Subsequent farewell and Refuse Anxiety command confirm the discourse role; no admission promised.',
5593:'Complete accepted legacy inventory unit preserves transition, collective attained understanding, means of inviting Kamatayan and here. Paano man is an admissible anyhow transition. Exact key has no current compiled RunLine/AddOption consumer; no chronology or live reachability is fabricated.',
6644:'Thanks remain regardless of whether the prior remark was sarcasm; past rest enables renewed walking for roughly two days without stopping. Vulgar register and speaker agency preserved.',
7223:'Unconditional concern for the homeowner remains an admissible reading of anuman ang mangyari in this emotional reassurance. Present worry, second-person advice and check question are preserved; this differs from the article conclusion context.',
7235:'Anuman iyon remains recoverable as irrespective of the troubling condition in the prior question; exhaustion makes it normal. No particular diagnosis, future event or new cause is asserted.',
8346:'Gayunman preserves the short concessive transition from knowing the homeowner\'s hatred to apology; no separate assertion or referent added.',
8710:'Unconditional future death is a player option addressed to the armed husband, contrasted with an escape/survival option. Second-person recipient, future death and regardless-of-outcome force retained; wife is not made the speaker.',
9613:'Accepted complete cycle004 correction: Gayunman closes the already discussed interpretation of the article; nakakatawa retains the amused appraisal. No false future contingency, new event, agency, timing or reveal is introduced.',
9614:'Objective omission: instruction25 explains that the article author mistook the appearances for two monsters because the face looked distorted through a window. The target only says the face seemed distorted; it drops the author as experiencer and the causal connection to his mistaken interpretation. This changes the complete explanatory proposition after instruction24.',
9615:'Rhetorical disbelief retains the author\'s failure to recognize that the apparently different sightings are one and the same monster; negation, singular identity and exasperation preserved.',
9616:'The author\'s observation distinguishes one suspicious stranger at windows and another at the doorway. Number, location and observation sequence preserved; no final identity resolution asserted here.',
9617:'The article mentions TWO pale frightening people, with emphasized number retained. Author possession, people-versus-monster distinction and information available before later rebuttal preserved.',
9618:'The article author made an error. Target preserves author as agent and the article referent before explaining the alleged error; no named author invented.',
9619:'Observation report mentions one pale man walking the streets. Singular number, male source reference, activity and setting preserved. Target does not prematurely identify a canonical named character.',
9620:'Concession acknowledges interesting ideas within the article; target retains partial appraisal and interlocutor address. It is distinct from endorsing the theories as canonical fact.',
9621:'Comparison to a science fiction novel title retains honest appraisal; fantasy/science-fiction sense is compatible with fantastic novel in this Visitors article context. No plot fact invented.',
9622:'Article title retains Panauhin and skin thieves as the subject/title wording. Its placement before novel comparison is verified in instruction14; speaker theory remains attributed to Theorist.'}
rows=jl(C/'next-delta-paired.jsonl');assert set(comments)=={r['acceptedOrdinal'] for r in rows}
proposal='Theorist: Sa palagay ko, ganoon ang inakala niya dahil mukhang baluktot ang mukha ng halimaw kapag tinitingnan ito mula sa bintana.'
rules={r['stableId']:r for r in load(ROOT/'Source/preserve-exactly-v4.json')['tableRows']};fresh=[];findings=[]
for r in rows:
 fid='fil-independent-04-001' if r['acceptedOrdinal']==9614 else None
 fresh.append(dict(r,reviewer='/root/fil_independent_review_04',decision='objective-full-unit-correction-required' if fid else 'accepted-independent-reviewed-unit',findingId=fid,evidenceMode='fresh-full-source-target-context-read',reason=comments[r['acceptedOrdinal']],contextPath='Translations/fil/independent-review-04/independent-compiled-context.json' if r['nodeNames'] else None,contextLimit='accepted legacy inventory unit; no current compiled consumer' if not r['nodeNames'] else None))
 if fid:
  check_value(rules[r['stableId']],proposal)
  findings.append(dict(r,findingId=fid,reason=comments[9614],replacement=proposal,proposedFullTarget=proposal,proposedTargetSha256=th(proposal),proposalProtectedSyntax='passed pinned v4 check_value; not applied',boundary='Theorist_Asking_3 instruction25, following instruction24 same-monster rebuttal and instruction21–22 two apparent sightings',contextPath='Translations/fil/independent-review-04/independent-compiled-context.json',priorDecisionReconciliation='This ID is explicitly invalidated in cycle004. Review03 marked it clean in the aggregate; this full-unit source-to-target read shows the omitted experiencer and causal proposition, not a stylistic preference.',boundedScope='One enumerated full-unit defect within the assigned26-unit delta; same node as current correction. No unbounded defect, changed source/glossary/binding or full-restart condition observed.'))
write('findings.json',dict(schemaVersion=1,reviewer='/root/fil_independent_review_04',locale='fil',gameVersion='1.3.19',sourceLocale='ru',status='one bounded objective full-unit correction required; all26 complete fresh pairs read',findings=findings,acceptedCycle004Corrections=1,recipeFindings=[]));writejl('fresh-decisions.jsonl',fresh)
fm={r['stableId']:r for r in fresh};reuse={r['stableId']:r for r in jl(OUT/'prior-decision-applicability.jsonl')};coverage=[]
for r in jl(C/'closure-paired.jsonl'):
 d=fm.get(r['stableId']) or reuse[r['stableId']]
 coverage.append(dict(stableId=r['stableId'],acceptedOrdinal=r['acceptedOrdinal'],sourceSha256=r['sourceSha256'],targetSha256=r['targetSha256'],key=r['key'],nodeNames=r['nodeNames'],components=r['components'],decision=d['decision'],findingId=d['findingId'],evidenceMode=d['evidenceMode'],decisionEvidence='Translations/fil/independent-review-04/fresh-decisions.jsonl' if r['stableId'] in fm else d['decisionEvidence']))
assert len(coverage)==len({r['stableId'] for r in coverage})==7612 and sum(bool(r['findingId']) for r in coverage)==1
writejl('closure-decision-applicability.jsonl',coverage)
cl=load(C/'closure.json');mandatory=set(next(r for r in cl['components'] if r['name']=='mandatoryRegression')['ids']);mr=[r for r in coverage if r['stableId'] in mandatory];assert len(mr)==7240 and sum(bool(r['findingId']) for r in mr)==1
writejl('mandatory-regression-applicability.jsonl',mr)
write('applied-correction-decisions.json',dict(reviewedFullUnits=1,acceptedOrdinals=[9613],decisions=[r for r in fresh if 'corrected' in r['deltaReason']],unchangedFullUnitFactsRetained=True))
ctx=load(OUT/'independent-compiled-context.json');iv=load(OUT/'input-verification.json');spec=load(C/'selector-specification.json')
write('read-coverage.json',dict(reviewer='/root/fil_independent_review_04',freshUnits=26,acceptedFresh=25,objectiveFindings=1,fullPairReadOrdinals=[r['acceptedOrdinal'] for r in rows],truncatedPairs=0,pairedInputPath=str((C/'next-delta-paired.jsonl').relative_to(ROOT)),pairedInputSha256=sha(C/'next-delta-paired.jsonl'),compiledSceneNodes=len(ctx['nodes']),compiledSceneInstructions=sum(len(n['instructions']) for n in ctx['nodes'].values()),legacyNoCompiledConsumerOrdinals=[5593],priorExactDecisionReuse=7586,retiredExactRows=54,contextReadsDoNotExpandSemanticCoverage=True))
write('recipe-regressions.json',dict(normalBuilderVerified=True,realSelectorControls=len(spec['regressionExamples']),syntheticSelectorControls=len(spec['syntheticSelectorRegressions']),result='passed',deltaUnion='1 corrected +13 new +12 explicitly invalidated =26 unique IDs',newRetired=5,priorRetiredStillRetired=49,priorRetiredReentered=0,retirementReason='all54 outside every current component; unchanged exact source/target/key/node and prior independent decision pins',recipeFindings=[],dynamicConsumers=dict(count=6,status='exact prior supplier/source/target/catalog/IL inputs and current actual compiled bytecode applicable',evidencePath='Translations/fil/independent-review-04/dynamic-input-applicability.json',limits='No live scheduling or rendered joins tested'),legacyAbsentCompiledConsumer=dict(ordinal=5593,key='line:talk_CultistEnds_1_05e1db9',status='already empty nodeNames in pinned inventory; absent from current compiled program',effect='source-target semantic read accepted; current runtime reachability remains unverified')))
# Recheck unchanged evidence immediately before the verdict receipt.
for r in iv['pinChecks']:assert sha(ROOT/r['path'])==r['sha256']
for r in iv['historicalChangedPins']:assert sha(ROOT/r['path'])==r['currentSha256']
for r in load(OUT/'dynamic-input-applicability.json')['pins']:assert sha(ROOT/r['path'])==r['sha256']
for n,v in load(C/'handoff.json')['cycleFilesSha256'].items():assert sha(C/n)==v
cutoff=datetime.datetime.now(datetime.timezone.utc).isoformat()
write('verification.json',dict(schemaVersion=1,reviewer='/root/fil_independent_review_04',cutoffUtc=cutoff,status='one bounded objective correction required',sourceAndAuthoredPinsUnchanged=True,closureUnits=7612,freshPairs=26,acceptedFresh=25,objectiveFindings=1,acceptedCycle004Corrections=1,priorExactDecisionsReused=7586,retiredNew=5,retiredPrior=49,mandatoryRegression=dict(total=7240,fresh=18,reused=7222,clean=7239,findings=1,status='one full-unit correction required at9614'),freshWholeCorpusGuard=dict(path='Translations/fil/independent-review-04/full-corpus-validation.json',sha256=sha(OUT/'full-corpus-validation.json'),rows=16538,structural='passed',exact='passed',boundary=load(OUT/'full-corpus-validation.json')['boundary']),compiledProgramSha256=load(C/'handoff.json')['compiledProgramSha256'],inputVerificationSha256=sha(OUT/'input-verification.json'),fullRestartPredicateObserved=False,limits=['No game launch, runtime scheduling/rendering, layout, glyph/font, image/texture, screenshot, installer, packaging, platform or publication check','Only new independent-review-04 artifacts authored; no shared/locale/source/glossary/Git/index changes','Parent owns adjudication, correction, final editorial acceptance and canonical integration'],modelTelemetry=dict(systemIdentity='GPT-6',exactDeployedModel=None,reasoningLevel=None,inputTokens=None,cachedInputTokens=None,outputTokens=None,reasoningTokens=None,totalTokens=None,reason='No reviewer usage counter exposed; parent collects actual per-agent telemetry',measurementCutoff=cutoff,reportingTail='unknown; report cannot measure itself',coordinatorAttribution='parent-owned; unknown to reviewer')))
print(json.dumps(dict(status='one bounded finding',fresh=26,accepted=25,corrected9613='accepted',finding9614='causal perception omission',mandatory=7240,mandatoryFindings=1,cutoff=cutoff)))
