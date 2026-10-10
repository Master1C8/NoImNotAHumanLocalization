"""Locate parsed entries[i].target JSON tokens and replace only their exact spans."""
import json

def rewrite_targets(raw,new_doc):
 text=raw.decode('utf-8');decoder=json.JSONDecoder();position=0;spans={}
 def ws():
  nonlocal position
  while position<len(text) and text[position] in ' \t\r\n':position+=1
 def parse(path):
  nonlocal position
  ws();start=position
  if text[position]=='{':
   position+=1;ws();obj={}
   if text[position]=='}':position+=1;return obj
   while True:
    ws();key,end=decoder.raw_decode(text,position);assert isinstance(key,str) and key not in obj;position=end;ws();assert text[position]==':';position+=1;obj[key]=parse(path+(key,));ws();ch=text[position];position+=1
    if ch=='}':return obj
    assert ch==','
  if text[position]=='[':
   position+=1;ws();arr=[]
   if text[position]==']':position+=1;return arr
   while True:
    arr.append(parse(path+(len(arr),)));ws();ch=text[position];position+=1
    if ch==']':return arr
    assert ch==','
  value,end=decoder.raw_decode(text,position);position=end
  if len(path)==3 and path[0]=='entries' and isinstance(path[1],int) and path[2]=='target':
   assert isinstance(value,str);spans[path[1]]=(start,end,value)
  return value
 old=parse(());ws();assert position==len(text) and len(spans)==len(old['entries'])==len(new_doc['entries'])
 assert {k:v for k,v in old.items() if k!='entries'}=={k:v for k,v in new_doc.items() if k!='entries'}
 pieces=[];offset=0
 for index,(a,b,value) in sorted(spans.items(),key=lambda x:x[1][0]):
  before=old['entries'][index];after=new_doc['entries'][index]
  assert {k:v for k,v in before.items() if k!='target'}=={k:v for k,v in after.items() if k!='target'}
  assert offset<=a<b;pieces.append(text[offset:a]);pieces.append(text[a:b] if value==after['target'] else json.dumps(after['target'],ensure_ascii=False));offset=b
 pieces.append(text[offset:]);result=''.join(pieces).encode();assert json.loads(result)==new_doc
 return result
