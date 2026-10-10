# Bulgarian text review handoff: correction cycle 001

Game: *No, I'm not a Human* v1.3.19. Source: Russian. Target: Bulgarian. Scope: 16,538 accepted visible text units; translated images and textures are excluded by the owner. This handoff prepares a separately assigned independent review. It does not record one.

## Pinned evidence

| Artifact | SHA-256 |
| --- | --- |
| `semantic-first-pass-cycle-000.json` | `c5a8b2a604bf4b78d2525bbbe1ef5a66a661397d3558e8a95fda6f509a7bde86` |
| `correction-batch-001.json` | `f253008c279f842b367d92381542892a62bf1fc337dcc52aa39a922deb557db0` |
| `correction-batch-001-result.json` | `53b09aa6d7e0556986b9565f9f5b6218443f76c3db56e792b9f6420cf71cc228` |
| `semantic-closure-selector-cycle-001.json` | `4314438702fdd6a76662b54271bd1dd4c7d552c3c22cb1991bbe5ac1cf984b2b` |
| `build_semantic_closure.py` | `d561f78b5ceb9ac4ba0428bde147f24ce1aa90a56f0c646f18c4c7553b699dd0` |
| `verify_correction_delta.py` | `e25671f3fefe115858fb7de05501c0d5543dda57f62d4ec6c52de5c0616517ca` |
| `semantic-closure-cycle-001.json` | `02f71990ef36924e648faabace5eddef3a2c6729738c83b082e3adb2ef689c2f` |
| `semantic-cycle-001-closure.ids` | `1e902d1254709186f20a571cb07c1a80be70ae07eb1dadda3ecec3f6904516aa` |

The closure JSON pins the accepted scope, Russian inventories, exact-preservation manifest, source and Bulgarian glossary, authored checkpoint, all 411 corrected authored files and validation receipts, Yarn metadata, and runtime binding objects. The first-pass file retains all 411 pre-correction reviewed hashes. The correction result records the 60 exact source-to-target replacements and 50 changed batch files. No source, glossary, parser, binding, or stable-ID mapping changed, so the universal full-restart boundary was not triggered.

## Reproduce before review

From the canonical game checkout, run:

```sh
python3 Translations/bg/build_semantic_closure.py verify
python3 Translations/bg/verify_correction_delta.py
```

The first command checks every pinned input and corrected authored/receipt hash, rebuilds every component in canonical accepted source order, and compares each immutable byte stream. The second reverses the 60 accepted replacements in memory and reproduces all 50 pre-correction file hashes: 12 files used compact entry lines and 38 used expanded JSON. The other 361 file hashes are unchanged. Thus the authored delta is exactly those 60 target fields. Stable-ID lists use UTF-8, LF, one ID per line, and a final LF when nonempty. If a hash differs, stop and reconcile the changed input; do not credit the existing closure on new files.

## Exact review set

| Component | IDs | Evidence list |
| --- | ---: | --- |
| Corrected IDs | 60 | `semantic-cycle-001-changed.ids` |
| Edited scene and UI-family context | 432 | `semantic-cycle-001-context.ids` |
| Exact Russian-source repetitions | 421 | `semantic-cycle-001-repetitions.ids` |
| Affected glossary terms, referents, and voice patterns | 280 | `semantic-cycle-001-glossaryReferents.ids` |
| Edited Yarn/UI consumer binding rows | 128 | `semantic-cycle-001-runtimeBindings.ids` |
| Mandatory regression surfaces | 908 | `semantic-cycle-001-mandatoryRegressions.ids` |
| Union, deduplicated | **1,506** | `semantic-cycle-001-closure.ids` |

The closure JSON contains a full Russian/Bulgarian comparison row for each of the 1,506 IDs, its authored path, source key, inferred or recorded node label, and component memberships. `sourceIndex` is the zero-based index in the accepted UI → ChecksDialogs → Dialogs → StaticTMP order. The component lists overlap; add no component counts to obtain the union. Of the 58 edited node labels, 55 occur in the pinned Yarn metadata; three (`NotTrue_Asking_4_2`, `phone_fortuneteller`, `phone_mother_8`) are line-key stems rather than confirmed runtime node names. The first restores a corrected row with empty `nodeNames`; the other two are aliases beside recorded node names. These three are context selectors, not claims about compiled Yarn nodes, and the reviewer should inspect their consumer mapping. Exact repetitions deliberately include all 364 source `Отпустить` choices: the Bulgarian object pronoun depends on the released character, not the repeated source string alone.

The 17 concept selectors include cat food, the Mushroom Country, Guest spirit, corpse disposal, substituted daughter, armpit/body hair, release-choice gender, the sisters' eye dialogue, coarse speaker language, the Doctor's repeated insult, the pale window figure, the Rocker's lens cap/night trip, and the other corrected images and referents. The selector is explicit about source spelling variants and target terms. Generic armpit menu labels and unrelated head-hair descriptions were not pulled into the hair concept set merely because they contain `Подмышки` or `волосы`; the affected inspection lines, self-check and TV sign are included. The full first pass remains evidence for unrelated unchanged lines.

Mandatory regressions comprise all 259 UI units (menus, save/load, locale selection, HUD and titles), all 178 accepted static units (including credits and environment text), the one accepted checks-dialogue unit, all 364 release choices for contextual gender, and 106 dialogue units containing format slots or TMP markup. The full 16,538-unit preserve-exactly check passed after correction; it is structural evidence, not a semantic review of these groups. Bulgarian is LTR; RTL shaping is not an applicable regression. No image-text IDs are added because image/texture translation is outside the owner's scope.

## Independent reviewer instructions

1. Establish reviewer identity and record this handoff and closure SHA before reading. Review **every closure row** against the Russian source, current Bulgarian target, approved glossary and actual scene/character rules. Check the complete replacement, not an excerpt. Use the stored Yarn node and source key to inspect branch choices, speaker/addressee, timing, referents, information reveal, profanity, and natural Bulgarian.
2. Check each mandatory regression group and the applicable dynamic consumer behavior: option order, separators, trimming, format slots, TMP emphasis, and player/item values. The source runtime binding and Yarn metadata hashes are context evidence; the game has not been launched, so rendered layout and runtime behavior remain unverified.
3. Record objective findings by stable ID with source, current full target, reason, and proposed full replacement. Record a clean result only after the whole exact closure and regression catalog have been reviewed on unchanged hashes. Mechanical regeneration of the closure is not independent semantic review.
4. If corrections follow, preserve this cycle intact. The next review set is exactly corrected IDs, plus IDs newly entering the current closure, plus previously reviewed IDs whose evidence the edits explicitly invalidated. Record retired dependencies. If a selector missed a real dependency, repair the selector/recipe and verify a new immutable cycle; do not patch only a generated ID list. Apply the universal restart boundary if source/glossary/mapping/coverage evidence changes or a systemic affected set cannot be bounded.

## Current acceptance boundary

Bulgarian draft coverage and the first semantic source-to-target pass are 16,538/16,538. The 60 corrections were applied and structurally validated. Dependency closure is reproducible. Independent diff review, final deterministic editorial gate, integration/build, and runtime/visual checks remain pending. The owner prohibited game launch for this stage. Do not stage or commit through the shared Git index from this locale chat.
