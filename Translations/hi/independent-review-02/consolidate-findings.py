import json,hashlib,re
from pathlib import Path
R=Path.cwd();P=R/'Translations/hi/independent-review-02';H=R/'Translations/hi'
j=lambda p:json.loads(p.read_text());sh=lambda s:hashlib.sha256(s.encode()).hexdigest()
src=[json.loads(x) for x in (R/'Source/localization-inventory-v3/strings.jsonl').read_text().splitlines()]; targets={};paths={}
for f in j(H/'semantic-cycle-002-structural-gate.json')['files']:
 d=j(R/f['path'])
 if 'collection' in d:
  for e in d['entries']:targets[d['collection'],str(e['id'])]=e['target'];paths[d['collection'],str(e['id'])]=f['path']
src=[r for r in src if (r['collection'],r['stableId'].rsplit(':',1)[1]) in targets]
bykey={r['key']:r for r in src};order={r['stableId']:i for i,r in enumerate(src)};delta={r['stableId']:r for r in [json.loads(x) for x in (P/'delta-pairs.jsonl').read_text().splitlines()]}
items=j(P/'findings-part-001.json')['items']
new=[
('line:Rocker_Entrance_2_0804a1e','Rocker: सुबह होने तक अभ्यास करता रहा, फिर कुछ पागलों ने हमारे अड्डे पर धावा बोल दिया। सब कुछ चुराने लगे। हम उनसे भिड़ गए। कमीनों ने मेरा गिटार तोड़ दिया!','Russian всё пиздить with objects denotes stealing; Hindi substitutes smashing everything, then redundantly reports guitar breaking. Preserve theft and subsequent fight/damage as distinct actions.','Full compiled Rocker_Entrance_2 order read; theft precedes fight and guitar break.'),
('line:Firefighter_Entrance_4_040351d','Firefighter: मैं जंगल की आग बुझाता रहना चाहता हूँ। बेहतर है कि वहाँ मैं मरूँ, वे साथी नहीं।','Current wish and prospective self-sacrifice (я бы хотел; погибну) become past wish and counterfactual death. Colleagues are still dying elsewhere.','Compiled Firefighter_Entrance_4 starts with this present wish, then says superiors forbade further work; Firefighter_Asking_1 distinguishes ongoing colleagues dying from speaker here.'),
('line:Esenin_Asking_SpecialEvent_1_055e5e0','Esenin: ऐसी कविता है। कैसी लगी?','Adds first-person poem ownership/authorship मेरी absent source; speaker is reading a poem found in a book in the player house.','Compiled Esenin_Asking_SpecialEvent says found poetry book, asks to read; successor recites and asks how it was.'),
('line:Entrance_Prophet_3_5_06adbe0','Prophet: जल्द कोई बिल्ली के साथ आएगा। दोनों को घर में आने देना ज़रूरी है।','Russian их refers to arriving person and cat; singular उसे drops the cat from the explicit invitation instruction.','Full compiled prophecy branches 3_4 and 3_5 read; keep unnamed person ambiguity and both arrivals.'),
('line:Twins_Entrance_YesLet_015d8b6','Twins: शायद आपके यहाँ उसकी हालत कुछ सँभल जाए।','Come to oneself in sustained depressive/catatonic exhaustion becomes regain consciousness होश आए; source never establishes unconsciousness. Preserve improvement without adding consciousness diagnosis.','Compiled preceding line: parents death worsened her longstanding state; approved Sirin/Alkonost context and later care/bathing scenes describe depression/exhaustion.'),
('line:Theorist_Ears_Gun_0d7a8f0','Theorist: अतिथियों पर निशाना लगाइए, उनका कंपन अलग होगा!','Hindi noun कंपन is masculine; उनकी...होगी is incompatible noun agreement. Correct oblique possessive and predicate gender together.','Compiled ear-check visitor branch: resonance/vibration; referent is कंपन, not visitor biological sex.'),
('line:Alkonost_Teeth_Gun_00b923d','Alkonost: मैं और मेरी बहन पहले ही बहुत झेल चुकी हैं। यह बंदूक नीचे रख दो।','दोनों subjects are established female sisters, but झेल चुके हैं is masculine plural. Use feminine plural चुकी हैं.','Approved two-sister referents and compiled Alkonost_Teeth_Gun directly identify sister and speaker, not occupant slot.'),
('line:Tough_Ears_DontShoot_0f30496','Tough: सोचती हूँ, यह सब ख़त्म होने पर उन लोगों को कैसा लगेगा जिन्होंने हद से ज़्यादा मनमानी की? हम्म?','Context condemns people allowing themselves excess abuse; Hindi जिन्होंने...छूट दी describes giving others leeway, shifting agency to permissive bystanders.','Compiled after player aims weapon then lowers it; second sentence asks how those offenders will feel. Preserve criticism of excessive acts.'),
('line:phone_psychics_8_049857b','Phone: अगर आप उसे पीते, तो आपके भीतर माइसीलियम उग सकता था और आपको कठपुतली की तरह नियंत्रित कर सकता था।','कवकजाल is a semantic synonym but breaks the approved canonical माइसीलियम term linking the psychic claim and Mushroom discourse. This is terminology consistency, not a claim the synonym denotes something else.','Approved mycelium meaning explicitly includes separate psychic human-internal claim; use term consistently while retaining conditional service claim.'),
('line:Anger_Asking_2_06ebb11','Anger: पागल हैं वे। साधारण लोगों को भी अपने बेतुके धर्म में फँसा लेते हैं, जैसे मेरी…','Completes source unfinished feminine possessive мою… into पत्नी, removing withheld family-role disclosure and the speaker interruption.','Compiled Asking2 ends unfinished мою… then pause; Asking3 later explicitly says Моя жена… before explanation.'),
('line:Anger_Asking_3_0ce7f67','Anger: यह सब बकवास शुरू होते ही उसे किसी नए संरक्षक पर नई आस्था हो गई।','Adds origin धरती के भीतर से आए absent this source unit. Prior Asking2 mentions the underground patron, but that does not authorize inserting repeated exposition into this sentence. Preserve exact new-faith/new-patron statement.','Full compiled Asking2 and3 order read; earlier underground information acknowledged, no claim this is a new global spoiler.')
]
for key,proposal,reason,context in new:
 r=bykey[key];sid=r['stableId']; k=(r['collection'],sid.rsplit(':',1)[1]);before=targets[k]
 items.append(dict(findingId=f'HI-R02-{len(items)+1:03}',stableId=sid,key=key,reviewIndex=order[sid],source=r['source'],before=before,proposedFullTarget=proposal,reason=reason,context=context,authoredPath=paths[k],sourceSha256=sh(r['source']),currentTargetSha256=sh(before),inAssignedDelta=sid in delta))
for x in items:x['reviewIndex']=order[x['stableId']];assert sh(x['before'])==x['currentTargetSha256'];assert x['proposedFullTarget']!=x['before']
normalize=lambda s:re.sub(r'\s+',' ',re.sub(r'^[A-Za-z][A-Za-z0-9_]*: ','',s)).replace('ё','е').replace('Ё','Е').strip()
repetitions=[]
for x in items:
 norm=normalize(x['source']);matched=[]
 for r in src:
  if normalize(r['source'])==norm:
   k=(r['collection'],r['stableId'].rsplit(':',1)[1]);matched.append(dict(stableId=r['stableId'],key=r['key'],source=r['source'],target=targets[k],targetSha256=sh(targets[k]),inAssignedDelta=r['stableId'] in delta))
 repetitions.append(dict(findingId=x['findingId'],normalizedSource=norm,exactSourceFamily=matched))
with (P/'consolidated-full-unit-findings.json').open('x') as f:json.dump(dict(schemaVersion=1,status='findings; all4429 assigned full pairs read, acceptance requires author adjudication and ordinary correction closure',locale='hi',items=items,findingCount=len(items),assignedDeltaFindingCount=sum(x['inAssignedDelta'] for x in items),outsideDeltaFindingCount=sum(not x['inAssignedDelta'] for x in items),authoredEditsMade=False,fullUnitProposals=True),f,ensure_ascii=False,indent=2)
with (P/'finding-repetition-family-evidence.json').open('x') as f:json.dump(repetitions,f,ensure_ascii=False,indent=2)
print('Findings',len(items));print('Exact source families',[(x['findingId'],len(x['exactSourceFamily'])) for x in repetitions]);print('All proposals full units; no authored changes.')
