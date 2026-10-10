# Swahili text draft coverage — No, I'm not a Human v1.3.19

Date: 2026-10-09. Source locale: Russian (`ru`). Target locale: Swahili (`sw`). Scope: accepted visible text only; translated images and textures are excluded by the owner.

## Current result

The Swahili authored draft covers **16,538 / 16,538 accepted visible IDs (100.000%)**: 16,100 `Dialogs`, 259 `UI`, one `ChecksDialogs`, and 178 static TMP fields. This is text coverage, not editorial or runtime acceptance.

There are 186 table batches (181 dialogue, four UI, one ChecksDialogs) plus the static draft. Every table batch has a matching SHA-256 validation sidecar with `structuralResult: passed`. The static draft also has a matching passed sidecar. The complete accepted ID set equals the authored ID set, with no missing, extra, or duplicate IDs. The aggregate exact-Russian-source consistency check passes across table collections, and no target adds a speaker prefix where the source has none. The alignment triage covered 16,360 table IDs and found zero extreme length outliers; this is only a mechanical triage.

The current manifest and all batch hashes are in `Translations/sw/checkpoint.json` (SHA-256 `01d08b3ab8ad4954eb2e6e08cd84a7d2d1e3ca008cfbc87c2493492ca8dc0e92`). The last dialogue batch is `dialogue-batch-181.json` (81 IDs; SHA-256 `2a18251566c3bf255a1bf9c71dc835888220f58f3ca0692b8aa732ecce190d81`). Its passed sidecar SHA-256 is `c056b921b0cecbccfb4b63e838b1ea6729eb4d7f60e8e73a44be4276a8c50254`. The static credits role map SHA-256 is `c56c08c0284003b01b67c7c1310d1df3e5374f0558e02759209201bbf808c6ad`.

The accepted source decision is pinned to SHA-256 `a70750766d64d031aa5ff67ac5c0eb6212014768764bbd66f667d1d9e1b971ce`, the string inventory to `ecd96645c2ca6f23f8bf3ab2fcf65709e961478ae15a38e83d94cc335a408bf0`, the static inventory to `3791c851b1c2282b2908ba288830df07110a9d9fcc75d7e86e710e8485024efc`, and the approved Swahili glossary layer to `95fe1a773cf228dfabad22f97b085694a725bf5d3e2d83e0a07f8fda316beeb3`.

## Reconciliation and corrections

The vanished launcher left `dialogue-batch-141.json` and its passed validation sidecar intact. Work resumed at the verified next missing source ID. Batches 142–181 were authored and validated. The initial write attempt for batch 181 failed its local row-count assertion before writing; the second attempt wrote all 81 remaining dialogue IDs and passed validation.

The aggregate audit found two divergent translations of identical Russian source lines. The supplemental `ChecksDialogs` copy and current `Dialogs` copy of Esenin's line now match. The cat action `Погладить` now uses `Mpapase` in its three dialogue choices and UI label. Two player choices in `dialogue-batch-110.json` had acquired an incorrect `Provocateur:` prefix; it was removed. A contextual reread also clarified the wheelchair character's stolen clutch (`klachi`) and restored the agency of the proverb about making offended people carry wheelchairs. All changed batches were revalidated, and the manifest was refreshed after the final edits.

## Acceptance boundaries and next work

The full source-to-target semantic audit, reproducible correction closure, and independent dependency-aware diff audit required by the universal editorial protocol remain pending. Mechanical checks and contextual spot corrections do not establish those gates. The source has a few difficult or malformed poetic lines, including dialogue source rows 13312 and 15957, that need explicit semantic review. The independent reviewer is not assigned in this locale chat.

Swahili font/layout feasibility, build/package integration, and in-game behavior remain unverified. The owner explicitly prohibited a game launch during this assignment. Runtime reachability of the accepted source set remains conditional under the shared source decision. The shared locale state still says probe/zero and must be updated by the integration coordinator after reviewing this draft. No shared files, Git index, commits, game fixture, saves, or other locales were changed here.
