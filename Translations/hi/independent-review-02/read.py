import json,sys
from pathlib import Path
D=Path(__file__).parent
rows=[json.loads(x) for x in (D/'delta-pairs.jsonl').read_text().splitlines()]
source={r['stableId']:r for f in ['Source/localization-inventory-v3/strings.jsonl','Source/localization-inventory-v3/static-text.jsonl'] for r in [json.loads(x) for x in Path(f).read_text().splitlines()]}
a,b=map(int,sys.argv[1:3])
for i,r in enumerate(rows[a:b],a):
 s=source[r['stableId']]
 print(f"{i} [{r['reviewIndex']}] {s.get('key') or r['stableId']}")
 print('RU '+r['source'].replace('\n','<NL>'));print('HI '+r['target'].replace('\n','<NL>'))
