import json,sys,pathlib,collections
p=pathlib.Path(__file__).parent;s=json.loads((p/'source.snapshot.json').read_text())['entries'];l=sys.argv[1];t=json.loads((p/(l+'.snapshot.json')).read_text());mode=sys.argv[2];a,b=map(int,sys.argv[3:5])
def compact(m,locale):
 es=s if locale=='source' else list(json.loads((p/(locale+'.snapshot.json')).read_text()).values());c=collections.Counter(e['meaning'].split('. ')[-1] for e in es)
 for j,(tail,n) in enumerate(c.most_common(4),1):
  if n>2 and m.endswith(tail):return m[:-len(tail)]+f'[{locale}:suffix{j}]'
 return m
for i in range(a-1,min(b,len(s))):
 e=s[i];v=t[e['id']];print(f"{i+1} {e['id']}")
 if mode=='pair':print('RU '+e['term']+' | '+compact(e['meaning'],'source'))
 print(l.upper()+' '+v['term']+' | '+compact(v['meaning'],l));print()
