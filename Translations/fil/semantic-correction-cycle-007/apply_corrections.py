#!/usr/bin/env python3
"""Preflight the two author-adjudicated full units, freeze preimages, apply once."""
import copy,hashlib,json,re,sys
from collections import Counter
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];F=ROOT/'Translations/fil';C=Path(__file__).resolve().parent;R=F/'independent-review-06'
sys.path.insert(0,str(ROOT/'Scripts'))
from preserve_exact import check_value
from validate_game_text_batch import TOKEN,DIGITS
from json_target_spans import rewrite_targets
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def th(s):return hashlib.sha256(s.encode()).hexdigest()
def load(p):return json.loads(p.read_text())
def save(n,d):
 p=C/n;assert not p.exists(),n;p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
TARGETS={2834:'Miner: Makinig ka, kakaiba ang daloy ng oras dito. Walang araw o orasan. Kaya malay natin kung gaano na kami katagal dito.',16128:'Mother: Mga kamay… Ipinangyakap ko ang mga ito sa mga anak ko, ginamit sa lahat ng gawain sa bahay, at ipinanghaplos sa asawa ko. Pero alam mo? Wala pa ring putanginang nagpapahalaga.'}
REASONS={2834:'The underground duration group excludes the upstairs addressee: following actual RunLine says там, наверху. Change only tayo to kami. Malay natin remains the accepted blunt shared-uncertainty idiom; it does not place the listener underground. All time/sun/clock facts and uncertainty preserved.',16128:'всё по дому делала denotes all household work, not cleaning only. Replace only ipinanglinis ng bahay with ginamit sa lahat ng gawain sa bahay. Hands remain the instruments used by Mother for embracing her children, household tasks and caressing her husband. Every other sentence, complaint and accepted profanity stays exact.'}
def main():
 assert not (C/'plan.json').exists(),'Already applied'
 pre=load(C/'preimage-pins.json');b=load(C/'bounded-author-inputs.json');review=load(R/'findings.json');layer=load(ROOT/pre['sourceAndGlossaryFingerprints']['filGlossary']['path'])
 for pin in load(R/'completion-manifest.json')['files']+load(R/'completion-manifest.json')['currentInputPins']:assert sha(ROOT/pin['path'])==pin['sha256'],pin['path']
 for pin in pre['sourceAndGlossaryFingerprints'].values():assert sha(ROOT/pin['path'])==pin['sha256']
 assert sha(C/'bounded-author-inputs.json')==pre['boundedInputsSha256'] and sha(F/'semantic-review-progress.json')==pre['firstPassProgressSha256']
 rules={r['stableId']:r for r in load(ROOT/'Source/preserve-exactly-v4.json')['tableRows']};rows=[];original={};docs={}
 for proposal in review['objectiveFindings']:
  ordinal=proposal['acceptedOrdinal'];target=TARGETS[ordinal];r=copy.deepcopy(next(x for x in b['rows'] if x['acceptedOrdinal']==ordinal));assert r['source']==proposal['source'] and r['target']==proposal['target'] and r['sourceSha256']==proposal['sourceSha256'] and r['targetSha256']==proposal['targetSha256'] and r['consumerIdentitySha256']==proposal['consumerIdentitySha256'];assert target==proposal['proposedFullTarget']
  check_value(rules[r['stableId']],target)
  assert Counter(TOKEN.findall(target))==Counter(TOKEN.findall(r['target'])) and Counter(DIGITS.findall(target))==Counter(DIGITS.findall(r['source']))
  assert re.findall(r'\r\n|\r|\n',target)==re.findall(r'\r\n|\r|\n',r['source']) and re.search(r'[ \t\r\n]*$',target).group()==re.search(r'[ \t\r\n]*$',r['source']).group()
  assert all(s['opcode']=='RunLine' and s['operands'][1]==0 for s in r['consumerIdentity']['sites']) and not re.search(r'\{\d+\}',target)
  glossaryId=proposal['context']['glossaryId'];r.update(findingId=proposal['findingId'],glossaryId=glossaryId,approvedGlossary=layer[glossaryId],decision='accept objective full replacement',reason=REASONS[ordinal],acceptedFullTarget=target,acceptedFullTargetSha256=th(target),protectedSyntaxPreflight='passed v4 exact grammar plus prefix/tokens/digits/whitespace/line breaks',semanticPreflight='source facts/participants/agency/instruments/time/modality/reveal and all unchanged sentences checked against actual branch and approved glossary',assembledPreflight='Actual pinned RunLine with0 substitutions. Prefix and every unrelated sentence unchanged; no dynamic inputs/joins introduced. Adjacent text from actual bytecode, not flattened JSON.',independentReadCredit=0)
  rows.append(r);path=ROOT/r['authoredPath']
  if r['authoredPath'] not in docs:original[r['authoredPath']]=path.read_bytes();docs[r['authoredPath']]=load(path)
  e=next(e for e in docs[r['authoredPath']]['entries'] if e['id']==int(r['stableId'].rsplit(':',1)[1]));assert e['target']==r['target'];e['target']=target
 assert set(TARGETS)=={r['acceptedOrdinal'] for r in rows} and len(docs)==2
 after={p:rewrite_targets(original[p],doc) for p,doc in docs.items()};files=[]
 for folder in ['before-authored-files','after-authored-files','before-validation-files']:(C/folder).mkdir()
 # Freeze both old files and both owning sidecars before any canonical target mutation.
 for path in docs:
  p=ROOT/path;side=p.with_suffix('.validation.json');name=p.name
  (C/'before-authored-files'/name).write_bytes(original[path]);(C/'after-authored-files'/name).write_bytes(after[path]);(C/'before-validation-files'/side.name).write_bytes(side.read_bytes())
  files.append(dict(authoredPath=path,beforeSnapshotPath=str((C/'before-authored-files'/name).relative_to(ROOT)),beforeSha256=hashlib.sha256(original[path]).hexdigest(),afterSnapshotPath=str((C/'after-authored-files'/name).relative_to(ROOT)),afterSha256=hashlib.sha256(after[path]).hexdigest(),validationPath=str(side.relative_to(ROOT)),beforeValidationSnapshotPath=str((C/'before-validation-files'/side.name).relative_to(ROOT)),beforeValidationSha256=sha(side),changedIds=[r['stableId'] for r in rows if r['authoredPath']==path]))
 decisions=[dict(r,authorDecision=REASONS[r['acceptedOrdinal']] if r['acceptedOrdinal'] in TARGETS else 'Retain exact: actual group membership is already exclusive where retrospective, or inclusive in later invitation/action branches. No objective preference edit.',correction=r['acceptedOrdinal'] in TARGETS,independentReadCredit=0) for r in b['rows']]
 save('correction-decisions.json',dict(rows=rows,dependentConceptDecisions=decisions,dismissedConcerns=review['dismissedConcerns'],additionalObjectiveFindings=[],authorIndependentCredit=0))
 save('plan.json',dict(schemaVersion=7,locale='fil',gameVersion='1.3.19',sourceLocale='ru',status='complete two-unit consolidated author adjudication/preflight before mutation',rows=rows,files=files,acceptedCorrections=2,sourceAndGlossaryFingerprints=pre['sourceAndGlossaryFingerprints'],preserveExactManifestSha256=pre['preserveExactManifestSha256'],firstPassProgressSha256=pre['firstPassProgressSha256'],compiledProgramSha256=b['compiledProgramSha256'],preimagePinsSha256=sha(C/'preimage-pins.json'),boundedInputsSha256=sha(C/'bounded-author-inputs.json'),correctionDecisionsSha256=sha(C/'correction-decisions.json'),review06CompletionManifestSha256=pre['review06CompletionManifestSha256'],review06VerdictSha256=pre['review06VerdictSha256'],previousClosureSha256=pre['previousClosureSha256'],previousPairedSha256=pre['previousPairedSha256'],priorAuthorChainSha256=pre['priorAuthorChainSha256'],priorTargetOnlyEvents=143,allOtherTargetsAndMetadataUnchanged=True,derivedRule='Two standalone dialogue units; unchanged option/static/credits recipes must remain exact. Rebuild only if concrete changed source intersects recipe.',fullRestartPredicateObserved=False,independentAcceptance=False,unresolved=[]))
 journal=[]
 for f in files:
  p=ROOT/f['authoredPath'];assert sha(p)==f['beforeSha256'];p.write_bytes(after[f['authoredPath']]);assert sha(p)==f['afterSha256'];journal.append(dict(path=f['authoredPath'],result='exact planned full replacements applied'))
 save('application-journal.json',dict(planSha256=sha(C/'plan.json'),files=journal,boundary='All preimages frozen and all full replacements preflighted before first write; per-file mutation is not a cross-file transaction. Final gates reconcile both files.'))
 print(json.dumps({'applied':2,'batches':2,'otherTargetsAndRawBytes':'unchanged'}))
if __name__=='__main__':main()
