import json, sys
from pathlib import Path
r = Path(__file__).parent
s = json.loads((r/'source.snapshot.json').read_text())['entries']
loc, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
mode = sys.argv[4] if len(sys.argv)>4 else 'paired'
t = json.loads((r/(loc+'.snapshot.json')).read_text())
# Policies are derived from the already fully read player and daughter entries.
policies = {}
for lang, data in [('RU', {e['id']: e for e in s}), (loc.upper(), t)]:
    if lang not in ['RU','TH','HU','NL']: continue
    for ident, label in [('player','M'),('neighbours-daughter','F')]:
        marker = {'RU':'Персонаж ', 'TH':'ตัวละครเป็น', 'HU':'A szereplő ', 'NL':'Dit personage is '}[lang]
        text = data[ident]['meaning']
        tail = text[text.rfind(marker):]
        policies[lang+'-'+label] = tail
    if lang in ['RU','TH','HU','NL']:
        marker = {'RU':'Пол канонически','TH':'เนื้อเรื่องไม่ได้ยืนยันเพศ ตาม','HU':'A nemet a kánon','NL':'Het canonieke geslacht'}[lang]
        text = data['fema-phone-doctor']['meaning']
        policies[lang+'-U'] = text[text.rfind(marker):]
def compact(v):
    for k,p in policies.items(): v=v.replace(p,'['+k+' exact previously-expanded policy]')
    return v
for n,e in enumerate(s[a-1:b],a):
    print(str(n)+' '+e['id'])
    if mode=='paired': print('RU '+e['term']+' | '+compact(e['meaning']))
    print(loc.upper()+' '+t[e['id']]['term']+' | '+compact(t[e['id']]['meaning'])+'\n')
