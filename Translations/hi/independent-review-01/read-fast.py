import json,sys,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[3];H=R/'Translations/hi';D=Path(__file__).parent
def j(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
c=j(H/'semantic-cycle-001-closure.json');gate=j(H/'semantic-cycle-001-structural-gate.json')
s=[json.loads(l) for p in ['Source/localization-inventory-v3/strings.jsonl','Source/localization-inventory-v3/static-text.jsonl'] for l in (R/p).read_text().splitlines()]
source={r['stableId']:r for r in s};by={(r.get('collection'),r['stableId'].rsplit(':',1)[-1]):r['stableId'] for r in s};t={};f={}
for x in gate['files']:
 d=j(R/x['path'])
 for r in d['entries']:
  sid=r.get('stableId') or by[d['collection'],str(r['id'])];t[sid]=r['target'];f[sid]=x['path']
rows=[dict(r,source=source[r['stableId']]['source'],target=t[r['stableId']],file=f[r['stableId']],key=source[r['stableId']].get('key'),nodes=source[r['stableId']].get('nodeNames',[])) for r in c['reviewRows']]
if sys.argv[1]=='prepare':
 for n,data in [('paired-closure-fast.jsonl',''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows)),('start-pins-fast.json',json.dumps({**{x['path']:sha(R/x['path']) for x in gate['files']},**{p:sha(R/p) for p in ['Translations/hi/semantic-cycle-001-closure.json','Translations/hi/semantic-cycle-001-adjudication.json','Translations/hi/semantic-cycle-001-application-plan.json','Translations/hi/semantic-pass-001-progress-immutable.json','Source/localization-inventory-v3/strings.jsonl','Source/localization-inventory-v3/static-text.jsonl','Documentation/glossary-translations/hi/layer.json','Source/glossary-corpus-v2/runtime-bindings.json']}},indent=2)+'\n')]:
  p=D/n;assert not p.exists();p.write_text(data)
 print(len(rows),sum(len(r['source'])+len(r['target']) for r in rows))
else:
 a,b=map(int,sys.argv[1:3])
 for i,r in enumerate(rows[a:b],a):print(f"{i} [{r['reviewIndex']}] {r['key'] or r['stableId']} {'*' if 'changed' in r['components'] else ''}\nRU {r['source'].replace(chr(10),'<NL>')}\nHI {r['target'].replace(chr(10),'<NL>')}")
