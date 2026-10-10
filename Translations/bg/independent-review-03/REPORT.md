# Bulgarian cycle 003 independent verdict

Status: **complete independent review, not clean**. Three objective full-unit findings are consolidated in `findings.json`; no authored translation, source, glossary, shared evidence, Git state, build, game, images or textures were changed.

## Findings

| Finding | Stable ID suffix | Objective defect | Proposed repair |
| --- | --- | --- | --- |
| bg-independent-03-001 | 110504455814848520 | Bald's temporal “Я как-то вернулся домой” becomes manner “Прибрах се някак.” He came home on one occasion and then found his injured family; the target says he somehow managed to get home. | Start the complete unit with “Веднъж се прибрах вкъщи.” Preserve the correctly repaired mother/grandmother reference and every remaining fact. |
| bg-independent-03-002 | 110504454481059851 | Scammer's standalone slang “Отвечаю” vouches for his survival strategy. Literal “Отговарям” supplies an unrelated act of answering. | End the complete unit with “Гарантирам.” |
| bg-independent-03-003 | 110504454460088329 | The same assurance calque occurs after Scammer's betting-scheme claim. This is outside the 311-row delta and was independently read as a bounded supplementary dependency. | End the complete unit with “Гарантирам.” |

`findings.json` contains the complete Russian units, exact current Bulgarian units, complete proposed replacements, hashes and compiled scene references. The two assurance occurrences are one shared semantic defect. A bounded search of all accepted Russian dialogue found exactly two “Отвечаю” occurrences, both with the erroneous target; both full pairs and compiled scenes were read. The current target “Прибрах се някак” occurs once. These are bounded source idiom defects, not a reason to discard the whole semantic audit.

Adjudicate all three proposals together, carry out one consolidated bounded remedial check of the implicated idioms and their dependencies, then generate and independently review the exact final delta. Do not start another chain of isolated one-line corrections. No full restart is warranted by the verified unchanged source, glossary, stable IDs, parsing or binding inputs.

## Coverage and accepted corrections

- Read all **311** exact `nextReviewRows`, indices 0–310, as complete source/target units. `read.ids` exactly equals the ordinary cycle 003 review list. `per-id-read-verdicts.json` records one decision for every ID with source and target hashes.
- Read **3** unique supplementary pairs: two unchanged dismissed proposals outside the delta and the second assurance calque. Total fresh independent coverage is **314 distinct units**. The supplemental set is separate and does not inflate the 311-row delta.
- Independently accept all **41 corrected complete units** and uphold all **3 dismissed register-only proposals** (`-010`, `-014`, `-029`). Source facts, agreement, agency, original sentence content and contextual Bulgarian profanity remain intact. Adding another generic oath to those three dismissed proposals restores no semantic fact.
- Bald's `ма и ба` correctly means mother and grandmother. His father is separately identified in later source context. Both Leper `Ёбаный свет` units now use exclamations. The compiled Wheelchair `IsImposter` branch places plural `им` at instruction 6 followed by `все они` at instruction 7; Bulgarian `им` and `всички те` preserve this referent. The stored duplicate without a current compiled use was reviewed as supplemental source context, without inventing runtime reachability.
- The corrected Wheelchair `Это… пиздец` uses grammatical `пълен шибан ужас`; the former malformed wording is absent from that current full unit. Natural idioms such as `спукам ... от бой`, `омитай`, `майната`, `Ебаси` and `през кура` were judged in their complete scenes. Oaths are not a count-based acceptance rule.
- The author's **982** affected-scope reads are author evidence; they are not credited as independent decisions.

## Dependency and technical evidence

The ordinary closure and delta generators reproduce **2,839 closure IDs**, **2,649 exactly applicable prior independent readings**, **190 IDs without applicable prior evidence**, **121 explicit invalidations**, **41 corrected IDs** and **311 distinct next-read IDs**. Components overlap. All 121 reasons were independently reconstructed from current corrected scene nodes, exact repetitions and affected referent groups. No prior dependency was retired.

All **908 mandatory regressions** are accounted for: **4 fresh independent decisions**, **904 exact applicable prior independent decisions**. The catalog is clean on current hashes; the overall delta is not clean because of the three nonmandatory findings. Exact source, target, key, collection and scene identity bind reuse to the sealed review 01/02 evidence.

The v6 ordinary lexical selector reproduces **741 candidates in 112 speaker categories**, including all six earlier missed source forms. Its positive and negative lexical controls pass; ordinary `хулиган`, `хулиганы`, `небось`, `тебя`, `учёба` and `нёбо` remain excluded. No generated ID was appended manually. Candidate selection is not a defect judgment. There is no fresh reread claim for every unchanged candidate or a claim that this bounded lexicon covers every possible Russian oath.

A fresh locale-only `Scripts/validate_locale_corpus.py bg` guard passes **16,538 unique current units**, including the owning structural and preserve-exact grammar checks, and writes only the new `locale-corpus.json`. All **411 authored inputs and 411 sidecars** match current cycle 003 pins. The **70** older review 02 authored/sidecar pin differences are exactly the **35 changed batches** and their sidecars; every other historic review 02 input pin remains exact. All **41 historical full source/target preimages** match immutable independently read rows, including the one earlier supplementary row. No missing historical authored file bytes were reconstructed or claimed.

The approved local Bulgarian glossary contains **201 entries** and is exactly equal to the current canonical Bulgarian layer. The source glossary and source inventory hashes remain unchanged. Ordinary reproduction verifies the existing cycle receipts without rewriting them.

The raw current Yarn program was reparsed and normalized equality was verified against all **3,255** immutable compiled nodes. Of the 311 delta rows, **302** have current compiled uses and **9** do not. Missing-use IDs are recorded; their accepted source-table context remains reviewable, while physical reachability is unverified. No delta row contains a numeric format slot. The current closure has **111 format-slot rows**, covered by unchanged applicable mandatory evidence.

Original managed assemblies still match prior independent hashes. The current source consumer evidence for `GetLocalization`, `SetupConsumable`, `InitGotTexts`, `GetCharacterOnPlace`, localized line retrieval, line/option substitution before markup, and `runSelectedOptionAsLine=false` was reconciled. The compiled program contains **56 `GetCharacterOnPlace` calls** and **18 `GetPhoneNumber` calls**. These are measured source producer domains, not admitted runtime-output counts. Localized consumable name/narrative output and the literal quantity suffix remain distinct. No arbitrary six-output count is used.

## Limits and input identity

This is an editorial verdict on unchanged authored Bulgarian text for game **1.3.19**, source **ru**, target **bg**, accepted denominator **16,538**. Physical game launch, rendering, fonts, layout, runtime reachability, packaging and release validation were not run. The owner prohibited game launch and excluded translated images/textures. No Bulgarian built artifact is claimed.

| Input | SHA-256 |
| --- | --- |
| Source strings | ecd96645c2ca6f23f8bf3ab2fcf65709e961478ae15a38e83d94cc335a408bf0 |
| Approved Bulgarian glossary | 28d7eb651d95b56a72a5a4acefcba5f434dcbe6925a2233126655e13b0e01cab |
| Cycle 003 correction plan | 14f37de52ed68f6be232e0e8b21ef262d7c99c8bc24e7c8d0c15f6ad4430fde5 |
| Cycle 003 corrected result | 656392e5c6229ab210e6d9babb3b5ba25283e9565a948a5cfbaf7f4bcf151a04 |
| Current closure | f31cb84fd91ca88c23d4626b0d559947b1ad6105199e08be86d5fadbe36957a7 |
| Exact delta | 423dcb03e4ddb29e4394e58aac4f24f072e3759b227c3f471d872271b042cd3e |
| Exact delta read IDs | 44f5cbd7ae603f2e5d5f5d9835d2dbee0a50f045658edf588ca10714af76b1fc |

The authoritative per-file hashes are in `input-verification.json` and the final review artifact manifest `evidence-sha256.json`. The read-ID hash is verified directly from bytes; it is not inferred from a count. Measured token telemetry is collected by the parent coordinator. Counters are unavailable to this agent, so usage here is unknown, not zero; the reporting tail is unmeasured.
