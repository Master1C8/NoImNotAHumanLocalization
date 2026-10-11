# Foreigner speech and radio development repair

Game 1.3.19, Unity 6000.3.10f1, build GUID `c003ddc7de634775a85305fef3b9a0d3`.
The current repair is a development draft authorized for a local commit. Independent editorial
acceptance, live IL2CPP hook verification and in-game visual QA are pending.
No fixture installation, package publication or production deployment is included.

## Source and first divergences

`outputs/localization-mechanics-v1/official-reference.json` records all 18 official
locale bundles, their checked original hashes and 38 relevant managed methods.
Every official locale contains the same 52 radio IDs. The managed backup is
analysis evidence; compilation references the actual fixture's IL2CPP interop DLLs.

The Foreigner's opaque Russian keyboard-layout speech had been copied into most
target drafts, while Bulgarian exposed some of it as ordinary readable dialogue.
Several understood words were also still Russian. These are distinct from the
stage directions, player choices and ordinary speech, which must remain readable.
`foreigner-source-v1.json` fixes the affected source boundary at 64 speech rows:
58 opaque or mixed rows and six understood rows. Each authored part specifies
whether it is opaque or understood; the latter also pins its original source cue.

Radio has two layers. The 52 authored messages contain permanent cut words and
unheard clauses. After localization, `RadioModel.GetDisplayedMessage` masks text
according to the tuning quality, including numeric codes. Perfect tuning restores
the exact authored message, including its permanent gaps. The previous target
noise tables included Russian pools, and the game's UTF-16 character masking
could separate combining signs from the characters they belong to.

Official pools use native Latin/Cyrillic letters, Hangul syllables, or punctuation
for Japanese and Chinese. Arabic uses a Latin pool and is explicitly excluded
from the radio view's `<mspace>` wrapper. These are source observations, not proof
that every official rendering is correct on every platform.

## Language policies

| Locales | Opaque Foreigner speech | Radio interference |
| --- | --- | --- |
| id, cs, hu, nl, ro, fil, sw | Native wording, A–Z Atbash; accented letters retained | Locale Latin alphabet |
| el | Greek alphabet Atbash; opaque accents normalized | Greek letters |
| bg | Bulgarian alphabet Atbash | Bulgarian Cyrillic |
| sr | Serbian Cyrillic Atbash | Serbian Cyrillic |
| th, fa, hi, he | Authored romanization of native wording | Neutral `#%*+=~` |

Understood speech stays in the target script with intentionally rough pronunciation.
The repeated question word matches the existing player's reply. No country of
origin is assigned. The damaged death fragment is interpreted as killing, not a
person called Ivan. The damaged photo/adoration phrase uses the neighboring stated
preference for photographs; its exact source syntax remains unresolved and is
explicitly flagged for independent review in every authored recipe.

`Resources/Localization/mechanics-v1.json` is the single policy used by translation
guards and embedded into the renderer DLL. Per-locale `foreigner-mechanics-v1.json`
contains authored wording and boundaries. `radio-mechanics-v1.json` freezes the
existing 52 authored radio messages; their wording was retained, not regenerated.

## Runtime boundary

`RadioText` masks complete .NET text elements, with explicit Devanagari virama/
join-control and Thai vowel merges needed by .NET 6. Noise is applied before
HarfBuzz or RTL shaping. Native punctuation and whitespace stay readable; numeric
codes share the normal signal masking. Weak, intermediate and perfect signal are
covered. The original tuning quality and wrong AM/FM multiplier are retained.
Message progression, delays, knob input, audio and radio node selection are unchanged.

For th/fa/hi/he the radio component's outer `<mspace>` wrapper is removed before
shaping, using its exact owning `RadioCloseUpView._messageBox` field. Other text
components keep their formatting. The original native UTF-16 threshold array is
retained; a separate complete-element map prevents switching back to an official
locale from giving the original implementation a shorter array.

The new plugin version is `0.4.0`. Builds are offline DLL artifacts; the existing
fixture and previously built packages still contain their previous plugin versions.
Do not infer live radio correctness from compilation or logical text tests.

## Reproducible correction and gates

After editing authored wording, preflight and apply one locale with a new receipt:

```sh
.venv/bin/python Scripts/foreigner_mechanics.py cs
.venv/bin/python Scripts/foreigner_mechanics.py cs --apply --receipt outputs/NEW/cs-speech.json
.venv/bin/python Scripts/localization_mechanics.py cs --apply-radio --receipt outputs/NEW/cs-radio.json
.venv/bin/python Scripts/validate_locale_corpus.py cs --output outputs/NEW/cs-corpus.json
```

A complete application plan and the before/after targets are persisted before
writing batches. Each file replacement is atomic; the entire locale is not a
transaction. A partial failure must be reconciled against its receipt and exact
pending file, then continued with a new receipt. Never reset shared Git state or
restore unrelated files. JSON patching preserves unrelated target bytes and format.

`locale_text_inputs.current_text` invokes the mechanics guard and pins both source
specifications, the shared policy and both locale recipes. It rejects stale batch
speech, the wrong noise pool, missing radio IDs or a removed authored outage.
This is a structural contract, not semantic proof. Independent review must read
original context and every changed target, including opaque/understood transitions.
Historical sidecars, exact reports and semantic acceptance are not rewritten to
pretend the changed drafts are accepted. Normal accepted builds reject these old
receipts until fresh structural and independent editorial evidence exists.

## Verified checks and remaining acceptance

The Python regression suite exercises actual current drafts and the real batch
writer. It injects failure on the second replacement, verifies the first committed
file and the untouched second file, reconciles the pending file, continues from
partial state, then checks an unchanged repeat. It also tests matching positive
controls against wrong noise and exposed speech rejections.

The .NET 6 radio suite links the actual `RadioText.cs`, embeds all 14 policies and
all 728 authored radio messages (52 per locale), and checks weak/intermediate/
perfect signals. It verifies Indic/Thai clusters, native punctuation, wrong-band
quality, masked numeric codes, preserved permanent gaps and exact text recovery.
It does not execute Unity, Harmony, TMP layout, game timing, audio or input.

Before release, independently review the 64 speech rows and their player/context
neighbors in each locale. In the actual game, verify all 13 radio nodes, changing
AM/FM, weak/intermediate/perfect tuning, code visibility, authored cut words,
message timing, th/hi combining signs and fa/he direction/shaping. Verify reopening
the radio and switching between custom and official locales. Capture the logical,
rendered and packaged plugin versions; reject any mismatch. Bind that evidence to
the exact authored recipes, source build and delivered DLL/package hashes.

Regression scenario: a Hindi conjunct or Thai preposed vowel must be hidden as a
unit; `18-8` and `451` must not stay readable at weakest signal; permanent gaps
must remain at perfect tuning; Foreigner's understood word must remain readable
between opaque parts; replacing the Bulgarian opaque body with fluent text must
fail the shared mechanics guard.

## Preview 0.2.1 integration

The owner authorized including all existing fixes and republishing on October 11, 2026. `Documentation/LAUNCHER_PREVIEW_021.json` records the current boundary. The launcher now reads every current authored value with the shared structural/mechanics guard instead of silently republishing stale frozen tables. It preserves baseline assets and records exact per-locale deltas and input hashes. Renderer 0.4.1 merges the current radio/RTL hooks with the reviewed Hindi/Hebrew bindings. Historical development evidence above remains unchanged.

The actual delivered DLL executed native RadioModel methods for all 728 custom radio messages and loaded all 896 repaired speech rows in the macOS wrapper. The Russian original implementation is a matching positive control. These tests use a task-owned model with null gameplay dependencies: they establish Harmony hook execution, tuning/noise and shipping table parity, but do not establish radio close-up TMP layout, gameplay timing/audio/input, all radio nodes or independent editorial acceptance. Preview publication must not be reported as full-game acceptance.
