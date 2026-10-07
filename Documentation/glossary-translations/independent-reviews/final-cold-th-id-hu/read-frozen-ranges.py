import pathlib,json,sys
p=pathlib.Path('/Users/antonkrutov/Desktop/no I\'m not a human/Documentation/glossary-translations/independent-reviews/final-cold-th-id-hu');s=json.loads((p/'source-frozen.json').read_text())['entries'];l=sys.argv[1];t=json.loads((p/f'{l}-frozen.json').read_text());start,end=map(int,sys.argv[2:4]);mode=sys.argv[4] if len(sys.argv)>4 else 'pair'
# Exact repetitions already read fully at source/target character entries. Definitions printed once per invocation for lossless references.
policies={}
for lang,field in [('RU','meaning'),(l.upper(),'meaning')]:
 rows=s if lang=='RU' else [t[e['id']] for e in s]
 for x in rows:
  for sentence in x[field].split('XXX_NEVER'):
   pass
 # Explicit recurring complete suffixes extracted from first evidenced male and female entry.
 for ix,label in [(0,'male'),(2,'female')]:
  text=rows[ix][field]
  if lang=='RU': suffix=text[text.index('Персонаж '):]
  elif l=='th': suffix=text[text.index('ตัวละครเป็น'):]
  elif l=='id': suffix=text[text.index('Tokoh '):]
  elif l=='hu': suffix=text[text.index('A szereplő '):]
  policies[f'{lang}-{label}']=suffix
if l in ['th','id','hu']:
 policies['RU-neutral']=s[79]['meaning'][s[79]['meaning'].index('Пол канонически'): ]
 policies[l.upper()+'-neutral']=t[s[79]['id']]['meaning'][t[s[79]['id']]['meaning'].index({'th':'เนื้อเรื่องไม่ได้ยืนยันเพศ','id':'Jenis kelamin tidak ditetapkan','hu':'A nemet a kánon'}[l]): ]
for k,v in policies.items(): print(f'POLICY {k}: {v}')
for n in range(start-1,end):
 e=s[n];a=t[e['id']];print(f'\n{n+1} {e["id"]}')
 for lang,row in ([('RU',e),(l.upper(),a)] if mode=='pair' else [(l.upper(),a)]):
  for f in ['term','meaning']:
   text=row[f]
   for k,v in policies.items():
    if k.startswith(lang+'-') and v in text: text=text.replace(v,'['+k+' POLICY]')
   print(lang+' '+f+': '+text)
