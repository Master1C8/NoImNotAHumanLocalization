# Dutch independent delta review, cycle 3

Game: No, I'm not a Human 1.3.19. Source `ru`; target `nl`. The text-only draft remains 16,538/16,538 accepted units. The first complete semantic pass remains preserved and is not being restarted. The owner excluded translated images and textures. Runtime and editorial acceptance remain pending.

## Immutable input and correction evidence

- Previous closure: `Translations/nl/semantic-cycle-2/closure/closure-manifest.json` SHA-256 `2065cdbc8c29ec50f15c5c3d31fb0126c54a8294d30a6374b11f00a392b325e7`; previous independent delta had 367 individually reviewed pairs.
- Independent review 02 evidence: `Translations/nl/independent-review-02/evidence-manifest.json` SHA-256 `f576e89933d20f1a9a2b6b3792c9894383f3ea02f415f5d57db97dcbc6df5ad3`; individual decisions SHA-256 `23f203aa3f12e7169e30dc2fe57ca125ed4c0207595ac2c49d154069fcaaab3b`. Review verdict required 40 corrections; it was not clean.
- Source, inventory, preserve-exact, and approved Dutch glossary pins are repeated in the cycle-3 closure manifest and checked against current files before correction. The compiled binding is `Source/glossary-corpus-v2/runtime-bindings.json` SHA-256 `dc3c46bbf7c327826d70b559ac0c0d924c33848ea5e6f4629b92507e6daae56c`.
- Full-unit adjudication: `Translations/nl/semantic-cycle-3/adjudicated-corrections-v2.json` SHA-256 `b934f9694126670128b45b2dc613ae9453409d2e53d40916cf0e61e25f4034f4`; protected-value and assembled-label preflight SHA-256 `5448ce24a9135e3dc8012a8379c8de66242a4e557e8115305a5c80e457e5df5a`. The initial preflight and adjudication are retained as superseded immutable evidence; the second version refines added residence assumptions in three full units.
- Exact before/after row evidence: `before-rows.jsonl` SHA-256 `1b4113cf39f4cc5d3811ece7d93594bd6ac7894e67be85b5ba54e46db6cc4bcb`; `after-rows.jsonl` SHA-256 `d788d81d6ded1151f51d9d42037a6cb7bbe68d2c33c218327844134d1464268c`.

All 40 findings were adjudicated against full Russian units, unchanged glossary, and pinned scene/consumer context. Thirty-one review proposals were accepted exactly and nine were refined to preserve source facts, question force, or natural Dutch. Thirty-nine corrections concern article-free `GetCharacterOnPlace` labels; one restores the Fatman bribe's purpose instead of treating it as a shooting tool. The two accepted inventory keys absent from the compiled program remain reachability-unverified. Substitution illustrations establish grammar only, not admissibility of every sample label in every scene.

## Cycle-3 review set

The immutable closure manifest is `Translations/nl/semantic-cycle-3/closure/closure-manifest.json` SHA-256 `1f509ca31050aa30d9eabce0029c439b140ad5be2f95e5d4c5071273aae53b19`. Its recipe is `Translations/nl/semantic-cycle-3/build-closure.py`; all component files and hashes are in the manifest.

| Set | IDs |
| --- | ---: |
| Current closure | 764 |
| Corrected IDs | 40 |
| New dependencies | 0 |
| Explicitly invalidated prior evidence | 0 |
| Exact next review delta | **40** |
| Retired dependencies, preserved as history | 157 |

`delta-ids.txt` is exactly corrected IDs ∪ new dependencies ∪ explicitly invalidated IDs, in canonical source order. `delta-review-rows.jsonl` SHA-256 `42c89762e930cda005bf429679947198da027cebdecaf75b4bdf07d996ec5a60` supplies the 40 full Russian and current Dutch pairs. The first delta ID is the first line of `delta-ids.txt`; read all 40 with scene and assembled consumer context, then record individual decisions and objective findings or a clean unchanged-hash result. Reuse unchanged prior review evidence only while all pins and authored hashes still match.

The bounded selector still includes all 58 occupant-label consumers plus all 57 UI `characterName_` labels; the one Jacket gift-item slot is excluded. All 39 review-02 label findings were already in that bounded selector, so no missing dependency was verified. No prior runtime-binding or glossary-referent ID was retired. The 157 retired IDs are recorded in `retired-dependencies-ids.txt`; they are not part of the next delta.

## Validation and boundaries

- 40 corrections applied to 38 authored batches; each changed batch passed structural validation. Prior batch bytes were reconstructed exactly to exclude collateral changes.
- Static draft rebuilt from the Dutch map and credits role map: 178 rows, 108 credits role matches, byte-identical SHA-256 `93c8c82cfd1800e95427f966826534968e1913accbb2b0a6937893157d6bd9f6`. No static map, credits source, or expansion depends on the changed dialogue IDs.
- Full 16,538-unit preserve-exact result: `Translations/nl/semantic-cycle-3/preserve-exact-v4-after.json` SHA-256 `90870b63b927b087b47f9edc01c95bee2a27861540f64279f3122016a714b955`. Structural report SHA-256 `3135faf10990620bc168ee431ca5e7194c776bc3badd74fa52a8b765ef07c237`.
- No game launch, fixture use, texture/image work, Git index work, shared state edit, independent clean review, or editorial acceptance occurred in this cycle.
