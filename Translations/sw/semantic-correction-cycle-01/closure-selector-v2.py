import json,glob,hashlib,re,unicodedata,datetime,collections
from pathlib import Path
R=Path("/Users/antonkrutov/Desktop/no I'm not a human");S=R/'Translations/sw';E=S/'semantic-correction-cycle-01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):
 if p.exists():raise RuntimeError('immutable path exists '+str(p))
 p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def jsonl(p,rows):
 if p.exists():raise RuntimeError('immutable path exists '+str(p))
 with p.open('w') as f:
  for x in rows:f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
def must(x,m):
 if not x:raise RuntimeError(m)
p=json.loads((S/'correction-progress.json').read_text());must(p['status']=='final-structural-gate-passed-closure-pending','checkpoint')
f=json.loads((E/'correction-batch-preflight.json').read_text());a=json.loads((E/'applied-batch-manifest.json').read_text())
vpath=R/p['finalValidationPath'];must(vpath.exists() and sha(vpath)==p['finalValidationSha256'],'validation pending');v=json.loads(vpath.read_text());must(v['validatedUnits']==16538 and v['validatedArtifacts']==187,'validation coverage')
reviewed={}
for path in sorted((S/'semantic-audit-pass-01').glob('reviewed-*.jsonl')):
 for line in path.open():
  x=json.loads(line);must(x['stableId'] not in reviewed,'review duplicate');reviewed[x['stableId']]=x
must(len(reviewed)==16538,'review count')
canon=sorted(reviewed,key=lambda sid:reviewed[sid]['sourceIndex']);order={sid:i for i,sid in enumerate(canon)}
source={}
for path in (R/'Source/localization-inventory-v3/strings.jsonl',R/'Source/localization-inventory-v3/static-text.jsonl'):
 for line in path.open():
  x=json.loads(line);source[x['stableId']]=x
by_num={int(sid.rsplit(':',1)[1]):sid for sid in reviewed if sid.startswith('string:')}
final={};artifact={}
for rec in v['artifacts']:
 path=R/rec['artifact'];must(sha(path)==rec['artifactSha256'] and sha(R/rec['sidecar'])==rec['sidecarSha256'],'validated artifact drift')
 d=json.loads(path.read_text())
 for row in d['entries']:
  sid=row.get('stableId') or by_num[row['id']];must(sid not in final,'duplicate target');final[sid]=row['target'];artifact[sid]=rec['artifact']
must(set(final)==set(reviewed),'coverage IDs')
changed={x['stableId']:x for x in f['replacements']};must(len(changed)==273,'changed count')
refine=json.loads((E/'post-apply-refinement.json').read_text());refined={x['stableId']:x['finalTarget'] for x in refine['refinements']}
for sid in canon:must(final[sid]==(refined.get(sid,changed[sid]['selectedFullTarget']) if sid in changed else reviewed[sid]['target']),'unplanned target '+sid)
components={}
components['changed']=set(changed)
# Complete Yarn node is the smallest available stable consumer grouping in the extracted inventory.
node_to_ids=collections.defaultdict(set)
for sid in canon:
 r=source[sid]
 for n in r.get('nodeNames',[]):node_to_ids[(r.get('collection'),n)].add(sid)
ctx=set()
for sid in changed:
 r=source[sid]
 for n in r.get('nodeNames',[]):ctx.update(node_to_ids[(r.get('collection'),n)])
# Static/UI fragments lacking Yarn nodes get immediate accepted source neighbors; UI/static catalog also applies.
for sid in changed:
 if not source[sid].get('nodeNames'):
  i=order[sid]
  for j in range(max(0,i-2),min(len(canon),i+3)):
   if reviewed[canon[j]]['collection']==reviewed[sid]['collection']:ctx.add(canon[j])
components['containing-context']=ctx
# Exact and punctuation/spelling-normalized source repeats plus exact old/new localized wording.
def norm(s):
 s=unicodedata.normalize('NFKC',s).casefold().replace('ё','е')
 return ''.join(c for c in s if c.isalnum())
source_norm={norm(source[sid]['source']) for sid in changed}
oldnew={x['oldTarget'] for x in changed.values()}|{x['selectedFullTarget'] for x in changed.values()}
rep={sid for sid in canon if norm(source[sid]['source']) in source_norm or reviewed[sid]['target'] in oldnew or final[sid] in oldnew}
components['exact-and-spelling-repetitions']=rep
# Glossary concepts actually implicated by corrections. Each regex deliberately includes Russian inflection and target wording.
patterns={
 'fema-and-acronym':r'КЧС|К[. ]Ч[. ]С|\bKHD\b|Культ Человеческой Смерти|Kamati ya Hali za Dharura',
 'visitors-and-signs':r'Гост[ьяиуейямов]*|Wageni|Mgeni|Visitors?',
 'death-personification-and-cult':r'Смерт[ьиьюей]*|\bKifo\b|Death',
 'house-and-anonymous-object':r'(?<!\w)дом(?:а|у|е|ом|ов|ами|ах|ой|ик|ика|ике)?(?!\w)|(?<!\w)Nyumba(?!\w)',
 'sun-and-sun-faced-references':r'солнц[а-яё]*|солнечн[а-яё]*|(?<!\w)jua(?!\w)|Uso wa Jua',
 'photo-and-camera':r'фото[а-яё]*|снимк[а-яё]*|камер[а-яё]*|(?<!\w)picha(?!\w)|(?<!\w)kamera(?!\w)',
 'teeth-and-eye-signs':r'зуб[а-яё]*|глаз[а-яё]*|радужк[а-яё]*|(?<!\w)meno(?!\w)|(?<!\w)macho(?!\w)|(?<!\w)jicho(?!\w)|(?<!\w)irisi(?!\w)',
 'visitor-detection-signs':r'признак[а-яё]*|далили|dalili',
}
concept={}
for name,pat in patterns.items():
 rx=re.compile(pat,re.I);concept[name]={sid for sid in canon if rx.search(source[sid]['source']+' '+final[sid])}
components['glossary-referents']=set().union(*concept.values())
# Runtime binding topology for changed TMP fields. Unknown dynamic bindings remain separately documented.
scope=json.loads((R/'Documentation/static-text-scope-v2.json').read_text())['rows'];scope_by={x['stableId']:x for x in scope}
run=set()
changed_static=[sid for sid in changed if sid.startswith('tmp:')]
for sid in changed_static:
 row=scope_by[sid];known={z.get('sourceStableId') for z in row['localizedStringBindings'] if z.get('sourceStableId')}
 run.update(known&set(canon))
 parent=row['sceneAncestry'][-2]['gameObjectId'] if len(row['sceneAncestry'])>=2 else None
 if parent is not None:
  run.update(x['stableId'] for x in scope if x['stableId'] in reviewed and len(x['sceneAncestry'])>=2 and x['sceneAncestry'][-2]['gameObjectId']==parent)
components['runtime-binding-and-layout']=run
# Stable mandatory semantic regression catalog. Full speaker/placeholder structural checks remain full-corpus gates.
gender=re.compile(r'(?i)(?<!\w)(?:он|она|его|её|ее|жена|муж|дочь|сын|брат|сестра|мама|мать|папа|отец|девочка|девушка|женщина|мужчина|ребёнок|ребенок)(?!\w)')
syntax=re.compile(r'\{[^{}]+\}|<[^<>]+>')
regsets={
 'ui-menu-hud-title-locale-save-input':{sid for sid in canon if reviewed[sid]['collection']=='UI'},
 'static-tmp-credits-environment':{sid for sid in canon if reviewed[sid]['collection']=='SupplementalStatic'},
 'accepted-checks-surface':{sid for sid in canon if reviewed[sid]['collection']=='ChecksDialogs'},
 'gender-kinship-address':{sid for sid in canon if gender.search(source[sid]['source'])},
 'placeholder-markup-linebreak':{sid for sid in canon if syntax.search(source[sid]['source']) or '\n' in source[sid]['source']},
 'mixed-script-target':{sid for sid in canon if re.search(r'[А-Яа-яЁё]',final[sid])},
}
reg=set().union(*regsets.values());components['mandatory-regressions']=reg
# Artifacts and lists in canonical source order.
changed_rows=[{'sourceIndex':reviewed[sid]['sourceIndex'],'stableId':sid,'collection':reviewed[sid]['collection'],'source':source[sid]['source'],'previousTarget':reviewed[sid]['target'],'finalTarget':final[sid],'origin':changed[sid]['origin'],'findingId':changed[sid]['findingId'],'authoredPath':artifact[sid]} for sid in canon if sid in changed]
jsonl(E/'changed-ids-v2.jsonl',changed_rows)
component_info={}
for name,ids in components.items():
 path=E/('component-'+name+'-v2.json');ordered=[sid for sid in canon if sid in ids];dump(path,{'schemaVersion':1,'cycle':'sw-semantic-correction-01','component':name,'count':len(ordered),'stableIds':ordered});component_info[name]={'path':str(path.relative_to(R)),'sha256':sha(path),'count':len(ordered)}
concept_info={}
for name,ids in concept.items():
 path=E/('concept-'+name+'-v2.json');ordered=[sid for sid in canon if sid in ids];dump(path,{'schemaVersion':1,'concept':name,'selectorRegex':patterns[name],'count':len(ordered),'stableIds':ordered});concept_info[name]={'path':str(path.relative_to(R)),'sha256':sha(path),'count':len(ordered)}
reg_info={}
for name,ids in regsets.items():
 path=E/('regression-'+name+'-v2.json');ordered=[sid for sid in canon if sid in ids];dump(path,{'schemaVersion':1,'regressionSurface':name,'count':len(ordered),'stableIds':ordered});reg_info[name]={'path':str(path.relative_to(R)),'sha256':sha(path),'count':len(ordered)}
catalog={'schemaVersion':1,'locale':'sw','gameVersion':'1.3.19','sourceAuditProgressSha256':p['baselineProgressSha256'],'categories':reg_info,'structuralFullCorpusGate':['JSON parse and 16538 exact accepted IDs','all source numeric values, markup, placeholders, newline, trailing whitespace','all Yarn speaker/service prefixes','all derived authored phrase-map expansions','all static TMP bindings and credits-role map'], 'notApplicable':['RTL/bidi shaping for Swahili Latin script','translated textures/images excluded by owner'], 'runtimeSurface':'not-run-per-owner'}
cat=E/'mandatory-regression-catalog-v2.json';dump(cat,catalog)
closure=set().union(*components.values());closure_rows=[]
for sid in canon:
 if sid in closure:
  closure_rows.append({'sourceIndex':reviewed[sid]['sourceIndex'],'stableId':sid,'collection':reviewed[sid]['collection'],'key':reviewed[sid].get('key'),'nodeNames':source[sid].get('nodeNames',[]),'source':source[sid]['source'],'target':final[sid],'firstPassTarget':reviewed[sid]['target'],'authoredPath':artifact[sid],'components':[name for name,ids in components.items() if sid in ids]})
jsonl(E/'closure-ids-v2.jsonl',closure_rows)
# Nontranslatable binding/scene context is separately hashed, never counted as an accepted unit.
runtime={'schemaVersion':1,'cycle':'sw-semantic-correction-01','staticScopePath':'Documentation/static-text-scope-v2.json','staticScopeSha256':sha(R/'Documentation/static-text-scope-v2.json'),'changedStaticConsumers':[{'stableId':sid,'source':scope_by[sid]['source'],'sceneAncestry':scope_by[sid]['sceneAncestry'],'localizedStringBindings':scope_by[sid]['localizedStringBindings']} for sid in changed_static],'dynamicRuntimeBindings':'sourceStableId null cannot be confirmed without running the game; owner forbids launch','countAsTranslationUnits':0}
runpath=E/'runtime-context-v2.json';dump(runpath,runtime)
manuals=['/Users/antonkrutov/.codex/instructions/sitefor-mods.md','/Users/antonkrutov/.codex/instructions/game-localization-prompt.md','/Users/antonkrutov/.codex/instructions/game-localization-audit-workflow.md','/Users/antonkrutov/.codex/skills/vn-game-localize/SKILL.md','/Users/antonkrutov/.codex/skills/vn-game-localize/references/CHARACTERS.md']
manifest={'schemaVersion':1,'cycle':'sw-semantic-correction-01','createdAtUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'locale':'sw','gameVersion':'1.3.19','acceptedUnits':16538,'changedIds':{'path':'Translations/sw/semantic-correction-cycle-01/changed-ids-v2.jsonl','sha256':sha(E/'changed-ids-v2.jsonl'),'count':len(changed_rows),'newline':'LF; one compact UTF-8 JSON object per line; final LF'},'closureIds':{'path':'Translations/sw/semantic-correction-cycle-01/closure-ids-v2.jsonl','sha256':sha(E/'closure-ids-v2.jsonl'),'count':len(closure_rows),'newline':'LF; one compact UTF-8 JSON object per line; final LF'},'components':component_info,'glossaryConceptSelectors':concept_info,'mandatoryRegressionCatalog':{'path':str(cat.relative_to(R)),'sha256':sha(cat),'count':len(reg)},'runtimeContext':{'path':str(runpath.relative_to(R)),'sha256':sha(runpath),'countAsTranslationUnits':0},'sourceAndGlossaryPins':p['sourceAndGlossaryPins'],'manuals':[{'path':x,'sha256':sha(Path(x))} for x in manuals],'derivedArtifactManifest':{'path':p['finalPayloadManifestPath'],'sha256':p['finalPayloadManifestSha256']},'validatedCorpus':{'path':str(vpath.relative_to(R)),'sha256':sha(vpath),'units':16538,'artifacts':187},'imagePlan':{'translatedImagesExcluded':True,'scopePath':'Documentation/embedded-text-assets-scope-v2.json','scopeSha256':sha(R/'Documentation/embedded-text-assets-scope-v2.json')},'firstSemanticPass':'complete; 16538/16538 reviewed, 211 findings','independentReview':'not-started','editorialAcceptance':'pending','runtime':'not-run-per-owner'}
m=E/'dependency-closure-v2.json';dump(m,manifest)
print(json.dumps({'changed':len(changed_rows),'closure':len(closure_rows),'componentCounts':{k:len(v) for k,v in components.items()},'manifestSha256':sha(m)},ensure_ascii=False))
