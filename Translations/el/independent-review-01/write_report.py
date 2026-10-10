import json,hashlib,subprocess,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).parent
D=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
T=lambda s:hashlib.sha256(s.encode()).hexdigest()
rows=[json.loads(l) for l in (ROOT/'Translations/el/correction-cycle-001-closure-review.jsonl').read_text().splitlines()]
source=[json.loads(l) for l in (ROOT/'Source/localization-inventory-v3/strings.jsonl').read_text().splitlines()]
bykey={r['key']:r for r in source if r['collection']=='Dialogs'}
byid={r['stableId']:r for r in source}; cur={}
for p in (ROOT/'Translations/el').glob('*-batch-???.json'):
 b=json.loads(p.read_text())
 if not b.get('entries'):continue
 g={'UI':'0cbd8a7a4f543344bb95659de87f67a5','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6'}[b['collection']]
 for e in b['entries']:cur[f'string:{g}:{e["id"]}']={'currentTarget':e['target'],'targetFile':str(p.relative_to(ROOT)),'targetFileSha256':D(p)}
nodes=json.load(open(OUT/'compiled-context.json'))['nodes']
contexts={}
for name,n in nodes.items():
 for x in n['instructions']:
  if x['opcode'] in [2,4] and x['args']:contexts.setdefault(x['args'][0],[]).append({'node':name,'pc':x['pc'],'opcode':x['opcode'],'args':x['args']})
proposals={
151:('έφηβο άτομο με καπέλο','Early UI label adds male agreement despite the approved undisclosed-gender label for the canonically female teenager.','bar-teenager'),
318:('Phone: (Ακούτε το άτομο στην άλλη άκρη της γραμμής να βγάζει μια δυνατή ανάσα.)','Masculine interlocutor adds a sex to the canonically unspecified recruitment voice.','fema-recruitment-voice'),
348:('Phone: Και σύντομα δεν θα υπάρχει κανείς να δώσει τίποτα.','Greek makes him lack a recipient. He is the giver who will soon be absent; the compiled follow-up reveals the planned suicide.','alkonosts-husband'),
378:('Μιλά το μέλος του πρ…οσωπικού 18-8: δεν καταφ…έραμε να περιορίσουμε την απ…ειλή.','Masculine employee adds a sex to the unspecified numbered radio voice; preserve the interrupted transmission and number.','radio-employee-18-8'),
383:('Αναφορά από το μέλος του προσωπικού 28-8. Κωδικός 451: χρειαζόμαστε συνεργείο για την καύση των πτωμάτων.','Masculine employee adds a sex to the unspecified numbered radio voice.','radio-employee-28-8'),
384:('Αναφορά από το μέλος του προσωπικού 32-8. Κωδικός 60: πολλά θύματα μεταξύ αμάχων, υπάλληλοι σκοτώθηκαν…','Masculine employee adds a sex to the unspecified numbered radio voice.','radio-employee-32-8'),
385:('Μιλά το άτομο που συντονίζει. Ελέγξτε τι συνέβη στη ζώνη καραντίνας. Κωδικός 51. Αναφέρονται εκρήξεις στις 3 τα ξημερώματα.','Masculine radio operator adds a sex to the unspecified dispatcher and narrows the role.','radio-dispatcher'),
444:('Leper: Εντάξει, κι αν σου δώσω κάτι; {0}, ας πούμε; Θα με αφήσεις να μπω τότε;','Compiled PeekDeficitItem → LocalizeItem inserts fixed dictionary-form labels. Το does not agree with Τσιγάρα, Καφές, Κομπούχα, Ενερζέκα, Γατοτροφή or Παρουσίαση στην ΕΕΑ. Removing its article preserves the citation-like item fragment.','coffee'),
456:('Jacket: Ορίστε, έχω {0}. Η ποσότητα είναι μικρή, αλλά ελπίζω να σας χρησιμεύσει.','Compiled LocalizeItem inserts singular and mass labels as well as Τσιγάρα. Greek πολλά/χρήσιμα imposes neuter plural agreement absent from the actual label domain.','coffee'),
459:('Jacket: Ορίστε, έχω {0}. Η ποσότητα είναι μικρή, αλλά ελπίζω να σας χρησιμεύσει.','Same fixed-label number/agreement defect as the occupied-room branch.','coffee'),
821:('Tough: Είπε πως έπρεπε να περάσει για λίγο από το σπίτι, για να δώσει κάτι στη μητέρα του. Δεν ήθελα να πάω μαζί του.','Greek orders the woman to go home and give the mother something; source and compiled following scene have the man do it while she waits outside.','tough-woman'),
826:('Experienced: Η γυναίκα μου βρήκε άλλον, το παιδί μου με φοβόταν και δεν μπορώ πια να βρω δουλειά εξαιτίας του ποινικού μου μητρώου.','Source present inability to obtain work becomes past inability. Keep the historical wife/child clauses and the explicitly current restriction.','ex-con'),
864:('Cultist3: Τους κάλεσε ο Θάνατος…','Greek pronoun Εκείνη omits the explicit Death revelation; actual preceding node lines do not supply a Death antecedent. Canonical feminine pronouns elsewhere remain valid.','death'),
1110:('Wifefema: Ποιος σκέφτηκε να αποκαλεί αυτά τα μη ανθρώπινα πλάσματα Επισκέπτες;','Нелюдей is nonhuman status here; απάνθρωπα means inhumane/cruel and shifts the asserted ontology into a moral property.','human'),
1404:('TaxiDriver: Ο πατέρας μου έκανε τότε μια μαλακία και το πληρώσαμε όλοι. Μετά ζούσαμε σαν αρουραίοι: χωρίς σπίτι, χωρίς λεφτά, χωρίς ησυχία…','Explicit rats become mice, the same species distinction corrected in the first cycle.','cat'),
1586:('NotTrue: Τα χέρια είναι για όσους κρατούν κάτι. Εγώ έχω σταματήσει να το κάνω εδώ και πολύ καιρό.','Transitive holding with hands becomes reflexive holding on/keeping oneself supported. Preserve the metaphor without changing its action.','cold-man'),
1652:('Ξεκλείδωσε τον γάτο','The accepted static unlock label uses generic feminine γάτα where the approved game referent and current cat lines use Γάτος.','cat'),
1676:('Στη λίστα επιθυμιών','The wishlist action becomes the semantically incomplete into the desired thing. Use the actual wishlist destination, consistent with Ending_ThanksWishlist.','collection')}
for i,r in enumerate(rows):
 if r['source']=="Here's a big long line of dialogue, ready to be shown to the player.":
  proposals[i]=('Ορίστε μια μεγάλη, μακροσκελή ατάκα, έτοιμη να εμφανιστεί στον παίκτη.','Adjective μακροσκελής is nominative; μια ... ατάκα here requires accusative μακροσκελή.','player')
findings=[]
for i,(proposal,reason,gid) in proposals.items():
 r=rows[i]
 findings.append({'findingId':f'EL-IR01-{len(findings)+1:03}','closureIndex':i,'scope':'published-closure','stableId':r['stableId'],'ordinal':r['ordinal'],'key':r['key'],'source':r['source'],'sourceSha256':r['sourceSha256'],'before':r['currentTarget'],'beforeSha256':r['currentTargetSha256'],'proposedTarget':proposal,'proposedTargetSha256':T(proposal),'reason':reason,'glossaryIds':[gid],'targetFile':r['targetFile'],'targetFileSha256':r['targetFileSha256'],'compiledOccurrences':contexts.get(r['key'],[])})
extra=[('line:phone_fortuneteller_04e9b94',"Phone: (Το άτομο στην άλλη άκρη της γραμμής κλείνει το τηλέφωνο. Αυτό ήταν… κάπως διαφορετικό απ' ό,τι περιμένατε.)",'voice-from-fortune-teller','Canonical neutral phone role is outside the closure; masculine Ο συνομιλητής incorrectly assigns its sex.'),('line:radio_12_066787a','Το άτομο που συντ…ονίζει καλεί όλα τα μέλη του πρ…οσωπικού της ΕΕΑ…','radio-day-12-dispatcher','Canonical neutral day-12 dispatcher is outside the closure; masculine Ο ασυρμ…ατιστής incorrectly assigns its sex and changes dispatcher to radio operator.')]
for key,proposal,gid,reason in extra:
 r=bykey[key];v=cur[r['stableId']]
 findings.append({'findingId':f'EL-IR01-{len(findings)+1:03}','scope':'bounded-selector-completeness-counterexample','stableId':r['stableId'],'key':key,'source':r['source'],'sourceSha256':r['sourceSha256'],'before':v['currentTarget'],'beforeSha256':T(v['currentTarget']),'proposedTarget':proposal,'proposedTargetSha256':T(proposal),'reason':reason,'glossaryIds':[gid],**{k:v[k] for k in ['targetFile','targetFileSha256']},'compiledOccurrences':contexts.get(key,[])})
for f in findings:assert f['before']!=f['proposedTarget'] and T(f['source'])==f['sourceSha256']
findbyid={f['stableId']:f for f in findings}
g=json.load(open(ROOT/'Documentation/glossary-translations/el/layer.json'))
ev=json.load(open(ROOT/'Documentation/glossary-research/final-v1/evidence.json'))
anchors=[]
for e in ev['evidence']:
 if not ('δεν προσδιορίζει το φύλο' in g[e['id']]['meaning']):continue
 r=bykey.get(e.get('source',{}).get('key'))
 if r:anchors.append({'glossaryId':e['id'],'stableId':r['stableId'],'key':r['key'],'selected':r['stableId'] in {x['stableId'] for x in rows},'source':r['source'],'sourceSha256':r['sourceSha256']})
callbacks=[]
for r in source:
 if r['collection']=='Dialogs' and 'килотон' in r['source'].lower():
  callbacks.append({'stableId':r['stableId'],'key':r['key'],'source':r['source'],'sourceSha256':r['sourceSha256'],'target':cur[r['stableId']]['currentTarget'],'targetSha256':T(cur[r['stableId']]['currentTarget']),'selected':r['stableId'] in {x['stableId'] for x in rows},'decision':'correct-current-wording; selector must retain callback relation','compiledOccurrences':contexts.get(r['key'],[])})
selector={'result':'incomplete-semantic-catalog','publishedClosureReproduction':'passed:1816','kilotonCallbacks':callbacks,'mandatoryUnknownGenderCanonicalAnchors':anchors,'repair':'Add the kiloton callback class and explicit canonical unknown-gender speaker/referent anchors with their actual scenes/branches to the next normal closure. Include every relevant inflected kinship and callback occurrence, not only bare noun fragments. Preserve source-only compiled instructions as technical context; never add them as translation IDs.','restart':'bounded selector repair and normal correction cycle; no universal full-pass restart condition found'}
report=json.load(open(ROOT/'Source/glossary-corpus-v2/report.json'));bind=ROOT/'Source/glossary-corpus-v2/runtime-bindings.json';compiled=json.load(open(OUT/'compiled-context.json'));assert D(bind)==report['runtimeBindingsSha256'];assert compiled['compiledSha256']==report['currentScope']['compiledProgramSha256']
compiledkeys={x['args'][0] for n in nodes.values() for x in n['instructions'] if x['opcode'] in [2,4] and x['args']};assert len(compiledkeys)==report['currentScope']['compiledLineIds']==15693
missing=[{'stableId':r['stableId'],'key':r['key']} for r in rows if r['collection']=='Dialogs' and r['key'] not in compiledkeys]
read_decisions=[]
for i,r in enumerate(rows):
 read_decisions.append({**r,'closureIndex':i,'fullSourceAndCurrentTargetRead':True,'firstPassComparisonRead':r['firstPassTarget']!=r['currentTarget'],'decision':'objective-replacement-proposed' if r['stableId'] in findbyid else 'accepted-current-wording','findingId':findbyid.get(r['stableId'],{}).get('findingId'),'glossaryFingerprint':D(ROOT/'Documentation/glossary-translations/el/layer.json'),'compiledOccurrences':contexts.get(r['key'],[]),'contextLimit':'static/serialized context only; no runtime launch' if r['collection']!='Dialogs' else ('no compiled-node occurrence; admitted supplemental source only' if r['key'] not in compiledkeys else 'compiled order available; gameplay reachability not verified')})
commands=[]
for cmd in [['.venv/bin/python','Translations/el/build_correction_closure.py','verify'],['.venv/bin/python','Scripts/expand_exact_text_batch.py','Translations/el/dialogue-repeats-001.authored.json','Translations/el/dialogue-batch-006.json','--verify']]:
 p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);commands.append({'command':cmd,'exitCode':p.returncode,'stdout':p.stdout,'stderr':p.stderr});assert p.returncode==0
proof={'result':'structural reproduction passed; semantic/selector acceptance failed','readUnits':1816,'publishedClosureFindings':len(proposals),'boundedOutsideClosureFindings':2,'findings':len(findings),'changedUnitsRead':sum('changed' in r['components'] for r in rows),'compiledNodes':len(nodes),'compiledLineIds':len(compiledkeys),'closureDialogueKeysWithoutCompiledOccurrence':missing,'commands':commands,'attemptAccounting':['An initial repeated-map verification incorrectly targeted batch-001 and failed expectedRows without writing. Resolving authoredMapSha256 identified batch-006; exact verification passed.','A compiled context query used nonexistent NotTrue_Hands_Talk and failed after printing the preceding requested nodes; key-to-node lookup resolved NotTrue_Hands_DontShoot.','Read-only glossary/input probes with incorrect schema assumptions were corrected against observed schemas; no authored/source side effects.'],'manualReadProtocol':{'rangesReadCompletely':[[0,1816]],'unit':'full Russian/current Greek pair; changed pairs include full first-pass target','truncationRepairRanges':[[259,360],[554,569]],'semanticMethod':'Direct complete-unit reading against approved Greek meanings, canonical referents/gender, source roles and compiled branch order. Per-ID decisions are recorded only after the full reading, not inferred from scripts.','notAFullRestart':True},'limits':['No game launch, rendering, UI screenshot or actual gameplay reachability checked.','Static/debug/placeholder units remain in the accepted inventory and are reviewed; reachability is not inferred.','Compiled opcode/argument reconstruction preserves order and branch labels; it does not execute all states.','Unknown-gender mandatory anchors and two kiloton callbacks demonstrate selector incompleteness. Additional bounded review after selector repair is required.','No replacement was applied; parent owns adjudication, regeneration and final gate.'],'telemetry':{'agent':'el_independent_review_01','model':'inherited; exact exposed model label unavailable in this tool surface','reasoning':'inherited; not exposed','inputTokens':None,'cachedInputTokens':None,'outputTokens':None,'totalTokens':None,'note':'No actual per-request or session token telemetry exposed to this reviewer. Parent may reconcile platform session records; unknown is not zero.'}}
for name,obj in [('findings.json',{'status':'objective proposals consolidated; author adjudication required','findings':findings}),('selector-completeness.json',selector),('verification.json',proof)]:
 p=OUT/name;assert not p.exists();p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
p=OUT/'decisions.jsonl';assert not p.exists();p.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in read_decisions))
print(json.dumps({'readUnits':1816,'findings':len(findings),'publishedClosureFindings':len(proposals),'outsideClosureFindings':2,'missingCompiledClosureKeys':len(missing),'omittedCanonicalUnknownGenderAnchors':sum(not x['selected'] for x in anchors)},ensure_ascii=False))
