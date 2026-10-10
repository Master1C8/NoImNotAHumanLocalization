# Bulgarian independent correction-closure review 01

Reviewer: `/root/bg_independent_review_01`, separately assigned without inherited history. Game: *No, I'm not a Human* v1.3.19; Russian → Bulgarian; text only.

**Verdict: review completed with findings; the current version is not clean.** All 1,506 closure pairs and all 908 mandatory regression IDs were read on unchanged inputs. A bounded selector follow-up read 50 additional source/target pairs outside the closure. This is not another full 16,538-unit audit.

The pinned closure SHA-256 remains `02f71990ef36924e648faabace5eddef3a2c6729738c83b082e3adb2ef689c2f`. The exact read-ID stream equals the canonical closure stream, SHA-256 `1e902d1254709186f20a571cb07c1a80be70ae07eb1dadda3ecec3f6904516aa`. Initial and final closure verification passed, and the reverse-delta verifier reproduced exactly 60 target-field edits across 50 files, with 361 files unchanged. The approved local Bulgarian glossary is byte-identical to the pinned artifact.

## Findings

`findings.json` contains 32 full-unit proposals within the closure: 11 meaning, grammar or terminology findings and 21 instances of erased coarse register. The first group includes:

| Closure index | Surface | Finding |
| --- | --- | --- |
| 389, 444 | Pale figure window descriptions | “Does not fit” becomes specifically “too tight” |
| 669, 674 | Ex-con's fourth conversation | Current employment inability becomes past; thought during first imprisonment becomes after it |
| 940 | `Nun_Ears` release option | Masculine `го` for the female nun |
| 1071 | `Scammer_Ears` | `Гостевой` spirit conflated with a Guest creature |
| 1302 | `Anger_Photo` | Permission to take a photograph becomes permission to fire a gun |
| 1342 | Static unlock-cat action | Does not retain the glossary's explicit `котарак` designation |
| 1366 | Static wishlist fallback | Noun `желания` truncated to `желани` |
| 1419 | Static Notepad text | Proper name `CRITICAL REFLEX` translated as an ordinary phrase |
| 1493 | Static beer narrative | Masculine object pronoun for the feminine named drink `Бира` |

All 364 release choices were checked against their actual character glossary entries; 363 are correct and one is wrong. The husband from the couple is distinguished from his wife, and the female teenager is distinguished from a grammatically masculine source label.

`selector-finding.json` records a dependency omission in `vulgarCharacterVoice`. Its existing five-speaker rule misses `пизд-`, initial `ёб-`, prefixed forms, and `хуя/хуй` inflections. `additional-voice-candidates-v2.json` and `supplementary-read.ids` reproduce 50 additional read pairs. `supplementary-findings.json` contains 19 further full-unit proposals. The initial broader candidate selector is retained with its false-positive and truncation limitation clearly marked; it is not credited as semantic coverage.

There are **51 full-unit proposals in total**, plus the selector finding. None were applied. The 50 supplementary IDs are an evidenced lower bound for omitted dependencies, not a claim that this regex exhausts every profanity spelling or speaker. Repair the canonical selector/specification and regenerate the next immutable cycle; do not patch a generated ID list.

## Context and limitations

`compiled-context.json` and `compiled-nodes.json` preserve raw wire-decoded evidence from the pinned compiled Yarn program. Of 1,068 dialogue rows in the closure, 1,036 have current compiled uses and 32 are accepted supplemental table rows without a current compiled consumer. Their wording and retained key/speaker context were read; current runtime reachability is not invented.

`managed-context.json` records static IL inspection of the exact source `Assembly-CSharp.dll` and `YarnSpinner.Unity.dll`, on their pinned hashes. The review inspected option order, conditional branches, service-prefix removal, substitution expansion before markup parsing, separate occupant names, and the selected-consumable name/narrative consumer. Flattened source-table neighbors were not assumed to form sentences.

The review does not establish physical rendering, final wrapping, runtime behavior, installation, integration or build readiness. No game was launched, and no source, authored translations, glossaries, shared scripts/state, other locales, fixtures, images/textures or Git index were modified. New evidence is confined to this directory.

## Next action and telemetry

Adjudicate the consolidated proposals, apply accepted corrections together through the owning workflow, repair the selector, and generate the next immutable closure. Review the exact correction/new-dependency/invalidated-evidence delta and mandatory regressions. Clean independent acceptance and the final deterministic editorial gate remain pending.

Available reviewer identity: Codex GPT-6 family; exact backend and reasoning level are not exposed. Input, cached input, output, reasoning and total token counters are unavailable to this reviewer and remain **unknown**, not zero. Failed inspection attempts are included in that unmeasured usage. No descendant agents were launched. Parent coordination/accounting is separate and is not measured by this report.
