"""Produce review evidence only; never writes authored or shared inputs."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'Scripts'))
import preserve_exact
import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from probe_assets import DEFAULT_GAME

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def ts(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
def read(p): return json.loads((ROOT / p).read_text())
def write(name, value):
    p = OUT / name
    assert not p.exists(), p
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
def jl(name, values):
    p = OUT / name
    assert not p.exists(), p
    p.write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in values))
def ids_sha(ids): return ts(''.join(x + '\n' for x in ids))

c = read('Translations/sr/semantic-cycle-001-closure.json')
rows = [json.loads(x) for x in (ROOT / c['reviewRows']).read_text().splitlines()]
extra = [json.loads(x) for x in (OUT / 'additional-context-rows.jsonl').read_text().splitlines()]
manifest = read('Source/preserve-exactly-v4.json')
canonical = [x['stableId'] for x in manifest['tableRows'] + manifest['staticRows']]
rules = {x['stableId']: x for x in manifest['tableRows'] + manifest['staticRows']}
assert len(canonical) == len(set(canonical)) == 16538
source = {}
for p in ('Source/localization-inventory-v3/strings.jsonl', 'Source/localization-inventory-v3/static-text.jsonl'):
    source.update({x['stableId']: x for x in map(json.loads, (ROOT / p).read_text().splitlines())})
guids = {'Dialogs': '444ff14f1967f5a4c8eb9e4cf4c913f1', 'UI': '0cbd8a7a4f543344bb95659de87f67a5', 'ChecksDialogs': '389c6d80595013c41b85a7197838c4b6'}
target = {}; location = {}; authored = []
for f in c['currentAuthoredFileHashes']:
    actual = sha(ROOT / f['path']); assert actual == f['sha256']
    batch = read(f['path']); assert len(batch['entries']) == f['units']
    for e in batch['entries']:
        identifier = e.get('stableId') or ('string:' + guids[batch['collection']] + ':' + str(e['id']))
        assert identifier not in target
        target[identifier] = e['target']; location[identifier] = f['path']
    authored.append(dict(f, actualSha256=actual, result='passed'))
assert set(target) == set(canonical)
set_hash = ts(''.join(f['path'] + '\t' + f['sha256'] + '\n' for f in sorted(authored, key=lambda x:x['path'])))
assert set_hash == c['currentAuthoredFileSetSha256']
assert [r['stableId'] for r in rows] == c['closureIds'] == [i for i in canonical if i in set(c['closureIds'])]
assert len(rows) == len(set(c['closureIds'])) == 687
assert ids_sha(c['closureIds']) == c['closureIdsSha256']
components = {}
for name, comp in c['componentLists'].items():
    assert len(comp['ids']) == comp['count'] and ids_sha(comp['ids']) == comp['idsSha256']
    assert comp['ids'] == [i for i in canonical if i in set(comp['ids'])]
    components[name] = dict(comp, result='passed')
assert set().union(*(set(x['ids']) for x in components.values())) == set(c['closureIds'])

pins = {
    'Source/localization-inventory-v3/strings.jsonl': c['sourceInventorySha256'],
    'Source/localization-inventory-v3/static-text.jsonl': c['sourceStaticSha256'],
    'Documentation/text-source-acceptance-v1.json': c['sourceAcceptanceSha256'],
    'Documentation/glossary-translations/sr/layer.json': c['glossaryFingerprint'],
    'Translations/sr/semantic-cycle-001-precorrection.json': c['precorrectionEvidenceSha256'],
    'Translations/sr/semantic-cycle-001-corrections.json': c['correctionEvidenceSha256'],
    'Translations/sr/semantic-cycle-001-static-regeneration.json': c['staticRegenerationEvidenceSha256'],
    c['currentPreserveExactReport']: c['currentPreserveExactReportSha256'],
    c['reviewRows']: c['reviewRowsSha256'], c['regressionCatalog']: c['regressionCatalogSha256'],
    'Source/preserve-exactly-v4.json': c['nontranslatableContextRuntime']['preserveExactManifestSha256'],
    'Translations/sr/static-authored-map.json': c['nontranslatableContextRuntime']['staticAuthoredMapSha256'],
    'Translations/sr/credits-role-map.json': c['nontranslatableContextRuntime']['creditsRoleMapSha256'],
    'Translations/sr/reproduce_static_draft.py': c['nontranslatableContextRuntime']['staticReproductionScriptSha256'],
    'Translations/sr/semantic-cycle-001-closure.json': '243bf0bbdacf698fe6199908086058a2923a72fb2a54b707bb8468d0d1979bfb',
}
for receipt in read('Documentation/text-source-acceptance-v1.json')['evidence'].values():
    pins[receipt['path']] = receipt['sha256']
verified_pins = []
for path, expected in pins.items():
    actual = sha(ROOT / path); assert actual == expected, path
    verified_pins.append({'path':path,'expectedSha256':expected,'actualSha256':actual,'result':'passed'})
assert ids_sha(c['changedIds']) == c['changedIdsSha256']
assert ts(json.dumps(c['nontranslatableContextRuntime'], ensure_ascii=False, sort_keys=True, separators=(',',':'))) == c['nontranslatableContextRuntimeSha256']

context = read(str((OUT / 'yarn-context.json').relative_to(ROOT)))
characters = read(str((OUT / 'character-runtime-data.json').relative_to(ROOT)))
assert characters['sourceSha256'] == sha(Path(characters['sourcePath']))
report = read('Source/glossary-corpus-v2/report.json')
bindings = ROOT / 'Source/glossary-corpus-v2/runtime-bindings.json'
assert sha(bindings) == report['runtimeBindingsSha256'] == context['bindingsSha256']
assert context['compiledProgramSha256'] == report['currentScope']['compiledProgramSha256']

dll = DEFAULT_GAME / 'NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed/Assembly-CSharp.dll'
pe = dnfile.dnPE(str(dll)); enums = {}; methods = {}
for t in pe.net.mdtables.TypeDef.rows:
    if str(t.TypeName) in ('ECharacterType','EConsumable'):
        values = {}
        for field in t.FieldList:
            for const in pe.net.mdtables.Constant.rows:
                if const.Parent.row is field.row:
                    values[str(int.from_bytes(const.Value.value,'little'))] = str(field.row.Name)
        enums[str(t.TypeName)] = values
    for m in t.MethodList:
        if str(t.TypeName) == 'DialogCommandsInstance' and str(m.row.Name) in ('GetCharacterOnPlace','LocalizeItem','GetCourierOrder','PeekDeficitItem') or str(t.TypeName) == 'ConsumablesController' and str(m.row.Name) == 'GetDeficitItem':
            body = read_method_body_from_bytes(pe.get_data(m.row.Rva)); ins=[]; strings=[]
            for i in body.instructions:
                operand = str(i.operand)
                if str(i.opcode) == 'ldstr':
                    operand = pe.net.user_strings.get(i.operand.value & 0xffffff).value; strings.append(operand)
                ins.append({'offset':i.offset,'opcode':str(i.opcode),'operand':operand})
            methods[str(t.TypeName)+'.'+str(m.row.Name)] = {'rva':m.row.Rva,'bodySha256':hashlib.sha256(body.get_bytes()).hexdigest(),'literalStrings':strings,'instructions':ins}
ui = {r['key']: r for r in rows if r['collection'] == 'UI'}
charrows = characters['rows']; byenum={enums['ECharacterType'][str(r['characterType'])]:r for r in charrows}
consumer_labels=[]
for node_name, node in context['nodes'].items():
    a=node.get('instructions',[])
    for index, ins in enumerate(a):
        if 'GetCharacterOnPlace' not in ins['operands']: continue
        owner_enum=a[index-2]['operands'][0]; owner=byenum[owner_enum]; choices=[]
        for candidate in charrows:
            enum=enums['ECharacterType'][str(candidate['characterType'])]
            if candidate['place'] != owner['place'] or enum == owner_enum: continue
            key='characterName_'+enum; label=ui.get(key)
            choices.append({'enum':enum,'serializedName':candidate['name'],'place':candidate['place'],'room':candidate['room'],'key':key,'labelStableId':label['stableId'] if label else None,'source':label['source'] if label else None,'target':label['target'] if label else None,'scope':'possible occupant by actual same-place predicate; game state/reachability not executed'})
        consumer_labels.append({'node':node_name,'instructionIndex':ins['index'],'argument':owner_enum,'place':owner['place'],'possibleLabels':choices})
fixture=ROOT/'runtime/No Human Probe.app/Contents/SharedSupport/prefix/drive_c/KS Games/No Im not a Human/NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/il2cppOutput'
snippets=[]
for filename,first,last in [('Assembly-CSharp__8.cpp',25458,25556),('Assembly-CSharp__8.cpp',25613,25690),('Assembly-CSharp__8.cpp',25813,25841),('Assembly-CSharp__8.cpp',26662,26746),('Assembly-CSharp__5.cpp',22933,23008),('YarnSpinner.cpp',15317,15408)]:
    p=fixture/filename; lines=p.read_text().splitlines(keepends=True)
    snippets.append({'path':str(p),'fileSha256':sha(p),'firstLine':first,'lastLine':last,'exactText':''.join(lines[first-1:last]),'scope':'read-only fixture generated source, corroborated by original shipped managed DLL for game methods'})
deficit=read(str((OUT/'deficit-consumable-config.json').relative_to(ROOT)))
deficit_labels=[]
for entry in deficit['fields']['_deficitConsumables']['_serializedList']:
    enum=enums['EConsumable'][str(entry['Key'])]; key='consumable_'+enum.lower()+'_name';label=ui[key]
    deficit_labels.append({'enum':enum,'key':key,'threshold':entry['Value'],'labelStableId':label['stableId'],'source':label['source'],'target':label['target']})
write('runtime-consumers.json', {'sourceDll':str(dll),'sourceDllSha256':sha(dll),'enums':enums,'methods':methods,'sourceAssetSha256':characters['sourceSha256'],'compiledProgramSha256':context['compiledProgramSha256'],'bindingsSha256':sha(bindings),'generatedSourceEvidence':snippets,'samePlaceLabelCandidates':consumer_labels,'deficitConfigSha256':sha(OUT/'deficit-consumable-config.json'),'deficitLabels':deficit_labels,'substitutionSemantics':'Yarn ExpandSubstitutions iterates substitutions and String.Replace on the indexed slot. No Serbian case/number/gender morphology is applied. Static code inspection, not game execution.','phoneAndCourier':'Phone substitutions are number literals. Courier order joins LocalizeItem output with count suffix (x{0}); Serbian introducers retain colon-separated labels. Priest alternatives are individual RunLine instructions under the saved branch labels, not assumed concatenated sentences.','limitations':'Some same-place candidate enum keys (Twins, Neighbour, Alkonost) have no source UI label. No label or runtime reachability is invented. Managed reference registry excluded from header-verified config field extraction; no complete serialized object validation claimed.'})

allrows={r['stableId']:r for r in rows+extra}; findings=[]
def finding(id_suffix, proposal, reason, category, sample=None):
    matches=[k for k in allrows if k.split(':')[-1]==id_suffix]; assert len(matches)==1
    identifier=matches[0]; r=allrows[identifier]
    assert r['source']==source[identifier]['source'] and r['target']==target[identifier]
    preserve_exact.check_value(rules[identifier],proposal)
    findings.append({'findingId':'SR-IR01-'+str(len(findings)+1).zfill(2),'stableId':identifier,'inClosure':identifier in set(c['closureIds']),'source':r['source'],'sourceSha256':ts(r['source']),'currentTarget':r['target'],'currentTargetSha256':ts(r['target']),'proposedTarget':proposal,'proposedTargetSha256':ts(proposal),'targetFile':location[identifier],'key':source[identifier].get('key'),'nodeNames':r.get('nodeNames',[]),'category':category,'objectiveReason':reason,'assembledCurrentExample':r['target'].replace('{0}',sample) if sample else None,'assembledProposedExample':proposal.replace('{0}',sample) if sample else None,'inputLabel':sample,'evidence':['runtime-consumers.json','yarn-context.json','Documentation/glossary-translations/sr/layer.json'],'structuralProposalPreflight':'passed; full-unit replacement preserves existing speaker, slots, markup, numbers, line breaks, exact protected values'})
finding('167520134505766919','сањалачки студентчић','Russian мечтательный means daydreaming/dreamy; Serbian сањиви means sleepy/drowsy. The approved fairytale-enjoyer term Сањалачки студент and this character’s fairy-tale context resolve the sense.','lexical meaning')
finding('110504457509347329','Alt: Добро. Да ли ти одговара ово: {0}?','LocalizeItem returns the raw nominative label; actual deficit config includes Cigarette -> Цигарете. The singular је plus that plural label is malformed. Also подойдёт asks suitability, not whether a quantity is sufficient. The complete replacement preserves the offer and introduces the verbatim label as a list.','dynamic item agreement','Цигарете')
for suffix,proposal in [('110504457379323908','Jacket: Ево шта имам: {0}. Није много, али надам се да ће вам користити.'),('110504457375129609','Jacket: Ако треба, ево шта имам: {0}. Да ли вам то одговара?'),('110504457375129606','Jacket: Ево шта имам: {0}. Није много, али надам се да ће вам користити.'),('110504457337380869','Unstable: Укратко, ево шта имам: {0}. Хоћеш?')]:
    finding(suffix,proposal,'The actual deficit set includes Enerjeka -> Енержека and Kombucha -> Чајна гљива. имам takes an accusative object (Енержеку / Чајну гљиву), but LocalizeItem returns the unchanged nominative label. A colon-separated inventory list makes the template valid for every raw label while retaining possession and the offer.','dynamic item case','Енержека')
finding('110504457224134665','Wheelchair: Не пушташ ме? Сад ћемо то средити! Ево шта имам: {0}, узмеш, машеш тиме на улазу и — хоп! — невидљив си.','Ево governing an ordinary noun takes genitive (Енержеке / Чајне гљиве), whereas this consumer substitutes raw nominative Енержека / Чајна гљива. Recasting only the introducer as an inventory label retains the gesture, action sequence and joke.','dynamic item case','Енержека')
finding('110504457249300481','Marauder: А! Нашао сам нешто: {0}. Узми, домаћине, само ми дај да преноћим.','The bare object after нашао сам needs accusative, but LocalizeItem emits nominative Енержека. The replacement supplies нешто as the object, followed by the exact found-item label. The offer and request for overnight shelter are unchanged.','dynamic item case','Енержека')
finding('110504457169608704','Hunter: Код тебе је већ {0}.','имаш needs accusative жену с тарот картама, but GetCharacterOnPlace(Hunter) can select FortuneTeller and returns the raw label жена с тарот картама. An existential nominative construction preserves the original occupant statement.','dynamic character case','жена с тарот картама')
finding('110504457144442885','Ballerina: Да ли је {0} код тебе?','имаш needs accusative верницу, but GetCharacterOnPlace(Ballerina) can select Nun and returns raw верница. Every existing named same-place candidate is singular; the proposed existential question accepts the unchanged labels.','dynamic character case','верница')
finding('110504457110888458','Wifefema: Ко је то код тебе — {0}?','GetCharacterOnPlace(Wifefema) can select Tough: жена у топу. Added masculine тај yields тај жена. The source Что это за identifies the occupant without male agreement. The replacement uses a neutral question followed by a nominative label.','dynamic character gender','жена у топу')
finding('110504457198968842','Киме? Па ево, погледај — {0}.','GetCharacterOnPlace(Marauder) can select Bald, whose label is ћелави. Fixed feminine та becomes та ћелави. The original source also uses a feminine default, but the target can preserve its pointing function without an agreement defect by retaining ево, погледај and the label.','dynamic character gender','ћелави')
finding('110504457148637194','Anger: Код тебе… {0}?','GetCharacterOnPlace(Anger) can select Sirin, whose literal UI label is две сестре. Inserted singular је makes Код тебе је две сестре. The source has no singular verb. The speaker’s terse question can preserve the literal label with an ellipsis.','dynamic character number','две сестре')
finding('110504457186385920','NotTrue: Јаој, боже мили! Па фотеља ти је већ заузета — {0}.','GetCharacterOnPlace(NotTrue) can select Sirin -> две сестре. Added singular седи produces седи две сестре. The replacement states that the armchair is occupied, then identifies its occupant with an unchanged display label; it preserves the chair, prior occupancy and exclamation.','dynamic character number','две сестре')
finding('110504457144442886','Ballerina: Еее, рекли су ми да овде не сме да буде таквих. Хајде, истерај ту особу.','This directly adjacent line follows GetCharacterOnPlace(Ballerina). Nun is a real same-place female input. Russian Давай, выгоняй has no male pronoun; target истерај га adds a male referent and contradicts that branch. ту особу permits either sex and preserves the expulsion demand.','dynamic character gender')
assert len(findings)==15 and sum(f['inClosure'] for f in findings)==14
write('findings.json', {'status':'objective full-unit proposals; not applied','inputAuthoredFileSetSha256':set_hash,'closureSha256':pins['Translations/sr/semantic-cycle-001-closure.json'],'count':len(findings),'closureFindings':14,'directContextFindings':1,'findings':findings})
affected={f['stableId']:f['findingId'] for f in findings}
for name, selected in [('read-evidence.jsonl',rows),('additional-context-read-evidence.jsonl',extra)]:
    records=[]
    for index,r in enumerate(selected,1):
        identifier=r['stableId'];assert r['source']==source[identifier]['source'] and r['target']==target[identifier]
        if 'sourceSha256' in r: assert ts(r['source'])==r['sourceSha256'] and ts(r['target'])==r['targetSha256']
        records.append(dict(r, sourceSha256=ts(r['source']),targetSha256=ts(r['target']),targetFile=location[identifier],readOrdinal=index,semanticRead='complete Russian/current Serbian pair was displayed and read by this reviewer; source/current bytes preserved here',semanticVerdict='objective finding' if identifier in affected else 'passed within reviewed context',findingId=affected.get(identifier),contextEvidence=['yarn-context.json','actual-key-node-mapping.json','character-runtime-data.json','runtime-consumers.json'],inputAuthoredFileSetSha256=set_hash))
    jl(name,records)
original=read('Translations/sr/semantic-cycle-001-precorrection.json')['acceptedCorrectionFindings']
write('original-corrections-verdict.json',{'count':26,'authoredFileSetSha256':set_hash,'result':'all original 26 complete replacements pass independent source/current semantic review','rows':[{'stableId':f['stableId'],'source':f['source'],'currentTarget':target[f['stableId']],'sourceSha256':ts(f['source']),'targetSha256':ts(target[f['stableId']]),'result':'passed','contextEvidence':'read-evidence.jsonl and actual compiled/supplemental context'} for f in original]})

catalog=read(c['regressionCatalog']); regressions={}
for name, reg in catalog['catalog'].items():
    assert len(reg['ids'])==reg['count'] and ids_sha(reg['ids'])==reg['idsSha256'] and set(reg['ids'])<=set(c['closureIds'])
    defects=[affected[i] for i in reg['ids'] if i in affected]
    regressions[name]=dict(reg, semanticResult='findings' if defects else 'passed',findingIds=defects,readEvidence='read-evidence.jsonl',structuralResult='passed')
write('mandatory-regressions.json',{'catalogSha256':c['regressionCatalogSha256'],'authoredFileSetSha256':set_hash,'regressions':regressions,'contextOnlyGates':{'speakerServicePrefixes':'passed all 16538 preserve-exact; no prefix edits proposed','glossaryRosterAndCharacterRules':'glossary pin unchanged; relevant actual roster, speaker, choice, referent and dynamic inputs read; lexical and dynamic gender findings above','protectedCommandsBranchesAndExactValues':'full exact gate passed; compiled instructions/branch labels saved unchanged in yarn-context.json','textBearingImages':'excluded by owner; not inspected or edited','rtl':'not applicable to Cyrillic Serbian LTR','runtimeRendererFontsAndLayout':'unrun; no game launch authorized for text-only review'}})
best=allrows['string:444ff14f1967f5a4c8eb9e4cf4c913f1:110504457127665669']
fortune=allrows['string:444ff14f1967f5a4c8eb9e4cf4c913f1:110504455550607364']
write('dismissed-candidates.json',{'rows':[dict(best,reason='Russian на меня похожий мужик explicitly permits a man resembling me. The context also permits a similar man referring to the resident, but ambiguity does not establish the existing interpretation is a mistranslation. No objective replacement.'),dict(fortune,reason='Phone referral context permits the metaphorical coming from someone formulation. More explicit на моју препоруку would be a preference, not an objective source/target error.')],'sourceInconsistencies':'Some source dialogue uses male/default referents where same-place data includes women, and Marauder source has feminine эта despite male Bald being a candidate. These source facts remain source facts; only avoidable target grammar/additional gender commitments are proposed as target corrections. Rocker and Foreigner male pronouns were checked against actual all-male supported label candidates, not guessed from a generic roster.'})

overlay=dict(target)
for f in findings: overlay[f['stableId']]=f['proposedTarget']
for identifier in canonical: preserve_exact.check_value(rules[identifier],overlay[identifier])
write('proposal-full-exact-preflight.json',{'inputAuthoredFileSetSha256':set_hash,'scope':'in-memory overlay of all 15 complete proposals; no authored writes, no validation sidecars changed','units':16538,'proposals':15,'result':'passed','ids':[f['stableId'] for f in findings],'idsSha256':ids_sha([f['stableId'] for f in findings])})
write('verification.json',{'result':'all pinned inputs, current authored hashes, canonical closure IDs and components verified before semantic review and reverified at evidence production','pins':verified_pins,'authoredFileSetSha256':set_hash,'authoredFiles':authored,'authoredUnits':16538,'canonicalClosureIds':c['closureIds'],'canonicalClosureIdsSha256':ids_sha(c['closureIds']),'components':components,'changedIdsSha256':ids_sha(c['changedIds']),'nontranslatableContextRuntimeSha256':c['nontranslatableContextRuntimeSha256'],'independentSelectorReproduction':'build_independent_review.py --write omitted: immutable closure/review rows/catalog/handoff all reproduced without mutation; component selectors additionally checked for canonical order/hash/union here','staticReproduction':'reproduce_static_draft.py --write omitted: 178 current static units reproduced; full original credits source/current pair read','hashEncoding':'File hashes are SHA256 of exact bytes; text hashes UTF-8 exact string; selected ID hashes UTF-8 canonical stable IDs with final LF; authored set sorted path TAB file SHA256 LF.','coverage':'687 exact closure pairs plus 451 disjoint source/current direct context pairs; 1138 distinct pairs. Context reads do not inflate the closure coverage.'})
write('summary.json',{'status':'complete independent review; changes required','locale':'sr','gameVersion':'1.3.19','authoredFileSetSha256':set_hash,'closureIdsSha256':c['closureIdsSha256'],'closureReviewed':687,'closureTotal':687,'closurePassed':673,'closureObjectiveFindings':14,'additionalContextReviewed':451,'additionalContextObjectiveFindings':1,'distinctPairsRead':1138,'allOriginal26Corrections':'passed','structuralResult':'passed for current full 16538 and in-memory proposed full overlay','semanticResult':'not clean on unchanged hashes; all 15 objective full-unit proposals require coordinator adjudication','editorialAcceptance':'pending; not accepted','systemicScope':'The failing raw-label item/character templates are enumerable within the pinned mandatory dynamic catalog and connected scene. No source/glossary/runtime input changed and no unbounded corpus-wide semantic pattern was established. Retain the original full-pass evidence, adjudicate this whole batch, and build the next exact delta closure including the newly found direct-context ID and all affected UI label/branch consumers. Do not claim convergence before independent review of the accepted next hashes.','writes':'new evidence only in Translations/sr/independent-review-01; no authored/source/glossary/shared state/Git/fixture/image mutation and no game launch','telemetry':{'servedModel':'unknown; platform supplies GPT-6 family identity only','reasoningSetting':'unknown','inputTokens':'unknown','cachedInputTokens':'unknown','outputTokens':'unknown','reasoningTokens':'unknown','totalTokens':'unknown','cutoff':'evidence production; exact per-request/session telemetry unavailable through exposed tools; reporting tail unmeasured','delegation':'none'},'attemptsAndLimitations':['System Python exact validator missing UnityPy; canonical .venv interpreter used successfully; no package install.','CLI preserve_exact rejects custom output path before writes; callable validate used with authorized evidence directory.','Context decoder rerun existing immutable output guard raised before mutation; read-only prefix load used.','UnityPy generated full object could not resolve ManagedReferencesRegistry; only header-verified schema prefix fields used, with no asset saves.','Deficit extraction diagnostic attempts failed on native node deepcopy, unavailable get_reader, child-copy/header alignment and unflattened-node reconstruction; corrected fresh flattened prefix verified m_Name and both script pointer fields before recording config. No failed attempt wrote config.','Static source/code/config evidence establishes substitution behavior and possible same-place inputs, not executed scene reachability.','No runtime visuals/fonts/layout validation or game launch.']})
print(json.dumps({'closureReviewed':687,'contextRead':451,'findings':15,'allCurrentInputsUnchanged':True,'overlayExactUnits':16538}))
