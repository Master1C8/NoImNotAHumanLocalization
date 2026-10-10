# Greek correction cycle 1: distinct-reviewer handoff

Scope: No, I'm not a Human v1.3.19, Russian source to Greek text only. Images and textures are excluded by the owner. This handoff is **not** an independent review or editorial acceptance.

## Pinned state

- Canonical accepted inventory: 16,538 IDs. Russian table SHA-256 `ecd96645c2ca6f23f8bf3ab2fcf65709e961478ae15a38e83d94cc335a408bf0`; supplemental static SHA-256 `3791c851b1c2282b2908ba288830df07110a9d9fcc75d7e86e710e8485024efc`.
- Approved Greek glossary snapshot SHA-256 `8bae2efffa702fcac1be38f7149d1e74393aa84a858d8f7d2ee4c052ee11d4e5`. Original Russian localization bundle, shared localization bundle, level1 scene and compiled assembly still match their source pins.
- First semantic pass: 16,538/16,538 manually compared on the former authored hashes. Its immutable `semantic-review-progress.json` SHA-256 is `3a816a9691c71b5ba4ed0dd63046ea99113f7e5871709ff99786a5f8bed7b630`. The first-pass reviewed-file hashes describe the **before** state and must not be mistaken for current authored hashes.
- `correction-cycle-001-adjudication.json` records the 37 accepted objective findings, three resolved context questions, all 40 full before/after replacements, scene reasons and protected-syntax preflight. SHA-256 `128e186c396b43b219e62a6ff38b1b196e44fb7974cdd319bd774c056c5fad33`.
- `correction-cycle-001-applied.json` pins all 59 changed authored and generated files. SHA-256 `a6de5089f3519093a698d506999992082a002b98561aacbe41f44eff5bd51bf1`.
- `correction-cycle-001-dynamic-consumer-evidence.json` pins serialized/compiled evidence and assembled x1/x2 Greek examples for the two item-hint messages and the language autonym. SHA-256 `9cba8c24ca580e3fcf4afa1dcf3d1a84722e6f1d99004be04f987da97523edde`.

## Exact review set

Run `python3 Translations/el/build_correction_closure.py verify` from the canonical checkout before review. The immutable `correction-cycle-001-closure-manifest.json` SHA-256 is `f9c53c076d45f1a163ea189e90df0106e5840ffed1969052562fc69428be49d2`.

The ordered closure contains **1,816 accepted IDs**, with zero unexplained missing or extra IDs. Its component lists are separately hashed in the manifest: 40 changed, 301 context, 42 exact repetitions, 364 glossary/referent, 14 runtime binding and 1,269 mandatory regression IDs. Components overlap. Read `correction-cycle-001-closure-review.jsonl` in canonical ID order with the source, first-pass target, current target and component labels. The two compiled/serialized consumer facts are kept separately as nontranslatable context; they do not inflate accepted-ID coverage.

The selector specification and generator are in `correction-cycle-001-selectors.json` and `build_correction_closure.py`. The specification records two prepublication selector repairs: the actual x1 static hint ID and the compiled `consumable_<item>_name` lookup omitted by an initial fridge-only selector. Rebuild a new immutable cycle if a reviewer finds a further missing dependency; do not hand-append an ID to the closure.

## Gates and next action

All 26 changed ordered maps reproduce their generated dialogue batches. The repeated-dialogue expansion and static credits draft also reproduce unchanged. All 33 affected batch validators passed. `correction-cycle-001-full-structural.validation.json` pins the full 419-batch structural gate, all 16,538 unique accepted IDs and the full preserve-exact pass; SHA-256 `beaf047e5fe5f4a237aa7cbf6aeff292f591e8d3d2c71ceaabe3b3a6e7bd0166`.

A **different reviewer** must audit this closure against the pinned Russian source, approved glossary, scene/branch context and assembled dynamic output, then record findings and the mandatory regression result. Any correction starts the universal dependency-aware delta cycle. No self-reread or deterministic gate here counts as independent review or final editorial acceptance.

Remaining runtime question: the compiled consumer inserts a fixed dictionary-form item name for any integer count. The new Greek action labels are count-invariant, but actual layout and item-name naturalness across all counts remain untested. The game was not launched. Runtime readiness remains separate.
