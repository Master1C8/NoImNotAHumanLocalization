"""Record already-read row ranges only. The human/model reviewer supplies ranges."""
import context_batch_v3 as c
import hashlib,json,sys
from pathlib import Path
name=sys.argv[1]
indices=set()
for token in sys.argv[2:]:
    a,b=map(int,token.split(':')); indices.update(range(a,b))
findings={}
for path in c.EVIDENCE.glob('findings-*.json'):
    for f in json.loads(path.read_text()).get('findings',[]):
        if f.get('closureIndexZeroBased') is not None:
            findings.setdefault(f['closureIndexZeroBased'],[]).append(f['findingId'])
with (c.EVIDENCE/name).open('x') as out:
    for i in sorted(indices):
        r=c.closure[i]
        record={'closureIndexZeroBased':i,'stableId':r['stableId'],'sourceIndex':r['sourceIndex'],
                'sourceSha256':hashlib.sha256(r['source'].encode()).hexdigest(),
                'targetSha256':hashlib.sha256(r['target'].encode()).hexdigest(),
                'consumerContext':'full ordered node source-target/context/control read; source-table repetitions read explicitly',
                'decision':('proposal recorded: '+', '.join(findings[i])) if i in findings else 'retain; no objective issue found in compared source-target and context',
                'consumerReachability':'not claimed'}
        out.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
print(json.dumps({'path':str(c.EVIDENCE/name),'recordedRows':len(indices),'sha256':hashlib.sha256((c.EVIDENCE/name).read_bytes()).hexdigest()}))
