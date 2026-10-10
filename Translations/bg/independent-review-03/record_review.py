"""Seal the independently completed full-pair decisions without editing authored text."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).parent
BG=ROOT/'Translations/bg'
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
tsha=lambda s:hashlib.sha256(s.encode()).hexdigest()
idbytes=lambda ids:('\n'.join(ids)+('\n' if ids else '')).encode()

def write(name,value):
    p=OUT/name
    assert not p.exists(), 'Immutable review already exists: '+name
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

d=load(BG/'semantic-delta-cycle-003.json')
c=load(BG/'semantic-closure-cycle-003.json')
plan=load(BG/'correction-batch-003.json')
pins=load(OUT/'input-verification.json')
rows=d['nextReviewRows']; current={r['stableId']:r for r in c['reviewRows']}
adjudications=load(BG/'independent-review-02-author-adjudication.json')['adjudications']
findings=[]

def finding(suffix,sid,reason,proposed,scope):
    row=current['string:444ff14f1967f5a4c8eb9e4cf4c913f1:'+sid]
    findings.append({'findingId':'bg-independent-03-'+suffix,'stableId':row['stableId'],
                     'category':'source meaning / idiomatic naturalness', 'scope':scope,
                     'source':row['source'],'currentFullTarget':row['target'],
                     'proposedFullTarget':proposed,'reason':reason,
                     'sceneNodes':row['sceneNodes'],'authoredPath':row['authoredPath'],
                     'sourceSha256':tsha(row['source']),'targetSha256':tsha(row['target']),
                     'applied':False})

finding('001','110504455814848520',
        "In Bald_Asking_4:25, Russian 'Я как-то вернулся домой' introduces one past occasion before he finds his injured family. Bulgarian 'Прибрах се някак' says he somehow managed to get home. The chronology-to-manner shift is unsupported; the subsequent attackers and flight do not precede this arrival. The mother/grandmother correction is correct and remains intact.",
        'Bald: Веднъж се прибрах вкъщи. Вратата отворена. Всичко с главата надолу. Мама и баба лежат със… мамка му… със счупени пръсти, крака и…',
        'exact delta; newly selected family-reference dependency')
finding('002','110504454481059851',
        "Scammer_Asking_2_3_2:3 uses standalone Russian slang 'Отвечаю' to vouch for his survival strategy, before explaining his relationship with KIS. Bulgarian 'Отговарям' literally says he is answering and supplies no object or question. This is an assurance, not an answer. Preserve the whole strategy statement and use an idiomatic assurance.",
        'Scammer: Трябва да видиш кой управлява положението и да си с него. Това е печеливша стратегия. Гарантирам.',
        'exact delta; explicitly invalidated same-scene dependency')
finding('003','110504454460088329',
        "The same literal assurance calque occurs in Scammer_Asking_1_2:3 after his claim about profitable betting schemes. A bounded search of all accepted Russian dialogue found exactly two 'Отвечаю' occurrences; both current targets end with 'Отговарям.' Both full pairs and their compiled scenes were read, so this shared semantic defect must be corrected together.",
        'Scammer: Да въртя схеми със залози беше лесно като детска игра, мамка му. Гарантирам.',
        'bounded supplementary dependency; outside 311-row delta')
issues={f['stableId']:f for f in findings}
write('findings.json',{'schemaVersion':1,'locale':'bg','status':'one consolidated objective batch; not applied',
                      'findings':findings,'findingCount':3,'deltaFindings':2,'supplementaryFindings':1,
                      'selectorDefectCount':0,
                      'boundingEvidence':{'standaloneRussianOtvechayuCount':2,'matchingBadTargetCount':2,
                                          'currentTargetPribrahSeNyakakCount':1},
                      'nextAction':'Adjudicate the entire batch, perform one consolidated bounded remedial review of these idioms and their real dependencies, then generate and independently review the exact final delta. No source/glossary/binding change or unbounded systemic issue requires a full semantic restart.'})
ledger=[]
for i,r in enumerate(rows):
    ledger.append({'deltaIndex':i,'stableId':r['stableId'],'sourceIndex':r['sourceIndex'],
                   'sourceSha256':tsha(r['source']),'targetSha256':tsha(r['target']),
                   'fullPairRead':True,'sceneNodes':r['sceneNodes'],
                   'verdict':'objective finding' if r['stableId'] in issues else 'no objective correction proposed after independent full-unit read',
                   'findingId':issues.get(r['stableId'],{}).get('findingId')})
write('per-id-read-verdicts.json',ledger)
readraw=idbytes([r['stableId'] for r in rows])
assert readraw==(BG/'semantic-cycle-003-review.ids').read_bytes()
(OUT/'read.ids').write_bytes(readraw)

dismissed=[a for a in adjudications if a['disposition']=='dismissed']
assert len(dismissed)==3
dismissed_verdicts=[]
for a in dismissed:
    r=current[a['stableId']]
    assert (r['source'],r['target'])==(a['source'],a['currentFullTarget'])
    dismissed_verdicts.append({'findingId':a['findingId'],'stableId':r['stableId'],
                               'source':r['source'],'currentFullTarget':r['target'],
                               'reviewerProposedFullTarget':a['reviewerProposedFullTarget'],
                               'fullPairRead':True,'inDelta':r['stableId'] in set(d['components']['review']['ids']),
                               'verdict':'dismissal independently upheld',
                               'reason':a['reason']+' Complete current pair and actual compiled scene inspected; no missing action, gender or fact is restored by the proposed generic oath.'})
write('dismissed-proposals-verdicts.json',dismissed_verdicts)
correction_verdicts=[]
for r in plan['decisions']:
    correction_verdicts.append({'stableId':r['stableId'],'basis':r['basis'],
                                'sourceSha256':tsha(r['source']),
                                'historicalPreimageSha256':tsha(r['currentFullTarget']),
                                'currentFullTargetSha256':tsha(r['acceptedFullTarget']),
                                'fullPairRead':True,'verdict':'corrected full unit independently accepted; no objective further change',
                                'reason':'Full source meaning, original unchanged facts, voice, Bulgarian grammar, speaker identity and scene consumer checked.'})
write('corrected-unit-verdicts.json',correction_verdicts)
suppids={a['stableId'] for a in dismissed if a['stableId'] not in set(d['components']['review']['ids'])}
suppids.add(findings[2]['stableId'])
supplementary=[dict(current[sid],fullPairRead=True,verdict='objective finding' if sid in issues else 'dismissal independently upheld',findingId=issues.get(sid,{}).get('findingId')) for sid in sorted(suppids,key=lambda sid:current[sid]['sourceIndex'])]
assert len(supplementary)==3
write('supplementary-pair-verdicts.json',supplementary)

fresh=pins['mandatoryFreshIds']; reuse=pins['mandatoryPriorApplicableIds']
(OUT/'mandatory-fresh-read.ids').write_bytes(idbytes(fresh))
(OUT/'mandatory-prior-applicable.ids').write_bytes(idbytes(reuse))
write('mandatory-verdicts.json',{'mandatoryIds':908,'fresh':4,'priorExactApplicable':904,
                                'freshDecisions':[v for v in ledger if v['stableId'] in set(fresh)],
                                'groups':{k:{'count':v['count'],'idsSha256':v['idsSha256'],
                                              'fresh':len(set(v['ids'])&set(fresh)),
                                              'reused':len(set(v['ids'])&set(reuse)),
                                              'result':'no objective correction; exact independent applicability verified'} for k,v in c['mandatoryRegressionGroups'].items()},
                                'result':'catalog clean on current hashes; overall delta remains not clean because of nonmandatory findings'})
write('selector-verdict.json',{'voiceSelectorSha256':sha(BG/'voice-risk-selector-v6.json'),
                              'normalCandidatesSha256':sha(BG/'voice-remedial-candidates-v6.json'),
                              'normalCandidateCount':741,'speakerCategories':112,
                              'positiveAndNegativeControls':pins['normalLexicalControls'],
                              'sixPriorMissesNormallySelected':pins['normalSelectedMisses'],
                              'manualIdAppend':False,'closureRegeneration':'2839 exact IDs; no retired dependency',
                              'deltaRegeneration':'311 exact IDs from41 corrected,190 without applicable prior read,121 explicit invalidations; components overlap',
                              'verdict':'no additional bounded selector defect; source lexical selection is candidate selection, not a semantic verdict',
                              'limits':'No claim of a universal profanity lexicon or fresh semantic reading of unchanged741 candidates.311 exactdelta was read; remaining candidate decisions retain exact prior evidence. Newly discovered assurance calque has exactly two inventoried occurrences and is passed as a bounded future correction dependency.'})

review={'schemaVersion':1,'reviewer':'/root/bg_independent_review_03',
        'independence':'Separate no-history reviewer; no delegation; owns only NEW independent-review-03 evidence',
        'model':'GPT-6 family; exact backend identifier not exposed','reasoningLevel':'not exposed',
        'game':"No, I'm not a Human",'gameVersion':'1.3.19','sourceLocale':'ru','targetLocale':'bg',
        'status':'independent review complete with3 objective full-unit findings; CLEAN rejected',
        'deltaSha256':sha(BG/'semantic-delta-cycle-003.json'),'closureSha256':sha(BG/'semantic-closure-cycle-003.json'),
        'correctionPlanSha256':sha(BG/'correction-batch-003.json'),
        'coverage':{'completeDeltaPairsRead':311,'indicesInclusive':[0,310],
                    'supplementaryUniqueFullPairsRead':3,'totalDistinctFreshIndependentPairs':314,
                    'correctedFullUnitsReadAndAccepted':41,'dismissedProposalsReadAndUpheld':3,
                    'priorReadingApplicableCount':2649,'invalidatedReasonsIndependentlyReconstructed':121,
                    'closureIds':2839,'retired':0,'mandatoryIds':908,'freshMandatoryReads':4,
                    'exactPriorApplicableMandatoryReads':904,'author982ScopeNotCountedAsIndependent':True,
                    'allCorpusRereadClaim':False,'readIdsSha256':sha(OUT/'read.ids')},
        'findings':{'fullUnitCount':3,'inDelta':2,'supplementary':1,'selectorDefects':0,'applied':False,
                    'path':'Translations/bg/independent-review-03/findings.json','sha256':sha(OUT/'findings.json')},
        'specialChecks':{'BaldFamily':'mother and grandmother retained; father appears separately in later source/glossary',
                         'LeperExclamation':'bothЁбаный свет units are idiomatic exclamations, no literal light',
                         'WheelchairPlural':'compiled IsImposter branch: instruction6 pluralим→7все они; corresponding Bulgarianим→всички те accepted. Duplicate source table pair accepted without inventing a current consumer.',
                         'NaturalProfanity':'all41 full replacements checked in complete scenes; idiomatic beatings,omитай,майната,Ебаси,през кура and contextual oath use accepted. No generic-oath quota applied; three dismissals independently upheld.',
                         'MalformedGrammar':'WheelchairЭто…пиздец nowпълен шибан ужас; no malformedпълна шибания remains in that corrected unit'},
        'preflight':{'freshOwningWholeLocaleGuard':'passed16538 unique current authored units including preserve-exact grammar; new ownreceipt',
                     'currentAuthoredAndSidecarPins':'411+411verified','historicalReview02ChangedPins':70,
                     'all41HistoricalFullPreimages':'exact independently sealed rows,including one supplemental pair',
                     'sourceGlossaryParity':'source hash unchanged; all201 approvedBG glossary entries equal currentcanonical layer',
                     'ordinaryClosureDeltaVoiceReproduction':'passed without overwriting historical evidence'},
        'context':{'compiledRawProgramSha256':pins['compiledProgramSha256'],'compiledNodes':3255,
                    'compiledReparse':'normalized exact equality with immutable prior parsednodes',
                    'deltaRowsWithCurrentCompiledUses':302,'deltaRowsWithoutCurrentCompiledUses':9,
                    'noCurrentConsumerIds':pins['deltaWithoutCompiledUses'],
                    'deltaFormatSlots':0,'closureFormatSlots':111,
                    'dynamicProducerCalls':pins['measuredCompiledDynamicProducerCalls'],
                    'managedSources':pins['managedSourceSha256'],
                    'dynamicBindingApplicability':pins['dynamicApplicability'],
                    'methodsChecked':'GetLocalization,SetupConsumable,InitGotTexts,GetCharacterOnPlace,GetLocalizedLine,HandleLine/HandleOptions expansion before markup; runSelectedOptionAsLine=false; localized name/narrative distinct; literal quantity suffix retained',
                    'physicalRuntime':'not run; ownerprohibited game launch','visualFontsLayout':'not run',
                    'builtBGArtifact':'not built; editorial review of authored text only'},
        'acceptance':{'independentClean':False,'mandatoryCatalogClean':True,'editorialAccepted':False,
                       'runtimeAccepted':False,'releaseAccepted':False,'imagesAndTextures':'excluded by owner'},
        'telemetry':'Parent collects measured token usage; this agent has no per-request counters; unknown here, notzero; reporting tail unmeasured',
        'nextAction':'Adjudicate all3 findings together; carry the two assurance occurrences as one shared bounded defect; consolidated remedial idiom/dependency pass and one exact final independent delta. Preserve source/glossary and unchanged evidence; no full restart warranted by these bounded findings.'}
write('review.json',review)
print(json.dumps({'deltaPairs':311,'supplementaryPairs':3,'correctedAccepted':41,'dismissalsUpheld':3,'findings':3,'independentClean':False}))
