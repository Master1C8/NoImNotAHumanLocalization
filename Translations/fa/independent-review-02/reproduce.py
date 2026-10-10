import importlib.util,json,hashlib,pathlib,contextlib,io
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;C=R/'Translations/fa/audit-cycle-002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
s=importlib.util.spec_from_file_location('closure',C/'build-closure.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def check_only(p,data):assert p.exists() and p.read_bytes()==data,str(p)
m.immutable=check_only
buf=io.StringIO()
with contextlib.redirect_stdout(buf):m.main()
s=importlib.util.spec_from_file_location('topology',C/'verify-photo-topology.py');t=importlib.util.module_from_spec(s);s.loader.exec_module(t)
with contextlib.redirect_stdout(buf):t.main()
cl=json.loads((C/'closure.json').read_text());delta=json.loads((C/'next-review-delta.json').read_text());prior=json.loads((R/'Translations/fa/independent-review-01/review-verdict.json').read_text())
rows=delta['rows'];assert len(rows)==1408
regids=set((C/'mandatoryRegression-ids.txt').read_text().splitlines());current={r['stableId']:r for r in cl['reviewRows']};old={r['stableId']:r for r in json.loads((R/'Translations/fa/independent-review-01/per-id-review.json').read_text())['reviewRows']}
reg_changed=[sid for sid in regids if current[sid]['source']!=old[sid]['source'] or current[sid]['target']!=old[sid]['target']]
pins={str(p.relative_to(R)):sha(p) for p in C.iterdir() if p.is_file()};pins.update({p:h for p,h in json.loads((C/'deterministic-gate.json').read_text())['authoredFileHashes'].items()});pins['Documentation/glossary-translations/fa/layer.json']=sha(R/'Documentation/glossary-translations/fa/layer.json')
result={'closureReproduction':json.loads(buf.getvalue().splitlines()[0]),'topologyReproduction':json.loads(buf.getvalue().splitlines()[1]),'mandatoryCount':len(regids),'mandatoryChangedIds':reg_changed,'pins':pins,'priorEvidenceVerifiedByBuilder':True,'writeMode':'read-only existing cycle evidence; outputs here only'}
(O/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(O/'full-read-inputs.jsonl').write_text(''.join(json.dumps({**r,'nodeNames':current[r['stableId']]['nodeNames'],'index':i+1},ensure_ascii=False)+'\n' for i,r in enumerate(rows)))
print({k:v for k,v in result.items() if k!='pins'})
