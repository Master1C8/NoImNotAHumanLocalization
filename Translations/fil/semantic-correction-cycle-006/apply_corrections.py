#!/usr/bin/env python3
"""Preflight and apply the consolidated Filipino cycle006 author decisions once."""
import hashlib,json,os,re,sys
from collections import Counter
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];FIL=ROOT/'Translations/fil';CYCLE=Path(__file__).resolve().parent;REVIEW=FIL/'independent-review-05'
sys.path.insert(0,str(ROOT/'Scripts'))
from preserve_exact import check_value
from validate_game_text_batch import TOKEN,DIGITS
from json_target_spans import rewrite_targets

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def th(s):return hashlib.sha256(s.encode()).hexdigest()
def load(p):return json.loads(p.read_text())
def require(ok,msg):
 if not ok:raise RuntimeError(msg)
def save(p,d):require(not p.exists(),'Immutable cycle file exists: '+p.name);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def encode(d):return (json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode()
VOICE={'Experienced':'ex-con','Bald':'theater-man','Fatman':'naked-fat-man','BigLebowski':'bar-teenager','Unstable':'jerky-man','Nervous':'creepy-man','Rocker':'rock-musician','Scammer':'amogus-shirt-man','Provocateur':'armchair-lawyer','Intruder':'sleepless-man','Wolfhound':'suit-bandit','Vigilante':'vigilante','Miner':'miner','Neighbour':'neighbour','Firefighter':'firefighter','FunnyGuy':'stand-up-guy','Jacob':'immortal-man','Marauder':'homeless-man','Dude':'stoner','Buddy':'friendly-gremlin','Greatmother':'big-momma','TaxiDriver':'taxi-driver','Anger':'angry-wounded-man','Fugitive':'wounded-fugitive','Wheelchair':'wheelchair-man','WheelChair':'wheelchair-man','Leper':'leper','Mother':'mother-with-child','Tough':'tough-woman','Jacket':'jacket-man','GraveDigger':'gravedigger','Phone':'mothers-husband'}
NOTES={
 2:'Coarse rhetorical С какого хера became neutral why. Mild Bwisit restores irritation; magazine search and request for peace remain.',
 4:'Source narrator uses coarse indifference about father and rules; restore mild rough register without asserting father speaks the line.',
 7:'Husband speaker crudely dismisses wife neglecting her own children; retain husband/wife roles and sigh, with source-supported rough particle.',
 8:'Coarse dismissive indifference was neutral; blunt pake retains flippancy without adding a new anger claim to Nervous.',
 9:'Херня is coarse trouble/nonsense here, not a literal plant; kagaguhang preserves sudden events affecting each friend.',
 10:'Restore coarse eviction dismissal. Russian выгнали has an unexpressed recipient: remove unsupported siya and preserve pro-drop, without asserting who evicted whom; all alternatives and refuge request remain.',
 13:'Experienced contemptuously notes sweaters/jackets and indifference in heat; coarse bwisit and dismissive pake restore source voice without new facts.',
 14:'Я хер знает expresses rough not-knowing, not an anatomical referent; putsa restores source register while all heat/fraer/other people facts remain.',
 19:'Coarse nonsense dismissal needs kagaguhan; boring addressee and two sentences remain.',
 20:'Хер пойми что expresses incomprehensibility with coarse force; plain Ano ba omitted that as well as register. Retain refusal to proceed; no new diagnosis or participant.',
 29:'Restore emphatic coarse contradiction of assumed deaths. Russian дочь этого мужика с ружьем identifies daughter of the armed man; gun qualifier remains on that man, rather than asserting daughter carries it. Days later, they find speaker, first arrival and all questions remain.',
 35:'Coarse remainder of obsolete social norms becomes kagaguhang; no new allegation about the speaker or others.',
 36:'Coarse dismissive Ну и похер became plain resignation; Eh/bahala na/putsa preserves dismissal without new action.',
 44:'Coarse bad situation and breathless cough retain mild rough particle, kaibigan and exact existing kh-kh.',
 45:'Херню на уши вешаю is feeding nonsense, not literal whispering. Full replacement retains truth-versus-bullshit possibility and speaker/addressee; no asserted lie or whisper action.',
 50:'Coarse nonsense characterization of stated debt excuse restores kagaguhan. Reported claim and hypothetical monthly mortgage debit remain.',
 51:'Player crudely dismisses story; colloquial blunt pake preserves indifference with no invented insult to speaker.',
 52:'Exact source repetition of51 receives identical full replacement, same dismissive function.',
 54:'Coarse trouble with collectors becomes kagaguhan; speaker still seeks help from friends after that event.',
 55:'Coarse nonsense contrasted with safety retains negation and option meaning.',
 59:'Ex-con coarse rhetorical clothing question lost expletive force. Mild bwisit restores it; other fools, jackets/sweaters/heat and Gets mo remain.',
 60:'Exact finding-source repetition: coarse clothing/heat rhetorical complaint needs same complete Bwisit replacement as6555.',
 61:'Accept final Review05 full replacement at6555: coarse Какого хрена restored with Bwisit; clothing, everybody, ongoing heat and ellipsis unchanged.',
 67:'Coarse emphatic denial of myths restored without turning Jacob belief into narrator proof; Committee knowledge/timing remains his assertion.',
 74:'Retain abuse by father and mother indifference, all temporal facts and absence of watching. Mild putsa restores coarse source indifference, not mother speech.',
 75:'Comic coarse diminutive nothing-at-all remains none of the films; lintik supplies mild roughness without adding films or losing private-room/TV fact.',
 78:'Hard-to-obtain cigars in present contrast with past ministry remains; mild putsa restores coarse хрен где without asserting absolute impossibility.',
 79:'Coarse disaster noun needs kagaguhan; counterfactual beer/football and interrupted introduction remain unchanged.',
 80:'Unbound source says some nonsense is resulting; preserve generic result rather than unsupported named story/question. No compiled consumer invented; Parang/kinalalabasan keeps source vagueness.',
 84:'Coarse dismissive consent to one photo becomes bahala na,putsa; no future photo outcome or force invented.',
 89:'Coarse resignation хер с ним restored; no added referent identity.',
 91:'Ex-con challenges gun being drawn and orders it put away; restore mild rough question without changing gun, actor or instruction order.',
 92:'Coarse rhetorical indifference remains a rhetorical Pero ano naman, with source-supported rough particle; no energy-drink safety claim.',
 95:'Source first alternative is vaguely bad/hard without glasses, second is no sight at all. Keep first broad, no invented clinical illness or narrowed vision fact; preserve current conjecture about child and coarse word.',
 96:'Coarse shocked challenge restored by Bwisit; dirt under nails and Guest inference remain the questioned claim.',
 98:'Coarse father action noun restored; family pays consequences, rat simile and all three privations remain.',
 102:'Coarse exhausted indifference restored; existing scream and ellipsis unchanged.',
 104:'Coarse indifference restored without changing next-time immediate shot, refusal to beg or agency.',
 105:'Coarse indifference restored without new reason or gun action.',
 107:'Coarse indifference restored; existing manong address and immediacy remain.',
 112:'Coarse vague problems represented as lintik na problema; armpits and rhetorical everybody-has-problems meaning remain, no invented diagnosis.',
 113:'Coarse dismissal restored before satisfied-question; no branch merge.',
 114:'Да хрен там is rough denial, not polite uncertainty; retained complete denial plus putsa and exactly interrupted al… tail. Branch alternative stays separate.',
 115:'Short exact-prefix variant gets same coarse denial; no missing trailing sentence fabricated from longer branch.',
 119:'Coarse surprise Нихрена себе becomes Pucha,grabe; genuine-check versus joking question remains.',
 120:'Coarse bad-luck adjective rendered lintik na malas; permission to check, nothing hidden and maybe-exception remain.',
 123:'Actual Anger_Photo starts with rough nonspecific Херачь then ShowSign Anger AURAPHOTO. Barilin mo invents firearm instruction. Gawin mo na preserves nonspecific imperative, putsa its register, without naming an unsupported weapon or early result.'
}
KEEP={
 26:'Lintik already carries coarse unit register; source rough destruction is fully retained, no word-for-word curse-count requirement.',
 27:'Complete unit already has Lintik and rough imperative/fight language; no objective new omission justified by candidate match alone.',
 30:'Complete unit is already coarse via putanginang; unknown whereabouts, sibling-family hostility and all facts remain. No extra swear for each Russian lexeme.',
 31:'Malay natin is idiomatic blunt unknown-duration language; not a neutral formal statement, no objective preference rewrite.',
 37:'Ewan ko is blunt colloquial uncertainty; possible home location and rhetorical where-else remain. No new generic curse justified.',
 39:'Walang kuwenta is a contemptuous security appraisal, carrying dismissive force of херня; no preference rewrite.',
 40:'Malay ko ba preserves blunt rhetorical not-knowing and casual neighbour voice; literal horseradish is not meant.',
 41:'Full unit already retains tanga and dismissive bahala ka; do not count isolated matches as mandatory extra swears.',
 42:'Binubuwisit and kalokohang together retain coarse irritation in why-burden-me question; full meaning remains.',
 43:'Exact repetition of42 remains identical and coarse.',
 53:'Manalasa plus impiyerno conveys forceful sun/disaster statement and intensification; no invented curse for a coarse action verb.',
 62:'Wala na akong pake is blunt slang indifference in exhausted speaker voice; avoid a blanket stronger rewrite.',
 63:'Pake/pare/Hay preserves blunt exhausted indifference; same local slang as62.',
 66:'Херачу energy drink is chugging, not shooting; nilalaklak is rough action idiom and the source-specific intensity survives.',
 68:'Unbound exact source repetition of45 already uses kagaguhan and generic said-to-you, no literal whisper; retain, no invented compiled consumer.',
 69:'Malay mo is idiomatic uncertain possibility, retaining the next passenger killing-you hypothetical; no new certainty or generic swear.',
 72:'Malay ko ba preserves grandmother blunt unknown plus affectionate anak; avoid invented rage/swearing.',
 76:'Malay ba plus interrupted question expresses rough not-knowing of energy-drink contents; no invented ingredients or anatomical literal.',
 88:'Halos matae gives complete-unit coarse fear register; no need another curse for each source expression.',
 93:'Complete unit already retains strong putangina and self-observation; source coarse force present.',
 99:'Forceful humahampas correctly denotes banging hands on steering wheel among anger reactions; no speech-expletive/anatomical/weapon action invented.'
}
def main():
 require(not (CYCLE/'plan.json').exists(),'Cycle006 already applied')
 pins=load(CYCLE/'preimage-pins.json')
 for pin in load(REVIEW/'input-verification.json')['pinChecks']:require(sha(ROOT/pin['path'])==pin['sha256'],'Preimage changed: '+pin['path'])
 for name,h in pins['review05FilesSha256'].items():require(sha(REVIEW/name)==h,'Review05 evidence differs')
 for name,h in pins['preparedFilesSha256'].items():require(sha(CYCLE/name)==h,'Bounded input differs')
 rules={r['stableId']:r for r in load(ROOT/'Source/preserve-exactly-v4.json')['tableRows']}
 source={r['stableId']:r for r in (json.loads(x) for x in (ROOT/'Source/localization-inventory-v3/strings.jsonl').open())}
 rows=load(CYCLE/'bounded-author-inputs.json')['rows'];replacements=load(CYCLE/'authored-replacements.json');glossary=load(ROOT/'Documentation/glossary-translations/fil/layer.json')
 require(len(rows)==125 and len(replacements)==56,'Adjudication count differs')
 require(replacements['61']==load(REVIEW/'findings.json')['findings'][0]['proposedFullTarget'],'Final full proposal differs')
 decisions=[];accepted=[];docs={};original={}
 for n,row in enumerate(rows,1):
  r=dict(row);s=source[row['stableId']];require(s['source']==r['source'] and th(s['source'])==r['sourceSha256'],'Pinned source differs')
  prefix=r['source'].split(':',1)[0] if ': ' in r['source'] else None;voice=VOICE.get(prefix,'player')
  require(voice in glossary,'Approved voice missing')
  r.update(authorOnly=True,independentReadCredit=0,glossaryId=voice,glossaryMeaning=glossary[voice]['meaning'])
  if str(n) not in replacements:
   r.update(decision='retain unchanged; no objective same-mechanism correction',reason=KEEP.get(n,'Full unit retains source roughness through its actual swear, insult, blunt idiom or forceful action wording; facts/uncertainty remain. Candidate matching is not a finding.'),acceptedFullTarget=r['target'])
  else:
   target=replacements[str(n)];require(target!=r['target'],'No-op correction')
   check_value(rules[r['stableId']],target)
   require(Counter(TOKEN.findall(target))==Counter(TOKEN.findall(r['target'])) and Counter(DIGITS.findall(target))==Counter(DIGITS.findall(s['source'])),'Token/numeric preflight failed')
   require(re.findall(r'\r\n|\r|\n',target)==re.findall(r'\r\n|\r|\n',s['source']) and re.search(r'[ \t\r\n]*$',target).group()==re.search(r'[ \t\r\n]*$',s['source']).group(),'Whitespace preflight failed')
   r.update(decision='accepted objective full-unit correction',reason=NOTES.get(n,'Coarse херня noun has been neutralized as ordinary kalokohan/problem; restore source-matched kagaguhan while every other sentence and fact remains.'),acceptedFullTarget=target,acceptedFullTargetSha256=th(target),protectedSyntaxPreflight='passed pinned v4 and owning prefix/token/digit/line-break/whitespace contracts',assembledOutputPreflight={'consumers':r['compiledConsumers'],'boundary':'actual RunLine/AddOption binding and bounded preceding/following text/control windows pinned; no changed line has substitution operands or placeholders','factsAgencyTimingReveal':'complete source/target and actual bounded context adjudicated; retain unchanged facts and ambiguity as described in reason','sourceAmbiguity':'no unexpressed participant, literal plant, new weapon, diagnosis or early identity invented'})
   accepted.append(r)
   path=ROOT/r['authoredPath']
   if str(path) not in docs:
    raw=path.read_bytes();doc=load(path);require(rewrite_targets(raw,doc)==raw,'Exact unchanged-span replay differs');original[str(path)]=raw;docs[str(path)]=doc
   entry=next(e for e in docs[str(path)]['entries'] if str(e['id'])==r['stableId'].rsplit(':',1)[1]);require(entry['target']==r['target'] and sha(path)==r['authoredSha256'],'Authored current mapping differs');entry['target']=target
  decisions.append(r)
 require(all(not re.search(r'\{\d+\}',r['source']) for r in accepted),'Changed dynamic consumer unexpectedly present')
 # Every old authored input is verified before claiming continued semantic coverage.
 for pin in pins['authoredFiles']:require(sha(ROOT/pin['path'])==pin['sha256'],'Authored corpus preimage differs')
 files=[]
 for folder in ['before-authored-files','after-authored-files','before-validation-files']:(CYCLE/folder).mkdir()
 for name,doc in docs.items():
  path=Path(name);before=CYCLE/'before-authored-files'/path.name;after=CYCLE/'after-authored-files'/path.name;side=path.with_suffix('.validation.json');sidebefore=CYCLE/'before-validation-files'/side.name
  before.write_bytes(original[name]);sidebefore.write_bytes(side.read_bytes());after.write_bytes(rewrite_targets(original[name],doc))
  files.append(dict(authoredPath=str(path.relative_to(ROOT)),beforeSnapshotPath=str(before.relative_to(ROOT)),beforeSha256=sha(before),afterSnapshotPath=str(after.relative_to(ROOT)),afterSha256=sha(after),validationPath=str(side.relative_to(ROOT)),beforeValidationSnapshotPath=str(sidebefore.relative_to(ROOT)),beforeValidationSha256=sha(sidebefore),changedIds=[r['stableId'] for r in accepted if r['authoredPath']==str(path.relative_to(ROOT))]))
 (CYCLE/'correction-decisions.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in decisions))
 prior=load(FIL/'semantic-correction-cycle-005/plan.json')
 plan={'schemaVersion':6,'locale':'fil','gameVersion':'1.3.19','sourceLocale':'ru','status':'complete consolidated author adjudication and full replacement preflight before one bounded application','candidateUnitsRead':125,'acceptedCorrections':56,'retainedUnchanged':69,'experiencedCandidates':6,'experiencedCorrections':6,'compiledSitesContextRead':122,'unboundCandidates':3,'authoredFilesChanged':41,'sourceAndGlossaryFingerprints':pins['sourceAndGlossaryFingerprints'],'preserveExactManifestSha256':pins['preserveExactManifestSha256'],'firstPassProgressSha256':pins['firstPassProgressSha256'],'compiledProgramSha256':load(CYCLE/'actual-consumer-topology.json')['compiledProgramSha256'],'preimagePinsSha256':sha(CYCLE/'preimage-pins.json'),'boundedInputsSha256':sha(CYCLE/'bounded-author-inputs.json'),'consumerTopologySha256':sha(CYCLE/'actual-consumer-topology.json'),'correctionDecisionsSha256':sha(CYCLE/'correction-decisions.jsonl'),'authoredReplacementsSha256':sha(CYCLE/'authored-replacements.json'),'finalReviewEvidenceSha256':dict(pins['review05FilesSha256'],**{'completion-manifest.json':pins['review05CompletionManifestSha256']}),'previousClosurePath':'Translations/fil/semantic-correction-cycle-005/closure.json','previousClosureSha256':pins['previousClosureSha256'],'previousPairedSha256':pins['previousPairedSha256'],'rows':accepted,'files':files,'allOtherTargetsAndMetadataUnchanged':True,'derivation':'All corrected sources are standalone dialogue, no option/static/credits recipe source. Full derived hashes will be rechecked/reused on exact pins with fresh owning corpus guard.','fullRestartPredicateObserved':False,'independentReview':'pending;125 author reads confer zero independent acceptance','unresolved':'Three candidates have no compiled consumer. Preserve accepted source identity and do not fabricate runtime applicability; generic legacy result at9772 stays generic. Russian pro-drop eviction remains unspecified; rhetorical coarse forms are classified by full context, not token substitution.','applicationBoundary':'41 per-file atomic replacements; not a filesystem transaction. Complete before/after snapshots and journal preserve any interrupted state.'}
 save(CYCLE/'plan.json',plan)
 journal={'planSha256':sha(CYCLE/'plan.json'),'status':'applying41 per-file atomic replacements; sidecars intentionally pending','appliedFiles':[]}
 (CYCLE/'application-journal.json').write_bytes(encode(journal))
 for record in files:
  path=ROOT/record['authoredPath'];require(sha(path)==record['beforeSha256'],'Apply preimage differs')
  temp=path.with_name(path.name+'.cycle006.tmp');temp.write_bytes((ROOT/record['afterSnapshotPath']).read_bytes());os.replace(temp,path);require(sha(path)==record['afterSha256'],'Post-write differs');journal['appliedFiles'].append(record['authoredPath']);(CYCLE/'application-journal.json').write_bytes(encode(journal))
 journal['status']='all41 authored files applied; affected owning validation pending';(CYCLE/'application-journal.json').write_bytes(encode(journal))
 print(json.dumps({'acceptedFullCorrections':56,'retained':69,'files':41,'planSha256':sha(CYCLE/'plan.json')}))
if __name__=='__main__':main()
