import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
rows=[json.loads(x) for x in (ROOT/'Translations/el/correction-cycle-001-closure-review.jsonl').read_text().splitlines()]
source={r['stableId']:r for x in (ROOT/'Source/localization-inventory-v3/strings.jsonl').read_text().splitlines() if (r:=json.loads(x))}
start,end=map(int,sys.argv[1:3])
for i in range(start,end):
 r=rows[i]; s=source.get(r['stableId'],{});print(i,'@'+str(r['ordinal']),r['key'],','.join(s.get('nodeNames',[])),sep=' | ')
 print('RU '+r['source']);print('EL '+r['currentTarget'])
 if 'changed' in r['components']:print('BEFORE '+r['firstPassTarget'])
