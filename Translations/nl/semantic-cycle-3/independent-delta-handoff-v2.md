# Dutch independent delta review, cycle 3

Game: No, I'm not a Human 1.3.19. Source `ru`; target `nl`. The text-only draft remains 16,538/16,538 accepted units. The first complete semantic pass remains preserved and is not being restarted. The owner excluded translated images and textures. Runtime and editorial acceptance remain pending.

## Immutable input and correction evidence

- Previous closure: `Translations/nl/semantic-cycle-2/closure/closure-manifest.json` SHA-256 `2065cdbc8c29ec50f15c5c3d31fb0126c54a8294d30a6374b11f00a392b325e7`; previous independent delta had 367 individually reviewed pairs.
- Independent review 02 evidence: `Translations/nl/independent-review-02/evidence-manifest.json` SHA-256 `f576e89933d20f1a9a2b6b3792c9894383f3ea02f415f5d57db97dcbc6df5ad3`; individual decisions SHA-256 `23f203aa3f12e7169e30dc2fe57ca125ed4c0207595ac2c49d154069fcaaab3b`. Review verdict required 40 corrections; it was not clean.
- Source, inventory, preserve-exact, and approved Dutch glossary pins are repeated in the cycle-3 closure manifest and checked against current files before correction. The compiled binding is `Source/glossary-corpus-v2/runtime-bindings.json` SHA-256 `dc3c46bbf7c327826d70b559ac0c0d924c33848ea5e6f4629b92507e6daae56c`.
- Full-unit adjudication: `Translations/nl/semantic-cycle-3/adjudicated-corrections-v3.json` SHA-256 `82204c3b9b111dcb0da1b92bc626606edf0d9e155c63aef9e51624a4ff3f606f`; protected-value and assembled-label preflight SHA-256 `e5c75f796f18fcdf618e02b4024cb416f480430f65fb66182f92163e183a04c4`. The initial preflight and adjudication are retained as superseded immutable evidence; the second version refines added residence assumptions in three full units. A third version corrects five singular phrases exposed by plural assembled-label examples; the initial correction, validation, and closure remain intact as superseded evidence.
- Exact before/after row evidence: `before-rows.jsonl` SHA-256 `1b4113cf39f4cc5d3811ece7d93594bd6ac7894e67be85b5ba54e46db6cc4bcb`; final `after-rows-v3.jsonl` SHA-256 `c161754554038b408090e192a2112e9e1b5d502ac447bf2a6a29898534090b20`.

All 40 findings were adjudicated against full Russian units, unchanged glossary, and pinned scene/consumer context. Thirty-one review proposals were accepted exactly and nine were refined to preserve source facts, question force, or natural Dutch. Thirty-nine corrections concern article-free `GetCharacterOnPlace` labels; one restores the Fatman bribe's purpose instead of treating it as a shooting tool. The two accepted inventory keys absent from the compiled program remain reachability-unverified. Substitution illustrations establish grammar only, not admissibility of every sample label in every scene.

## Cycle-3 review set

The final immutable closure manifest is `Translations/nl/semantic-cycle-3/closure-v2/closure-manifest.json` SHA-256 `f3e3c19f26fceb374478d678dbf7860496d82f962627f37225dbccc296564cd4`. Its recipe is `Translations/nl/semantic-cycle-3/build-closure-v2.py`; all component files and hashes are in the manifest.

| Set | IDs |
| --- | ---: |
| Current closure | 764 |
| Corrected IDs | 40 |
| New dependencies | 0 |
| Explicitly invalidated prior evidence | 0 |
| Exact next review delta | **40** |
| Retired dependencies, preserved as history | 157 |

`closure-v2/delta-ids.txt` is exactly corrected IDs ∪ new dependencies ∪ explicitly invalidated IDs, in canonical source order. `closure-v2/delta-review-rows.jsonl` SHA-256 `bba2030eccdd3ac973c4e503db08db9fff82dfee1dbdaf100c1f69c3ea679d99` supplies the 40 full Russian and current Dutch pairs. The first delta ID is the first line of `delta-ids.txt`; read all 40 with scene and assembled consumer context, then record individual decisions and objective findings or a clean unchanged-hash result. Reuse unchanged prior review evidence only while all pins and authored hashes still match.

The bounded selector still includes all 58 occupant-label consumers plus all 57 UI `characterName_` labels; the one Jacket gift-item slot is excluded. All 39 review-02 label findings were already in that bounded selector, so no missing dependency was verified. No prior runtime-binding or glossary-referent ID was retired. The 157 retired IDs are recorded in `closure-v2/retired-dependencies-ids.txt`; they are not part of the next delta.

## Validation and boundaries

- 40 corrections applied to 38 authored batches; each changed batch passed structural validation. Prior batch bytes were reconstructed exactly to exclude collateral changes.
- Static draft rebuilt from the Dutch map and credits role map: 178 rows, 108 credits role matches, byte-identical SHA-256 `93c8c82cfd1800e95427f966826534968e1913accbb2b0a6937893157d6bd9f6`. No static map, credits source, or expansion depends on the changed dialogue IDs.
- Full 16,538-unit preserve-exact result: `Translations/nl/semantic-cycle-3/preserve-exact-v4-after-v2.json` SHA-256 `cad3c4d2f29b3f0361b8dd0979bfd2390711d0157a8bf4ea7df12a5546ecdf8b`. Structural report SHA-256 `35a2589f50f8ebea4a3759fd3e015f8758e51025989bddb6cc4fe4969370ca51`.
- No game launch, fixture use, texture/image work, Git index work, shared state edit, independent clean review, or editorial acceptance occurred in this cycle.

The five post-application refinements have separate exact before/after records: `postapply-refinement-before-rows.jsonl` SHA-256 `3f97d87e3752e41147f9b121152fc32aa8967d3002ef1969ea76ce549ae7b94a` and `postapply-refinement-after-rows.jsonl` SHA-256 `eecb3f58b61a814881c48a55fff0716dc7e59d785b2056126be9b83b94f78c70`. The first cycle-3 closure is retained, but the reviewer must use `closure-v2` and its current authored hashes.
