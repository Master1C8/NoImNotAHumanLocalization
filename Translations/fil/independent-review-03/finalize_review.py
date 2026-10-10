"""Seal model-authored cycle003 delta decisions on independently checked inputs."""
import json,hashlib,datetime,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent;C=ROOT/'Translations/fil/semantic-correction-cycle-003';P=ROOT/'Translations/fil/independent-review-02'
sys.path.insert(0,str(ROOT/'Scripts'))
from preserve_exact import check_value

def load(p):return json.loads(p.read_text())
def jl(p):return [json.loads(x) for x in p.read_text().splitlines()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def th(s):return hashlib.sha256(s.encode()).hexdigest()
def write(name,d):
 p=OUT/name;assert not p.exists();p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def writejl(name,rows):
 p=OUT/name;assert not p.exists();p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows))
rows=jl(C/'next-delta-paired.jsonl');cl=load(C/'closure.json');iv=load(OUT/'input-verification.json');rules={r['stableId']:r for r in load(ROOT/'Source/preserve-exactly-v4.json')['tableRows']}
comments={
943:'Clean complete correction: mangyari preserves open future contingency; sa iyo na locates the next calamity on the only remaining house owner. No completed past event or invented named calamity.',
944:'No other recipient remains to absorb the mad attackers; plural perpetrators and negation preserved.',
945:'The player house alone remains standing throughout the surrounding area; no change of owner or locality.',
946:'All neighboring houses were destroyed; plural and completed destruction retained.',
2915:'Unconditional resolve to stop the Mushroom Festival is preserved with anuman ang mangyari; actual scene frames no choice and a forthcoming journey.',
2992:'Full unit retained: reassurance, limited present understanding, instruction to remember, shared obligation and unconditional resolve; approved Pista ng mga kabute retained.',
7223:'No objective correction: anuman ang mangyari is an admissible unconditional reassurance in this concern-for-the-player exchange. Worry, second-person emotional advice and question retained; no new event asserted.',
9613:'Finding: article conclusion uses a discourse transition regardless of the preceding interpretive dispute. Whatever happens introduces an unrelated future contingency; use Gayunman.',
10320:'Dismissal and nausea retained; actual scene ends after the curse.',
10321:'Standalone vulgar expletive preserved; no invented action or referent.',
10322:'Vulgar pants-soiling metaphor retained as inability to live without feces in the pants; same collective subject.',
10323:'Self-created problems and expletive retained. Sarcastic gumawa ng sarili has recoverable problems antecedent immediately in the sentence; no objective full-unit correction required.',
10324:'Both complete conditional stages retained: sun may kill us, then Visitors; overcoming Visitors is followed by self-burial alive. Subjects, instruments, collective number and approved term preserved.',
10325:'Speaker anticipates all of us dying soon; uncertainty pakiramdam ko and near-future malapit retained.',
10326:'Clean complete correction: everyone claims to solve problems; actual absence of progress remains present. Putangina functions as a curse separate from the event noun, preserving vulgar register.',
10327:'Catastrophe appraisal and vulgarity retained without invention.',
10328:'Intentional hesitation-only unit exactly preserved.',
10329:'Entire unit retains nausea, homeowner addressee, decision to drink a little and rhetorical denial of criminality.',
10330:'Speaker drank a small quantity of beer at the addressee house; first-person agency and limited amount preserved.',
14523:'Absolute photography prohibition is retained by Huwag...anuman ang mangyari; uppercase anonymous IYON refers to the terrifying creature, not a prematurely named character. Actual neighboring line says photographing strengthens it.'}
assert set(comments)=={r['acceptedOrdinal'] for r in rows}
proposed='Theorist: Gayunman, nakakatawa ang artikulong ito…';finding=[];fresh=[]
for r in rows:
 fid='fil-independent-03-001' if r['acceptedOrdinal']==9613 else None
 fresh.append(dict(r,reviewer='/root/fil_independent_review_03',evidenceMode='fresh-full-pair-scene-read',decision='objective-full-unit-correction-required' if fid else 'accepted-independent-reviewed-unit',findingId=fid,reason=comments[r['acceptedOrdinal']],contextPath='Translations/fil/independent-review-03/independent-compiled-context.json'))
 if fid:
  check_value(rules[r['stableId']],proposed)
  finding.append(dict(r,findingId=fid,reason=comments[9613],replacement=proposed,proposedFullTarget=proposed,proposedTargetSha256=th(proposed),proposalProtectedSyntax='passed pinned v4 check_value; not applied',boundary='Theorist_Asking_3 instruction27; closing appraisal after22–25 debate whether two observed strangers are the same monster. No future-event condition exists.',contextPath='Translations/fil/independent-review-03/independent-compiled-context.json',boundedScope='All accepted occurrences of the affected current wording are already in this20-unit delta. No source/glossary/binding change or unbounded systemic defect observed.'))
write('findings.json',dict(schemaVersion=1,reviewer='/root/fil_independent_review_03',locale='fil',sourceLocale='ru',gameVersion='1.3.19',status='one objective bounded full-unit correction required; all20 complete fresh pairs read',findings=finding,acceptedCycle003Corrections=2,recipeFindings=[]))
writejl('fresh-decisions.jsonl',fresh)
reuse={r['stableId']:r for r in jl(OUT/'prior-decision-applicability.jsonl')};fm={r['stableId']:r for r in fresh};coverage=[]
for r in jl(C/'closure-paired.jsonl'):
 d=fm.get(r['stableId']) or reuse[r['stableId']]
 coverage.append(dict(stableId=r['stableId'],acceptedOrdinal=r['acceptedOrdinal'],sourceSha256=r['sourceSha256'],targetSha256=r['targetSha256'],key=r['key'],nodeNames=r['nodeNames'],components=r['components'],evidenceMode=d['evidenceMode'],decision=d.get('decision','applicable-independent-reviewed-unit'),findingId=d.get('findingId'),decisionEvidence='Translations/fil/independent-review-03/fresh-decisions.jsonl' if r['stableId'] in fm else d['decisionEvidence']))
assert len(coverage)==7604 and sum(r['findingId'] is not None for r in coverage)==1
writejl('closure-decision-applicability.jsonl',coverage)
mandatory=set(next(r for r in cl['components'] if r['name']=='mandatoryRegression')['ids']);mr=[r for r in coverage if r['stableId'] in mandatory];assert len(mr)==7234 and not any(r['findingId'] for r in mr)
writejl('mandatory-regression-applicability.jsonl',mr)
write('applied-correction-decisions.json',dict(reviewedFullUnits=2,acceptedOrdinals=[943,10326],decisions=[r for r in fresh if 'corrected' in r['deltaReason']],unchangedSentencesRetained=True))
write('read-coverage.json',dict(reviewer='/root/fil_independent_review_03',freshUnits=20,sourceLocale='ru',targetLocale='fil',fullPairReadOrdinals=[r['acceptedOrdinal'] for r in rows],truncatedFreshPairs=0,pairedInputPath=str((C/'next-delta-paired.jsonl').relative_to(ROOT)),pairedInputSha256=sha(C/'next-delta-paired.jsonl'),actualCompiledSceneNodes=list(load(OUT/'independent-compiled-context.json')['nodes']),actualCompiledSceneInstructions=97,priorCompiledContextApplicabilityNodes=90,priorCompiledContextApplicabilityInstructions=1427,sceneContextExtractionIsAdditionalCorpusCoverage=False,priorExactDecisionReuse=7584,retiredExactRows=49))
spec=load(C/'selector-specification.json')
write('recipe-regressions.json',dict(normalBuilderVerified=True,realSelectorControls=len(spec['regressionExamples']),syntheticSelectorControls=len(spec['syntheticSelectorRegressions']),result='passed',deltaUnion='2 corrected +8 new +10 invalidated =20',retired=49,retiredReason='outside every current selector, unchanged source/target/key/node and prior clean decision verified',futureOpenContingencyAcceptedSourceMatches=1,absenceOfProgressAcceptedSourceMatches=1,nonacceptedDuplicateTables='excluded by canonical scope; no translation IDs fabricated',independentBroadProbe='alternate source scan of что...ни...случ and nothing-happens word order found both true affected accepted units. Other hits are past-event questions/uncertainty, not open contingency; no omitted true affected unit observed.',recipeFindings=[],dynamicConsumers=dict(count=6,status='exact source/target, supplier/context evidence and compiled program pins remain applicable',contextEvidence='Translations/fil/independent-review-01/dynamic-assembly-decisions.json',contextEvidenceSha256=sha(ROOT/'Translations/fil/independent-review-01/dynamic-assembly-decisions.json'),limits='Static compiled/serialized/IL admissibility; live scheduling and rendered joins not exercised.')))
# Final guard applicability: recheck every receipt input rather than alter old sidecars.
guard=load(OUT/'full-corpus-validation.json')
for row in guard['authoredFiles']:assert sha(ROOT/row['path'])==row['sha256']
for row in iv['pinChecks']:assert sha(ROOT/row['path'])==row['expected']
for row in iv['historicalChangedPins']:assert sha(ROOT/row['path'])==row['currentSha256']
for n,h in load(C/'handoff.json')['cycleFilesSha256'].items():assert sha(C/n)==h
cutoff=datetime.datetime.now(datetime.timezone.utc).isoformat()
write('verification.json',dict(schemaVersion=1,reviewer='/root/fil_independent_review_03',cutoffUtc=cutoff,status='one objective correction required',sourceAndAuthoredPinsUnchanged=True,closureUnits=7604,freshPairs=20,acceptedFresh=19,objectiveFindings=1,acceptedCycle003Corrections=2,priorExactDecisionsReused=7584,retiredDependenciesVerified=49,mandatoryRegression=dict(total=7234,fresh=12,reused=7222,status='passed on exact pins'),gateCommand='.venv/bin/python Translations/fil/semantic-correction-cycle-003/build_gate.py --verify',closureCommand='.venv/bin/python Translations/fil/semantic-correction-cycle-003/build_closure.py --verify',freshWholeCorpusGuard=dict(path='Translations/fil/independent-review-03/full-corpus-validation.json',sha256=sha(OUT/'full-corpus-validation.json'),rows=16538,structural='passed',exact='passed',boundary=guard['boundary']),compiledProgramSha256=load(C/'handoff.json')['compiledProgramSha256'],inputVerificationSha256=sha(OUT/'input-verification.json'),fullRestartPredicateObserved=False,modelTelemetry=dict(systemModelIdentity='GPT-6',exactDeployedModel=None,reasoningLevel=None,inputTokens=None,cachedInputTokens=None,outputTokens=None,reasoningTokens=None,totalTokens=None,reason='No per-agent/request usage counter exposed to reviewer. Parent collects actual telemetry; no estimates used.',coordinatorAttribution='parent responsibility, unknown here',measurementCutoff=cutoff),limits=['No game launch, runtime, layout, glyph, fonts, images, textures, screenshot, installer, package or platform check','Review seals delta criterion with finding; complete corpus acceptance and canonical integration remain parent-owned','No authored/source/glossary/shared/Git/index edits']))
print(json.dumps(dict(status='one finding',fresh=20,acceptedCorrections=2,mandatory=7234,cutoff=cutoff,findingsSha256=sha(OUT/'findings.json'),verificationSha256=sha(OUT/'verification.json'))))
