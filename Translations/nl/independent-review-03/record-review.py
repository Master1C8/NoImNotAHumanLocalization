"""Record model-authored full-unit decisions; scripts only verify and serialize."""
import json,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Scripts'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads((ROOT/p).read_text())
def write(name,value,jsonl=False):
    p=OUT/name;assert not p.exists()
    if jsonl:data=''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in value)
    elif isinstance(value,str):data=value
    else:data=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
    p.write_text(data)
notes=[
"Occupant is present; uncertainty about getting along is retained. Label introduction does not assert residence or change the plural 'we'.",
"Surprised recognition and presence are retained; the raw label is introduced without adding an article or singular agreement.",
"Fear of discomfort and the condition of sharing the same room are retained; collective 'gezelschap' accepts either individual or group labels.",
"Prior presence, exactly that occupant's past belittling, and the reason being his appearance are all retained. Actual place-compatible descriptors include a woman, and 'die persoon' remains neutral.",
"The brief recognition of an occupant here is retained; the descriptor is isolated as an identifying label.",
"Presence with the player and a tentative joint proposal to eject the occupant are retained; 'die' does not impose gender or number.",
"The identity question and occupant's presence with the player are retained; the dash attaches the supplied label to the question.",
"Apology, occupant presence, distrust of such people, and trailing hesitation are retained; formal address remains 'u'.",
"Dislike of the identified occupant is retained; collective introduction avoids forced singular personal agreement for the place-compatible Couple label.",
"Recognition and presence with the player are retained; the raw label follows an identifying colon.",
"The hearth question, prior presence, immediate judgment and female wolf-in-sheep's-clothing metaphor are retained. The feminine metaphor comes from the source; synthetic male substitutions do not authorize silently changing it.",
"Fear and an occupant already seated with the addressee are retained. Getter argument is Alkonost and the normal competing place candidate is Raskolnikov; arbitrary Sirin examples are not established inputs here.",
"Surprise, the identity question about the person sitting with the player, and 'what a meeting' are all retained.",
"The occupant-presence identity question remains attached to the raw label; informal address is retained.",
"The interjection and observation that the bathroom is already occupied are retained; no residence or citizenship is asserted.",
"The coarse interjection and already-present company are retained; the home setting is established by the entrance scene rather than by a new residence claim.",
"Hesitation, observation, prior presence in the house and formal address are retained.",
"The request not to misunderstand and presence at home are retained; the comma and colloquial address introduce no new fact.",
"Conditional willingness to enter, obstacle of an already-present occupant, and the occupant's continuing concern about tomorrow are retained. Compatible labels are individual characters, so 'die persoon' is supported.",
"Narrated dislike and the full pointing order occupant → self → occupant are retained. The speaking actor remains a man. Doc/Nervous are the relevant other same-place candidates, so both 'hem' references remain supported; Ballerina/Sirin illustrations are synthetic here.",
"The child's brief surprised recognition and occupant presence are retained; raw labels include individual or Couple descriptors without forcing singular agreement.",
"Prior presence, inability to extract money, and inability to get entertaining stories are retained. The collective/neutral 'Daar' does not invent a resident or alter the negative meaning.",
"Thanks, realization somebody is already here, refusal to enter and its occupancy condition are retained. The template no longer asserts a singular current inhabitant's identity as a complete noun phrase.",
"The demand that the identified occupant leave first, profanity, and speaking afterward remain in order.",
"Human address, capitalized SUN, its prohibition, the conditional duration and concealed presence in the house are retained; collective phrasing preserves possible group labels.",
"Willingness to enter, present-time obstacle and occupant presence there are retained; 'op dit moment' does not become permanent residence.",
"Reluctance to inconvenience formal 'u', both members' inability to live alongside the identified company and the nearby condition are retained. The collective phrase allows the place-compatible pair descriptor.",
"The occupant-presence question remains an identity question with the descriptor attached; Anger's place includes the actual plural UI descriptor 'twee zussen'.",
"The occupant-presence question remains attached to the label. The home setting follows the entrance scene; no ownership or permanent residence is inferred.",
"Apology, seen occupant presence, formal address and questioning force remain; the dash introduces the descriptor rather than ending the question before it.",
"The claimed feeling of an occupant here and judgment that something is wrong with that person are retained as Blind's impressions, not objective evidence. The place contains individual characters, including the female FortuneTeller; 'die persoon' is neutral.",
"The offer remains something given for the purpose of the player using the player's own gun against them. 'zodat' restores purpose; ellipses and euphemistic unfinished violence are preserved.",
"Profane recognition, demand to eject the occupants, unwillingness to fight and the bath motive are all retained. The standalone label avoids a bare descriptor being forced into the subject of a finite clause.",
"Friendly 'maatje', observation of somebody already warming a place and informal address are retained. A who-clause introduces the raw label without changing the agency.",
"Occupant already on the sofa, the speaker's hesitation and fear of such men are retained. Other same-place candidates are Esenin/Rocker/TaxiDriver, all male individuals; arbitrary female/plural substitutions are not evidence against this sentence.",
"Inability to enter, friendly address, having previously encountered such people and this occupant's presence in the house are retained. No continuing residence is asserted.",
"The identifying question, formal address and occupant presence here are retained; punctuation makes the question explicit without changing the referent.",
"Apology, wish not to sound rude and the already-present occupant are retained. The exact label follows collective company rather than functioning as an incomplete noun phrase.",
"Tentative refusal and occupant presence here are retained. This accepted inventory key is absent from the compiled program; the text decision does not assert its consumer or live reachability.",
"Every sentence remains: recognition; already-present occupant; one glance establishing the impression; everybody keeping quiet and bowing to others to avoid being disturbed; inability to tolerate such people. The collective plural and conditional purpose are retained. The accepted key is not compiled, so no arbitrary descriptor is asserted as a live input."
]
delta=[json.loads(l) for l in (ROOT/'Translations/nl/semantic-cycle-3/closure-v2/delta-review-rows.jsonl').read_text().splitlines()]
assert len(notes)==len(delta)==40
adjudication=load('Translations/nl/semantic-cycle-3/adjudicated-corrections-v3.json')
prior=load('Translations/nl/semantic-cycle-2/closure/closure-manifest.json');now=load('Translations/nl/semantic-cycle-3/closure-v2/closure-manifest.json')
oldhash={v['path']:v['sha256'] for v in prior['manual']['authoredBatches']}
changes={}
for r in adjudication['corrections']:changes.setdefault(r['authoredPath'],[]).append(r)
reconstruction=[]
for v in now['manual']['authoredBatches']:
    p=v['path'];raw=(ROOT/p).read_bytes()
    if p in changes:
        doc=json.loads(raw)
        for r in changes[p]:
            entry=next(e for e in doc['entries'] if str(e['id'])==r['stableId'].rsplit(':',1)[-1]);assert entry['target']==r['after'];entry['target']=r['before']
        restored=(json.dumps(doc,ensure_ascii=False,indent=2)+'\n').encode()
        assert hashlib.sha256(restored).hexdigest()==oldhash[p]
        reconstruction.append({'path':p,'beforeSha256':oldhash[p],'afterSha256':sha(ROOT/p),'correctedUnits':len(changes[p]),'priorBytesReconstructedExactly':True})
    else:assert sha(ROOT/p)==oldhash[p]
assert len(reconstruction)==38
write('batch-reconstruction.json',{'changedBatches':38,'correctedIds':40,'reconstructed':reconstruction,'unchangedBatchCount':len(now['manual']['authoredBatches'])-38,'noCollateralAuthoredChange':True})
canonical=load('/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary-translations.json')
snapshot=load('Documentation/glossary-translations/nl/layer.json');assert canonical['nl']==snapshot
write('glossary-parity.json',{'status':'passed','entries':len(snapshot),'snapshotSha256':sha(ROOT/'Documentation/glossary-translations/nl/layer.json'),'canonicalRawSha256':sha(Path('/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary-translations.json')),'comparison':'entire approved Dutch layer exact JSON value equality; other layers neither reviewed nor changed'})
from preserve_exact import check_value
manifest=load('Source/preserve-exactly-v4.json');rules={r['stableId']:r for r in manifest['tableRows']+manifest['staticRows']}
consumers=json.loads((OUT/'assembled-consumers.json').read_text());consumerbyid={r['stableId']:r for r in consumers['examples']}
decisions=[]
for i,(r,note) in enumerate(zip(delta,notes),1):
    assert not check_value(rules[r['stableId']],r['target'])
    decisions.append({**r,'deltaRow':i,'decision':'no-objective-text-finding-in-independent-read','fullUnitRead':True,'allUnchangedFactsChecked':True,'priorReview02Correction':'resolved in current complete target unit','semanticNote':note,'assembledConsumerEvidence':'Translations/nl/independent-review-03/assembled-consumers.json' if '{0}' in r['source'] else None,'assembledSamePlaceExampleCount':len(consumerbyid.get(r['stableId'],{}).get('rawLabelExamples',[])),'compiledSceneEvidence':'Translations/nl/independent-review-03/compiled-context.json' if r['nodeNames'] else None,'protectedValueCheck':'passed','reviewer':'/root/nl_independent_review_03'})
write('review-decisions.jsonl',decisions,True)
write('reviewed-ids.txt',''.join(r['stableId']+'\n' for r in decisions))
write('findings.json',{'verdict':'clean independent 40-ID text delta on unchanged pins','findings':[],'objectiveTextFindings':0,'sourceRuntimeLimits':consumers['preexistingSourceKeyLimits'],'sourceLimitClassification':'exact getter-key candidates are static place-compatible only; missing key observations are baseline runtime questions, not newly introduced Dutch defects or proof of reachable failure'})
preflight=json.loads((OUT/'preflight.json').read_text());retained=preflight['reusedUnchangedDecisions'];mandatory=set((ROOT/now['components']['mandatory-regressions']['path']).read_text().splitlines());fresh={r['stableId'] for r in decisions}
assert mandatory<={r['stableId'] for r in retained}|fresh
assert len(mandatory&fresh)==40 and sum(r['mandatoryRegression'] for r in retained)==529
write('regression-result.json',{'status':'passed static editorial catalog with exact hash-bound reuse','catalogRecipePath':now['recipePath'],'catalogRecipeSha256':now['recipeSha256'],'selectorGroupsSha256':now['selectorGroupsSha256'],'mandatoryIds':569,'freshFullUnitReads':40,'reusedUnchangedIndependentReads':529,'allUIAndStaticUnitsRetained':437,'dynamicConsumersRetained':58,'uiRawDescriptorLabelsRetained':57,'excludedItemGiftConsumer':1,'scope':'gender/kinship, guest/human terminology, profanity/wordplay, format/markup, complete UI/static; exact symbols/protected syntax checked on all 16538 current units','nonapplicable':'owner excluded images/textures; Dutch does not require RTL/bidi/shaping','notRun':['rendered font face/weights/fallbacks','narrow UI and wrapping','dialogue advancement','actual scene reachability','packaging/installation/release']})
write('checkpoint.json',{'gameVersion':'1.3.19','locale':'nl','sourceLocale':'ru','reviewer':'/root/nl_independent_review_03','reviewedPairs':40,'newObjectiveTextFindings':0,'reusedUnchangedDecisions':724,'previousClosureCount':921,'currentClosureCount':764,'correctedIds':40,'newDependencyIds':0,'explicitInvalidatedIds':0,'retiredDependencyIds':157,'verdict':'clean independent exact delta; final acceptance remains coordinator gate','runtime':'not-run','imagesTextures':'owner excluded','modelFamily':'GPT-6 per agent instructions','exactServingModel':'unknown','reasoningLevel':'unknown','usage':{'inputTokens':'unknown','cachedInputTokens':'unknown','outputTokens':'unknown','reasoningTokens':'unknown','totalTokens':'unknown'},'descendantAgents':0,'usageLimits':'No actual per-request telemetry exposed; failed helper attempts included in this same agent, with unknown token counts; final reporting tail unmeasured.'})
print('Saved 40 full-unit decisions; zero objective text findings; 38 batches reconstructed exactly; 569 mandatory rows accounted for.')
