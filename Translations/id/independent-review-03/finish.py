"""Seal manually authored full-unit semantic decisions and unchanged-hash verdict."""
import datetime, hashlib, json
from pathlib import Path
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
def load(p):return json.loads((R/p).read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def write(name,value):
    p=O/name;assert not p.exists(),p
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
reasons={
211:'Full contact label identifies the child’s female friend, not the answering mother. Daughter_Asking_3 instructions17–21 bind DaughtersFriend/GetPhoneNumber/one format slot/UnlockPhoneNumber. The approved phone-numbers rule and unchanged source-only mother context agree.',
8343:'Adults invite the same female friend and she is permitted to go; when the child invites her, the child is scolded. Current clause subjects and action direction preserve the contrast after the corrected introduction and phone line.',
8344:'Complete replacement retains hesitant child request and invitation, and now explicitly introduces her female friend. Playing at the house is supported by the child context and source-only invitation phrasing. Prefix and all other wording retained.',
9898:'Second player option preserves uncertainty about whether her father will collect her and lack of knowledge of what happened to him. Compiled option branches to Daughter_Asking_3_2; no claim of confirmed death added.',
9899:'First player option preserves not knowing what the child witnessed and the qualified inference that her father died. Compiled option branches to Daughter_Asking_3_1; remains distinct from the uncertain alternative.',
9900:'Child asks permission to watch cartoons on the television seen in the player’s room. First-person seeing, location and permission question retained; Anda agrees with established respectful address.',
9901:'Child asks what the player means; question and respectful address retained. Actual instruction14 precedes the television/friend requests.',
11424:'Final narration recalls the deceased female friend as a good and attractive girl. gadis and Cantik preserve both facts without converting her to an adult woman.',
11425:'Profane reaction to the drowning remains profane and expresses the catastrophic situation. Sialan, kacau sekali retains the intended register.',
11426:'Female friend was walking drunk, misstepped, fell into a river and drowned. Current complete unit preserves that causal order, agency and river; dia refers back to the corrected female introduction.',
11427:'Rhetorical question introduces the subsequent revelation about the friend; current Indonesian question performs the same transition in the actual compiled sequence.',
11428:'Complete unit preserves locating her photograph, printing it, and posting missing-person notices everywhere. In this consecutive completed narrative, mencari fotonya followed immediately by mencetaknya entails that they obtained the photograph; no unresolved search or different result is stated. No preference-only replacement proposed.',
11429:'Complete corrected first introduction now preserves the female friend, plural group relationship, elapsed days, homeward trip and failure to reach home. Later gadis is not used as a substitute for this initial disclosure.',
11430:'Initial narration preserves another occasion of collective drinking. Suatu kali and lagi convey the recurring event; no later outcome is disclosed early.',
12115:'Restored callback retained unchanged. Daughter_Ears_Gun instruction4 now introduces the female best friend; Listen branch runs Daughter_Ears_DontShoot, whose instructions1–7 keep the same friend/mother antecedent. temanku naturally refers back to that established female friend, and father pickup chronology is preserved. Reopening the prior generic-callback decision is unsupported.',
12123:'Listen choice retains its imperative meaning. It is distinct from Shoot and enters Daughter_Ears_DontShoot on the decoded branch.',
12124:'Shoot choice retains its imperative meaning. It is distinct from Listen and enters Daughter_Death on the decoded branch.',
12125:'Complete corrected comparison preserves sometimes, the player as addressee, female identity and best-friend relationship. The unchanged prefix/hesitation remain exact; the following callback has a clear antecedent.',
12126:'Child asks whether the player wants to hurt her. Current wording keeps modality, agent and recipient in the weapon-threat context; no agency reversal.',
12127:'Child threatens to tell about this incident too. First-person future intention and additive too are retained, without inventing the person she will tell.',
12128:'Child’s startled interjection remains a short startled interjection after SetupGun true. No additional injury claim is required by Aduh in this context.'
}
delta=list(map(json.loads,(R/'Translations/id/semantic-correction-cycle-03/delta-review-rows.jsonl').read_text().splitlines()))
assert set(reasons)=={r['sourceOrderIndex'] for r in delta}
coverage=[]
for i,r in enumerate(delta,1):
    coverage.append({**r,'deltaIndex':i,'reviewer':'/root/id_independent_review_03',
      'sourceTargetRead':True,'replacementUnit':'complete current target display cell',
      'sourceSha256':sha(r['source'].encode()),'targetSha256':sha(r['target'].encode()),
      'status':'no-objective-correction-found','findingId':None,'reason':reasons[r['sourceOrderIndex']],
      'contextEvidence':'Translations/id/independent-review-03/compiled-context.json',
      'runtime':'not exercised'})
write('coverage.json',coverage)
initial=load('Translations/id/independent-review-03/verification-initial.json')
for p in initial['pins']:assert sha((R/p['path']).read_bytes())==p['sha256'],p['path']
layer=load('Documentation/glossary-translations/id/layer.json')
canonical=load('/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary-translations.json')['id']
assert layer==canonical and len(layer)==201
now=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
telemetry={'model':'GPT-6 family per system context; exact model identifier not exposed',
 'reasoning':'unknown','inputTokens':'unknown','cachedInputTokens':'unknown','outputTokens':'unknown',
 'reasoningTokens':'unknown','totalTokens':'unknown','measurementCutoffUtc':now,
 'collection':'No per-agent/request counter is exposed in the available tool metadata. No estimates from text length or file size.',
 'reportingTail':'unmeasured; report cannot measure its own later output or platform overhead'}
write('findings.json',{'schemaVersion':1,'reviewer':'/root/id_independent_review_03',
 'verdict':'clean independent exact delta on unchanged pins','textFindings':0,'selectorFindings':0,'rows':[],
 'resolvedChecks':[{'sourceOrderIndex':12115,'decision':'preserve unchanged callback','reason':reasons[12115]},
                   {'sourceOrderIndex':11428,'decision':'no objective correction','reason':reasons[11428]}]})
write('verification-final.json',{'initialVerificationSha256':sha((O/'verification-initial.json').read_bytes()),
 'hashChecksAtStartAndEnd':initial['hashChecks'],'distinctPinnedPaths':len({p['path'] for p in initial['pins']}),
 'allPinnedInputsUnchanged':True,'deltaCoverageRows':21,'unreadDeltaRows':0,
 'mandatoryUniqueIds':845,'mandatoryCurrentDeltaReads':10,'mandatoryExactPriorDecisionsReused':835,
 'currentClosureIds':1414,'reusedClosureDecisions':1393,'exactThreeFullUnitChanges':True,
 'canonicalLocaleGlossaryEqualsApprovedSnapshot':True,'glossaryEntries':201,
 'structuralVerificationAttempts':[{'attempt':1,'result':'review helper failed before final receipt on optional key None; earlier evidence preserved'},
 {'attempt':2,'result':'review helper failed because source-only manifest is a documented projection of source records, not entire inventory rows'},
 {'attempt':3,'result':'projection identity reconciled exactly; complete verifier passed; no authored or shared mutation in any attempt'}],
 'completedAtUtc':now})
write('review.json',{'schemaVersion':3,'reviewer':'/root/id_independent_review_03','completedAtUtc':now,
 'gameVersion':'1.3.19','sourceLocale':'ru','targetLocale':'id',
 'scope':'21 exact cycle03 delta units plus applicable independent mandatory decisions; offline text only',
 'verdict':'clean independent exact delta on unchanged artifact and closure hashes','cleanIndependentVerdict':True,
 'editorialAcceptance':'root final deterministic gate and integration pending',
 'deltaRowsRead':21,'unreadRows':0,'textFindings':0,'selectorFindings':0,
 'threeAppliedReplacements':'all accepted as full units in actual decoded consumer context',
 'selectorRepair':'normal recipe covers подруг*/подруж*, compiled phone contact and restored ear callback without generated-ID append',
 'closureSha256':'6489d453612e70fcc1ace025df924d86ded7c968be4a74cc4db7187c9bec8eb2',
 'deltaSha256':'662678567b5bf8984d1df69b700277bf5c718140c7d7870437bcddcde26e7510',
 'deltaArithmetic':initial['arithmetic'],'reusedCurrentClosureDecisions':1393,
 'mandatoryCatalog':{'uniqueIds':845,'currentDeltaReads':10,'reusedExactApplicablePriorIndependentDecisions':835,'newGenderRows':9,'status':'clean'},
 'hashChecks':initial['hashChecks'],'hashMismatches':[],'unchangedPinsAtReviewEnd':True,
 'sourceOnlyPhoneContext':{'rows':60,'acceptedOverlap':0,'status':'exact unchanged prior context applicable; key introduction/mother source lines checked','runtimeReachability':'unverified'},
 'retiredDependencies':{'count':38,'unchangedValues':True,'recordedFormerComponentsAndReasonsVerified':True,'rereadRequired':False},
 'resolvedPriorQuestions':['BodyEater UI mimpi remains unchanged and supported by prior static consumer evidence','Fatman singular-object proposal remains rejected and unchanged'],
 'limits':{'gameLaunch':'not run','actualDynamicSubstitution':'not run','renderedLayoutFontWrapping':'not tested',
           'installationPackaging':'not run','imagesTextures':'excluded by owner','compiledContext':'Static wire-decoded instruction and branch correspondence, no VM execution or global reachability proof'},
 'telemetry':telemetry,'nextAction':'Root runs the final full machine gate on unchanged inputs and owns canonical integration. This clean delta does not certify runtime, visual, packaging or release readiness.'})
write('evidence-manifest.json',{'schemaVersion':1,'cutoffUtc':now,
 'files':[{'path':str(p.relative_to(R)),'sha256':sha(p.read_bytes())} for p in sorted(O.iterdir()) if p.is_file()],
 'immutableBoundary':'All independent review evidence confined to this new directory; authored, source/glossary, shared state/scripts and Git/index untouched.'})
print(json.dumps({'verdict':'clean','rows':21,'pins':initial['hashChecks'],'mandatory':845,'completedAtUtc':now,'telemetry':telemetry}))
