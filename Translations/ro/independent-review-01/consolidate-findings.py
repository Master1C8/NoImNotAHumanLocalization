"""Consolidate full-unit semantic proposals without changing authored files."""
import hashlib,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('recipe',ROOT/'Translations/ro/correction-cycle-001-recipe-v3.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
progress=json.loads(m.PROGRESS.read_text());rows={}
for x in progress['reviewSegments']:
 for l in (ROOT/x['path']).read_text().splitlines():r=json.loads(l);rows[r['ordinal']]=r
_,values,locations=m.authored();closure=[json.loads(l) for l in (ROOT/'Translations/ro/correction-cycle-001-closure-v3/review-rows.jsonl').read_text().splitlines()];closureids={r['stableId'] for r in closure}
rules=json.loads(m.MANIFEST.read_text());rules={r['stableId']:r for r in rules['tableRows']+rules['staticRows']}
from preserve_exact import check_value
proposals=[]
def add(o,target,reason,group):
 r=rows[o];current=values[r['stableId']];assert target!=current;check_value(rules[r['stableId']],target)
 proposals.append({'findingId':f'ro-ir01-{o:05d}','ordinal':o,'stableId':r['stableId'],'collection':r['collection'],'key':r['key'],'source':r['source'],'currentTarget':current,'proposedTarget':target,'reason':reason,'defectGroup':group,'authoredPath':locations[r['stableId']][0],'insideAuthoritativeClosure':r['stableId'] in closureids,'fullUnitRead':True})
add(151,'persoana adolescentă cu șapcă','Approved bar-teenager entry expressly requires the initial entrance label to remain neutral before disclosure. adolescentul introduces a male reading and conflicts with that exception.','hidden-character-label')
add(5427,'Și cu cât sunt ciupercile mai mari...','Russian nominative грибы with больше compares size; quantity would require грибов. Compiled Mushroom_end_2 puts this immediately before ordinal5619 and explains that larger caps contain more malice. Current target compares quantity.','mushroom-size')
add(3736,'Hunter: M-ai mai și omorî cu cuțitul noaptea.','прирезал denotes killing with a knife; înjunghia alone denotes stabbing and omits death. Same distinction as the accepted Esenin correction13765.','violent-action')
add(8544,'Hunter: Dacă unul dintre ei se dovedește Musafir, mă păcălește și mă omoară cu cuțitul noaptea.','зарежет denotes knife murder. Current înjunghie loses the fatal outcome, as in the accepted Esenin13765 correction.','violent-action')
dogreason='The scene explicitly uses generic собака without independent biological-sex evidence; the approved rule forbids inferring sex from Russian feminine noun agreement. Source also says the dog was old. Current authored story already uses generic câine at9186 and the corrected13185. Keep that referent and its Romanian grammatical agreement across the connected branches.'
for o in [9217,9223]:add(o,'Buddy: Aveam un câine, iar zilele trecute… a murit.',dogreason,'dog-referent')
add(9190,'Buddy: Ai văzut vreodată cum plâng câinii? Ochii lui parcă mă rugau să-i curm toată suferința.',dogreason,'dog-referent')
add(9192,'Buddy: El… suferea foarte mult. Pur și simplu nu puteam să mă uit.',dogreason,'dog-referent')
add(9200,'Buddy: MAȘINA AIA NENOROCITĂ! Dacă taximetristul se uita pe unde mergea, el ar fi trăit mai mult.',dogreason,'dog-referent')
add(9202,'Buddy: Știu cum poate suna. Dar lasă-mă să-ți spun, amice. El… suferea foarte mult. Pur și simplu nu puteam să mă uit.',dogreason,'dog-referent')
add(9205,'Buddy: L-am ucis.',dogreason,'dog-referent')
add(9210,'Buddy: L-am ucis…',dogreason,'dog-referent')
add(9214,'Buddy: Tocmai asta e. Deși era bătrân și bolnav, totuși...',dogreason,'dog-referent')
add(14695,'Buddy: Îmi fotografiam des câinele. Nu mă mai săturam să-l privesc. Voiam să le arăt și altora pozele cu el.',dogreason,'dog-referent')
add(14696,'Buddy: Ciudat, nu? El a plecat, dar eu încă îi port urmele pe mine, ca să zic așa…',dogreason,'dog-referent')
add(14697,'Buddy: M-am gândit că poate îl încălzesc, poate o să-i fie mai bine… Și uite că mi-a lăsat, pesemne, o micoză drept amintire.',dogreason,'dog-referent')
add(14698,'Buddy: În ultima lui noapte n-am plecat de lângă el.',dogreason,'dog-referent')
add(14703,'Buddy: Cu mâinile astea îmi țineam odată câinele, pe când încă trăia. Îl mângâiam și avea blana atât de moale!',dogreason,'dog-referent')
add(14740,'Buddy: N-ai ce să vezi aici, pe cuvânt. Sunt mari, păroase și mai am și o micoză. Probabil am luat-o când am dormit cu câinele pe podea.',dogreason,'dog-referent')
add(7113,'Cat: (Aveți senzația ciudată că în noaptea asta puteți dormi liniștit.)','The parenthetical narration addresses the single male Player using polite plural verbs. liniștiți incorrectly makes the addressee plural; singular masculine liniștit preserves the actual protagonist. Same agreement class as the accepted polite-player corrections.','player-number')
add(9949,'Neighbour: Apropo, ți-am adus o ladă de bere. Fratele soției mele lucrează la o fabrică de bere.','Russian specifies the wife’s brother. Cumnatul also permits a sibling’s husband and loses which kinship edge is stated. The approved audit requires preserving explicit kinship roles.','kinship')
add(12080,'Arată ca o iritație sau, mai rău, o micoză.','This is the selfcheck_armpit_imposter medical lesion context, not an edible mushroom. Approved armpit-fungus term is Micoză la axile, and other authored armpit lines use micoză.','fungal-condition')
add(13698,'Cold: E vreo micoză acolo? Probabil fiindcă totuși transpir sub geacă.','Cold_Armpit_Gun discusses an axillary fungal infection, not an edible ciupercă. Use the approved medical referent, as in other armpit branches.','fungal-condition')
add(15056,'Raskolnikov: Dar într-o zi un bătăuș mi-a zburat un dinte și atunci mi-am promis: dacă nu pot fi puternic, măcar voi fi fără cusur.','выбил denotes a tooth knocked out by a bully. scos describes removal without the blow. This repeats the accepted Buddy14705/Scammer15654 distinction; compiled branch explains inability to defend himself.','violent-action')
add(15060,'Raskolnikov: Dar într-o zi un bătăuș mi-a zburat un dinte. Și ce crezi că am făcut?','Same knocked-out tooth as15056, on the other IsImposter branch. Preserve the violent blow rather than neutral extraction.','violent-action')
add(15169,'O ureche cât se poate de obișnuită, nu? Cercelul? Trebuie să fiu măcar puțin feminină, heh.','Compiled Wifefema_Ears examines her ear. The Romanian predicate must refer to feminine ureche. This is the same explicit referent agreement problem corrected in Wifefema_Photo15174. Speaker-prefix absence remains preserved.','body-referent-agreement')
add(16310,'Firefighter: Știi, cof-cof, n-am reușit niciodată să-i obișnuiesc pe copii să se spele pe dinți zilnic. Iar acum… acum nu mai am cui să amintesc asta.','некому напоминать marks the absent person to whom he can give a reminder. Current nu mai are cine să le amintească instead says there is no reminding agent. Earlier scene says his children are at home and he stays away; this does not establish their death. Preserve the addressee/agent distinction.','action-role')
add(16398,'La lista de dorințe','В желаемое is the wishlist control. La cel dorit means to the desired one and fails to name the list/action. Serialized static binding points to the wishlist key86605930199502848; no live binding/reachability claim.','wishlist-ui')
for o,target in [(12206,'Esenin: Du-te-n pula mea, mă…'),(12228,'Esenin: Atunci du-te-n pula mea.'),(15596,'Scammer: Du-te-n pula mea cu casa ta cu tot, eu plec.')]:
 add(o,target,'Source нахуй is explicit coarse dismissal; dracului weakens it to a mild curse. These speaker voices require the explicit register, and accepted Scammer10042 already corrected precisely this mapping to du-te-n pula mea.','coarse-register')
def write(name,obj):
 p=OUT/name;assert not p.exists();p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
proposals.sort(key=lambda x:x['ordinal']);assert len({x['stableId'] for x in proposals})==len(proposals)
write('findings.json',{'schemaVersion':1,'review':'Romanian independent correction-closure review01','status':'consolidated objective proposals; author adjudication required','findings':proposals,'findingCount':len(proposals),'closureFindingCount':sum(x['insideAuthoritativeClosure'] for x in proposals),'dependencyFindingCount':sum(not x['insideAuthoritativeClosure'] for x in proposals),'proposedTargetsPreserveExactlyPassed':True,'authoredEdits':0})
byfinding={x['stableId']:x for x in proposals};placements=json.loads((OUT/'compiled-placements.json').read_text())['rows'];byplace={x['stableId']:x['placements'] for x in placements}
p=OUT/'per-id-decisions.jsonl';assert not p.exists()
with p.open('w') as f:
 for r in closure:
  decision={'ordinal':r['ordinal'],'stableId':r['stableId'],'key':r['key'],'sourceSha256':hashlib.sha256(r['source'].encode()).hexdigest(),'targetSha256':hashlib.sha256(r['after'].encode()).hexdigest(),'fullSourceAndCurrentTargetRead':True,'decision':'correction-proposed' if r['stableId'] in byfinding else 'no-objective-correction-in-reviewed-unit','findingId':byfinding[r['stableId']]['findingId'] if r['stableId'] in byfinding else None,'compiledPlacements':byplace[r['stableId']],'contextLimit':'Pinned compiled ordering reviewed; no VM/live runtime or visual proof. Catalog dependency omissions separately fail closure completeness.'}
  f.write(json.dumps(decision,ensure_ascii=False)+'\n')
write('additional-dependency-decisions.json',{'reason':'Bounded connected dog referent branches inspected after the closure read, not a restarted16538-unit semantic pass.','proposals':[x for x in proposals if not x['insideAuthoritativeClosure']]})
print('findings',len(proposals),'insideClosure',sum(x['insideAuthoritativeClosure'] for x in proposals),'dependency',sum(not x['insideAuthoritativeClosure'] for x in proposals),'decisions',len(closure))
