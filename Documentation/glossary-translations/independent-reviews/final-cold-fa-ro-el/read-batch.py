import pathlib,json,sys
p=pathlib.Path(__file__).parent
s=json.loads((p/'source.snapshot.json').read_text())['entries'];markers=json.loads((p/'policy-markers.json').read_text())
l,mode,start,end=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]);t=json.loads((p/f'{l}.snapshot.json').read_text())
def render(text,locale):
 for k,v in markers[locale].items():text=text.replace(v,k)
 return text
for n,e in enumerate(s[start-1:end],start):
 print(f'{n} {e["id"]}')
 if mode=='paired': print('RU:',e['term'],'|',render(e['meaning'],'source'))
 print(l.upper()+':',t[e['id']]['term'],'|',render(t[e['id']]['meaning'],l))
