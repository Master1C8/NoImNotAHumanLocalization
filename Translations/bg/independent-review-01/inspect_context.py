"""Read-only compiled Yarn wire inspection; writes only independent evidence."""
import json, struct, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent

def varint(data,pos):
    n=0;s=0
    while True:
        x=data[pos];pos+=1;n|=(x&127)<<s
        if not x&128:return n,pos
        s+=7

def fields(data):
    out=[];pos=0
    while pos<len(data):
        tag,pos=varint(data,pos);f,w=tag>>3,tag&7
        if w==0:v,pos=varint(data,pos)
        elif w==2:
            n,pos=varint(data,pos);v=data[pos:pos+n];pos+=n
        elif w==5:v=struct.unpack('<f',data[pos:pos+4])[0];pos+=4
        elif w==1:v=data[pos:pos+8].hex();pos+=8
        else:raise ValueError((f,w,pos))
        out.append((f,w,v))
    return out

def strings(data):
    try:return data.decode('utf8')
    except UnicodeDecodeError:return data.hex()

def main():
    binding=ROOT/'Source/glossary-corpus-v2/runtime-bindings.json'
    b=json.loads(binding.read_text());program=bytes(b['sharedassets0.assets:2743']['compiledYarnProgram'])
    nodes={}
    for f,w,v in fields(program):
        if f!=2:continue
        entry=fields(v);name=next(x[2].decode() for x in entry if x[0]==1)
        nf=fields(next(x[2] for x in entry if x[0]==2));ins=[];labels={}
        for nn,ww,vv in nf:
            if nn==2:
                op=0;args=[]
                for k,wire,val in fields(vv):
                    if k==1:op=val
                    elif k==2:args.append([(a,wt,strings(av) if wt==2 else av) for a,wt,av in fields(val)])
                ins.append({'index':len(ins),'opcode':op,'operands':args})
            elif nn==3:
                ll=fields(vv);labels[next(x[2].decode() for x in ll if x[0]==1)]=next((x[2] for x in ll if x[0]==2),0)
        nodes[name]={'instructions':ins,'labels':labels}
    corpus=[json.loads(x) for x in (ROOT/'Source/localization-inventory-v3/strings.jsonl').read_text().splitlines()]
    bykey={r['key']:r for r in corpus if r['collection']=='Dialogs'}
    closure=json.loads((ROOT/'Translations/bg/semantic-closure-cycle-001.json').read_text())
    keyuses={}
    for name,node in nodes.items():
        for ins in node['instructions']:
            for operand in ins['operands']:
                for f,w,v in operand:
                    if w==2 and isinstance(v,str) and v.startswith('line:'):keyuses.setdefault(v,[]).append({'node':name,'instruction':ins['index'],'opcode':ins['opcode']})
    rows=[]
    for r in closure['reviewRows']:
        if r['collection']=='Dialogs':rows.append({'stableId':r['stableId'],'key':r['key'],'uses':keyuses.get(r['key'],[])})
    evidence={'bindingSha256':hashlib.sha256(binding.read_bytes()).hexdigest(),'compiledSha256':hashlib.sha256(program).hexdigest(),'nodeCount':len(nodes),'closureDialogueMappings':rows,'editedNodes':{n:nodes.get(n) for n in closure['consumerTopology']['editedYarnNodes']},'note':'Raw protobuf fields/opcodes; no runtime execution and no unverified opcode-name assertion.'}
    (OUT/'compiled-context.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    (OUT/'compiled-nodes.json').write_text(json.dumps(nodes,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'nodes':len(nodes),'closureRows':len(rows),'unmapped':[x for x in rows if not x['uses']],'editedAliases':[n for n in evidence['editedNodes'] if evidence['editedNodes'][n] is None]},ensure_ascii=False))
if __name__=='__main__':main()
