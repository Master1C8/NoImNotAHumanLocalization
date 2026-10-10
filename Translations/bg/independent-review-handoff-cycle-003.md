# Bulgarian correction003 independent review handoff

Status: author correction complete for this cycle; independent clean review, editorial acceptance, shared integration, and runtime QA remain pending. The owner explicitly prohibited a game launch for this task.

## Input identity and prior evidence

- Game v1.3.19, source locale `ru`, target locale `bg`, text-only denominator **16,538 accepted IDs**.
- Source strings SHA-256 `ecd96645c2ca6f23f8bf3ab2fcf65709e961478ae15a38e83d94cc335a408bf0`; static source `3791c851b1c2282b2908ba288830df07110a9d9fcc75d7e86e710e8485024efc`; preserve-exact manifest `d431b758ca205925e637e2020ac60f47a290d9680299b1774387d951079fe226`.
- Approved Bulgarian glossary layer `28d7eb651d95b56a72a5a4acefcba5f434dcbe6925a2233126655e13b0e01cab`; master source glossary `14eb83652b636b36b3110ddedaf2eaf72127e7e46f23474cad816dbbe8dbf401`. No source or glossary edit was made.
- Review02 is historically sealed and not clean. Its final v2 proof and 851 input pins were checked before author edits. Its immutable `independent-review-02/` files, including the failed diagnostic verifier and final corrected verifier, were preserved. Current authored file hashes intentionally differ from Review02's pre-correction pins; use the correction003 receipts below.

## Adjudication and bounded read

- All **43** Review02 complete-unit proposals were adjudicated in `independent-review-02-author-adjudication.json` (SHA-256 `e16ea793f084f285a5d9c107e34a0acb4a9b05b6bbfc9b7dbaff594ea922145a`). **40** were accepted or revised; **3** register-only suggestions were dismissed (`bg-independent-02-010`, `-014`, `-029`) because their existing Bulgarian idioms already carry the required force and the proposed generic oath disrupted the complete line.
- One additional full-unit correction was authored for the newly selected Unstable `хз` row. The final single batch changes **41 IDs in 35 dialogue batches**: `correction-batch-003.json` `14f37de52ed68f6be232e0e8b21ef262d7c99c8bc24e7c8d0c15f6ad4430fde5`; applied result `correction-batch-003-result.json` `656392e5c6229ab210e6d9babb3b5ba25283e9565a948a5cfbaf7f4bcf151a04`. The plan pins the original Russian, old full Bulgarian line, and accepted full replacement for every edit.
- The bounded affected scope contains **982** complete pairs across corrected scene nodes, all proposal scene nodes, exact Russian repetitions, family and sign referents, color-verb and Leper exclamation concepts, Rocker imperatives, target grammar, and the canonical voice selector. All 982 are in the cycle003 closure. **142** were outside Review02's 2,110-ID delta and were read as full pairs; one yielded the additional correction. Pre-correction scope SHA-256 `3f5d54510ccaf393cd02ace69f1c38f49dc26b59cf4339ea21b884ca8f516bc3`; author verdicts `74cccc8e0d560220517b583d926c0ba96e2d54b7dd01a8259752655f3f04f506`. Review02's independently read pairs remain independent evidence, not author self-credit.
- Bald's clipped `ма и ба` now resolves to mother and grandmother, consistent with his later account and approved glossary. The Leper's `Ёбаный свет` is an exclamation, not literal light. The two Wheelchair duplicates use plural signs in the compiled branch that continues with `все они`; the next reviewer should check this referent again in scene order. All three dismissed proposals retain their unchanged original targets.

## Selector and validation

- Canonical `voice-risk-selector-v6.json` SHA-256 `c04a6e81300989de9b6a98a32803f0d07057811f032943fdaff7aa7f411bdbe1` and `build_voice_remedial_candidates.py` reproduce **741** Russian voice candidates across **112** speaker categories on the corrected authored bytes. The six Review02 missed IDs are selected through normal source-lexical matching; regression controls include `посрать`, `срал`, `теребонькаешь`, `смехуечки`, `ахуитительных`, `хз`, `хули` and exclude ordinary `хулиган`, `хулиганы`, `небось`, `тебя`, `учёба`, `нёбо`. Candidate artifact SHA-256 `9602e6c971fac46722cea5232b19094a21068dd2f997506e7d776396af006535`. No generated ID was manually appended.
- All 35 affected batch sidecars passed on exact final bytes. The owning whole-locale structural receipt checked 16,538 rows: `locale-corpus-cycle-003.json` `9b4704717c5da6f0c7c4f9baa9fe2ef15e4cda2a8060141b412aed1c4266ec39`. The owning preserve-exact function checked all 16,538 rows: `preserve-exact-cycle-003.json` `c02e27cb252d39cea7aa89dbcd95ae928c2037ed68711a721c1189cab2a41b2f`. No static authored content changed; the full-corpus guards checked it.

## Exact next independent delta

- Closure selector `semantic-closure-selector-cycle-003.json` `40f8a7cd248c235f12804655cf53d6630f39b74af35d2933771a8a46bb46e905`; generated closure `semantic-closure-cycle-003.json` **2839 IDs**, SHA-256 `f31cb84fd91ca88c23d4626b0d559947b1ad6105199e08be86d5fadbe36957a7`.
- Exact formula: **corrected IDs ∪ (current closure − exact applicable prior independently read IDs) ∪ explicit invalidations**. Cycle002's 2,686 closure IDs were fully covered by Review01/Review02 together. On current exact source, target and consumer identity, **2,649** old readings remain applicable: 2,070 Review02 delta pairs, 576 Review01-only pairs, and three of Review02's four outside-delta supplemental voice pairs. The fourth supplemental pair is corrected here. All old closure IDs remain selected; **zero retired dependencies**.
- Delta `semantic-delta-cycle-003.json` SHA-256 `423dcb03e4ddb29e4394e58aac4f24f072e3759b227c3f471d872271b042cd3e`: **41 corrected**, **190 without applicable prior read**, **121 explicitly invalidated prior** with per-ID reasons, **311 distinct IDs for next independent read**. `semantic-cycle-003-review.ids` SHA-256 `44f5cbd7ae603f2e5d5f5d9835d2dbee0a50f045658edf588ca10714af76b1fc`. The corrected IDs overlap the new-closure term, so component counts must not be added as disjoint sets. All 908 mandatory regression IDs remain in the closure; four belong to the next read and the others retain exact applicable evidence.

## Reproduction and gates

Run from the canonical game checkout with `.venv/bin/python`:

```text
.venv/bin/python Translations/bg/build_correction_result_003.py
.venv/bin/python Translations/bg/build_voice_remedial_candidates.py --version 6
.venv/bin/python Translations/bg/build_semantic_closure_cycle_003.py verify
.venv/bin/python Translations/bg/build_semantic_delta_cycle_003.py verify
```

The next independent reviewer should read the 311 exact current `nextReviewRows`, recheck the 121 invalidation reasons and four mandatory rows, and inspect the Wheelchair plural reference, natural Bulgarian profanity, and unchanged facts in each corrected full line. A clean independent review and editorial acceptance have **not** been claimed. Root coordinates subsequent shared integration and runtime QA; this author chat has not launched the game, modified images/textures, staged or committed Git, or touched other locales.
