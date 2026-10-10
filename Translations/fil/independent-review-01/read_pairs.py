#!/usr/bin/env python3
"""Bounded independent review inputs; does not create review decisions."""
import hashlib,json,sys
from pathlib import Path
base=Path(__file__).resolve().parent
root=base.parents[2]
p=root/'Translations/fil/semantic-correction-cycle-001.paired.jsonl'
rows=[json.loads(x) for x in p.read_text().splitlines()]
a=int(sys.argv[1]);b=int(sys.argv[2]); selected=rows[a-1:b]
raw=''.join(json.dumps(dict(closureRow=i,**r),ensure_ascii=False,separators=(',',':'))+'\n' for i,r in enumerate(rows[a-1:b],a)).encode()
file=base/f'input-{a:04d}-{b:04d}.jsonl'
if file.exists(): assert file.read_bytes()==raw
else:file.write_bytes(raw)
print('INPUT',file.name,'rows',len(selected),'sha256',hashlib.sha256(raw).hexdigest())
for i,r in enumerate(selected,a):
 print(i,r['acceptedOrdinal'],','.join(r['nodeNames']) or r.get('key'))
 print(r['source']);print('→',r['target'])
