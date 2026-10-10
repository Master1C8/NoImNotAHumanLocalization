import json,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HI=ROOT/'Translations/hi'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
closure=load(HI/'semantic-cycle-001-closure.json')
gate=load(HI/'semantic-cycle-001-structural-gate.json')
sources=[json.loads(l) for p in ['Source/localization-inventory-v3/strings.jsonl','Source/localization-inventory-v3/static-text.jsonl'] for l in (ROOT/p).read_text().splitlines()]
targets={};files={}
for f in gate['files']:
 p=ROOT/f['path'];d=load(p)
 for row in d['entries']:
  if 'stableId' in row:sid=row['stableId']
  else:
   found=[s['stableId'] for s in sources if s.get('collection')==d['collection'] and s['stableId'].rsplit(':',1)[-1]==str(row['id'])]
   assert len(found)==1;sid=found[0]
  targets[sid]=row['target'];files[sid]=str(p.relative_to(ROOT))
source={s['stableId']:s for s in sources}
rows=[dict(r,source=source[r['stableId']]['source'],target=targets[r['stableId']],file=files[r['stableId']],key=source[r['stableId']].get('key'),nodes=source[r['stableId']].get('nodeNames',[])) for r in closure['reviewRows']]
if sys.argv[1]=='prepare':
 p=Path(__file__).parent/'paired-closure.jsonl';assert not p.exists();p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
 pins={f['path']:sha(ROOT/f['path']) for f in gate['files']}
 pins.update({str(p.relative_to(ROOT)):sha(p) for p in [HI/'semantic-cycle-001-closure.json',HI/'semantic-cycle-001-adjudication.json',HI/'semantic-cycle-001-application-plan.json',HI/'semantic-pass-001-progress-immutable.json',ROOT/'Source/localization-inventory-v3/strings.jsonl',ROOT/'Source/localization-inventory-v3/static-text.jsonl',ROOT/'Documentation/glossary-translations/hi/layer.json',ROOT/'Source/glossary-corpus-v2/runtime-bindings.json']})
 (Path(__file__).parent/'start-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
 print(len(rows),sum(len(r['source'])+len(r['target']) for r in rows),'characters')
else:
 a,b=map(int,sys.argv[1:3])
 for i,r in enumerate(rows[a:b],a):
  print(f"{i} [{r['reviewIndex']}] {r['key'] or r['stableId']} {'*' if 'changed' in r['components'] else ''}")
  print('RU',r['source'].replace('\n','\\n'));print('HI',r['target'].replace('\n','\\n'))
