# Persian text audit cycle 2: independent reviewer handoff

Scope: No, I'm not a Human 1.3.19, Persian text only, 16,538 accepted IDs. The first complete source-to-target pass and cycle-1 evidence remain immutable. Review01 read 1,506 closure units and 544 mandatory regressions and returned four objective findings; its clean independent gate did not pass.

## Inputs and author decisions

- The review01 verdict, findings and evidence index are pinned by SHA-256 in `semantic-review-progress.json`. Before edits, all 31 reviewer evidence files, 27 verdict pins and 419 authored file hashes matched. Source inventory, preserve-exact manifest and approved Persian glossary were unchanged.
- `selector-spec.json` replaces the narrow photo pattern with `фото|фотк|сним(?:ок|к)`. All 231 accepted direct source matches, their 161 named nodes, all same-node accepted rows, and the full relevant `_Photo` node families form the bounded photo context. The 91 reviewer omissions and the 323-unit candidate are strict subsets; the candidate was not treated as a completed read.
- `photo-topology.json` checks 53 photo families, 155 compiled family nodes and 102 internal branch edges against the pinned 3,255-node Yarn program. There are zero accepted photo concept, same-node or family rows missing from the repaired closure. Source matches with no node binding remain direct matches without an invented branch.
- `unbound-photo-binding.json` records 31 accepted direct photo matches with no source `nodeNames` and no matching line-key reference among the pinned compiled Yarn instructions. Their text is covered. Whether another consumer can display them is not established from this evidence; no runtime reachability is claimed. The report SHA-256 is `308b17e93150bcf99a19e8701c7e4520f1f94a6cd28e850f3e9ba36c731587ad`.
- `remedial-read.json` pins the author's complete one-pass read of the 1,195 newly affected accepted source/target units before corrections. This is an author read, not an independent review.
- `correction-plan.json` adjudicates all four reviewer proposals and one additional objective daughter address-form error. Its five full-unit replacements preserve speaker prefixes, facts, agency, participants, timing, reveal order and protected syntax. `preflight.json` records the passed full-unit preflight. No other objective replacement was accepted in the bounded read.

| Finding | Stable ID suffix | Correction |
| --- | --- | --- |
| F01 | `110504456301387782` | Neighbour's established female cousin, not a sibling. |
| F02 | `110504453935800327` | Tough is the photo subject; the player operates the camera. |
| F03 | `tmp:level0:1955:m_text` | Dig-hole action uses approved `حفره`. |
| F04 | `tmp:level0:2195:m_text` | Unlock phone numbers, not calls. |
| A05 | `110504452048363530` | Daughter's informal singular `Покажешь` uses Persian informal singular address. |

The five target values changed in four authored files: dialogue batches 141, 301 and 392, and the static draft. The two static changes were made in `static-phrase-map.json` and regenerated into `static-text-draft.json`; all 177 accepted phrase-map matches were checked. `before/`, `after/`, `file-delta-manifest.json` and `diff-audit.json` preserve exact before/after bytes and confirm exactly five planned target changes with no other authored value or metadata change. Cycle-1 and review01 files were not modified.

## Reproducible closure and next review set

From the canonical checkout, run:

```sh
.venv/bin/python Translations/fa/audit-cycle-002/build-closure.py
.venv/bin/python Translations/fa/audit-cycle-002/verify-photo-topology.py
```

The builder checks all 16,538 current accepted targets against `Source/preserve-exactly-v4.json` and verifies the full prior review evidence, current corrected files, compiled node existence, component sets, exact hashes and canonical source order. `closure.json` SHA-256 is `930ac081e5402688bc782a180bee590151059d118a1c08339b24707785d6a7d1`; `closure-ids.txt` contains 2,701 IDs and has SHA-256 `abbbd58412faa360092b56294b653fd367eaeccb4cd0d2ef1d119664897d907e`. Missing or extra accepted IDs: zero.

The next review formula is **corrected ∪ (current closure − prior independently reviewed closure) ∪ explicitly invalidated prior IDs**. There are 5 corrected units, 1,195 newly selected units and 213 prior reviewed units in the four changed authored files. The union is **1,408 distinct IDs**; 0 prior IDs retired. The 213 are conservatively invalidated by changed authored-file hashes, even where their individual text is unchanged. `next-review-delta.json` SHA-256 is `960338d5974ae5859e71fa12f6343a2ca8ccf9c4f89ae0b13110163448a25bed`; `nextReviewDelta-ids.txt` SHA-256 is `58710f112e6b8d50b8908aeed420ad894da5536dde92a5d4700c90b77b390d12`. Review every full source/target unit in this set with scene and branch context. Previously reviewed per-ID evidence remains usable outside the explicit invalidation set.

## Gates and limits

- Affected validators passed for dialogue batches 141, 301 and 392 and all 178 static fields.
- All 418 current batch structural sidecars match their authored SHA-256 and sum to 16,360 table units; the 178 static units bring the total to 16,538. `structural-sidecar-gate.json` SHA-256 is `5a2303761a3ff3e282bda7a801eb6ce01f699d4a17e61b435c58a2ee4d48099e`.
- The full preserve-exact gate passed 16,538/16,538 current targets for whole-text exact values, placeholders, markup, numeric order, line breaks, trailing whitespace and speaker prefixes. `deterministic-gate.json` SHA-256 is `ee1bfc762b8eb65024ad7ad8a6ece662ce04d46b1ca9de4e1223644aec348f4c`.
- The unchanged 2,841-ID common-option expansion verified from its 34 authored phrases. No other derived expansion depends on the five changed IDs. The 81-role credits recipe stayed unchanged.
- Two context questions remain from cycle 1: the unbound role of `tmp:level1:3842:m_text` and the MushroomEater drink/ordeal wordplay at `110504456997642245`. They are recorded in `closure.json` and the prior context-watchlist adjudication. The 31 accepted photo strings without compiled Yarn line references remain a separate reachability limit, as described above. RTL shaping, game runtime and visual checks were not run under the no-game instruction.

Next action: assign a **distinct** reviewer to reproduce this closure, read the exact 1,408-ID delta and adjudicate the two retained questions. The author's bounded remedial read and deterministic gates do not establish independent clean review or final editorial acceptance. Git integration remains with the root coordinator; no stage, commit, push, publication or deployment occurred here.
