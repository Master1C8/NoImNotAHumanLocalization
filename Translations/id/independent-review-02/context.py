"""Save actual compiled context for every delta unit, without VM execution."""
import json, hashlib, importlib.util
from pathlib import Path
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
def load(p):return json.loads((R/p).read_text())
def rows(p):return list(map(json.loads,(R/p).read_text().splitlines()))
def sha(b):return hashlib.sha256(b).hexdigest()
spec=importlib.util.spec_from_file_location('ctx',R/'Translations/id/independent-review-01/compiled_context.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
nodes,programsha=m.load()
raw=bytes(load('Source/glossary-corpus-v2/runtime-bindings.json')['sharedassets0.assets:2743']['compiledYarnProgram'])
labels={}
for f,w,v in m.fields(raw):
    if f!=2:continue
    mapping={a:c for a,b,c in m.fields(v)};name=mapping[1].decode();labels[name]={}
    for a,b,c in m.fields(mapping[2]):
        if a==3:
            q={z:t for z,s,t in m.fields(c)};labels[name][q[1].decode()]=q.get(2,0)
assert labels==load('Translations/id/independent-review-01/compiled-labels.json')
source=rows('Source/localization-inventory-v3/strings.jsonl')
sourcebykey={x['key']:x for x in source if x.get('collection')=='Dialogs'}
targets={}
for p in (R/'Translations/id').glob('dialogue-batch-???.json'):
    for x in json.loads(p.read_text())['entries']:targets[str(x['id'])]=x['target']
delta=rows('Translations/id/semantic-correction-cycle-02/delta-review-rows.jsonl')
selected={n for r in delta for n in r['nodeNames']}
annotated={}
for name in nodes:
    if name not in selected:continue
    annotated[name]={'labels':labels[name],'instructions':[]}
    for i in nodes[name]:
        q=dict(i)
        if i['opcode'] in [2,4] and i['operands'][0] in sourcebykey:
            r=sourcebykey[i['operands'][0]]
            q.update(stableId=r['stableId'],source=r['source'],target=targets[r['stableId'].split(':')[-1]])
        annotated[name]['instructions'].append(q)
out=[];action=[]
for r in delta:
    occurrences=[]
    for name in r['nodeNames']:
        for i in nodes[name]:
            if i['opcode'] in [2,4] and i['operands'][0]==r['key']:
                q={'node':name,'instruction':i['index'],'opcode':i['opcode'],'operands':i['operands']}
                if i['opcode']==4:q['destinationInstruction']=labels[name][i['operands'][1]]
                occurrences.append(q)
    out.append({'stableId':r['stableId'],'sourceOrderIndex':r['sourceOrderIndex'],'occurrences':occurrences,'classification':'compiled line/option' if occurrences else 'UI binding' if r['collection']=='UI' else 'accepted historical table cell; no compiled occurrence'})
    if r['source']=='Выдать явку в КЧС':
        assert len(occurrences)==1
        q=occurrences[0];ins=nodes[q['node']];at=q['instruction'];dest=q['destinationInstruction']
        assert q['opcode']==4 and q['operands'][2:]==[0.0,True]
        guard=ins[at-6:at]
        assert [(i['opcode'],i['operands']) for i in guard]==[(6,['Povistka']),(7,[1.0]),(12,['GetItemCount']),(7,[0.0]),(7,[2.0]),(12,['Number.GreaterThan'])]
        branch=ins[dest:dest+8]
        assert [(i['opcode'],i['operands']) for i in branch[:2]]==[(6,['Povistka']),(7,[1.0])]
        assert branch[2]['opcode']==6 and branch[3]['operands']==[3.0] and branch[4]['operands']==['TryGiveItemFor']
        assert branch[6]['operands'][0] in ['FEMA_GivingPostcard','FEMA_GivingPostcard_Firefighter'] and branch[7]['opcode']==16, (r['sourceOrderIndex'],q['node'],branch)
        action.append({'sourceOrderIndex':r['sourceOrderIndex'],'stableId':r['stableId'],'node':q['node'],'optionAt':at,'destination':dest,'recipient':branch[2]['operands'][0],'guard':'GetItemCount(Povistka)>0','branch':'TryGiveItemFor(Povistka,1,recipient); if true RunNode '+branch[6]['operands'][0],'formatSlots':0})
for name,x in [('compiled-delta-nodes.json',{'programSha256':programsha,'nodes':annotated}),('compiled-correspondence.json',out),('reporting-action-consumers.json',action)]:
    p=O/name;assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
print('saved',len(annotated),'nodes;',len(out),'ID correspondences;',len(action),'action branch contracts')
print('uncompiled',[(r['sourceOrderIndex'],r['classification']) for r in out if not r['occurrences']])
for x in action:print(x['sourceOrderIndex'],x['node'],x['recipient'],x['optionAt'],x['destination'])
