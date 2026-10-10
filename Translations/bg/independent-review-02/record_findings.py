#!/usr/bin/env python3
"""Serialize reviewer-authored full-unit proposals; no authored input mutation."""
import json,hashlib,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
rows=json.loads((ROOT/'Translations/bg/semantic-delta-cycle-002.json').read_text())['nextReviewRows']
proposals={
228:'Nervous: Шибан откачалник ли?',
239:'Bald: Преди живеех тук с мама и баба, но колекторите ни изгониха от апартамента. Историята е пълна шибана каша. Ако ме пуснеш, ще ти я разкажа някой път.',
304:'Anger: Или да пребия някого, мамка му.',
326:'Vigilante: А те се смеят: „Трябва да те вземем при нас“. Да вървят на майната си. Само отвеждат хората, а Гостите после пак си остават.',
341:'Vigilante: Предаде се като парцал. Виждаш резултата — жена му и детето или са в гроба, или кой знае къде, мамка му.',
415:'Gasmask: Това е, защото инатливи шибани тъпаци ни пречат да работим.',
429:'Fatman: Къде да ида? Ебан съм.',
433:'Fatman: Не, аз… хич не съм добре, мамка му.',
442:'Fugitive: Щом видях тая шибана гадост, веднага разбрах каква е работата и реших — трябва да се омитам, мамка му.',
539:'Anger: Или да спукам някого от бой, мамка му.',
544:'Anger: Те просто седят и чакат някой да ги пребие, мамка му, да им изтръгне зъбите или да им направи нещо друго.',
604:'Я се разкарай по добрия начин, мамка му',
606:'Я се разкарай по добрия начин, мамка му',
629:'Тоест просто ти писна до гуша, мамка му, и си тръгна?',
647:'FunnyGuy: Съседите ми се обадиха. Казаха, че при тях става някакъв шибан ад. Почти не излизат от къщи.',
699:'Bald: Или се възползваха от мен, защото им беше удобно, или ме псуваха зад гърба ми, мамка им.',
709:'Разкарай се, мамка му',
738:'Experienced: Знаеш ли, балък, по-добре да си почина, преди да превъртя, мамка му.',
748:'Ебаси якия признак. Отдавна ли го откри?',
750:'Ебаси якия признак. Отдавна ли го откри?',
757:'Да не си откачил, мамка му?',
765:'Rocker: Разправях, че съм преживял куп шибани ужасии и съм станал по-силен, но блъфирах. Просто скрих едно сополиво хлапе под суичъра си.',
774:'Rocker: За какъв дявол изобщо да се старая и да се бъхтя повече, мамка му?..',
786:'Rocker: Сега с тези Гости и палещото слънце е същото — просто нов кръг на шибания кошмар, а аз вече съм свикнал с него.',
787:'Unstable: Все пак благодаря. Отдъхнах си и мога пак да крача два дни без почивка, мамка му.',
1112:'Звучи като пълна шибана простотия',
1121:'Звучи като пълна шибана простотия',
1152:'Esenin: Разкарай се, мамка му, моля те. Не ми е добре.',
1209:'Anger: Мислех си, че никога не ме е обичала, че само е чакала удобен случай да се омете, мамка му. Да ме нарани.',
1236:'Anger: Поне да не се кланяш на слънцето като някой шибан тъпак.',
1318:'Leper: Мамка му…',
1325:'Leper: Мамка му, какво правиш?',
1357:'Bald: На лекар, разбира се, няма да отида, защото, както се казва: „Шибаната простотия минава, а шибаната катастрофа не се лекува“.',
1366:'Bald: Нямам представа кога се появи, но се насрах от страх.',
1425:'Rocker: ДАВАЙ РОК, МАМКА МУ!',
1436:'Rocker: Правих си тунели в ушите. После… някак ми писна, мамка му.',
1456:'Unstable: А, леле. Езикът ми се е оцветил.',
1771:'Wheelchair: Ако… ако ти не вярваш на този признак, как аз да им вярвам?',
1939:'Scammer: По ръцете трябва да разпознаваш шибаните тъпанари и балъците. Какво общо имат Гостите?',
1941:'Scammer: Да ме гръмнеш в лицето заради зъбите, мамка му... това не е по правилата.',
2014:'Anger: Ако бях друг човек, сигурно щях да се уплаша от това, което си причинявам. Но ми е през кура.',
2070:'Wheelchair: Ако… ако ти не вярваш на този признак, как аз да им вярвам?',
2080:'Wheelchair: Това е… пълен шибан ужас.',
}
reasons={
239:('kinship','The clipped Russian ма и ба is resolved by Bald_Asking_4: he lived with his mother and grandmother, while his father left. The approved theater-man glossary explicitly gives mother and grandmother. Current тате invents a father in this household.'),
1318:('idiom','Ёбаный свет is an obscene exclamation here, followed by the warning that the gun threat will cause a heart attack. Literal шибана светлина invents a reference to light.'),
1325:('idiom','The compiled gun setup immediately precedes this frightened exclamation. Ёбаный свет is a curse, not an observation about illumination; шибана светлина gives it a false literal referent.'),
1357:('wordplay-register','The quoted saying deliberately contrasts the two obscene labels хуйня and пиздец; the complete current quotation replaces both with ordinary little nonsense/major trouble. Preserve the contrast and the coarseness in the complete line.'),
1366:('scatological-register','Обосрался expresses being shit-scared. Ме хвана шубето is colloquial but removes the source scatological register; the whole line has no replacement for that feature.'),
1425:('agency-register','ЕБАШЬ РОК is a coarse singular imperative addressed outward after the Kill command. ДА ГО РАЗМАЖЕМ С РОК changes it to a first-person plural exhortation and removes the profanity. Retain the direct imperative and rock reference.'),
1456:('added-detail','Покрасился means became coloured/stained, not specifically became red. The immediately preceding Енержека/chemistry dialogue and IsImposter branch do not state the hue. Use the source-supported colouring description; no excluded texture or imagined colour is used to supply a fact.'),
1771:('number-reference','The speaker asks whether he can trust them (им), followed immediately in the same compiled branch by все они referring to the signs. Bulgarian му reduces that plural reference to the single current sign.'),
2070:('number-reference','This supplemental table duplicate has exactly the same plural Russian им; retain that plurality as in the mapped compiled counterpart, without inventing a separate current consumer.'),
2080:('grammar-naturalness','Пълна шибания is not natural Bulgarian for this shocked curse. Replace the malformed phrase with a grammatical coarse complete unit.'),
}
prior=json.loads((ROOT/'Translations/bg/correction-batch-002.json').read_text());priorDec={r['stableId']:r for r in prior['decisions']};disp=json.loads((ROOT/'Translations/bg/voice-remedial-disposition-cycle-002.json').read_text());byDisp={r['stableId']:r for r in disp['dispositions']};findings=[]
for i,target in proposals.items():
 r=rows[i];assert target!=r['target'];assert re.match(r'^[A-Za-z][A-Za-z0-9]*:',r['source']).group(0) if re.match(r'^[A-Za-z][A-Za-z0-9]*:',r['source']) else True
 prefix=re.match(r'^[A-Za-z][A-Za-z0-9]*:',r['source']);assert not prefix or target.startswith(prefix.group(0))
 assert re.findall(r'\{[0-9]+\}|<[^<>]+>',r['target'])==re.findall(r'\{[0-9]+\}|<[^<>]+>',target)
 category,reason=reasons.get(i,('voice-register','The full Russian unit uses explicitly obscene wording, while the complete current Bulgarian unit uses only neutral or ordinary colloquial wording. Restore a coarse full-line equivalent while preserving its actors, action, polarity, facts and timing; an aggressive colloquial verb alone is insufficient here.'))
 f={'findingId':f'bg-independent-02-{len(findings)+1:03d}','deltaIndex':i,'stableId':r['stableId'],'source':r['source'],'currentFullTarget':r['target'],'proposedFullTarget':target,'category':category,'reason':reason,'sceneNodes':r['sceneNodes'],'authoredPath':r['authoredPath'],'priorAuthorDisposition':byDisp.get(r['stableId']),'previousCorrectionDecision':priorDec.get(r['stableId'])}
 if i in [539,1209]:f['newEvidenceAgainstPriorDecision']='The author changed an ordinary verb to a stronger colloquial verb, but the entire resulting unit still contains no coarse equivalent for the explicitly obscene source verb. This is a register finding on the delivered complete replacement, not a preference reversal.'
 findings.append(f)
path=OUT/'findings.json';assert not path.exists();path.write_text(json.dumps({'reviewer':'/root/bg_independent_review_02','status':'43 consolidated full-unit proposals for author adjudication; not applied','findings':findings},ensure_ascii=False,indent=2)+'\n');print(len(findings),hashlib.sha256(path.read_bytes()).hexdigest())
