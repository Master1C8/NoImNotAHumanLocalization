# Persian text audit cycle 1: distinct reviewer handoff

Game: No, I'm not a Human v1.3.19. Locale: `fa`. Source: pinned Russian (`ru`). Scope: 16,538 accepted visible text IDs; images and textures are excluded by the owner.

## Evidence and reproduction

- The immutable [first-pass snapshot](first-pass.snapshot.json) is SHA-256 `f7d47eebe60a8a8d26a039d29b21b49ce7926b00bad2213a8655e6d3db6da7bd`. Its 447 segment receipts cover all 16,538 accepted IDs and pin the pre-correction authored files.
- The [correction plan](correction-plan.json) records 76 adjudicated full-unit replacements. Its SHA-256 is `cf6e8374e025b0e8afc897a5b5ae29b0cada3b2e0d516bd2fa54b3ad4705d3ec`. The [preflight](preflight.json) checks protected syntax, exact repetitions, and representative assembled `{0}` resident values.
- The [file delta manifest](file-delta-manifest.json) pins exact before/after hashes for 56 authored batches. Its SHA-256 is `adead6c5286cba75e9495eb3533d7b3a03f2994266fdada9df297cb83067290d`; matching complete file copies are in `before/` and `after/`.
- Run `.venv/bin/python Translations/fa/audit-cycle-001/build-audit-closure.py` from the canonical game checkout. It refuses changed immutable outputs. The [selector](selector-spec.json) and [closure](closure.json) enumerate 1,506 IDs in canonical accepted-ID order. `closure-ids.txt` SHA-256 is `277e88123dc3f02e6cd1d90c4bcaa2353157fe0933da72ce25eb68704a4d4912`; `closure.json` SHA-256 is `9dc68ec942a7ae9a0f12326bf64b78673942b93fa5777f902584668644c1f8e4`.
- Components in `closure.json`: changed 76, scene/context 440, exact repetition 79, glossary/referent 201, runtime binding 504, mandatory regression 544, first-pass context watchlist 4. Their union is 1,506. Every component ID belongs to the accepted manifest; there are zero unexplained missing or extra IDs relative to the selector specification. Two provisional selector attempts and their hashes remain in `selector-attempt-001/` and `selector-attempt-002/`; the final selector repairs the verified photo-variant and watchlist omissions.
- The [deterministic gate](deterministic-gate.json) SHA-256 is `6add4a6ff767e4428fca46fec1ce78aeb8b00c63cd9ec37c6fd6be839de6d394`: 418 current batch sidecars, all 178 static rows, all 16,538 preserve-exact values, and the 2,841-row common-option expansion passed. Static credits still regenerate exactly from the unchanged role map. The static phrase map and other authored recipes were unaffected by these 76 edits and their outputs were checked.

## Review task

Read each `reviewRows` source/target pair in `closure.json` with the named scene, relevant glossary entry, and branch context. Check all changed facts, agency, participant count, time, information reveal, profanity, wordplay, and protected syntax. Include the mandatory regression component and the assembled dynamic lines in `preflight.json`. Confirm selector completeness against source variants and actual consumer topology. If a dependency is missing, repair the selector and preserve the superseded closure as another immutable attempt before issuing a new one.

The [context watchlist](context-watchlist-adjudication.json) closes the coffee interpretation without a change and preserves the radio-noise semantic function while leaving visual RTL layout untested. The exact static screen role of `tmp:level1:3842:m_text` (`Экстрасенсы`) and the literal/figurative `MushroomEater_Entrance_3_6` drinking pun remain unresolved for the reviewer. Runtime resident-value enumeration is unavailable from the serialized Yarn line table; the two changed `{0}` lines have representative assembled checks, not runtime proof.

No independent review or editorial acceptance is recorded. The game has not been launched. Do not infer runtime, visual, font, image, package, or publication readiness from this text audit.
