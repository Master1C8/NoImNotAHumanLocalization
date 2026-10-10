"""Pin actual compiled consumer topology and serialized place domains; never launch."""
import sys, json, hashlib, struct, ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Scripts'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads((ROOT/p).read_text())
def write(name,v):
    p=OUT/name;data=json.dumps(v,ensure_ascii=False,indent=2)+'\n'
    if p.exists():assert p.read_text()==data
    else:p.write_text(data)
binding=load('Source/glossary-corpus-v2/runtime-bindings.json')
raw=bytes(binding['sharedassets0.assets:2743']['compiledYarnProgram'])
# Reuse only the prior read-only decoder function, not its top-level writer.
tree=ast.parse((ROOT/'Translations/nl/independent-review-02/prepare-context.py').read_text())
fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='decode')
exec(compile(ast.Module(body=[fn],type_ignores=[]),'<pinned decoder>','exec'))
nodes={}
for f,w,e in decode(raw):
    if f!=2:continue
    d=decode(e);name=next(v.decode() for f,w,v in d if f==1);nb=next(v for f,w,v in d if f==2);instructions=[]
    for f,w,v in decode(nb):
        if f!=2:continue
        ins=[]
        for x,y,z in decode(v):
            if y==2:z=[(a,c.decode(errors='replace') if d==2 else c) for a,d,c in decode(z)]
            ins.append((x,z))
        instructions.append(ins)
    nodes[name]=instructions
delta=[json.loads(l) for l in (ROOT/'Translations/nl/semantic-cycle-3/closure-v2/delta-review-rows.jsonl').read_text().splitlines()]
allrows=[json.loads(l) for l in (ROOT/'Translations/nl/semantic-review-rows-pass1.jsonl').read_text().splitlines()]
current={r['key']:r for r in allrows}
for l in (ROOT/'Translations/nl/semantic-cycle-3/closure-v2/closure-review-rows.jsonl').read_text().splitlines():
    r=json.loads(l);current[r['key']]=r
prior=load('Translations/nl/independent-review-02/consumer-context.json')
scenes={}
for name in sorted({n for r in delta for n in r['nodeNames']}):
    assert json.loads(json.dumps(nodes[name]))==prior['scenes'][name]['instructions']
    ordered=[]
    for index,ins in enumerate(nodes[name]):
        for f,z in ins:
            if f==2:
                for k,s in z:
                    if k==1 and isinstance(s,str) and s.startswith('line:') and s in current:
                        ordered.append({'instructionIndex':index,**{k:current[s][k] for k in ['stableId','key','source','target','sourceSha256','targetSha256']}})
    scenes[name]={'instructions':nodes[name],'lineAndChoiceRowsInCompiledOrder':ordered}
write('compiled-context.json',{'bindingSha256':sha(ROOT/'Source/glossary-corpus-v2/runtime-bindings.json'),'compiledProgramSha256':hashlib.sha256(raw).hexdigest(),'scenes':scenes,'unboundDeltaIds':[r['stableId'] for r in delta if not r['nodeNames']]})
import UnityPy
from unity_types import CheckedTypeTreeGenerator
from UnityPy.helpers.TypeTreeNode import TypeTreeNode
from UnityPy.helpers import TypeTreeHelper
from UnityPy.streams import EndianBinaryReader
from probe_assets import DEFAULT_GAME
base=DEFAULT_GAME
report=load('Source/glossary-corpus-v2/report.json')
pins={}
for suffix in ['NoImNotAHuman_Data/sharedassets0.assets','NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed/Assembly-CSharp.dll']:
    p=base/suffix;assert sha(p)==report['sourcePins'][suffix];pins[str(p)]=sha(p)
g=CheckedTypeTreeGenerator('6000.3.10f1');g.load_local_dll_folder(str(base/'NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed'))
env=UnityPy.load(str(base/'NoImNotAHuman_Data/sharedassets0.assets'));env.typetree_generator=g
characters=[]
for obj in env.objects:
    if obj.type.name!='MonoBehaviour':continue
    node=obj.generate_monobehaviour_node()
    if node.m_Type!='CharacterSOData':continue
    rawobj=obj.get_raw_data();nodeslist=node.to_dict_list();cut=next(i for i,n in enumerate(nodeslist) if n['m_Name']=='_place')
    # Prefix includes every field through _place. The stripped managed-reference
    # registry in the suffix cannot be decoded, and is outside this contract.
    selected=nodeslist[:cut+1]
    for n in selected:
        n.pop('m_Children',None)
        if n['m_Name']=='m_Enabled' and n['m_Level']==1:n['m_MetaFlag']|=0x4000
    schema=TypeTreeNode.from_list(selected)
    t=TypeTreeHelper.read_typetree(schema,EndianBinaryReader(rawobj,endian=obj.reader.endian),check_read=False,assetsfile=obj.assets_file)
    head=obj.parse_monobehaviour_head();assert t['m_Name']==head.m_Name and t['m_Enabled']==head.m_Enabled
    assert t['m_Script']=={'m_FileID':head.m_Script.m_FileID,'m_PathID':head.m_Script.m_PathID}
    assert obj.get_raw_data()==rawobj
    characters.append({'pathId':obj.path_id,'name':t['m_Name'],'characterType':t['_characterType'],'room':t['_room'],'place':t['_place'],'rawSha256':hashlib.sha256(rawobj).hexdigest()})
cpp=ROOT/load('Translations/nl/independent-review-01/consumer-context.json')['getterCpp']['path'];cpptext=cpp.read_text()
method='IL2CPP_EXTERN_C IL2CPP_METHOD_ATTR int32_t CharactersManager_GetPlace_m1DAEB17CABD5E96FBA3796655CBE3CA8510FD5D4'
start=cpptext.index(method);end=cpptext.index('IL2CPP_EXTERN_C',start+1);getplace=cpptext[start:end]
labels={r['key']:r for r in current.values() if r['collection']=='UI' and (r['key'] or '').startswith('characterName_')}
# Name spelling comes from the compiled getter argument; enum/localization spelling
# is reconciled below to the UI key, not inferred from a display description.
aliases={'WolfHound':'Wolfhound','Doc':'Doctor','FairyTaller':'Fairytaller','Fan':'Fanatic'}
domains=[]
for r in delta:
    if '{0}' not in r['source']:continue
    args=[]
    for name in r['nodeNames']:
        ins=scenes[name]['instructions']
        for i,entry in enumerate(ins):
            if any(f==2 and any(k==1 and s=='GetCharacterOnPlace' for k,s in z) for f,z in entry):
                previous=ins[i-2];args.extend(s for f,z in previous if f==2 for k,s in z if k==1)
    entry={'stableId':r['stableId'],'getterArguments':args,'status':'unbound accepted inventory text' if not args else 'static place-compatible candidates; live state and scene arrival not proven'}
    if args:
        matches=[c for c in characters if aliases.get(c['name'],c['name']).lower()==aliases.get(args[0],args[0]).lower()]
        assert len(matches)==1,(args,matches)
        place=matches[0]['place'];possible=[c for c in characters if c['place']==place]
        entry['place']=place;entry['candidateCharacters']=possible
    domains.append(entry)
write('consumer-domains.json',{'sourcePins':pins,'cppPath':str(cpp.relative_to(ROOT)),'cppSha256':sha(cpp),'getPlaceExcerpt':getplace,'characters':characters,'domains':domains,'limits':['A complete generated tree read failed at the stripped managed-reference registry; schema prefix through _place was read with exact header checks and no source serialization.','Static compatible occupants establish domain exclusions and admissible descriptor classes, not complete live arrival conditions or reachability.','Arbitrary Blind/Ballerina/Sirin substitution examples are grammatical synthetic examples when their places differ.']})
import report_locale_readiness as readiness
readiness.LOCALES=('nl',)
write('full-exact-readiness.json',readiness.snapshot(exact=True))
print('Compiled scenes',len(scenes),'domains',len(domains),'character definitions',len(characters))
for d in domains:
    print(d['stableId'].rsplit(':',1)[-1],d['getterArguments'],d.get('place'),[c['name'] for c in d.get('candidateCharacters',[])])
