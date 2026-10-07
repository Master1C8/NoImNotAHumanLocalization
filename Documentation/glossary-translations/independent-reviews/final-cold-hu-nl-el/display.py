import json,pathlib,sys
b=pathlib.Path(__file__).parent
s=json.loads((b/'ru.json').read_text())['entries'];t=json.loads((b/(sys.argv[1]+'.json')).read_text())
ps=json.loads((b/'display-policies.json').read_text()) if (b/'display-policies.json').exists() else {}
def compact(v,l):
 for j,policy in enumerate(ps.get(l,[]),1): v=v.replace(policy,f'[EXACT PREVIOUSLY FULLY READ {l} POLICY {j}]')
 return v
lo,hi=int(sys.argv[2]),int(sys.argv[3]);targetonly=len(sys.argv)>4
for i,e in enumerate(s[lo-1:hi],lo):
 print(f"{i} {e['id']}")
 if not targetonly: print('RU TERM:',e['term'],'\nRU MEANING:',compact(e['meaning'],'ru'))
 print(sys.argv[1].upper()+' TERM:',t[e['id']]['term'],'\n'+sys.argv[1].upper()+' MEANING:',compact(t[e['id']]['meaning'],sys.argv[1]),'\n')
