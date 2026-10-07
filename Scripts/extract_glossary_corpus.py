#!/usr/bin/env python3
"""Read-only Russian glossary research corpus. Serialized rows are not runtime coverage."""
import argparse,hashlib,json,re,copy
from collections import Counter
from pathlib import Path
import UnityPy
from probe_assets import DEFAULT_GAME,ROOT,digest,require,EXPECTED_BUILD_GUID,EXPECTED_UNITY

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'Source/glossary-corpus-v2');args=parser.parse_args()
 out=args.output.resolve();require(out.is_relative_to(ROOT/'Source'),'Output must be inside canonical Source directory')
 require(not out.exists(),'Existing extraction must not be overwritten')
 state=json.loads((ROOT/'Documentation/localization-state.json').read_text())
 aa=DEFAULT_GAME/'NoImNotAHuman_Data/StreamingAssets/aa/StandaloneWindows64'
 paths=[aa/'localization-string-tables-russian(ru)_assets_all.bundle',aa/'localization-assets-shared_assets_all.bundle']
 pins={str(p.relative_to(DEFAULT_GAME)):digest(p) for p in paths}
 for key,value in pins.items():require(value==state['sourceInputs'][key],f'Source hash changed: {key}')
 require(f'build-guid={EXPECTED_BUILD_GUID}' in (DEFAULT_GAME/'NoImNotAHuman_Data/boot.config').read_text().splitlines(),'Build changed')
 shared={}
 for o in UnityPy.load(str(paths[1])).objects:
  if o.type.name!='MonoBehaviour':continue
  t=o.read_typetree()
  if 'm_TableCollectionName' not in t:continue
  require(o.path_id not in shared,'Duplicate shared object ID')
  ids=[x['m_Id'] for x in t['m_Entries']];require(len(ids)==len(set(ids)),'Duplicate shared key ID')
  shared[o.path_id]=t
 records=[];reports=[]
 for o in UnityPy.load(str(paths[0])).objects:
  if o.type.name!='MonoBehaviour':continue
  t=o.read_typetree()
  if 'm_TableData' not in t:continue
  require(str(o.assets_file.unity_version)==EXPECTED_UNITY,'Unity version changed')
  require(t['m_LocaleId']['m_Code']=='ru','Non-Russian source table')
  s=shared[t['m_SharedData']['m_PathID']];keys={x['m_Id']:x for x in s['m_Entries']}
  ids=[x['m_Id'] for x in t['m_TableData']];require(len(ids)==len(set(ids)),'Duplicate string ID')
  name=s['m_TableCollectionName'];sc=Counter();unknown=0
  refs={x['rid']:x for x in s['references']['RefIds']}
  for row in t['m_TableData']:
   binding=keys.get(row['m_Id']);text=row['m_Localized'];m=re.match(r'^([A-Za-z][A-Za-z0-9_]*):\s',text)
   speaker=m.group(1) if m else None
   if speaker:sc[speaker]+=1
   if binding is None:unknown+=1
   records.append({'collection':name,'guid':s['m_TableCollectionNameGuidString'],'tablePathId':o.path_id,'id':row['m_Id'],'key':binding['m_Key'] if binding else None,'text':text,'speaker':speaker,'metadata':binding['m_Metadata'] if binding else None,'yarnMetadata':[refs[z['rid']]['data'] for z in binding['m_Metadata']['m_Items'] if z['rid'] in refs and refs[z['rid']]['type']['class']=='LineMetadata'] if binding else []})
  reports.append({'collection':name,'rows':len(ids),'unmatchedStringIds':unknown,'sharedKeysWithoutRussian':len(set(keys)-set(ids)),'speakers':dict(sc.most_common())})
 from unity_types import CheckedTypeTreeGenerator,generated_tree
 generator=CheckedTypeTreeGenerator(EXPECTED_UNITY);managed=DEFAULT_GAME/'NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed';generator.load_local_dll_folder(str(managed))
 bindings={}
 for filename,selected in [('level1',[4471,4667]),('sharedassets0.assets',[2743])]:
  source=DEFAULT_GAME/'NoImNotAHuman_Data'/filename;key=str(source.relative_to(DEFAULT_GAME));pins[key]=digest(source)
  if key in state['sourceInputs']:require(pins[key]==state['sourceInputs'][key],'Changed source asset: '+key)
  env=UnityPy.load(str(source));env.typetree_generator=generator
  for pid in selected:
   tree,_=generated_tree(env.file.objects[pid]);bindings[filename+':'+str(pid)]=tree
 for name in ['Assembly-CSharp.dll','YarnSpinner.Unity.dll']:
  source=managed/name;pins[str(source.relative_to(DEFAULT_GAME))]=digest(source)
 require(bindings['level1:4471']['yarnProject']['m_PathID']==2743,'Runner project changed')
 require(bindings['level1:4471']['lineProvider']['m_PathID']==4667,'Runner provider changed')
 require(bindings['level1:4667']['stringsTable']['m_TableReference']['m_TableCollectionName']=='GUID:444ff14f1967f5a4c8eb9e4cf4c913f1','Current collection changed')
 program=bytes(bindings['sharedassets0.assets:2743']['compiledYarnProgram']);compiled_ids={x.decode() for x in re.findall(rb'line:[A-Za-z0-9_]+',program)}
 current=[x for x in records if x['collection']=='Dialogs'];keys={x['key'] for x in current}
 scope={'compiledProgramSha256':hashlib.sha256(program).hexdigest(),'compiledLineIds':len(compiled_ids),'tableKeys':len(keys),'keysNotFoundInCompiledBytes':sorted(keys-compiled_ids),'compiledIdsWithoutRussian':sorted(compiled_ids-keys),'limit':'Compiled ASCII ID presence is not scene reachability proof. Supplemental current-table strings remain in research scope.'}
 require(not scope['compiledIdsWithoutRussian'],'Unbound compiled line IDs')
 out.mkdir(parents=True)
 (out/'runtime-bindings.json').write_text(json.dumps(bindings,ensure_ascii=False,indent=2)+'\n')
 (out/'current-dialogs.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in current))
 (out/'current-dialogs-scope.json').write_text(json.dumps(scope,ensure_ascii=False,indent=2)+'\n')
 corpus=out/'strings.jsonl';corpus.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records))
 (out/'shared-metadata.json').write_text(json.dumps(shared,ensure_ascii=False,indent=2)+'\n')
 report={'schemaVersion':1,'scope':'Russian serialized glossary research corpus; legacy/demo/test retained separately; active runtime closure not claimed','sourceLocale':'ru','buildGuid':EXPECTED_BUILD_GUID,'unityVersion':EXPECTED_UNITY,'sourcePins':pins,'extractorSha256':digest(Path(__file__)),'corpusSha256':digest(corpus),'records':len(records),'collections':reports,'currentScope':scope,'runtimeBindingsSha256':digest(out/'runtime-bindings.json')}
 (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
