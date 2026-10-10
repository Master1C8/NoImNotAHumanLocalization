from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Scripts'))
from preserve_exact import check_value
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[json.loads(l) for l in (ROOT/'Translations/nl/semantic-cycle-2/closure/delta-review-rows.jsonl').read_text().splitlines()]
pre=json.loads((OUT/'preflight.json').read_text())
rulesdata=json.loads((ROOT/'Source/preserve-exactly-v4.json').read_text());rules={r['stableId']:r for r in rulesdata['tableRows']+rulesdata['staticRows']}
# Complete replacements manually authored by the independent reviewer after reading all delta pairs.
proposals={
5:'Tourist: Kijk wie hier is: {0}. Ik weet niet zeker of we met elkaar overweg kunnen.',
10:'Alt: Hé, kijk wie hier is: {0}.',
16:'Fairytaller: Maar ik vrees dat ik me ongemakkelijk zal voelen zolang ik de ruimte deel met dit gezelschap: {0}.',
21:'Leper: Kijk wie hier al is: {0}. Juist die persoon kleineerde me om mijn uiterlijk.',
27:'Nervous: O, kijk wie hier is: {0}.',
29:'Bald: Kijk wie hier bij je zit: {0}. Zullen we die misschien op de een of andere manier eruit werken?',
33:'Tough: Wie heb je hier in huis — {0}?',
36:'Jacket: O… Het spijt me, maar u hebt gezelschap in huis: {0}. Ik vertrouw zulke mensen niet erg…',
38:'Experienced: Dit gezelschap bevalt me niet: {0}.',
46:'Unstable: Hé, je hebt hier gezelschap: {0}.',
55:'Wolfhound: Wie zit hier al bij je haard — {0}? Ik zie meteen dat het een wolvin in schaapskleren is.',
64:'Twins: Ik vrees dat u al gezelschap in huis hebt: {0}.',
69:'Greatmother: Hé, wie zit hier bij jou — {0}? Wat een ontmoeting!',
74:'Widow: Wie is hier bij jou — {0}?',
82:'FormerFema: O… ik zie wie er al in de badkamer is: {0}.',
87:'GraveDigger: Potverdorie, je hebt al gezelschap in huis: {0}.',
94:'Provocateur: Tja… ik zie wie u al in huis hebt: {0}.',
98:'TaxiDriver: Begrijp me niet verkeerd, maar je hebt gezelschap in huis: {0}.',
101:'Edgar: Ik zou binnenkomen, maar kijk wie daar al is: {0}. Die persoon maakt zich nog altijd zorgen over morgen…',
103:'Foreigner: (Het lijkt erop dat hij die bewoner niet mag — {0}. Hij wijst naar hem, dan naar zichzelf en daarna weer naar hem.)',
113:'Daughter: O, kijk wie hier is: {0}.',
117:'Scammer: Hé, je hebt hier al gezelschap: {0}. Daar valt geen geld of leuk verhaal uit te halen.',
120:'Cold: Bedankt… O, er is hier al iemand. Ik kom niet binnen zolang dit gezelschap hier is: {0}.',
123:'Esenin: Laat die hier eerst oprotten: {0}. Dan praten we verder.',
132:'Fanatic: Mens! De ZON gebiedt me niet binnen te gaan zolang dit gezelschap zich in je huis schuilhoudt: {0}.',
136:'Luka: Ik zou graag binnenkomen, maar kijk wie daar op dit moment is: {0}.',
139:'Couple: O, ik vind het heel vervelend om u hiermee lastig te vallen, maar we kunnen niet samenleven met dit gezelschap in de buurt: {0}…',
144:'Anger: Wie is hier bij jou — {0}?',
148:'Ballerina: Wie heb je in huis — {0}?',
154:'Teacher: Neem me niet kwalijk, ik zie wie hier bij u is — {0}?',
163:'Blind: Ik voel wie hier bij je is: {0}. Er klopt iets niet aan die persoon.',
165:'Fatman: Ik geef je liever iets, zodat je… ze met je geweer… je weet wel!',
166:'Fatman: Verdomme, je hebt hier gezelschap… {0}. Jaag die de deur uit! Ik ben niet klaar om… voor een bad te vechten.',
169:'Buddy: O, maatje, ik zie wie bij jou al een plekje warmhoudt: {0}.',
172:'Bestson: Ik zie wie er al op je bank zit: {0}. Ik… nou… ik ben bang voor zulke mannen.',
176:'Fugitive: Dat kan ik niet… Vriend, ik ben zulke mensen wel eens tegengekomen. Kijk wie bij jou in huis woont: {0}.',
180:'Nun: Zo, wie hebt u hier wonen — {0}?',
183:'Raskolnikov: Neem me niet kwalijk, ik wil niet onbeleefd klinken, maar je hebt al gezelschap: {0}.',
207:'Twins: Ik denk het niet. Kijk wie hier is: {0}.',
217:'Anger: ...Aha. Duidelijk. Kijk wie hier al is: {0}. Eén blik was genoeg: iedereen hier houdt zich stil en kruipt voor een ander, als ze maar met rust worden gelaten. Zulke mensen kan ik niet uitstaan.',
}
context=json.loads((OUT/'consumer-context.json').read_text())
findings=[]
for idx,target in sorted(proposals.items()):
 r=rows[idx-1];check_value(rules[r['stableId']],target)
 reason='GetCharacterOnPlace returns the exact article-free UI characterName_<enum> label. In this sentence the inserted singular descriptive label is used as a complete noun phrase without its required determiner (and bare plural labels must not be forced into singular agreement). Introduce the exact label separately while retaining the source facts and referent.'
 concept='dynamic-occupant'
 if idx==33:reason='The comma before the occupant label makes the label read as the addressee of the question. The source asks the player who occupies the home, so mark the label as the questioned occupant, not a vocative.'
 if idx==180:reason='The source introduces the queried occupant with an em dash. The target separates the lower-case runtime label into a new sentence after the question; restore its syntactic connection to the identity question.'
 if idx==165:
  reason='The source offers to give the player something so that the player shoots the occupants with the player’s gun. waarmee makes the offered object the means used to shoot, changing the offered inducement into a shooting tool. Preserve purpose with zodat and every pause/referent.';concept='bribe-versus-tool'
 if not r['nodeNames']:
  reason+=' Exact accepted key is absent from the pinned compiled program; this text finding does not establish live reachability or its actual consumer.';concept+='-unbound'
 bindings=[]
 for n in r['nodeNames']:
  ins=context['scenes'][n]['instructions']
  for k,i in enumerate(ins):
   if any(f==2 and any(a==1 and s==r['key'] for a,s in z) for f,z in i):bindings.append({'node':n,'instructionIndex':k,'instruction':i,'precedingInstructions':ins[max(0,k-3):k]})
 findings.append({**r,'deltaRow':idx,'findingId':f'NL-IR02-{len(findings)+1:03d}','decision':'objective correction proposed; author adjudication required','reason':reason,'concept':concept,'proposedReplacement':target,'proposedReplacementSha256':hashlib.sha256(target.encode()).hexdigest(),'consumerBindings':bindings,'protectedSyntaxPreflight':'passed shared preserve_exact.check_value on full unit'})
ids={f['stableId']:f for f in findings}
def write(name,obj):
 p=OUT/name;assert not p.exists();p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
write('findings.json',{'reviewer':'/root/nl_independent_review; same independent reviewer as review 01, distinct from author','model':'exact serving model/reasoning not exposed','closureManifestSha256':sha(ROOT/'Translations/nl/semantic-cycle-2/closure/closure-manifest.json'),'deltaReviewRowsSha256':sha(ROOT/'Translations/nl/semantic-cycle-2/closure/delta-review-rows.jsonl'),'reviewedPairCount':367,'findings':findings})
decisions=[]
changed=set(pre['correctedIds'])
for i,r in enumerate(rows,1):
 decisions.append({**{k:r[k] for k in ['stableId','sourceSha256','targetSha256','components','key','nodeNames']},'deltaRow':i,'decision':'correction-proposed' if r['stableId'] in ids else 'no-objective-text-finding-in-independent-read','findingId':ids[r['stableId']]['findingId'] if r['stableId'] in ids else None,'priorFindingCorrection':'resolved in current full-unit wording' if r['stableId'] in changed else None,'reviewBoundary':'Russian source/current Dutch target; unchanged approved glossary; compiled node and getter evidence where bound; accepted inventory text only where unbound; no game launch'})
p=OUT/'review-decisions.jsonl';assert not p.exists();p.write_text(''.join(json.dumps(d,ensure_ascii=False,sort_keys=True)+'\n' for d in decisions))
p=OUT/'reviewed-ids.txt';assert not p.exists();p.write_text(''.join(r['stableId']+'\n' for r in rows))
assert sha(p)==sha(ROOT/'Translations/nl/semantic-cycle-2/closure/delta-ids.txt')
write('checkpoint.json',{'schemaVersion':1,'game':'No, I’m not a Human','gameVersion':'1.3.19','sourceLocale':'ru','locale':'nl','reviewer':'/root/nl_independent_review','closureManifestSha256':sha(ROOT/'Translations/nl/semantic-cycle-2/closure/closure-manifest.json'),'deltaReviewRowsSha256':sha(ROOT/'Translations/nl/semantic-cycle-2/closure/delta-review-rows.jsonl'),'pairReadCoverage':{'read':367,'total':367,'corrected':38,'newDependencies':329,'explicitInvalidated':0},'reusedReview01UnchangedDecisions':554,'retiredDependencies':848,'allPrior38ProposalsResult':'resolved in current full-unit wording','findingsCount':len(findings),'mandatoryRegressionResult':'remaining dynamic-occupant findings; previous correction regressions resolved','independentVerdict':'corrections required; not clean','editorialAcceptance':'not awarded','runtime':'not-run; owner forbids game launch','imagesTextures':'excluded by owner','unboundDeltaRows':context['unboundDeltaRows'],'unboundConsumerLimitation':'No assertion of live reachability for inventory keys absent from pinned compiled program, including findings on Twins/Anger alternate occupied rows and prior corrected NotTrue key.','nextAction':'Author adjudicates complete findings batch, applies accepted full units, rebuilds immutable closure with all already-enumerated affected dynamic consumers, and hands same reviewer exact corrected + new + explicitly invalidated delta. Do not repeat full corpus or full closure read.','usage':{'inputTokens':'unknown','cachedInputTokens':'unknown','outputTokens':'unknown','reasoningTokens':'unknown','totalTokens':'unknown'},'evidence':{p.name:sha(p) for p in OUT.iterdir() if p.is_file()}})
print('Read 367/367; reused 554 unchanged decisions; prior38 resolved; findings:',len(findings),'; protected syntax passed; not clean.')
