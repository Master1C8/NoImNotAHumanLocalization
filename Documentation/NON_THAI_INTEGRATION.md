# Non-Thai text integration, game 1.3.19

This is the shared technical handoff for `id, cs, hu, nl, fa, ro, hi, fil,
el, bg, sr, sw, he`. Locale chats own authored wording and their own files under
`Translations/<locale>/`. This checkout's `main` branch and Git index have one
integration coordinator. The Thai-only preview and its goal remain separate.

## Pinned source and readiness

`Documentation/text-source-acceptance-v1.json` accepts 16,538 text units per
locale: 259 `UI`, 16,100 `Dialogs`, one specific `ChecksDialogs` ID, and 178
unbound static TMP fields. Its source hashes bind
`Source/localization-inventory-v3/{strings,static-text}.jsonl`. Images and
textures are outside this delivery. The remaining runtime reachability questions
in that acceptance record remain open.

Run `python3 Scripts/report_locale_readiness.py --compact` for a current,
read-only snapshot. Its JSON mode pins every parsed draft file by SHA-256 and
reports authored and currently validated IDs separately. The percentage is
`unique in-scope authored IDs / 16,538`. It is draft coverage, never editorial,
font, build, runtime, visual, or release acceptance. Invalid or partial files
are excluded and listed under `problems`; a stale validation sidecar does not
count. Run `python3 Scripts/report_locale_readiness.py --update-state --compact`
after a handoff to record a bounded snapshot in the existing
`Documentation/localization-state.json` rows. The scan leaves editorial and
runtime statuses separate. Do not create a competing readiness tracker.

The existing `validate_game_text_batch.py` checks a batch against its full
source collection. For `ChecksDialogs`, that collection is larger than the
accepted selected scope. The integration snapshot enforces the selected ID;
all final gates must do so too. A structurally successful batch sidecar is not
proof that its IDs belong to the accepted 16,538. A complete draft must also
cover all selected IDs exactly once, pass the preserve-exact checks, and retain
the canonical glossary and inventory fingerprints.

## Build path and boundaries

The verified Thai path is:

1. `Scripts/build_locale_probe.py --codes th` produced the one-locale native
   base in `outputs/th-native-base-v1/` (24 artifacts).
2. `Scripts/build_th_text_draft.py` consumed accepted Thai text, checked its
   semantic and preserve-exact evidence, and produced 10 text artifacts. Its
   verifier reread 16,538 values, including 165 `originalText` fields.
3. `Scripts/assemble_th_only_package.py` composed the two layers into 31
   artifacts; `Scripts/verify_th_only_package.py` confirmed the one-locale
   boundary and hashes. The report SHA-256 is
   `a480dadbe3d98d470845277992bfc00c136dd72572116170c653d2c9a82aa1ad`.

`build_locale_probe.py --codes <locale>` already supplies a configurable
single-locale native base. Its locale mappings are technical probes. The Thai
text builder, verifier, assembler and installer remain Thai-specific; their
passed reports do not certify another locale. A reusable text builder must
consume an accepted locale-specific semantic report and preserve-exact report,
verify all selected authored IDs, and write only that locale's table objects.
Its read-back verifier must compare all 16,538 serialized target values, all
applicable `originalText` fields, the one-locale catalog/UI key/font boundaries,
all original objects and every artifact hash. It must reject an incomplete
draft before creating a package. Compare its Thai mode byte-for-byte against
the pinned Thai outputs before using it for another locale; retain the pinned
Thai artifact rather than replacing it. Because 178 static TMP fields are
serialized outside locale tables, a shared multilingual package needs a
separately proven runtime switch for those fields. The current safe assembly
unit is one locale per isolated package.

Do not run the copied game fixture or modify its preferences while any worker
is drafting or the owner is using it. Package verification is offline. For
runtime QA, reserve a bounded exclusive fixture window, verify the fixture is
stopped and its exact installed hashes, then install one complete package. The
installer's per-file atomic replacements are not a transaction: after a
failure between writes, reconcile the receipt, all target hashes and backups
before launch. Bind screenshots, logs and progression to the exact package.

## Locale-specific technical checks

| Locales | Script requirement and evidence still needed |
| --- | --- |
| `id cs hu nl ro fil sw` | Latin accents, narrow UI, wrapping, dynamic values and dialogue advancement. Existing menu/selector binding is only a probe. |
| `el` | Greek accents, metrics, wrapping, narrow UI and dialogue advancement. |
| `bg sr` | Cyrillic glyph coverage, metrics, wrapping and dialogue advancement. |
| `fa` | Persian joining and ZWNJ, RTL with Latin, numbers, tags and placeholders, dialogue progression. The runtime module repaired menu/selector only. |
| `hi` | Devanagari conjuncts, reordering and marks, wrapping, typewriter and dialogue progression. The runtime module repaired menu/selector only. |
| `he` | Hebrew marks and mixed-direction text, tags and placeholders, dialogue progression. The runtime module repaired menu/selector only. |

Every locale still needs final font face and style, dense UI, dynamic values,
dialogue, later states, layout and actual screenshot review. The probe font
mappings and a clean Unity log cannot establish those checks. Do not inherit
Thai runtime evidence for another locale or a rebuilt package.

## Handoff and canonical integration

For one worker handoff, require final authored file list and hashes, complete
16,538-ID structural and preserve-exact results, approved glossary hash, full
source-to-target semantic coverage, immutable correction closure and clean
independent diff audit with its reviewer identified. Check the mandatory
regression catalog and exact current hashes before marking editorial accepted.
The source inventory or shared binding changing can invalidate prior review.
Only accepted, verified locale files enter the Git stage. Inspect the complete
staged diff immediately before commit and verify the resulting tree and HEAD.
Leave active drafts untracked and preserve unrelated changes. Runtime, visual,
release and publication remain distinct fields in the existing checkpoint.
