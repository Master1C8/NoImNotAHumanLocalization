#!/usr/bin/env python3
"""Freeze the author-only cycle004 handoff and advance the Bulgarian mutable summary."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];BG=ROOT/'Translations/bg'
load=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def freeze(p,obj):
 raw=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()
 if p.exists():assert p.read_bytes()==raw,str(p)+' drift'
 else:p.write_bytes(raw)
def main():
 result=load(BG/'correction-batch-004-result.json');delta=load(BG/'semantic-delta-cycle-004.json');closure=load(BG/'semantic-closure-cycle-004.json');verification=load(BG/'correction-cycle-004-final-verification.json')
 nextrow=delta['nextReviewRows'][0]
 link=lambda name:{'path':'Translations/bg/'+name,'sha256':sha(BG/name)}
 progress=load(BG/'correction-cycle-004-baseline/semantic-review-progress.json')
 progress.update(status='Complete first16538-unit author semantic pass preserved; sealed Review03 not clean, all three proposals now applied in cycle004; exact120-ID independent delta ready; no clean or editorial acceptance',currentAuthoredFiles=result['allAuthoredFiles'],independentDiffReview='Review03 accepted all41 prior corrections/upheld3 dismissals; three new findings author-corrected; cycle004120-ID independent review pending root assignment',nextAction='Root assigns a distinct reviewer to all120 exact current delta full pairs, three corrected pairs and one fresh mandatory assembled consumer; retain907 exact prior mandatory credits; no game launch.')
 progress['correctionBatch004']=dict(link('correction-batch-004-result.json'),changedIds=3,changedFiles=3,reviewerProposalsAccepted=3)
 progress['dependencyClosureCycle004']=dict(link('semantic-closure-cycle-004.json'),ids=2911)
 progress['independentDeltaCycle004']=dict(link('semantic-delta-cycle-004.json'),ids=120,nextId=nextrow['stableId'],nextSourceIndex=nextrow['sourceIndex'],nextKey=nextrow['key'])
 progress['currentReviewedFilesBasis']='First-pass reviewedFiles remain immutable baseline author evidence; currentAuthoredFiles pin cycle004 corrected corpus. Bounded cycle00481-family complete-pair author read and three full replacements are separate from independent credit.'
 progress['draftCoverage']={'acceptedUnits':16538,'authoredUnits':16538,'percent':100.0}
 progress['runtimeVisual']='not-run; no game launch or built/runtime acceptance claimed'
 assert progress['acceptedUnits']==progress['reviewedUnits']==16538
 freeze(BG/'semantic-review-progress-cycle-004.json',progress)
 # Mutable summary update only; old exact bytes physically retained in baseline.
 raw=(json.dumps(progress,ensure_ascii=False,indent=2)+'\n').encode();(BG/'semantic-review-progress.json').write_bytes(raw)
 checkpoint={'schemaVersion':1,'locale':'bg','gameVersion':'1.3.19','status':'complete bounded cycle004 author correction handoff; separate independent review pending',
  'acceptedUnits':16538,'authoredUnits':16538,'draftCoveragePercent':100.0,'firstSemanticPassReviewedUnits':16538,'semanticFullPassRestart':False,
  'review03':{'manifestSha256':'7528f1c522bf30a4a2f6999568e3dcfed48a684cea7122f720b29a791c733f61','deltaRead':311,'supplementaryRead':3,'priorCorrectionsAccepted':41,'priorDismissalsUpheld':3,'clean':False},
  'cycle004':{'reviewerProposals':3,'accepted':3,'appliedUnits':3,'affectedFiles':3,'additionalCorrections':0,'unchangedUnits':16535,'unchangedFiles':408,'fullGuardRows':16538},
  'result':link('correction-batch-004-result.json'),'sourcepairs':link('correction-cycle-004-sourcepairs.json'),'preimages':link('correction-cycle-004-baseline/manifest.json'),
  'closure':dict(link('semantic-closure-cycle-004.json'),ids=2911),'delta':dict(link('semantic-delta-cycle-004.json'),ids=120),'reviewIds':{'path':delta['components']['review']['path'],'sha256':delta['components']['review']['sha256'],'count':120},
  'formula':delta['formula'],'reasonCatalog':delta['reasonCatalog'],'deltaComponents':{name:{k:v for k,v in c.items() if k!='ids'} for name,c in delta['components'].items()},
  'mandatoryRegressions':{'total':908,'freshIndependentReadsRequired':1,'priorExactApplicableRetained':907},
  'verification':link('correction-cycle-004-final-verification.json'),'fullLocaleReceipt':link('locale-corpus-cycle-004.json'),'preserveExactReceipt':link('preserve-exact-cycle-004.json'),
  'currentProgressSnapshot':link('semantic-review-progress-cycle-004.json'),'currentAuthoredFiles':result['allAuthoredFiles'],
  'next':{'stage':'independent delta review assigned by root','deltaIndex':0,'stableId':nextrow['stableId'],'sourceIndex':nextrow['sourceIndex'],'key':nextrow['key'],'action':'Read exact120 full pairs plus real compiled context, adjudicated sourcepairs and mandatory fresh consumer; root owns clean verdict, acceptance and integration.'},
  'unresolvedLimits':verification['limits']+['Fresh mandatory Bald occupied-name consumer requires independent admitted-output/agreement check; compiled producer and assemblies reconciled without inventing a domain count.','Two accepted delta IDs have no current compiled use; table/source context reviewed, physical reachability unverified.'],
  'telemetry':{'actualTokens':'unknown; no exposed per-request counters','newAgents':0},'changesOutsideLocale':'none by this task; shared Git/index/source/glossary/game/otherlocale unchanged'}
 freeze(BG/'correction-cycle-004-handoff-checkpoint.json',checkpoint)
 hashes={n:sha(BG/n) for n in ['correction-batch-004.json','correction-batch-004-result.json','correction-cycle-004-sourcepairs.json','semantic-closure-cycle-004.json','semantic-delta-cycle-004.json','semantic-cycle-004-review.ids','locale-corpus-cycle-004.json','preserve-exact-cycle-004.json','correction-cycle-004-final-verification.json','correction-cycle-004-handoff-checkpoint.json','idiom-dependency-spec-cycle-004.json']}
 table='\n'.join('| '+n+' | `'+h+'` |' for n,h in hashes.items())
 handoff=f'''# Bulgarian cycle004 author correction handoff

Status: **three complete author corrections applied; exact independent delta ready**. No clean independent verdict, editorial acceptance, built artifact or runtime readiness is claimed.

## Author correction and preserved facts

| Finding | Stable ID suffix | Complete-unit adjudication |
| --- | --- | --- |
| Review03-001 | 110504455814848520 | Accept “Веднъж се прибрах вкъщи.” Bald arrives on one past occasion, before finding the family and fleeing attackers. Open door, chaos, mother AND grandmother, broken fingers/legs, coarse hesitation and unfinished speech retained. |
| Review03-002 | 110504454481059851 | Accept final “Гарантирам.” Scammer vouches for the winning survival strategy; remaining strategy and affiliation statement retained. |
| Review03-003 | 110504454460088329 | Accept final “Гарантирам.” Betting schemes, past action, ease comparison and oath retained. |

One consolidated three-ID batch changes **three authored dialogue files**. All **16,535 other units** and **408 other authored files** remain exact. Six affected authored/sidecar preimages are physically saved in `correction-cycle-004-baseline/`; the complete before/after pairs and hashes are in `correction-cycle-004-sourcepairs.json`. Per-file atomic replacements are resumable from verified old/new bytes; the three-file application is not a filesystem transaction. All final postconditions verify.

The sealed Review03 manifest matches the owner's exact SHA-256 `{checkpoint['review03']['manifestSha256']}`. All **878** current input pins were verified before editing. After correction, the only six intentional historical pin differences are the three target batches and their refreshed receipts; **872** Review03 input pins remain exact. Its **41** accepted cycle003 corrections and **three** upheld Review02 register dismissals remain preserved. No generic profanity was appended. Review02's failed diagnostic evidence and final corrected v2 proof remain immutable; final sealed proof is the applicability input.

## Bounded source-family review and ordinary recipe

`idiom-dependency-spec-cycle-004.json` is the locale-owned source-family specification. Its ordinary source predicates select **76** accepted `как-то` units and **five** accepted `отвечаю` units across the inventory. Exactly **two** standalone `Отвечаю.` matches select both Scammer assurance defects; no generated ID append or speaker whitelist is used. All **81** complete Russian/Bulgarian family pairs were read; ambiguous controls and the corrected units were checked against actual compiled scenes, and twelve preimage target controls were read. No additional objective correction was identified.

Temporal anecdote and means/degree are distinct senses. Unstable's current hand-cramp “Как-то я их перекрутил” retains manner wording; Death's current fatigue retains its downtoner. Miner “за всё отвечаю,” Scammer “за базар отвечаю” and Experienced's contextual pledge retain their valid constructions. Positive/negative controls, exact three full replacements and unchanged control pairs are verified by `verify_cycle_004.py`. These are author checks, not independent read credit.

Ordinary cycle004 closure generation retains cumulative cycle001–004 corrections, all applicable Review02/03 proposal scenes, exact source repetitions, glossary/referent rules, source voice v6, runtime dependencies and mandatory regressions. New idiom families are selected through predicates in the canonical cycle004 recipe. Voice v6 selects the same **741 IDs / 112 speaker categories** with passing include/exclude controls; no voice selector defect or lexicon change exists. Its historical candidate target snapshot remains immutable. **Review current full targets in closure004/delta004**, not the old voice snapshot.

## Exact next independent review

- **2,911** current closure IDs; all **2,839** previous closure IDs remain selected; **zero retired**.
- **2,836** exact applicable prior independently read pairs, bound to full source, target, key, collection and consumer identity. Review03 supplemental credits reuse exactly two unchanged pairs; the corrected assurance supplemental pair loses current read credit.
- **75** current IDs lack applicable prior evidence: **72 newly selected dependencies + three corrected targets**.
- **45** explicit prior-read invalidations: same actual corrected node and/or directly affected temporal/assurance source family. Every row has objective reasons in `invalidatedPriorReasons`; no blanket voice reread or full-pass restart.
- **120** exact next-read IDs = corrected ∪ (current closure − exact applicable prior independently read IDs) ∪ explicit invalidations. Component lists overlap. `semantic-cycle-004-review.ids` is authoritative; `nextReviewRows` supplies the exact full pairs.
- **908 mandatory regressions** = **one fresh next-delta read + 907 retained exact prior reads**. Groups, exact IDs, hashes, applicability origins and retirement/reason catalogs are retained separately.

Start at delta index **0**, stable ID `{nextrow['stableId']}`, source index **{nextrow['sourceIndex']}**, key `{nextrow['key']}`. Root assigns a distinct reviewer to every one of the 120 exact pairs and the three full corrections. A reviewer may reuse prior rows only while their full-pair/consumer applicability remains exact.

### Fresh mandatory assembled consumer

`110504457479987203`, `Bald_Entrance_Occupied:4`, contains slot `{{0}}`. The actual compiled stack is `Bald` → `GetCharacterOnPlace` → localized `characterName_{{occupant}}` → slot0 before markup. Original managed assembly and raw compiled-program hashes remain exact. The next reviewer must check admitted occupant-name outputs and agreement/referent of the retained “го” in the complete consumer context, without assuming an arbitrary output count. This is a fresh mandatory dependency, not an established new finding. Physical gameplay is unrun.

Two delta IDs (`110504451960283141`, `110504451817676809`) have no current compiled use; accepted table/source context is available, while runtime reachability remains unverified.

## Deterministic gates and reproduction

The owning **locale-only** `Scripts/validate_locale_corpus.py bg` passes **16,538 unique IDs**, selected scope/order, structural guards, full preserve-exact protected grammar and unchanged credits derivation. Only three affected receipts were refreshed from that full-corpus proof; no per-batch parse pools or all-locale scan ran. No UI/check/static values or credits-role map were changed. The preserve-exact receipt references the same owning gate and is not claimed as another invocation.

```sh
.venv/bin/python Translations/bg/apply_correction_batch_004.py verify
.venv/bin/python Translations/bg/build_correction_result_004.py
.venv/bin/python Translations/bg/build_semantic_closure_cycle_004.py verify
.venv/bin/python Translations/bg/build_semantic_delta_cycle_004.py verify
.venv/bin/python Translations/bg/verify_cycle_004.py verify
```

`prepare_cycle_004.py` captures the exact **pre-correction** boundary and must not be rerun against corrected current targets. Immutable preimages prove restore identity; current verification checks successful continued execution and final old/new postconditions. To rerun the owning full guard, use a **new** BG receipt path, never overwrite the sealed one.

No universal restart condition changed: source inventory, accepted scope, glossary, canonical gender rules, exact spans and compiled consumer/binding topology remain pinned. The complete first **16,538-unit** author semantic pass remains reusable. Draft coverage remains **16,538/16,538 (100%)**, separately from pending runtime readiness.

## Exact artifacts

| Artifact | SHA-256 |
| --- | --- |
{table}

Source strings: `ecd96645c2ca6f23f8bf3ab2fcf65709e961478ae15a38e83d94cc335a408bf0`.
Approved BG glossary: `28d7eb651d95b56a72a5a4acefcba5f434dcbe6925a2233126655e13b0e01cab`.
Source glossary: `14eb83652b636b36b3110ddedaf2eaf72127e7e46f23474cad816dbbe8dbf401`.
Full pin maps include static source, exact manifest, assemblies, compiled nodes, recipes, guard helpers and all 411 current authored inputs/sidecars. Seal: `correction-cycle-004-evidence-sha256.json` (does not recursively hash itself).

## Historical author diagnostics

The initial unsealed closure generation had a copied descriptive recipe path pointing to cycle003. Its exact JSON bytes are preserved as `semantic-closure-cycle-004-v1-diagnostic.json`; the corrected ordinary cycle004 recipe produces the authoritative closure above with unchanged membership. A first author verification attempt assumed every receipt had batch-schema keys; the static receipt has draft-schema keys. The checker now handles both schemas and the corrected proof passes. Neither diagnostic is a failed owning corpus gate or an independent editorial verdict.

## Pending owner gates

Distinct independent delta review and root editorial acceptance remain required, followed by coordinated text integration, rendering/fonts/layout/runtime, packaging and release gates when authorized. No game launch, shared/Git mutation, other-locale change, build, images/textures, publication or new agent was performed. Actual token telemetry is **unknown**: no counters are exposed in this chat; the reporting tail is unmeasured.
'''
 p=BG/'independent-review-handoff-cycle-004.md';raw=handoff.encode()
 if p.exists():assert p.read_bytes()==raw
 else:p.write_bytes(raw)
 print(json.dumps({'checkpointSha256':sha(BG/'correction-cycle-004-handoff-checkpoint.json'),'handoffSha256':sha(p),'nextIndependentReadIds':120,'nextId':nextrow['stableId']}))
if __name__=='__main__':main()
