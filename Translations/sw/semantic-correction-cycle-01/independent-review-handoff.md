# Swahili text correction: independent review handoff

Game: *No, I'm not a Human* v1.3.19. Source locale: `ru`. Target locale: `sw`. Scope: text only. The owner excludes translated textures and images and forbids launching the game or using the shared fixture.

## Status

- Draft coverage: **16,538 / 16,538 accepted visible text units (100%)**. This is text coverage, not runtime readiness.
- First complete source-to-target semantic pass: **16,538 / 16,538** reviewed on the pinned draft hashes. It recorded **211 finding groups affecting 267 IDs**. It is the only complete semantic pass; do not repeat it unless a universal restart condition is met.
- Adjudication: all 211 findings accepted against Russian source, approved glossary, and scene context. The correction batch changed **273 IDs**: 267 finding IDs and six additional occurrences of the same authored inspection choice. A post-apply spelling refinement changed the final wording of one of those 273 IDs without increasing the count.
- Deterministic structural gate: **passed** on the final 16,538-unit corpus and all **187** artifacts. Both generated dialogue batches verify against their authored phrase maps. No runtime, renderer, font, visual, or in-game claim is made.
- Independent semantic diff review: **not started**. Mandatory regression semantic review: **pending**. Editorial acceptance: **pending**. Git integration: **pending with the shared coordinator**; this chat did not touch the index.

## Immutable evidence to read

1. `../semantic-review-progress.json` and `../semantic-audit-pass-01/inputs.json`: first-pass coverage, reviewed segment hashes, and pinned source/glossary evidence.
2. `adjudication-0001-0025.json` through `adjudication-0201-0211.json`: each objective finding, decision, old target, and selected full replacement. `correction-batch-preflight.json` has all 273 planned IDs, protected-syntax preflight, and authored-file baselines.
3. `apply-intent.json`, `applied-batch-manifest.json`, `derived-recipe-reconciliation.json`, and `post-apply-refinement.json`: application and recovery trail. The phrase-map repair changed the map's `Погладить` target from `Mpake` to `Mpapase` to reproduce the **already reviewed** three output rows; those three outputs were not semantic changes. The refinement corrected `KULANIWA` to `KULAANIWA` in `sw-sem-0131`.
4. `final-payload-manifest.json` and `final-corpus-validation-v2.json`: exact final artifact, sidecar, authored-map, and corpus hashes. The earlier `final-corpus-validation.json` is the full pass before the one-ID spelling refinement; the affected batch was rerun and every final sidecar reconciled in v2.
5. `dependency-closure-v2.json`, `changed-ids-v2.jsonl`, and `closure-ids-v2.jsonl`: **273 changed IDs** and the **5,211-ID independent review set**, in canonical source order, with source, final target, first-pass target, component tags, and artifact path. JSONL uses UTF-8, LF separators, and a final LF. `closure-verification.json` verifies hashes, order, exact union, and inclusion. `selector-revision-v2.json` records the 851-ID expansion from the preserved first closure; `closure-selector-v2.py` is its locale-owned recipe.
6. `mandatory-regression-catalog-v2.json` and its category lists: UI/menu/HUD/locale/save/input, static TMP/credits/environment, the accepted checks surface, gender/kinship/address, placeholder/markup/linebreak, and mixed-script target text. `runtime-context-v2.json` separately hashes dynamic binding/scene context without counting those fragments as translation units.

## Independent review task

Read each row of `closure-ids-v2.jsonl` against the pinned Russian source, final Swahili target, scene/node context, approved 201-entry glossary, character address rules, and actual consumer topology. Check the mandatory regression category lists and assembled output risks, including branch order, separators, trimming, player/item substitution, exact repetitions, spoilers, and the unchanged sentences inside full replacements. Record reviewer identity, row decisions, objective findings, and exact reviewed hashes. The structural gate is evidence of syntax and coverage only.

If this review produces corrections, keep the current immutable closure. Build the next closure and review exactly corrected IDs plus newly added current dependencies plus previously reviewed IDs whose evidence was explicitly invalidated. Record removed dependencies. Continue until an independent clean pass on unchanged artifact and closure hashes. Do not self-credit the current editor as the independent reviewer.

The owner forbids game launch. Keep runtime, visual, font, packaging, and release statuses separate. Coordinate shared Git index and final integration with the owner-designated coordinator; this locale chat owns only `Translations/sw/` and its assigned locale-specific documentation.
