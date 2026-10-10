# Dutch text semantic cycle 1: independent review handoff

Game: No, I'm not a Human v1.3.19. Source: Russian. Target: Dutch. Text only; images and textures are outside the owner-approved scope.

First semantic pass: 16,538/16,538 on the immutable pre-correction authored hashes in `Translations/nl/semantic-review-progress.json` (SHA-256 `f966dbec76255902cc3518c2e82b9fa89e9e90236092ec6421e3e1c082e790ea`). All 138 objective findings were adjudicated and corrected as one preflighted batch. The original reviewed hashes intentionally differ from the current authored hashes.

Use `Translations/nl/semantic-cycle-1/closure-v2/closure-manifest.json` (SHA-256 `4126276fde69a4b581c1ee883618b51b42c0b49558e757a4cd7ddaef1f0a223d`) as the current closure. The earlier `semantic-cycle-1/closure-manifest.json` is an immutable overbroad selector candidate and is superseded by closure-v2.

## Pinned evidence

| Purpose | Path | SHA-256 |
| --- | --- | --- |
| Adjudication | `Translations/nl/semantic-cycle-1/adjudicated-corrections.json` | `41f7a58defaf6747b5076e1f298264df42e17a2333aedc1001656f42d3e3be52` |
| Complete-batch preflight | `Translations/nl/semantic-cycle-1/complete-batch-preflight.json` | `cb02526d1c970376101829ec3c26bbf2b1a7fc17c5ef11f3cf30de86e644e3fe` |
| Before rows | `Translations/nl/semantic-cycle-1/before-rows.jsonl` | `d87a002c7ca45073a8c20fd4b330ecb1e972832a58ffdb25f94635a11a3dff9a` |
| After rows | `Translations/nl/semantic-cycle-1/after-rows.jsonl` | `8afffba3b4ed884c6e73a6a701ce2f0075e4579b4af34e9aeb2fb81d09118aa0` |
| Changed/full structural validation | `Translations/nl/semantic-cycle-1/structural-validation.json` | `845ebc577b532d4c4a0e72f608d1de16788543aa3598520174f5bc158586b1db` |
| Full exact-text report | `Translations/nl/semantic-cycle-1/preserve-exact-v4-after.json` | `a55f17dd4e980903eb57ad51ab1baf587de1aaa811c0ef8c68bdb123ce9dc126` |
| Closure manifest | `Translations/nl/semantic-cycle-1/closure-v2/closure-manifest.json` | `4126276fde69a4b581c1ee883618b51b42c0b49558e757a4cd7ddaef1f0a223d` |
| Closure review rows | `Translations/nl/semantic-cycle-1/closure-v2/closure-review-rows.jsonl` | `df5d60a54c82739b58922497d52084db31bc76bf5abc66d5207ff0f213402ec7` |
| Selector groups | `Translations/nl/semantic-cycle-1/closure-v2/selector-groups.json` | `51576ee3c2ec85c683ac25d6973be90aa8f1372ffe71da8b6c5785e66745fa9f` |

The closure uses UTF-8 LF with exactly one stable ID per line. Review rows are JSONL in the same canonical order as `Source/preserve-exactly-v4.json`.

## Component lists

| Component | Count | Path | SHA-256 |
| --- | ---: | --- | --- |
| changed | 138 | `Translations/nl/semantic-cycle-1/closure-v2/changed-ids.txt` | `93a8d8b323f7faf497e8034ab3fda4f6d95f42d16d36898e41b5109e21fd29eb` |
| context | 820 | `Translations/nl/semantic-cycle-1/closure-v2/context-ids.txt` | `c738b6cf6de6733cb96f826e731d09f03a23f0b400600f15af4d4fa6e574500a` |
| repetitions | 138 | `Translations/nl/semantic-cycle-1/closure-v2/repetitions-ids.txt` | `93a8d8b323f7faf497e8034ab3fda4f6d95f42d16d36898e41b5109e21fd29eb` |
| glossary-referents | 256 | `Translations/nl/semantic-cycle-1/closure-v2/glossary-referents-ids.txt` | `bf341f3439f2f93c6147610c05e8e42f7e27bd55554c91b8389e1802ccb454c3` |
| runtime-bindings | 21 | `Translations/nl/semantic-cycle-1/closure-v2/runtime-bindings-ids.txt` | `997e8d0717ed06a503b118bc68c1f75459c2aad8990638001840822cabcb7963` |
| mandatory-regressions | 727 | `Translations/nl/semantic-cycle-1/closure-v2/mandatory-regressions-ids.txt` | `bb5e6c0ea02d6da8a4ef2925a455222afadf78a9fb9a21bb70308abf4e08dcaf` |
| closure | 1440 | `Translations/nl/semantic-cycle-1/closure-v2/closure-ids.txt` | `f3004091734943c912e3f0081881e112ade1b5c0b25d5ff03fe1863c9c579292` |

## Reviewer task

1. Verify the hashes in the closure manifest, source/glossary pins, current authored hashes, and the 1,440 review rows.
2. Independently compare every closure source/target pair in its scene and consumer context. Check the `context`, `repetitions`, `glossary-referents`, `runtime-bindings`, and `mandatory-regressions` component lists. For dynamically inserted occupants, inspect the `{0}` consumer at changed findings 46, 51, and 78; check player choices and branch order at findings 44, 53, and 66–69. Inventory order is not proof of compiled Yarn execution order.
3. Record objective findings with stable IDs, evidence and full-unit replacements, or a clean decision on unchanged artifact and closure hashes. If corrections are needed, use the universal delta algorithm: corrected IDs plus new closure IDs plus previously reviewed IDs whose evidence was explicitly invalidated. Keep the prior closure and record retired dependencies.
4. Do not mark independent review or editorial acceptance complete without an identifiable independent reviewer and a clean final deterministic gate. Runtime, visual, font, package and integration readiness remain separate.

The complete pass did not restart: source content, inventory, glossary, stable-ID mapping and reviewed evidence remain pinned. All current changes are local Dutch text inputs and locale-owned evidence; there was no game launch, Git staging, commit, image or texture work.
