"""Read-only IL consumer evidence from pinned source assemblies."""
import json,hashlib
from pathlib import Path
import dnfile
from dncil.cil.body import CilMethodBody
from dncil.cil.body.reader import CilMethodBodyReaderBytes
OUT=Path(__file__).resolve().parent
BASE=Path('/Volumes/KINGSTONMAC/Applications/No Im not a Human.app/Contents/SharedSupport/prefix/drive_c/KS Games/No Im not a Human/NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed')
SCOPE={'Assembly-CSharp.dll':{'DialogCommandsInstance':{'GetCharacterOnPlace','GetCharacterName'},'ConsumableCloseUpView':{'SetupConsumable'},'FridgeItemView':{'InitGotTexts'},'LocalizationExtension':{'GetLocalization'}},'YarnSpinner.Unity.dll':{'<>c__DisplayClass101_0':{'<HandleLine>g__HandleLineInternal|1'},'<>c__DisplayClass98_0':{'<HandleOptions>g__HandleOptionsInternal|1'},'DialogueRunner':{'HandleLine','HandleOptions','SelectedOption'},'OptionsListView':{'RunOptions'},'<RunLineInternal>d__28':{'MoveNext'},'<<RunLineInternal>g__PresentLine|0>d':{'MoveNext'},'UnityLocalisedLineProvider':{'GetLocalizedLine'},'LineView':{'RunLineInternal','AddLineBreaks'},'OptionView':{'set_Option'},'LocalizedLine':{'get_TextWithoutCharacterName'}}}
PINS={'Assembly-CSharp.dll':'c674f171c61b644e6e746e0ced079ffa365abee2336d04ea9e67cbbc93e88213','YarnSpinner.Unity.dll':'727e3827d0f71c0e54d5669c22ec4b0ee5936508113a13eddc15ebb3912841b5'}
result={}
for filename,types in SCOPE.items():
 p=BASE/filename;sha=hashlib.sha256(p.read_bytes()).hexdigest();assert sha==PINS[filename]
 pe=dnfile.dnPE(str(p));tables=pe.net.mdtables
 def resolve(x):
  value=getattr(x,'value',None)
  if value is None:return str(x)
  tid,index=value>>24,value&0xffffff
  if tid==0x70:
   data,_=pe.net.user_strings.get_with_size(index);return data.decode('utf-16le')
  table={0x0a:'MemberRef',0x06:'MethodDef',0x04:'Field',0x01:'TypeRef',0x02:'TypeDef',0x2b:'MethodSpec'}.get(tid)
  if not table:return str(value)
  row=getattr(tables,table).rows[index-1]
  for attr in ['Name','TypeName']:
   if hasattr(row,attr):return str(getattr(row,attr))
  return str(value)
 methods={}
 for t in tables.TypeDef.rows:
  name=str(t.TypeName)
  if name not in types:continue
  for x in t.MethodList:
   m=x.row;mn=str(m.Name)
   if mn not in types[name] or not m.Rva:continue
   b=CilMethodBody(CilMethodBodyReaderBytes(pe.get_data(m.Rva,60000)))
   methods[name+'.'+mn]=[{'offset':i.offset,'op':i.opcode.name,'operand':resolve(i.operand) if i.operand is not None else None} for i in b.instructions]
 result[filename]={'sha256':sha,'methods':methods}
(OUT/'managed-context.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
for f,d in result.items():
 for method,ins in d['methods'].items():
  if 'HandleLineInternal' not in method and 'HandleOptionsInternal' not in method:continue
  print(f,method)
  for i in ins:
   if i['op'] in ['ldstr','call','callvirt','ldfld','stfld','newobj']:print(i['offset'],i['op'],i['operand'])
