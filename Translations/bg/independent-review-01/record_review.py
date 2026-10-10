"""Record independently authored review proposals without mutating review inputs."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
c=json.loads((ROOT/'Translations/bg/semantic-closure-cycle-001.json').read_text());rows=c['reviewRows']
proposals={
389:('unsupported specificity','Window: Сякаш тази кожа не му е по мярка.','Russian says the skin does not fit his size, without saying whether it is too tight or too loose. Тясна asserts too tight; the preceding folds do not authorize that direction. The compiled window_2_1 sequence is pale person → folds → size mismatch → gaze → fear.'),
444:('unsupported specificity','Window: Сякаш тази кожа не му е по мярка.','Exact Russian-source repetition of closure row 389. This is an accepted supplemental row without a current compiled use; the same unsupported tightness assertion must not survive in the retained translated table.'),
669:('tense','Experienced: Жена ми си намери друг, детето се страхуваше от мен, а заради присъдата вече не мога да си намеря работа.','Source contrasts past family events with current inability to obtain work (не могу). Target не можех makes the employment problem past. Compiled Experienced_Asking_4 instruction 21 places this after the account of his third imprisonment and before the player asks what prevents returning now.'),
674:('chronology','Experienced: Когато бях в затвора за първи път, си мислех: само да изляза и веднага спирам.','Будучи первоходом and вот освобожусь locate the thought during first imprisonment. След първия си престой says after that imprisonment, contradicting the still-future release. Compiled Experienced_Asking_4 instruction 16 precedes the account of finding a wife after release.'),
940:('character agreement','Пусни я','This option ends the ear check on the canonically female nun. Compiled Nun_Ears instruction 6 is this exact option, following ShowSign Nun EAR and before the gun option. Approved glossary nun requires feminine agreement; masculine го points to a male.'),
1071:('approved concept distinction','Scammer: Гледаш човека, казваш му, че в него е Гостният дух, и му искаш пари, за да не разказваш на никого.','Source explicitly uses Гостевой, the spirit term, not Гость. Approved visitor-spirit requires Гостният дух and forbids merging it with a Guest creature. Compiled Scammer_Ears instruction 1 is his account of a blackmail scam, between his claim to have invented it and asking not to use it against him.'),
1302:('action and consumer','Anger: Давай, снимай, мамка му.','This is permission to take an aura photograph, not permission to fire the shotgun. Compiled Anger_Photo instruction 0 is followed immediately by ShowSign Anger AURAPHOTO; drawing the gun is a later separate player option. Bulgarian стреляй instructs gun firing and changes the action. The replacement keeps an impatient coarse tone.'),
1342:('approved cat designation','Отключи котарака','The source debug action unlocks the game cat. Approved cat explicitly preserves котарак and the source male grammatical designation without claiming independently established biological sex. Котката departs from that specified designation; it is not a reason to change the glossary or infer biological facts.'),
1366:('word truncation','Добави в списъка с желания','Желани is a truncated adjective, not the noun желания required by wishlist. Source В желаемое and the correctly translated full UI wishlist unit identify the action. Serialized scope maps this exact label to a missing source-table binding, so its retained authored fallback text also needs to be correct.'),
1419:('proper name','ЛЕЛЕ! CRITICAL REFLEX!','CRITICAL REFLEX is the unchanged Latin proper name in the Russian-source exclamation, alongside retained developer names in the same static inventory. Translating it to КРИТИЧЕН РЕФЛЕКС replaces the publisher name with an ordinary phrase. Serialized scope identifies the unbound Notepad/LeftPage text.'),
1493:('object agreement','Приятел я донесе. Дори бирата ме приспива...','The description refers to beer, labeled Бира in the adjacent same consumable display, and Бира is feminine in the approved glossary. Го disagrees with that named drink. Serialized scope places this in ConsumablesCloseUp/NarrativeDescriptionPanel; the actual SetupConsumable consumer sets localized name and narrative for the same selected consumable. This is a retained static initial value, not a claim it remains visible after SetupConsumable overwrites it.'),
565:('profanity','Wolfhound: Тия ваши обществени норми и всякакви други шибани простотии вече не важат.'),
594:('profanity','Защо, мамка му, ме занимаваш с това?'),
634:('profanity','Bald: И това е пълен шибан кошмар…'),
641:('profanity','Bald: Беше пълен шибан ужас…'),
643:('profanity','Bald: А с целия този шибан ад, който настана тук, хората озверяха, особено събирачите на дългове.'),
644:('profanity','Bald: С две думи, пълен шибан ужас.'),
679:('profanity','Rocker: Животът е пълна шибана гадост, с две думи…'),
683:('profanity','Rocker: По-добре да разеба стара китара, отколкото главата си. Китарата можеш да залепиш, ако се наложи, главата — не.'),
684:('profanity','Rocker: Всеки път завършвахме песента с пауза. Седим, мълчим и някой тихо добавя: „Този куплет беше за еди-кой си приятел“. И толкова — без плач, без шибани глупости.'),
772:('profanity','Couple: Мамка му, писна ми от нея, разбирате ли?'),
815:('profanity','Esenin: Всички са откачили, мамка му. Някои от стрес, други от алкохола.'),
831:('profanity','Anger: Шибани откачалки. Привличат дори нормални хора към налудничавата си вяра, като моята…'),
842:('profanity','WheelChair: Аз самият не разбирам много. И ми е през кура.'),
904:('profanity','Tough: Нали не си от ония изроди, които ще се заяждат заради този шибан признак?'),
952:('profanity','Anger: Това адски ме напряга, ебаси. Но се усещам твърде късно, че пак го правя.'),
959:('profanity','Esenin: Но не е там работата. Работата е, че щом свалиш пушката след такава шибана простотия, ще те пребият здравата.'),
1146:('profanity','Fatman: Голяма работа, имам проблем с подмишниците! Кой в днешно време няма някакви шибани гадости?'),
1292:('profanity','Anger: Преди мислех, че е някаква шибана нервна простотия.'),
1293:('profanity','Anger: Тогава се смеех и ѝ казвах: „Абе, бабо, това са пълни шибани глупости.“'),
1294:('profanity','Anger: Не ми е останала дори снимка на баба ми. Не обичаше тези шибани глупости.'),
1298:('profanity','Anger: Не мога да повярвам. Ти си просто шибан откачалник!..'),
}
findings=[]
for index,p in sorted(proposals.items()):
 row=rows[index];category,target=p[:2]
 reason=p[2] if len(p)>2 else 'The full Russian unit contains explicit coarse profanity, while its current Bulgarian rendering removes it. The approved character voice and universal contract retain profanity; the author already accepted equivalent register restoration in correction decisions 40–42 and 47. This proposal restores coarse register in this complete unit without changing the speaker, event or referent.'
 source_prefix=re.match(r'^([A-Za-z][A-Za-z0-9]*):',row['source'])
 if source_prefix:assert target.startswith(source_prefix.group(0))
 assert re.findall(r'\{\d+\}|<[^<>]+>',row['target'])==re.findall(r'\{\d+\}|<[^<>]+>',target)
 findings.append({'findingId':f'bg-independent-01-{len(findings)+1:03d}','closureIndex':index,'stableId':row['stableId'],'authoredPath':row['authoredPath'],'key':row['key'],'sceneNodes':row['sceneNodes'],'source':row['source'],'currentFullTarget':row['target'],'proposedFullTarget':target,'category':category,'objectiveReason':reason,'status':'proposal for author adjudication; not applied'})
(OUT/'findings.json').write_text(json.dumps({'schemaVersion':1,'locale':'bg','cycle':'001','closureSha256':hashlib.sha256((ROOT/'Translations/bg/semantic-closure-cycle-001.json').read_bytes()).hexdigest(),'findingCount':len(findings),'profanityFindingCount':sum(x['category']=='profanity' for x in findings),'findings':findings},ensure_ascii=False,indent=2)+'\n')
ids=[r['stableId'] for r in rows];payload=('\n'.join(ids)+'\n').encode();(OUT/'read.ids').write_bytes(payload)
assert payload==(ROOT/'Translations/bg/semantic-cycle-001-closure.ids').read_bytes()
mandatory=set(c['components']['mandatoryRegressions']['ids'])
(OUT/'mandatory-read.ids').write_text('\n'.join(r['stableId'] for r in rows if r['stableId'] in mandatory)+'\n')
print({'findings':len(findings),'profanity':sum(x['category']=='profanity' for x in findings),'exactReadIds':len(ids),'mandatoryReadIds':len(mandatory),'readIdsSha256':hashlib.sha256(payload).hexdigest()})
