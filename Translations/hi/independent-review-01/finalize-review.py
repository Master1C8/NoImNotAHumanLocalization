"""Write new immutable static review evidence; never alter locale inputs."""
import json, hashlib, struct
from pathlib import Path
import dnfile
from dncil.cil.body import CilMethodBody
from dncil.cil.body.reader import CilMethodBodyReaderBytes

R=Path(__file__).resolve().parents[3]; H=R/'Translations/hi'; D=Path(__file__).parent
def j(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n, data):
    p=D/n; assert not p.exists(),p
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
ns={'__file__':str(D/'read-fast.py')}
exec((D/'read-fast.py').read_text().split('if sys.argv')[0],ns)
source=ns['source']; target=ns['t']; files=ns['f']; rows=ns['rows']
bykey={r.get('key'):r for r in source.values() if r['stableId'] in target}
closure={r['stableId']:r for r in rows}; findings=[]
def unit(key):
    r=source[key] if key.startswith('tmp:') else bykey[key]
    sid=r['stableId']; c=closure.get(sid)
    return {'stableId':sid,'key':r.get('key'),'source':r['source'],'currentTarget':target[sid],
            'authoredPath':files[sid],'inSuppliedClosure':c is not None,
            'reviewIndex':c['reviewIndex'] if c else None,'components':c['components'] if c else [],
            'sourceSha256':hashlib.sha256(r['source'].encode()).hexdigest(),
            'targetSha256':hashlib.sha256(target[sid].encode()).hexdigest()}
def finding(code,keys,title,reason,repair,context,proposals=None):
    units=[unit(k) for k in keys]
    if proposals:
        for u,p in zip(units,proposals):u['proposedFullTarget']=p
    findings.append({'findingId':code,'status':'objective-full-unit-finding','title':title,
                     'units':units,'reason':reason,'requiredRepair':repair,'contextEvidence':context})

finding('HI-IR01-001',['line:Twins_Entrance_AlkonostOccupied_0df5a23'],
 'Incoming-character parameter mistaken for the occupying person',
 'Current वह औरत / देगी specifies a female blocker. GetCharacterOnPlace("Alkonost") resolves the incoming Alkonost placement, then finds an existing occupant of that placement. Original CharacterSOData puts male Raskolnikov in the same default place 68; the previous adjudication premise that the returned blocker must be Alkonost is false.',
 'Retain the predicted reproaches toward the younger sister, while referring to the actual blocker without assigning an unsupported sex.',
 ['compiled-changed-node-instructions.json:Twins_Entrance_AlkonostOccupied indices 0–7','managed-dynamic-methods.json','character-placement-source-prefix.json:Alkonost/Raskolnikov place 68','approved hi glossary bandana-man male'],
 ['Twins: मुझे लगता है उस व्यक्ति की तरफ़ से मेरी छोटी बहन पर तानों की बौछार होगी।'])
finding('HI-IR01-002',['line:Fanatic_Entrance_Occupied_01deafb'],
 'Raw dynamic label fails oblique agreement',
 'The actual GetCharacterOnPlace("Fan") default domain includes Dude, whose approved/current UI label is ड्रेडलॉक वाला रस्ताफारी. Substitution yields ड्रेडलॉक वाला रस्ताफारी के छिपे रहने तक; वाला is direct-case masculine where the following के requires oblique वाले. The runtime returns the uninflected label and performs no Hindi inflection.',
 'Use a construction that accepts the exact supplier labels of all actual occupants and retains hiding, the Sun instruction, and the until condition.',
 ['compiled-changed-node-instructions.json:Fan_Entrance_Occupied indices 0–4','managed-dynamic-methods.json','dynamic-assembled-default-domains.json'])
finding('HI-IR01-003',['line:Fanatic_Photo_0397c21'],
 'Unchanged repetition still invents a handshake',
 'Russian здоровался is greeting; हाथ मिलाया specifies physical handshaking absent from source. The exact Russian repetition line:Fanatic_Photo_0a4e55d was correctly repaired in cycle 001, but this supplied repetition component still has the old error.',
 'Apply the same greeting meaning in the complete repeated unit without adding a handshaking fact.',
 ['semantic-cycle-001-adjudication.json:line:Fanatic_Photo_0a4e55d','paired-closure-fast.jsonl:closure indices 1343 and 1470'],
 ['Fanatic: क्या किसी ने तुम्हें बताया कि मैंने ख़ुद सूर्य नेता का अभिवादन किया था?'])
finding('HI-IR01-004',['line:Wheelchair_Ears_DontShoot_03a980a'],
 'Unchanged repetition narrows plural signs to one',
 'Russian им is plural and contrasts with этому признаку, whereas उस पर is singular. The exact source-equivalent cycle correction line:Wheelchair_Ears_DontShoot_02cee3c uses plural उन पर; this other supplied repetition retains the error.',
 'Preserve the this-sign versus other-signs distinction in the full unit.',
 ['semantic-cycle-001-adjudication.json:line:Wheelchair_Ears_DontShoot_02cee3c','paired-closure-fast.jsonl:closure indices 1356 and 1498'],
 ['Wheelchair: अगर… अगर तुझे इस लक्षण पर भरोसा नहीं, तो मैं उन पर कैसे करूँ?'])
finding('HI-IR01-005',['line:Widow_Photo_09ce21a'],
 'Accepted repetition still reduces leave-alone request to physical touch',
 'In the Widow photo exchange, не трогай меня is a request to leave her alone; the scene concludes Теперь просто уйди. Current मुझे मत छुओ limits this to touch. The exact source-equivalent compiled row line:Widow_Photo_06bb696 was corrected, while this accepted serialized duplicate remains unchanged.',
 'Preserve the leave-alone request consistently. Do not infer this accepted duplicate is runtime reachable merely because its source is repeated.',
 ['compiled-changed-node-instructions.json:Widow_Photo','semantic-cycle-001-adjudication.json:line:Widow_Photo_06bb696','paired-closure-fast.jsonl:closure indices 1291 and 1444'],
 ['Widow: जो चाहो करो, बस मुझे अकेला छोड़ दो।'])
finding('HI-IR01-006',['line:FormerFema_Asking_4_013f11d'],
 'Completed removal becomes only a collection attempt',
 'Russian забрал says the agent actually took the person. लेने गया था only says he went to collect him, leaving the removal uncompleted. This changes the established action in the later account of the detained man and his wife.',
 'Retain the completed removal, the one occasion, another person, and Guest signs.',
 ['paired-closure-fast.jsonl:closure index 968, complete unit and FormerFema account'],
 ['FormerFema: एक बार मैं अतिथि के लक्षण वाले एक और आदमी को ले गया था।'])
finding('HI-IR01-007',['line:Bestson_Asking_2_0b65628'],
 'Discovery of Guest identity becomes a transformation',
 'Russian оказалась Гостем is turned out to be a Guest. अतिथि बन गई हों says grandmother became a Guest, inventing a transformation rather than uncertainty about her identity. The second hypothetical emergency-committee capture must remain intact.',
 'Restore the turned-out identity hypothesis without changing either feared outcome.',
 ['compiled-changed-node-instructions.json:Bestson_Asking_2 index 21','paired-closure-fast.jsonl:closure index 1097'],
 ['Bestson: अगर दादी अतिथि निकली हों और उन्हें मार दिया हो तो? अगर आपात समिति ने रोककर उन्हें ले लिया हो तो…'])
finding('HI-IR01-008',['line:Experienced_Asking_4_X_061a510'],
 'Already formed or established identity is replaced with age alone',
 'Source first says he is already a состоявшийся person, then says life is near its end. मेरी उम्र भी हो चली है conveys only advanced age and loses the first assertion. The surrounding fixed cupboard, hardened habits and difficulty accepting new arrangements confirm the formed-identity contrast.',
 'Retain the assertion of an already formed or established person as well as the separate nearing-end-of-life clause; avoid adding an occupation or economic-success claim.',
 ['compiled-changed-node-instructions.json:Experienced_Asking_4_X indices 0–9','paired-closure-fast.jsonl:closure index 741'])
finding('HI-IR01-009',['line:Death_Income_7_09b9b75','line:Death_Income_7_0b49122','line:Death_Income_3_0c3bfa8'],
 'Avoidable masculine agreement assigns the ambiguous Death speaker a sex',
 'समझता, चलूँगा, and सकता mark Death as masculine. The approved Death meaning explicitly says poetic भाई and Russian она do not establish biological sex and contextual ambiguity must remain. These source verbs do not assign speaker sex. The two additional rows were read from actual compiled scene context, outside the supplied closure; they are not credited as supplied closure coverage.',
 'Use natural neutral speaker constructions, preserving understanding, the definite promise to lead into the night, and seeing the anticipated yes. Keep source-marked player gender distinct from speaker gender.',
 ['approved hi glossary death','supplementary-death-context.jsonl','compiled-supplementary-nodes.json:Death_Income_3/7'])
finding('HI-IR01-010',['line:Buddy_Armpit_0240b62'],
 'Full corrected unit retains masculine armpit adjectives',
 'The inspected referent is बगलें, feminine plural. मोटे, बालों वाले is masculine plural. Actual Buddy_Armpit inspection instructions and the preceding unit establish the referent; the later फफूँद ... लगी already uses feminine agreement. Correcting the dog term left this full-unit agreement defect.',
 'Use feminine plural adjectives for armpits while retaining every other fact, the fungus and sleeping on the floor with the dog.',
 ['compiled-changed-node-instructions.json:Buddy_Armpit indices 0–4','paired-closure-fast.jsonl:closure index 1386'],
 ['Buddy: देखने लायक कुछ नहीं है, सच कह रहा हूँ। मोटी, बालों वाली, ऊपर से कोई फफूँद भी है। शायद तब लगी जब कुत्ते के साथ फ़र्श पर सोया था।'])
finding('HI-IR01-011',['tmp:level1:3842:m_text','tmp:level1:4228:m_text','tmp:level1:4275:m_text'],
 'Plain serialized service labels do not use the approved service term',
 'All three accepted static labels have source Экстрасенсы and current साइकिक्स. This plain phone-service label has the approved term अतींद्रिय विशेषज्ञों की सेवा, also used in the table UI. These are plain service occurrences, not the source gag Гавнасэнсы; no wordplay exemption is evidenced. Serialized-placeholder visibility remains unproved.',
 'Apply the approved service meaning to these plain labels; keep source wordplay variants separately adjudicated.',
 ['approved hi glossary psychics-service','paired-closure-fast.jsonl:closure indices 1597/1655/1664','Source/localization-inventory-v3/static-text.jsonl'],
 ['अतींद्रिय विशेषज्ञों की सेवा']*3)
write('consolidated-full-unit-findings.json',{
 'schemaVersion':1,'locale':'hi','reviewerTask':'hi_independent_review_01',
 'sourceLocale':'ru','gameVersion':'1.3.19','verdict':'not-clean-static-independent-review',
 'groupCount':len(findings),'affectedUnitCount':sum(len(f['units']) for f in findings),
 'suppliedClosureAffectedUnitCount':sum(u['inSuppliedClosure'] for f in findings for u in f['units']),
 'findings':findings,'note':'Objective meaning, agreement, dynamic-domain and approved-term issues only. Full replacements offered where unambiguous; author adjudication required. No authored input edited.'})

# Additional bounded Death source pairs actually read, including player options.
death=[r for r in source.values() if r['stableId'] in target and (r.get('key') or '').startswith(('line:Death_Income_','line:talk_CultistEnds_'))]
p=D/'supplementary-death-context.jsonl';assert not p.exists()
p.write_text(''.join(json.dumps(unit(r['key']),ensure_ascii=False)+'\n' for r in death))

assembly=R/'Runtime/No Human Probe.app/Contents/SharedSupport/prefix/drive_c/KS Games/No Im not a Human/NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed/Assembly-CSharp.dll'
assert sha(assembly)=='c674f171c61b644e6e746e0ced079ffa365abee2336d04ea9e67cbbc93e88213'
pe=dnfile.dnPE(str(assembly));owners={ref.row_index:str(t.TypeName) for t in pe.net.mdtables.TypeDef.rows for ref in t.MethodList}
tables={0x06:'MethodDef',0x04:'Field',0x0A:'MemberRef',0x02:'TypeDef',0x01:'TypeRef',0x2B:'MethodSpec'}
def operand(o):
    if o is None:return None
    value=getattr(o,'value',None)
    if value is None:return str(o)
    token=int(value); kind=token>>24; index=token&0xffffff
    if kind==0x70:
        raw,_=pe.net.user_strings.get_with_size(index)
        return {'token':hex(token),'string':raw.decode('utf-16le')}
    if kind in tables:
        table=getattr(pe.net.mdtables,tables[kind]);r=table.rows[index-1]
        return {'token':hex(token),'table':tables[kind],'name':str(getattr(r,'Name',getattr(r,'TypeName',''))),'methodOwner':owners.get(index) if kind==0x06 else None}
    return {'token':hex(token)}
managed=[]
for index,m in enumerate(pe.net.mdtables.MethodDef.rows,1):
    if m.Rva and (str(m.Name) in ['GetCharacterOnPlace','GetPhoneNumber'] and owners[index]=='DialogCommandsInstance' or str(m.Name).startswith('<GetCharacterOnPlace>')):
        body=CilMethodBody(CilMethodBodyReaderBytes(pe.get_data(m.Rva,12000)))
        managed.append({'methodToken':hex(0x06000000|index),'owner':owners[index],'method':str(m.Name),
                        'instructions':[{'offset':i.offset,'opcode':i.opcode.name,'operand':operand(i.operand)} for i in body.instructions]})
write('managed-dynamic-methods.json',{'assemblyPath':str(assembly.relative_to(R)),'assemblySha256':sha(assembly),'methods':managed,'limit':'Static original managed IL and accepted-source fingerprint; no runtime execution or event reachability proof.'})

# Decode all nodes once to retain supplementary Death speaker/choice context.
bind=j(R/'Source/glossary-corpus-v2/runtime-bindings.json'); f=ns.get('fields')
selector_ns={'__file__':str(H/'build-semantic-cycle-001-closure.py'),'__name__':'review_import'}
exec(compile((H/'build-semantic-cycle-001-closure.py').read_text(),str(H/'build-semantic-cycle-001-closure.py'),'exec'),selector_ns); f=selector_ns['fields']
allnodes={}
for num,wire,v in f(bytes(bind['sharedassets0.assets:2743']['compiledYarnProgram'])):
    if (num,wire)!=(2,2):continue
    parts=list(f(v));name=parts[0][2].decode();ins=[];labels=[]
    for n,w,val in f(parts[1][2]):
        if (n,w)==(2,2):
            op=0;args=[]
            for nn,ww,vv in f(val):
                if (nn,ww)==(1,0):op=vv
                elif (nn,ww)==(2,2):args.append([{'field':a,'wire':b,'value':c if b==0 else struct.unpack('<f',c)[0] if (a,b)==(3,5) else c.decode('utf-8','backslashreplace')} for a,b,c in f(vv)])
            ins.append({'index':len(ins),'opcode':op,'operands':args})
        elif (n,w)==(3,2):labels.append([{'field':a,'wire':b,'value':c if b==0 else c.decode('utf-8','backslashreplace')} for a,b,c in f(val)])
    allnodes[name]={'instructions':ins,'labels':labels}
write('compiled-supplementary-nodes.json',{'runtimeBindingSha256':sha(R/'Source/glossary-corpus-v2/runtime-bindings.json'),'nodes':{n:d for n,d in allnodes.items() if n.startswith(('Death_Income_','talk_CultistEnds_'))},'limit':'Static line/option and branch roles; not runtime proof.'})

placements=j(D/'character-placement-source-prefix.json')['rows'];domains=[]
for incoming,node in [('Alkonost','Twins_Entrance_AlkonostOccupied'),('Fan','Fan_Entrance_Occupied'),('BigLebowski','BigLebowski_Entrance_Occupied'),('Tourist','Tourist_Entrance_Occupied')]:
    place=next(r['place'] for r in placements if r['name']==incoming)
    blockers=[r for r in placements if r['place']==place and r['name']!=incoming]
    consumers=[]
    for i in allnodes[node]['instructions']:
        values=[v['value'] for a in i['operands'] for v in a]
        if i['opcode']==2 and values[0] in bykey and (values[1] or node.startswith('Twins_')):
            u=unit(values[0]);assemblies=[]
            for b in blockers:
                label=bykey.get('characterName_'+b['name'])
                assert label,(incoming,b['name'])
                assemblies.append({'occupant':b['name'],'labelId':label['stableId'],'labelSource':label['source'],'labelTarget':target[label['stableId']],
                                   'assembledRussian':u['source'].replace('{0}',label['source']),
                                   'assembledHindi':u['currentTarget'].replace('{0}',target[label['stableId']])})
            consumers.append({'instructionIndex':i['index'],'unit':u,'assemblies':assemblies})
    domains.append({'incomingPlacementLookup':incoming,'place':place,'defaultBlockerCandidates':blockers,'node':node,'consumers':consumers})
write('dynamic-assembled-default-domains.json',{'domains':domains,'evidence':['managed-dynamic-methods.json','character-placement-source-prefix.json','compiled-changed-node-instructions.json','current authored UI labels'],'limit':'These are source default-placement candidates and assembled static consumers, not synthetic invented names. Runtime CharactersManager.GetPlace may reflect state; no claim of exhaustive reachable gameplay combinations, nor any executed dialogue.'})

changed=j(H/'semantic-cycle-001-adjudication.json')['items'];c=j(H/'semantic-cycle-001-closure.json')
fragments=[]
for r in c['nontranslatableRuntimeBindingFragments']:
    node=allnodes[r['node']];matches=[i for i in node['instructions'] if any(v['value']==r['lineKey'] for a in i['operands'] for v in a)]
    fragments.append({'declaredDescriptor':r,'actualInstructionMatches':matches,'acceptedAuthoredUnit':unit(r['lineKey'])})
write('closure-evidence-omissions.json',{'mandatoryCatalog':'regression-catalog-reconciliation.json',
 'runtimeFragmentClassification':{'declaredCount':7,'rows':fragments,'finding':'The seven descriptors point to accepted authored translated line records, including non-dynamic context lines. They are not identified nontranslatable fragments. Store actual function names, arguments, supplier fields/labels and source pins separately; do not count technical input records as translations.'},
 'changedRowsWithoutExactCompiledLineReference':c['changedRowsWithoutExactCompiledLineReference'],
 'acceptedDuplicateReachability':{'key':'line:talk_CultistEnds_4_0a991ad','status':'unresolved; exact accepted serialized duplicate has no matching compiled line operand; nearby compiled source-equivalent variants do not establish this ID reachability'},
 'additionalEditorialQuestion':{'unit':unit('line:Theorist_Asking_2_04f4138'),'status':'needs-author-adjudication; not counted as objective correction above','question':'The source КЧС alternate-expansion joke uses a genuine acronym. Current आपात समिति के संक्षिप्त नाम ... मानव मृत्यु का पंथ has no matching Hindi initials. Preserve the source joke mechanism under the glossary rather than a preference rewrite; an explicit treatment/exception is needed.'}})

affected={u['stableId']:[f['findingId'] for f in findings if any(v['stableId']==u['stableId'] for v in f['units'])] for f in findings for u in f['units']}
ledger=[]
for i,r in enumerate(rows):
    ledger.append({'closureOrdinal0':i,'stableId':r['stableId'],'reviewIndex':r['reviewIndex'],'components':r['components'],
                   'sourceSha256':hashlib.sha256(r['source'].encode()).hexdigest(),'currentTargetSha256':hashlib.sha256(r['target'].encode()).hexdigest(),
                   'fullRussianAndCurrentHindiRead':True,'readScope':'full unit plus supplied closure context; exact compiled context where available',
                   'glossaryVersionSha256':sha(R/'Documentation/glossary-translations/hi/layer.json'),
                   'findingIds':affected.get(r['stableId'],[]),
                   'result':'objective-finding' if r['stableId'] in affected else 'no-objective-finding-in-static-read'})
p=D/'per-id-read-evidence.jsonl';assert not p.exists();p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in ledger))
write('read-coverage-receipts.json',{'readPairCount':1691,'uniqueStableIds':len({r['stableId'] for r in ledger}),
 'pairArtifactSha256':sha(D/'paired-closure-fast.jsonl'),'ledgerSha256':sha(p),
 'method':'Every full Russian/current Hindi unit was explicitly read in bounded displayed tool outputs. Script records this completed manual review; it did not generate semantic verdicts.',
 'pairReadRanges0BasedHalfOpen':[[0,100],[100,260],[260,430],[324,376],[430,540],[540,650],[650,760],[760,880],[880,1000],[1000,1120],[1120,1230],[1230,1340],[1340,1450],[1450,1560],[1560,1691]],
 'truncationRecovery':'260–430 recovered 324–376; long credits row 1688 read as physical lines 0–59, 60–164, 165–203 with matching Hindi lines.',
 'compiledOrderRead':{'exactChangedNodes':80,'instructions':1220,'displayReceipts':['72540c','c0d587','7e6843'],'labelsBranchesLineAndOptionRolesRead':True},
 'supplementaryDeathPairsRead':82,'supplementaryDisplayReceipts':['f49780','33bc8c'],
 'limits':'No semantic read is credited for the 4,048 required catalog IDs outside supplied closure. Static review does not prove rendering, event reachability, delivered package behavior, or release acceptance.'})
print('FINDINGS',len(findings),'UNITS',sum(len(f['units']) for f in findings),'CLOSURE',sum(u['inSuppliedClosure'] for f in findings for u in f['units']))
print('LEDGER',len(ledger),'SUPPLEMENTARY',len(death),'DYNAMIC_DOMAINS',len(domains))
