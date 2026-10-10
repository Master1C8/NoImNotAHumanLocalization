import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
rows=[json.loads(x) for x in (ROOT/'Translations/el/correction-cycle-002-delta-review.jsonl').read_text().splitlines()]
compiled=json.loads((ROOT/'Translations/el/independent-review-01/compiled-context.json').read_text())
occ={}
for name,node in compiled['nodes'].items():
 for r in node['instructions']:
  if r['args'] and isinstance(r['args'][0],str) and r['args'][0].startswith('line:'):occ.setdefault(r['args'][0],[]).append((name,r['pc'],r['opcode']))
for i in range(*map(int,sys.argv[1:3])):
 r=rows[i]; print(i,r['stableId'].split(':')[-1],r['key'],occ.get(r['key'],[]),'CHANGED' if 'changed' in r['components'] else '')
 print('RU',r['source']); print('EL',r['currentTarget'])
