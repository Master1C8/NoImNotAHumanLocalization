from pathlib import Path
import json,hashlib,struct
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).parent
binding=ROOT/'Source/glossary-corpus-v2/runtime-bindings.json'
report=json.loads((ROOT/'Source/glossary-corpus-v2/report.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(binding)==report['runtimeBindingsSha256']
b=bytes(json.loads(binding.read_text())['sharedassets0.assets:2743']['compiledYarnProgram'])
assert hashlib.sha256(b).hexdigest()==report['currentScope']['compiledProgramSha256']
def decode(b):
 p=0; out=[]
 def var():
  nonlocal p
  n=s=0
  while True:
   q=b[p];p+=1;n|=(q&127)<<s;s+=7
   if q<128:return n
 while p<len(b):
  t=var();f,w=t>>3,t&7
  if w==0:v=var()
  elif w==2:l=var();v=b[p:p+l];p+=l
  elif w==5:v=struct.unpack('<f',b[p:p+4])[0];p+=4
  elif w==1:v=b[p:p+8];p+=8
  else:raise ValueError((p,w))
  out.append((f,w,v))
 return out
nodes={}
for f,w,e in decode(b):
 if f!=2:continue
 d=decode(e);name=next(v.decode() for f,w,v in d if f==1);nb=next(v for f,w,v in d if f==2)
 instructions=[]
 for f,w,v in decode(nb):
  if f!=2:continue
  ins=[]
  for x,y,z in decode(v):
   if y==2:z=[(a,c.decode(errors='replace') if d==2 else c) for a,d,c in decode(z)]
   ins.append((x,z))
  instructions.append(ins)
 nodes[name]=instructions
rows=[json.loads(l) for l in (ROOT/'Translations/nl/semantic-cycle-1/closure-v2/closure-review-rows.jsonl').read_text().splitlines()]
allrows=[json.loads(l) for l in (ROOT/'Translations/nl/semantic-review-rows-pass1.jsonl').read_text().splitlines()]
current={r['key']:r for r in allrows}
for r in rows:current[r['key']]=r
selected=['Doctor_Entrance_Occupied','Mother_Entrance_Occupied','NotTrue_Entrance_Occupied','Courier_Entrance_2_1_X','BigLebowski_Entrance_Occupied','SuperFake_Entrance_13_4','SuperFake_Entrance_13_3','MushroomEater_Entrance_3_5','Marauder_Eyes_DontShoot','Leper_Teeth_Gun','Leper_Ears_DontShoot','tv_8_necessary','Firefighter_Ears_DontShoot','Twins_Entrance_SirinOccupied','Hunter_Entrance_Occupied']
scene={}
for n in selected:
 ins=nodes[n];context=[]
 for i in ins:
  for f,v in i:
   if f==2:
    for k,s in v:
     if k==1 and isinstance(s,str) and s.startswith('line:') and s in current:
      r=current[s];context.append({k:r[k] for k in ['stableId','key','source','target','sourceSha256','targetSha256']})
 scene[n]={'instructions':ins,'lineAndChoiceRowsInCompiledOrder':context}
cpp=next((ROOT/'runtime').rglob('il2cppOutput/Assembly-CSharp__8.cpp'))
text=cpp.read_text();start=text.index('IL2CPP_EXTERN_C IL2CPP_METHOD_ATTR String_t* DialogCommandsInstance_GetCharacterOnPlace_m70AEE67C007EDA40E33E291E99893ABCAB7FCBF6 (String_t* ___0_characterRaw, const RuntimeMethod* method) \n{')
end=text.index('IL2CPP_EXTERN_C IL2CPP_METHOD_ATTR int32_t DialogCommandsInstance_GetEnergy',start)
cpp2=cpp.with_name('Assembly-CSharp__2.cpp');text2=cpp2.read_text();start2=text2.index('IL2CPP_EXTERN_C IL2CPP_METHOD_ATTR String_t* LocalizationExtension_GetLocalization_m34257247FBE67CB59C831E5E16FC1297021BC6A8 (String_t* ___0_key, String_t* ___1_table, ObjectU5BU5D_t8061030B0A12A55D5AD8652A20C922FE99450918* ___2_args, const RuntimeMethod* method) \n{');end2=text2.index('IL2CPP_EXTERN_C',start2+1)
occupied=[{**r,'inCurrentClosure':r['stableId'] in {r['stableId'] for r in rows},'reviewStatus':'enumerated dependency candidate; not additional credited semantic coverage'} for r in allrows if '{0}' in r['source'] and 'Occupied' in (r['key'] or '')]
obj={'bindingPath':str(binding.relative_to(ROOT)),'bindingSha256':sha(binding),'compiledProgramSha256':hashlib.sha256(b).hexdigest(),'scenes':scene,'getterCpp':{'path':str(cpp.relative_to(ROOT)),'sha256':sha(cpp),'excerpt':text[start:end]},'localizationCpp':{'path':str(cpp2.relative_to(ROOT)),'sha256':sha(cpp2),'excerpt':text2[start2:end2]},'literalIdentity':{'method':'SHA1 of UTF-16LE spelling matches IL2CPP string literal identifier','characterName_':hashlib.sha1('characterName_'.encode('utf-16le')).hexdigest(),'UI':hashlib.sha1('UI'.encode('utf-16le')).hexdigest()},'finding78Binding':'Exact key line:NotTrue_Entrance_Occupied_0abf2b1 is absent from pinned compiled program. Its dynamic consumer is unverified; do not assert live runtime reachability.','occupiedPlaceholderCandidates':occupied}
p=OUT/'consumer-context.json';assert not p.exists();p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
print('Saved 15 compiled scene contexts and 59 occupied placeholder dependency candidates.')
for name in ['MushroomEater_Entrance_3_5','Marauder_Eyes_DontShoot']:
 print(name)
 for ins in scene[name]['instructions']:print(ins)
