# Isolated text delivery, game 1.3.19

Root is the only Git coordinator. Locale authors own wording and immutable
review evidence. Every preview contains exactly one added locale; the 178
static fields have no proven runtime language switch. Images and textures are
excluded. Runtime, installation, font rendering and layout remain untested.

## Acceptance input

After a complete first semantic pass, a clean independent dependency delta,
verified mandatory regression decisions and reproducible derived text, a locale
hands off `Translations/<locale>/final-gate/root-handoff.json`. The coordinator
reviews the actual chain, full-unit decisions, final hashes and limits.
`Scripts/accept_locale_text.py` binds this editorial decision to all current
authored inputs and final evidence; the script itself is not a semantic review.

The Dutch adapter receipt is `Translations/nl/root-acceptance-v1/root-handoff.json`.
It reconciles the single administrative progress-document change with the exact
archived reviewed preimage. All translation/source/glossary/closure inputs and
40 fresh decisions remain unchanged; the mandatory union is 40 fresh plus 529
exact applicable prior decisions. Serbian has an independently replayed final
gate; its package is still pending.

## Shared commands

Use the canonical checkout's `.venv/bin/python` and new output paths. Existing
reports, failed attempts and partial output directories are immutable evidence.

```sh
.venv/bin/python Scripts/validate_locale_corpus.py nl --output outputs/nl-full-structural-new.json
.venv/bin/python Scripts/accept_locale_text.py --handoff Translations/nl/root-acceptance-v1/root-handoff.json --output Documentation/nl-semantic-acceptance-new.json
.venv/bin/python Scripts/build_locale_probe.py --codes nl --output outputs/nl-native-base-new
.venv/bin/python Scripts/build_locale_text.py nl --base outputs/nl-native-base-new --output outputs/nl-text-new --acceptance Documentation/nl-semantic-acceptance-new.json --exact Translations/nl/final-gate/preserve-exact-v4.json
.venv/bin/python Scripts/verify_locale_text.py --build outputs/nl-text-new
.venv/bin/python Scripts/package_locale_text.py assemble --base outputs/nl-native-base-new --text-build outputs/nl-text-new --output outputs/nl-package-new
.venv/bin/python Scripts/package_locale_text.py verify --package outputs/nl-package-new
.venv/bin/python Scripts/package_locale_text.py archive --package outputs/nl-package-new --destination dist/NoImNotAHuman-nl-preview-new.zip
```

The corpus validator fresh-checks the original batch/static structural guards,
metadata, accepted ID coverage/order, exact grammar/nesting and credits derivation
with one source parse. It writes a new receipt and preserves historical sidecars.
Its scope is structural safety; locale-specific derived recipes and editorial
evidence remain separate. Running one old CLI per batch repeatedly parses the
27 MB source and caused observed contention during parallel final checks. Do
not start additional validator pools; reconcile exact owned jobs before changing
their execution strategy or stopping redundant local processes.

## Verified boundaries

`Documentation/locale-delivery-proof-v1/` preserves the initial delivery evidence:

- The generalized Thai mode matches all ten pinned Thai text payloads byte for
  byte. The original Thai ZIP SHA-256 remains
  `300a409c6e0f6eae576bda12b20cb40e81f52d3998988ad23aa3f7d242cef24a`.
- Real incomplete-corpus and incomplete/stale receipt cases fail at the intended
  boundary, with a matching positive acceptance control. Rejected builds create
  no overlay/package output. The repeatable recipe is
  `Scripts/check_locale_build_gates.py`; its corpus fixture replaces only the
  input directory, retaining real source/glossary/parser/contracts.
- Dutch overlay read-back compares 16,360 table values, 178 static values and
  165 `originalText` values. It also compares 12,749 unchanged objects and every
  other field of the 181 selected objects, and regenerates the catalog update.
- Native read-back compares original raw objects or exact permitted additions,
  Russian clone templates, one locale/key, original catalog location prefixes
  and three font-role dictionaries. These font mappings are technical bindings;
  glyph coverage, metrics, bidi/shaping and actual rendering are unverified.
- The composed package has 31 data artifacts. Its delivered text is reopened;
  all artifact hashes and all 33 ZIP members, including receipts, are compared.
  `dist/NoImNotAHuman-nl-preview-v1.zip` is an offline preview without an installer.

Builds write only new canonical `outputs/` directories. Failed builds preserve
partial evidence. Assembly is per-file copying into a new directory, not a
multi-file transaction. Archive output remains `.partial` until ZIP read-back
passes and is then renamed; writing the separate archive receipt is a later
operation. No original game/saves, installation, publication or deployment are
part of these commands. Source and artifact pins are rechecked before acceptance
and at package read-back; a missing source mount is an environment prerequisite.
