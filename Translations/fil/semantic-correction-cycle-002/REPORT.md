# Filipino author correction cycle 002

Status: **ready for a distinct delta reviewer; no clean independent or editorial acceptance claimed**.

The final independent review 01 identified 19 objective complete-unit corrections. All 19 were adjudicated against the pinned Russian source, approved Filipino glossary and compiled scene order, then applied to 16 authored dialogue batches. Its five provisional candidates remain withdrawn. Before and after copies of all changed batches, the complete plan, scene evidence and file hashes are preserved in this directory.

The affected 16 batch validators passed. The project's exact-scope readiness command and the complete authored preserve-exact check passed for 16,538/16,538 accepted IDs with zero missing, extra or duplicate IDs. The unchanged option map covers 2,674 owned rows and 2,675 exact-source occurrences; 177 static phrases and credits regenerate exactly. The six reviewed dynamic consumer targets and the 20 supplemental reviewer pairs remain byte-exact to their reviewed source and target pins.

The repaired selector covers father inflections, grandchildren, genuine youth/life-stage forms, ear-wax inflections including `серой`, and interrupted radio `субъ…кт` variants. Its regression examples exclude the `молодец` and `субъективный` homographs. The current closure has 7,645 IDs. Against the prior immutable 7,956-ID closure, 207 are new and 518 are retired. The exact next delta is 286 IDs: 19 corrected, 207 new, and 60 explicitly invalidated previous rows. The 20 supplemental new rows already have applicable independent reads on unchanged hashes, leaving **266 paired IDs for the next distinct reviewer**. Missing and extra closure IDs: zero.

The first cycle 002 compiled snapshot recorded protobuf opcode field numbers in place of opcode values. `compiled-context-erratum.json` preserves that error and pins `compiled-context-corrected.json`. All 17 node names, instruction order, operands, source lines and stable IDs were verified unchanged; use the corrected snapshot for opcode and branch interpretation. This evidence repair did not change authored text or the delta ID sets.

Use `handoff.json` for exact paths, hashes, scope, limits and reviewer instructions. Verify the closure with:

```text
.venv/bin/python Translations/fil/semantic-correction-cycle-002/build_closure.py --verify
```

No game/runtime, font/layout, package, screenshot or release check was run. Three older accepted repeat IDs still lack compiled Yarn keys; the cycle 002 camera/gun repeat at ordinal 15480 is also inventory-only and is linked to the compiled equivalent at 13483. Text draft coverage remains 100%; editorial acceptance remains 0.
