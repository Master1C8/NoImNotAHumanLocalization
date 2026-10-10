"""Record manually reviewed bounded voice-selector omissions as new evidence."""
import json,re
from pathlib import Path
OUT=Path(__file__).resolve().parent
candidates=json.loads((OUT/'additional-voice-candidates-v2.json').read_text())
wording={
2:'Anger: Не, с такава шибана отрепка няма да живея под един покрив. Тогава вече няма да се сдържа.',
7:'Anger: Или на страната на жертвите. И двете страни са пълен шибан ужас.',
9:'Anger: А когато Бог умря в очите им, у тях не остана нищо човешко, мамка му.',
14:'Esenin: Това е пълен шибан ад.',
16:'Anger: Още преди да започне цялото това шибано безумие, тя беше дълбоко вярваща.',
23:'Esenin: Ти си просто шибан откачалник.',
24:'Esenin: Това е пълен шибан ужас...',
26:'Esenin: Беше ужасяващо, ебаси.',
27:'Esenin: Все неволно се удрям в нещо, мамка му. Особено в маршрутките.',
31:'Esenin: Впечатлен съм. И това е пълна шибана лудост.',
34:'Esenin: Извини ме, но като гледам какво правиш, изведнъж разбрах, че ни е спукана работата, ебаси.',
36:'Esenin: Или си се натряскал, мамка му? Мислех, че вече съм изпил всичко силно.',
40:'Esenin: Тогава престани да ме тормозиш с тия шибани тестове.',
41:'Anger: Понякога забелязвам, че дърпам меката част на ухото си, но чак когато вече пари адски, ебаси.',
43:'Anger: Понякога ръцете така ме сърбят, че ми се иска да си разкъсам цялата кожа. Или да забия юмрук в стената, мамка му. Или и двете наведнъж.',
44:'Anger: Понякога ръцете така ме сърбят, че ми се иска да си разкъсам цялата кожа. Или да забия юмрук в стената, мамка му. Или и двете наведнъж.',
46:'Anger: Да не си откачил, мамка му? Само ти показах зъбите си.',
47:'Anger: През кура ми е.',
49:'Anger: Е, през кура ми е. На.',
}
compiled=json.loads((OUT/'compiled-nodes.json').read_text());uses={}
for node,d in compiled.items():
 for ins in d['instructions']:
  for a in ins['operands']:
   for f,w,v in a:
    if w==2 and isinstance(v,str) and v.startswith('line:'):uses.setdefault(v,[]).append({'node':node,'instruction':ins['index'],'opcode':ins['opcode']})
findings=[]
for index,target in sorted(wording.items()):
 r=candidates['rows'][index];assert target.startswith(r['source'].split(':',1)[0]+':')
 findings.append({'findingId':f'bg-independent-01-supplement-{len(findings)+1:03d}','candidateIndex':index,'stableId':r['stableId'],'key':r['key'],'source':r['source'],'currentFullTarget':r['target'],'proposedFullTarget':target,'category':'profanity','objectiveReason':'This full source unit contains coarse profanity while the full Bulgarian unit removes it. It is an occurrence of the same five-character voice risk already addressed by the author, but the selector omits пизд-, ёб-, prefixed доёб-/уеб-/наеб-, and хуя/хуй inflections. Restore the register, then include real context in the normal regenerated next closure.','compiledUses':uses.get(r['key'],[]),'status':'proposal outside original closure; not applied'})
(OUT/'supplementary-findings.json').write_text(json.dumps({'schemaVersion':1,'locale':'bg','supplementaryReadCount':len(candidates['rows']),'findingCount':len(findings),'selectorRepairRequired':True,'findings':findings},ensure_ascii=False,indent=2)+'\n')
(OUT/'supplementary-read.ids').write_text('\n'.join(r['stableId'] for r in candidates['rows'])+'\n')
(OUT/'selector-finding.json').write_text(json.dumps({'findingId':'bg-independent-01-selector','selectorPath':'Translations/bg/semantic-closure-selector-cycle-001.json','rule':'vulgarCharacterVoice','objectiveReason':'The current rule selects еб... and заеб..., хер..., хуйн..., and ублюд..., but misses enumerated profanity in the same selected speakers: пизд-, initial ёб-, prefixed доёб-/уеб-/наеб-, and хуя/хуй forms. The accepted corrections explicitly restore profanity for these voices. Fifty accepted source IDs outside the current closure match the bounded supplementary selector, including nineteen units whose current full target removes coarse register.','boundedSupplementarySelector':candidates['selector'],'additionalReadIdsPath':'Translations/bg/independent-review-01/supplementary-read.ids','additionalReadCount':50,'supplementaryFindingCount':len(findings),'repairInstruction':'Author should expand the canonical rule or specification to retain these still-applicable source spelling/inflection dependencies, reconcile full accepted source and authored target inputs, then regenerate an immutable next cycle including the containing scenes, repetitions and mandatory regressions. Do not append these IDs only to a generated list. The fifty matches are an evidenced lower bound for missing dependencies, not proof that this proposed supplementary regex covers every possible profanity form or all speakers.','fullRestart':'No source/glossary/mapping change found. This bounded pattern can be repaired with dependency expansion; full corpus acceptance remains pending until the expanded evidence is reviewed.'},ensure_ascii=False,indent=2)+'\n')
print({'supplementaryRead':50,'supplementaryFindings':len(findings),'unmappedFindings':[f['key'] for f in findings if not f['compiledUses']]})
