from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Scripts'))
from preserve_exact import check_value
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[json.loads(l) for l in (ROOT/'Translations/nl/semantic-cycle-1/closure-v2/closure-review-rows.jsonl').read_text().splitlines()]
manifest=json.loads((ROOT/'Source/preserve-exactly-v4.json').read_text());rules={r['stableId']:r for r in manifest['tableRows']+manifest['staticRows']}
# Every replacement below is authored directly by the independent reviewer as a complete unit.
proposals={
212:('Een vreemde paddenstoel. Hoe kon die nou in een aardappel groeien?','The source в картошке and approved strange-mushroom entry locate growth inside a potato; tussen de aardappels changes it to among potatoes.','strange-mushroom'),
433:('TV: Voor hen klinken de klokken luider. Er is meer oorsmeer.','The day-8 television scene concerns growth in ears; approved ear-wax expressly forbids substituting industrial sulfur. zwavel selects the wrong sense of сера.','ear-wax'),
436:('TV: Alleen oorsmeer blijft over. Vuile gedachten.','Same day-8 earwax motif and explicit approved ear-wax meaning; zwavel changes the referent.','ear-wax'),
623:('U hebt hier gezelschap: {0}...','GetCharacterOnPlace inserts the article-free UI character label. U hebt hier vrouw met een kat is ungrammatical. A colon introduces the exact label without choosing singular/plural articles.','dynamic-occupant'),
639:('Doctor: Hm, ik zie wie je hier in huis hebt: {0}.','Finding 46 changed address but retained an invalid join: GetCharacterOnPlace returns characterName_<enum> from UI with no article, producing ik zie dat je man zonder ogen in huis hebt. Use a label introduction.','dynamic-occupant'),
646:('NotTrue: Hemeltje! Die stoel bij je is al bezet: {0}.','The exact label is article-free; Er zit al vrouw met een kat bij je in de stoel has a missing determiner. Keep already-occupied chair and identity using a label introduction.','dynamic-occupant'),
655:('Hunter: Je hebt hier al gezelschap: {0}.','The getter inserts an article-free label; Je hebt hier al man ... is an invalid assembled noun phrase. A label introduction supports one person or a pair.','dynamic-occupant'),
670:('Mother: Hm… Je hebt hier gezelschap: {0}. Mijn kleintje is al zo vaak bang geweest…','Finding 51 retained Je hebt vrouw ... hier, an invalid assembled noun phrase. The getter inserts the UI label exactly; a label introduction supports its number without inventing an article.','dynamic-occupant'),
691:('BigLebowski: Shit, nee. Jouw fijne plekje is al bezet: {0}, dus ja.','The getter inserts an article-free label; Op jouw fijne plekje zit al man ... is an invalid noun phrase. Preserve the already-occupied nice place and exact label.','dynamic-occupant'),
843:('NotTrue: O, vriendje… wat heb je hier in huis? {0}?','The current comma makes the inserted occupant label read as an addressee after vriendje. Separate the queried label. Exact key is absent from the pinned compiled program, so live consumer/reachability remains unverified; proposed wording is safe for label substitution and requires author adjudication.','dynamic-occupant-unbound'),
690:('BigLebowski: Als je me binnenlaat, maak dan ook een plekje voor me vrij, maat.','Finding 53 uses vrijlaten (leave/keep free) where source освободить and compiled occupied branch require freeing an already-occupied spot. binnenlaat/vrijlaten also lacks the claimed matching finite-form rhyme. This replacement retains freeing, conversational filler and binnenlaat/maat rhyme before the next explicit rhyme comment.','occupied-rhyme'),
714:('MushroomEater: Wacht even. Kun je me laten zien hoe laat het is?','Finding 57 says the previous target only requests being told the time, but laten zien explicitly requests a visual display. Source часы and compiled node do not establish a wristwatch; je horloge introduces an unsupported object restriction. Restore the source-compatible visual time request rather than assume a wristwatch.','clock-at-twelve'),
1162:('Leper: Godverdomme…','Finding 121 reads Ёбаный свет literally as a light reference. In this compiled post-gun ear scene it is an idiomatic exclamation followed by complaints about the gun/ear criterion, with no light referent; Dat verdomde licht introduces one. Restore the expletive.','idiomatic-expletive'),
1165:('Leper: Godverdomme, wat doe je?','Finding 122 similarly literalizes the established exclamation Ёбаный свет in response to drawing a gun. The source addresses the players action, not a lighting observation.','idiomatic-expletive'),
1206:('Marauder: Ik zette hem af en keek naar de glazen. Er stonden nog vingerafdrukken op. Ik bleef me voorstellen hoe dat kind hem droeg en de wereld zag…','Снял их describes taking the glasses off; pakte hem op describes picking them up. Compiled scene narrates finding the childs glasses, then inspecting them, then worrying the child cannot see. Retain the removal action, fingerprints and every remaining sentence.','glasses-removal'),
1261:('Firefighter: Als het vuur om je heen raast, besef je hoe kostbaar stilte is. Kuch-kuch, mijn oren kan het nu niet meer schelen, maar mijn ziel nog wel.','ушам теперь всё равно says ears no longer care, contrasting with the soul; zijn er nu doof voor introduces deafness rather than preserving that emotional/metaphorical contrast. Keep the source-level statement without inventing a clinical loss of hearing.','hearing-versus-indifference'),
640:('NotTrue: Och, lieverd toch, lieverd. Ach, kun je voor oma misschien een stoeltje naar buiten brengen?','babushka'),
641:('NotTrue: O, dank je, vriendje! Je hebt oma geholpen. Jammer dat je iemand voor mij weg moest sturen…','babushka'),
1109:('NotTrue: Het leven lijkt stil te staan, lieverd.','babushka'),
1110:('NotTrue: Och, lieverd…','babushka'),
1111:('NotTrue: O, die ouwe zak is dood, lieverd.','babushka'),
1116:('NotTrue: Och, lieverd, gelukkig ben ik van mijn man af. Wat een ouwe zak was het. Bah.','babushka'),
1117:('NotTrue: Iedereen is me vergeten, lieverd.','babushka'),
1118:('NotTrue: Ik heb geen buitenhuisje. En ook geen familie. Of kleinkinderen… Och, lieverd…','babushka'),
1119:('NotTrue: Ik ben een stadsvrouw, lieverd. Ik woonde gewoon in een flatje.','babushka'),
1212:('NotTrue: Wat is dit nu weer, vriendje? Wat kun je aan oren zien?','babushka'),
1216:('NotTrue: Haha, vriendje, wat heb je nu bedacht.','babushka'),
1217:('NotTrue: Nou, wat zeg je nu, vriendje?','babushka'),
1243:('NotTrue: “Naar de zesvingerige onwaarheid het huis in…” Naar mij, vriendje. Kom maar binnen.','babushka'),
1244:('NotTrue: Zo leef ik dus, vriendje, met dat onafgemaakte karwei in mijn mond.','babushka'),
1245:('NotTrue: Nou ja. Ik heb er niets op tegen, integendeel. Wat kan mij het schelen, vriendje? Ik wil al lang naar God toe.','babushka'),
1246:('NotTrue: Wat is dit nu weer, vriendje? Wat kun je aan oren zien?','babushka'),
1250:('NotTrue: Het is, vriendje, een stempel van de ouderdom. Iedereen die zijn leven bijna achter de rug heeft, krijgt zo’n cadeautje. Wist je dat niet?','babushka'),
1252:('NotTrue: Haha, vriendje, wat heb je nu bedacht.','babushka'),
1253:('NotTrue: Nou, wat zeg je nu, vriendje?','babushka'),
1254:('NotTrue: Kijk er niet in, vriendje. Er zit niets.','babushka'),
1255:('NotTrue: O, vriendje… weet je zeker dat je dat wilt?..','babushka'),
1256:('NotTrue: Hehe. Kijk maar goed, vriendje. Je zult toch niets nieuws zien.','babushka'),
}
findings=[]
for idx,p in sorted(proposals.items()):
 r=rows[idx-1];target=p[0]
 if len(p)==2:
  reason='Finding 78 correctly identified loss of NotTrue\u2019s affectionate address in bare jongen, but the same risk remains here. Approved babushka explicitly uses lieverd for милок and vriendje for дружок; preserve this recurring voice and the source\u2019s affection, not just the addressee\u2019s age.';concept=p[1]
 else:reason,concept=p[1:]
 check_value(rules[r['stableId']],target)
 findings.append({**r,'closureRow':idx,'findingId':f'NL-IR01-{len(findings)+1:03d}','decision':'objective correction proposed; author adjudication required','reason':reason,'concept':concept,'proposedReplacement':target,'proposedReplacementSha256':hashlib.sha256(target.encode()).hexdigest(),'protectedSyntaxPreflight':'passed shared preserve_exact.check_value on full unit'})
ids={f['stableId']:f for f in findings}
def write(name,obj):
 p=OUT/name;assert not p.exists();p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
write('findings.json',{'reviewer':'/root/nl_independent_review; distinct from corpus author','model':'GPT-6; exact serving model/reasoning not exposed','closureManifestSha256':'4126276fde69a4b581c1ee883618b51b42c0b49558e757a4cd7ddaef1f0a223d','reviewedPairCount':1440,'findings':findings})
decisions=[]
for i,r in enumerate(rows,1):decisions.append({**{k:r[k] for k in ['stableId','sourceSha256','targetSha256','components']},'closureRow':i,'decision':'correction-proposed' if r['stableId'] in ids else 'no-objective-text-finding-in-independent-read','findingId':ids[r['stableId']]['findingId'] if r['stableId'] in ids else None,'reviewBoundary':'source/current authored target; glossary; scene/key context; explicit compiled consumer contexts for high-risk joins; no game launch'})
p=OUT/'review-decisions.jsonl';assert not p.exists();p.write_text(''.join(json.dumps(d,ensure_ascii=False,sort_keys=True)+'\n' for d in decisions))
p=OUT/'reviewed-ids.txt';assert not p.exists();p.write_text(''.join(r['stableId']+'\n' for r in rows))
write('checkpoint.json',{'schemaVersion':1,'game':'No, I\u2019m not a Human','gameVersion':'1.3.19','sourceLocale':'ru','locale':'nl','reviewer':'/root/nl_independent_review','closureManifestSha256':'4126276fde69a4b581c1ee883618b51b42c0b49558e757a4cd7ddaef1f0a223d','pairReadCoverage':{'read':1440,'total':1440},'findingsCount':len(findings),'mandatoryRegressionResult':'findings','independentVerdict':'corrections required; not clean','editorialAcceptance':'not awarded','runtime':'not-run; owner forbids game launch','imagesTextures':'excluded by owner','unchangedContextLimitation':'Finding 78 key is unbound in pinned compiled program; no claim of live reachability. Supplemental static/debug strings are reviewed within accepted text inventory, not asserted visible.','nextAction':'Author adjudicates full findings batch, repairs bounded selector/recipe for all affected dynamic-label and old-woman-address uses, applies accepted corrections, rebuilds immutable closure and prepares exact delta: corrected IDs + new closure IDs + explicitly invalidated prior evidence. Do not rerun the full 16,538-unit semantic pass.','usage':{'inputTokens':'unknown','cachedInputTokens':'unknown','outputTokens':'unknown','totalTokens':'unknown','reasoningTokens':'unknown'},'evidence':{p.name:sha(p) for p in OUT.iterdir() if p.is_file()}})
print('Reviewed 1440 pairs; proposed',len(findings),'full-unit corrections; protected syntax all passed; not clean.')
