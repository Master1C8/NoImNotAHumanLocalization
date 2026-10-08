# No, I'm not a Human localization

Canonical project: `/Users/antonkrutov/Desktop/no I'm not a human`.
Standard localization from Russian, version 1.3.19, Unity 6000.3.10f1, IL2CPP.

The approved source glossary and all 14 target glossaries are complete. Thai game
text has a separate local preview. Thirteen non-Thai text-only locale drafts are
now being authored in separate chats; see the
[technical integration guide](Documentation/NON_THAI_INTEGRATION.md) and run
`python3 Scripts/report_locale_readiness.py --compact` for current draft coverage.
The approved Russian source glossary has 201 entries. All 14 target locales are
complete: Thai, Indonesian, Czech, Hungarian, Dutch, Persian, Romanian, Hindi,
Filipino, Greek, Bulgarian, Serbian, Swahili and Hebrew. Each final layer passed
at least two consecutive full clean editorial audits, including independent review.
The 2,814 translated term/meaning pairs are synchronized with SiteForMods and
passed canonical structural validation and 39 focused tests. All 14 glossary layers
were initially published to the production site database on October 8, 2026 (Vietnam time).
The subsequent Czech photo-submission and Hungarian character-list corrections
are saved locally and require separately authorized publication.
Every initially stored term and meaning was verified against that accepted layer through the
canonical CLI; see the [publication receipt](Documentation/glossary-translations/publication/2026-10-08/receipt.json).
Public-page rendering was not checked. Rendering feasibility
remains a separate incomplete gate. The accepted text-only inventory contains
16,538 selected units per locale. No final multi-locale package or release
exists yet. See [the shared checkpoint](Documentation/localization-state.json).

## Reproduce the bounded static checks

Create an isolated Python environment and install `requirements-probe.txt`.
The verified environment used Python 3.9; all direct analysis tools are pinned.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-probe.txt
.venv/bin/python -O -m unittest discover -s Tests -v
.venv/bin/python Scripts/probe_assets.py --output outputs/new-assets-run
.venv/bin/python Scripts/probe_fonts.py --output outputs/new-fonts-run
```

`--game` accepts the actual Windows game directory, not the macOS wrapper.
The default points at the owner's KINGSTONMAC installation. These scripts only
write new directories under this project's `outputs/`; existing results are
never overwritten. They check the build GUID and recheck original input hashes.

The asset probe selects `UI_ru/Common_NewGame` by its shared numeric ID, checks
the Russian source value, rewrites a no-op and one synthetic sample for every
target locale, reopens each bundle, and compares every serialized object in the
Russian string bundle. Its carrier locale remains `ru`. It does not create
target runtime locales or prove rendering. For each rebuilt bundle it also produces
a matching copy of the Addressables catalog with that bundle's CRC and size
updated. It compares all 26 bundle locations and every byte outside the two
integrity fields; source catalogs are never modified and CRC checking stays enabled.
Validation remains enabled with Python optimization (`-O`).

Runtime regression: rebuilding the Russian bundle without changing its old
catalog produced `No translation found`. The runtime logged expected CRC
`93218230`, calculated CRC `2b91d6f2`, and refused the bundle. Read-back equality
alone therefore does not establish runtime acceptance. Always use the bundle
and catalog from the same completed probe report. Install both only into the
stopped isolated fixture, verify both hashes, then launch and check the same
Russian menu. Two separate file replacements are not a transaction; never
launch between them. No installer/rollback protocol is provided by this probe.

The font probe reads embedded font cmaps and three exact font-role assets.
It generates custom type trees from the game's shipped managed backup using
`CheckedTypeTreeGenerator.load_local_dll_folder`. Narrow the object scope before
generation: unrelated Yarn editor classes require DLLs absent from the build.
The backup DLLs are analysis inputs; editing them cannot patch the live IL2CPP
game. Cmap coverage does not prove TMP atlas coverage, shaping or fallback.

## Native locale binding probe

```sh
.venv/bin/python -O Scripts/build_locale_probe.py --output outputs/new-native-build
```

This technical adapter registers `th,id,cs,hu,nl,fa,ro,hi,fil,el,bg,sr,sw,he`
as separate Unity locales. It retains all 18 official locale objects and their
catalog bindings. Each new locale has nine Russian carrier string tables and
one Russian carrier image table. Only `UI/Common_NewGame` contains a synthetic
script sample. The carrier content is untranslated and is not a source inventory.
Fourteen native language-name keys are added to shared UI data and all official
UI tables. Every original string is retained. All three font-role dictionaries
receive the new codes; original mappings and original font assets are preserved.
The Hebrew probe has its own dynamic font, material and atlas, using the game's
embedded Liberation Sans. Probe font assignments are not final visual styling.

The binary catalog uses Unity's official Addressables 2.9.0 package schema,
format version 2. New key/location storage is appended. Existing asset locations,
providers, dependencies and key order are retained; changed bundles get their
verified CRC and size. Reopened object bytes, container bindings and independent
UI sample/code pairs are checked. The verified build is
`outputs/native-locale-probe-v6/report.json`; it contains 24 artifacts.

Three concrete regressions are encoded in the recipe:

- UnityPy 1.25.4's `get_raw_data()` and `read_typetree()` keep reading the original
  reader after `save_typetree()`. Use `serialized_bytes()` and `current_tree()`
  for accumulated mutations. Fourteen saved locale objects are insufficient if
  repeated container edits retain only the last binding; compare the complete
  saved container set against the saved assets.
- The generated MonoBehaviour header lacks alignment after `m_Enabled`.
  Correct that node, compare native script/game-object pointers, and require a
  byte-exact no-op before editing generated fields.
- TypeTreeGeneratorAPI 0.0.10 puts native load/generate calls inside `assert`.
  Python `-O` removes the calls themselves. The checked wrapper executes them
  explicitly and checks their results under optimization.

Install only into the stopped isolated fixture with a previous installation
receipt. The installer verifies every previous and replacement hash and preserves
backups. It makes per-file atomic replacements, not a multi-file transaction;
launch only after the complete receipt says `allInstalledHashesVerified: true`.
An injected failure between the two replacements is tested with real files:
the first file remains new, the second remains old, backups survive and the
receipt stays unverified. The test replaces process inventory and a copy failure;
it does not prove actual Wine process isolation. After any installation failure,
preserve receipts/backups and reconcile the stopped fixture's exact hashes before
retrying or launching.

```sh
.venv/bin/python Scripts/install_locale_probe.py \
  --build outputs/new-native-build \
  --previous-receipt outputs/native-locale-install-v3/receipt.json \
  --output outputs/new-native-install
```

The saved-locale runner edits only `TextSettingsData.SelectedLanguage` in this
fixture's stopped Wine prefix. It preserves other logical settings, launches
one case, captures menu and settings, saves the fresh log, and terminates only
processes verified through the fixture app path, exact command and start time.
It waits for surviving Wine children to exit. Startup window resizing is a
transient readiness condition; a running case is resumed without another launch.
Native screenshots and saved preferences must agree before crediting a locale.

```sh
.venv/bin/python Scripts/run_saved_locale_probe.py \
  --codes cs hu nl ro hi fil el bg sr sw he \
  --reference outputs/native-fa-menu-v1/native.png \
  --output outputs/new-saved-locale-check
```

This runner is calibrated for the observed 1440×900 window and 2880×1800 native
frame. It initializes Python helpers before work and pins every later Swift
helper read. Do not edit a live run's execution version. Every frame still needs
visual review: capture readiness and process completion do not establish script
shaping, bidi, layout, dialogue progression or final font appearance.

## Runtime fixture and guards

The isolated wrapper is `runtime/No Human Probe.app`. Its bundle ID is
`fun.vnrevival.no-human.probe`; its prefix is inside that copied wrapper. The
original application and saves are outside the fixture. All game payloads,
wrapper files and extracted outputs are ignored by Git.

Before modifying a fixture payload, verify that its exact game process has
stopped. Verify prefix/symlink resolution, pin the original and replacement
hashes, then replace only the intended copied bundle. Capture the actual game
surface and independently prove the active locale and changed binding. A
running process or menu confirmation alone does not prove resource loading.
Use exact task-owned process identities for cleanup, never kill Wine by name.

The workstation's Stardew visual-QA architecture is the capture reference:
process ownership, expected-screen guards, native unannotated frames, timeouts,
save isolation, locale restoration, and machine-readable evidence. Oculix,
Java 17 and ImageMagick are now available. The project capture adapter uses
native window capture and fresh-image Oculix recognition, with immutable helper
copies per run. Screen access must run outside the shell sandbox. Computer Use
could not attach to Wine; the native adapter captured the full 2880×1800 frame.
The Russian failure log is historical evidence, not acceptance of the corrected
catalog. Its native frame is no longer present in the recorded output directory;
do not credit that capture as current visual evidence. The corrected Russian
settings frame and fresh Unity log are recorded in
`outputs/runtime-catalog-verified-20261007/evidence.json`: Russian labels render
and no CRC/resource-provider failure was logged. After the owner pressed Back,
the unobscured Russian menu passed visual review; all five action labels are
present in `outputs/runtime-catalog-menu-20261007/evidence.json`. The isolated
fixture was verified stopped. The automated Back click had correctly refused
input when another app was active. That Russian no-op result is historical;
the current native adapter is recorded separately below.

For an already-running authorized fixture, capture without input or save actions:

```sh
.venv/bin/python Scripts/visual-qa/run_capture.py --output outputs/new-capture
```

An optional `--marker <path>` checks an expected visual state. Automated capture
and visual review remain separate; inspect every frame before accepting it.
The runner rejects a missing or ambiguous fixture window. Do not substitute
blind clicks or treat the owner's menu confirmation as visual acceptance.
Capture-only runs use native window capture without initializing Oculix's mouse
subsystem. Wine fullscreen may use window layer 26; exact fixture ownership,
window title and uniqueness remain required. Guarded clicks compare a fresh
native region against a reviewed reference, focus the exact fixture with
Accessibility, and refuse input if focus is lost. A changed hover color is not
equivalent to a changed language; use a stable text region for selector guards.
Opening a dropdown is not selecting its next item. The earlier assumed-cycle
batch was rejected after its captured frames contradicted the intended locales.

## Shared stage binding

All 14 locales follow the same fixed stages from `vn-localization`:
`scope → probe → source → glossary → translate-edit → editorial → resources →
package → runtime → delivery`.

`scope` is established. All 14 native locales load their independent menu
samples and appear in settings in the isolated v6 build. Full frames were
reviewed for locale/table binding, with their hashes recorded in
[the native evidence matrix](Documentation/native-locale-evidence.json).
The eleven saved-locale cases have fresh logs with no recorded CRC mismatch,
asset-load failure, missing translation, missing key or null-reference exception.
Thai and Indonesian also passed explicit dropdown selection. These observations
cover menu/settings only. Later stages remain unaccepted. Thai text has passed
its offline editorial gate; runtime rendering is still untested for this build.
The [text-only source acceptance](Documentation/text-source-acceptance-v1.json)
now pins 16,538 selected stable-ID rows for editorial review. Its runtime
reachability conditions remain open. The nine Russian table row counts include
historical/demo content and are not the selected translation workload.

The shared candidate source inventory is generated offline by
`Scripts/build_localization_inventory.py`. Its current
[summary](Documentation/localization-source-inventory-v3.json) and
`Source/localization-inventory-v3/` contain all 52,788 Russian string rows and
244 serialized TMP text objects found across 16 scene and shared-asset files.
The [full TMP extraction](outputs/text-path-audit-v2/report.json) pins each
source file and script identity. Earlier inventory versions remain as audit
history. Textures and images are excluded from the current inventory.
The [legacy UI text audit](Documentation/legacy-ui-text-scope-v1.json) also
accounts for 149 `UnityEngine.UI.Text` fields. All are resource-prefab descendants
of `DebugUI*` roots used by the rendering pipeline, with none in game scenes;
they are excluded from the game-text candidate inventory.
The [embedded TextAsset audit](Documentation/embedded-text-assets-scope-v2.json)
accounts for 18 text resources. `FakePeople_RU` is a Twine-era story with 298
dialogue or choice lines absent from any extracted string table. No serialized
`DialogueTwine` component, readable resource reference, or literal resource
name was found in the game code metadata, so this appears to be legacy content; runtime reachability remains
unverified and source-scope acceptance is pending.
The [other serialized string audit](Documentation/other-serialized-text-scope-v2.json)
found no additional readable Russian display sentence outside text components:
338 candidate fields reduce to technical metadata and 60 reviewed unique
names or labels for fonts, input schemes, resources and timeline tracks. The
153 components whose type trees could not be read had no raw UTF-8 Cyrillic
spans in the same audit; their full fields are still unresolved.

The [text scope audit](Documentation/text-source-scope-v7.json) compares every
extracted row with the Russian source and identifies 16,360 selected string
candidates: 16,100 `Dialogs`, 259 `UI`, and one `ChecksDialogs` row referenced
by two character objects in `sharedassets0.assets`. Together with 178
supplemental static fields, the accepted text-only source-ID denominator is
16,538, subject to reopening if a new runtime consumer is found. The seven
scene files contain GUID
references only to `Dialogs` and `UI`. The managed assembly has 16 string-table call sites: 13
through the `UI` helper, and direct calls for `UI` and `Dialogs`; the third
`GetTable` call receives the helper argument. The corrected
[static binding audit](Documentation/static-text-scope-v2.json) resolves 60 TMP
objects to existing `UI` keys. One more points to a
missing Russian `UI` key (`86605930199502848`) on the standalone
`В желаемое` text. Fifteen fields have unconfigured localization events and
168 have no serialized event binding; six of those 184 fields are empty.
The 178 nonempty fields require standalone draft text until their runtime
consumers are resolved. The expanded inventory keeps all 52,788 string-table
rows byte-for-byte unchanged.
Eight Thai UI draft batches now cover all 259 extracted UI table IDs, and
325 Thai dialogue batches cover all 16,100 IDs, including 2,868 repeated
exact-source options expanded from authored Thai maps.
One Thai `ChecksDialogs` batch covers the shared-asset reference with the same
Russian source and Thai wording as its current `Dialogs` counterpart.
The supplemental Thai draft now covers all 178 nonempty TMP fields
without a resolved table binding. The [preserve-exact manifest](Source/preserve-exactly-v4.json)
pins protected grammar and exact values for all 16,538 candidate Thai units.
The [Thai comparison](Documentation/th-preserve-exact-v8.json) passed for the
expanded source: stable IDs, speaker/service prefixes, numbered slots, TMP tags,
ordered numbers, line breaks, trailing whitespace, and designated technical
values were intact. The original credits contain malformed TMP nesting; the
comparison requires their exact tag sequence without silently repairing it.
The isolated [Thai text build](outputs/th-text-draft-v7/report.json)
applies authored text to copied locale tables and TMP source assets. Its
[artifact verification](outputs/th-text-draft-v7/verification.json) reread all
16,360 table values, 178 static values, 165 RTL source fields and 10 artifact
hashes successfully. The [Thai-only native base](outputs/th-native-base-v1/report.json)
adds only Thai to the game's locale catalog. The resulting
[31-file package](outputs/th-only-package-v1/report.json) passed an independent
[locale and hash check](outputs/th-only-package-v1/verification.json): only
`th`, `language_th` and three `th` font-role bindings were added. A local
[preview archive](dist/NoImNotAHuman-th-preview-v1.zip) contains those verified
files. It is not a release because the full runtime gate is still pending.
The [paired semantic review input](outputs/th-semantic-audit-input-v4/report.json)
aligns all 16,538 source and Thai draft rows with stable IDs and scene or
dialogue context. The [completed first pass](Documentation/th-semantic-audit-progress-v44.json)
read every row and recorded 145 objective findings. The
[correction plan](Documentation/th-semantic-correction-plan-v2.json) applied
450 row changes, including identical repeated options. The
[independent diff audit](Documentation/th-semantic-diff-audit-findings-v1.json)
reviewed all 186 distinct changes and prompted seven final revisions.
The [offline semantic acceptance](Documentation/th-semantic-acceptance-v2.json)
has no open objective findings. The review input pins the accepted source
scope, approved Thai glossary and [mandatory regression IDs](Documentation/th-semantic-regressions-v1.json).
A runtime observation on the earlier 14-locale technical base found an Arabic placeholder in the answer panel. The
corrected Thai text is written to both the TMP display field and the RTL
component's source field; the prior acceptance and exact-text reports remain
as immutable predecessors. The [Thai runtime report](Documentation/th-runtime-qa-v1.json)
records 13 translated dialogue lines, the corrected answer-panel text and zero
missing-glyph warnings in the final sampled run.
The [Thai-only preview report](Documentation/th-only-preview-v1.json) records
menu, Settings and intro screenshots on the exact 31-file package. Its dialogue
and later gameplay surfaces remain to be checked on that exact package.
The [orphan wishlist key audit](Documentation/missing-ui-key-86605930199502848-v1.json)
pins the underlying source defect: key `86605930199502848` is absent from
`UI Shared Data` and from the Russian UI table, although 11 of 18 official
locale tables contain a row for that numeric ID. The scene event targets this
ID, and its serialized Russian text is `В желаемое`. Adding a translated table
row alone may not resolve the absent shared key; the isolated runtime path must
be checked before choosing the patch. The scene's `Пропустить` fallback is
assigned a localized `control_key_*` value by `ControlView.SetDescription`,
so its serialized text is not a separate authored line.
The sole same-source UI variant is intentional: `Common_LanguageName` displays
`ไทย` for the active locale, while `language_ru` keeps `Русский` in the picker.
All extracted
`SuperFake_Entrance*`, `radio*`, `Day1_*`, `NewfemaEnding*`, `Fan_*` and the
`Cultist1_*`, `Cultist2_*`, `Cultist3_*`, `CultistPriest_*`, `Death_*`,
`AloneEnding_*`, `RageEnding_*`, `Ending_*`, `selfcheck*`, `selfchek*` and
`Killer_*`, `MushroomEater_*`, `Mushroom_*`, `Rock_*`, `Cat_*`, `StaticBoy_*`,
`FEMA_*`, `Fighter_*`, `Tough_*`, `Fugitive_*`, `Twins_*`, `Miner_*`, `Sirin_*`, `Alkonost_*`, `Rocker_*`, `Luka_*`, `Mother_*`, `Fairytaller_*`, `WheelChair_*`, `Wheelchair_*`, `Foreigner_*`, `Firefighter_*`, `Bald_*`, `Jacket_*`, `Leper_*`, `Wifefema_*`, `Edgar_*`, `GraveDigger_*`, `Theorist_*`, `Tourist_*`, `Marauder_*`, `Alt_*`, `Nervous_*`, `NotTrue_*`, `Blind_*`, `Raskolnikov_*`, `FortuneTeller_*`, `BigLebowski_*`, `Nun_*`, `TaxiDriver_*`, `Cold_*`, `Intruder_*`, `Jacob_*`, `Ballerina_*`, `FunnyGuy_*`, `Buddy_*`, `Dude_*`, `Anger_*`, `Greatmother_*`, `Provocateur_*`, `FormerFema_*`, `Bestson_*`, `Teacher_*`, `Wolfhound_*`, `FatalDame_*`, `Hunter_*`, `Esenin_*`, `Unstable_*`, `Experienced_*`, `Doctor_*`, `Fatman_*`, `Fanatic_*`, `Couple_*`, `Widow_*`, `Scammer_*`, `Anxiety_*`, `entrance_*`, `Entrance_*`, `talk_*`, `Neighbour_*`, `window_*`, `office_*`, `bigroom_*`, `pantry_*`, `kitchen_*`, `bedroom_*`, `bathroom_*`, `Character_*` and all `tv_*` lines are now
drafted and reviewed. Intentional keyboard-layout garble in `Foreigner_*`
remains as in the source script. Thai text coverage and offline semantic
review are complete for the accepted 16,538-unit text-only scope. Menu, Settings
and sampled dialogue rendering passed in the isolated fixture. Dense gameplay UI,
dynamic substitutions, later dialogue branches and next semantic state remain
unchecked; full runtime and visual acceptance remain pending.

Run `.venv/bin/python Scripts/audit_translation_alignment.py th` before the
full Thai semantic pass. It flags unusual source/target length ratios and prints
four neighboring stable IDs on each side for review; a clean result does not
count as semantic coverage. Regression case: in `dialogue-batch-179`, a long
soldier-head description was paired with the short question "มีใครรอดบ้างไหม?".
The outlier must lead the reviewer to inspect the surrounding window lines,
where five adjacent targets had been assigned to the wrong source IDs.

Native locale, table and font bindings now exist as an isolated technical probe.
After text translation, exercise menu, dense UI, dialogue, mixed RTL/LTR text
and progression on this adapter before accepting a release. Menu samples stress a
narrow binding and may overflow; their presence is not layout acceptance. Keep
unverified shaping and other surfaces explicit, and never remove target locales
or patch managed backup DLLs as a substitute for repairing the live mechanism.

The unmodified v6 rendering path failed Hindi shaping and Persian/Hebrew selector
endonyms. The bounded `probe_menu_features.py` experiment improved only part of
Hindi with `liga`; `level0` was restored byte-for-byte. That evidence remains in
`Documentation/native-locale-evidence.json`. The same-font CoreText references
are diagnostic controls, not game acceptance. Subsequent authorized runtime work
is described below; it supersedes those specific menu/selector blockers, while the
full shared gate remains incomplete.

Four earlier owner-authorized Thai dialogue attempts are recorded in
[`Documentation/dialogue-th-probe-evidence.json`](Documentation/dialogue-th-probe-evidence.json).
The owner confirmed closing or using the copied game window during the attempts.
The third attempt revealed that Settings can obscure New Game while leaving its
border visible; the fourth verified a corrected guard rejecting that overlay
before input. They captured no Thai dialogue event. After the Thai text was
completed, the later isolated runs captured real Thai dialogue, identified and
corrected the answer-panel placeholder, and restored the copied preferences.

## Runtime shaping module

The owner subsequently approved a separate IL2CPP runtime module. The bounded
integration and reproduction recipe are in
[Documentation/RUNTIME_RENDERER.md](Documentation/RUNTIME_RENDERER.md).
This adds Hindi shaping and repairs the Persian/Hebrew selector path in the copied
fixture; the full renderer-feasibility gate remains incomplete. Consult the latest
[artifact-bound evidence](Documentation/runtime-renderer-evidence.json) before
continuing. Earlier v6 restoration evidence describes the fixture before this module.

## Standalone glossary translation checkpoint

The canonical locale layers are maintained in SiteForMods. The complete export
in `Documentation/glossary-translations/glossary-translations.json` is a
byte-identical project snapshot. Per-locale `authored.json` rows contain the
model-authored ID, term and meaning; `layer.json` is their mechanical export.
Run `python3 Scripts/assemble_glossary_translation.py <locale> --complete` to
validate the reviewed source pin and exact source-ID order before exporting.
The assembler never generates wording or awards editorial acceptance.

Per-locale `review.json` records findings, pinned versions and acceptance status.
Its historical review artifacts resolve relative to that review file. Complete
two consecutive clean full-entry audits after corrections before marking a
locale ready. The owner authorized parallel locale groups on 2026-10-08; each
author finishes one assigned locale before starting the next. A final independent
review compares the frozen layer directly with the Russian source before reading
the author’s audit notes. Any correction resets the clean count. The shared
checkpoint records current locale status; the canonical export is refreshed only
during coordinated integration. The final export contains all14 complete layers
and passed structural validation and 39 existing tests. These checks
exercise loaders, schemas and publication safeguards; translation quality comes
from the recorded full editorial reviews.

Final acceptance and immutable evidence are indexed in
[acceptance-manifest.json](Documentation/glossary-translations/acceptance-manifest.json).
[validation.json](Documentation/glossary-translations/validation.json) binds the
checks to the delivered export. [agent-usage.json](Documentation/glossary-translations/agent-usage.json)
records actual author/reviewer session totals and the mixed coordinator window,
with cache subsets, measurement cutoffs and unmeasured reporting overhead explicit.

Full audits check what a phrase asserts, not just whether its topic is retained.
Regression examples: a hoodie with a hood does not establish that its hood is
worn up; leaving service does not establish being fired or never having served;
cleansing from Guests does not mean cleansing the Guests themselves; civilian
victims do not all become deaths; one sound source does not imply one speaker.
A failed guest appearance does not mean the guest physically collapsed; gaming
vocabulary is distinct from playful wording. A generic rescue service does not
establish an ambulance service, and a dirty yellow man gains no body-shape fact.
Preserve clue versus puzzle terminology and native word meanings across every
term/meaning cross-reference. Correct model-authored rows before mechanically
rebuilding layers; immutable reviewed versions must remain available.

Additional regression scenarios from independent review: uncertainty about
whether several voices belong to the same person must retain that sameness
relation, rather than merely saying their identities are unknown. A request to
be given a cigarette is distinct from permission to smoke. Calling oneself a
son, grandmother or young man must refer to the speaker, not their own relative.
Do not add paternal or maternal lineage to an unspecified grandmother. A service
provided for a charge is not necessarily already paid for. Preserve slips of
the tongue rather than replacing them with self-corrections. A source-language
wordplay explanation must keep both words in that source language, and a native
fictional acronym must match the native organization name wherever it recurs.

Canonical sex, source grammatical evidence and native agreement are separate.
Translated grammatical-evidence quotations are valid when explicitly attributed
to the Russian source or original scene; a genderless target quote must not be
described as a native masculine/feminine inflection. Swahili instructions use
noun-class agreement and appropriate sex-specific words, preserving canonical
sex and disclosure timing without inventing male/female agreement rules.
Neutral labels must retain the person and professional role: a telephone doctor
cannot become only a medical consultation. Explicitly preserve who controls
the protagonist and who performs each reported action.
An eyewitness is a person who saw the events, not merely a voice conveying
testimony. Close that distinction across the caller, dispatcher and shared
dialogue cards; neutral wording must retain firsthand observation and ownership
of the person's words and answers. Recheck every affected reference before
starting the two final clean full-entry audits.

Adjudicate grammar findings against the complete native construction, including
linked clauses and verb focus. In Filipino, a positive example with `handa siyang`
does not by itself reject `handa niyang kupkupin`: the genitive actor may belong
to the following patient-voice predicate. The withdrawn review candidate and
native counterevidence are preserved in the final Filipino review package. A
preferred paraphrase is not an objective error; unsupported findings do not
reset acceptance or authorize a taste-only rewrite.

`acceptance-manifest.json` binds coordinator acceptance to unchanged authored
content, layer hashes and full review evidence. Run
`python3 Scripts/package_glossary_translations.py --complete` only when every
authorized locale has accepted final evidence. It verifies structure and copies
accepted artifacts; it cannot conduct or award editorial reviews. The
coordinator separately integrates the byte-identical export and review packages
into SiteForMods. Per-file replacements are not a transaction across the two
repositories; compare both delivered exports and committed trees before crediting
integration. This workflow does not publish glossary content.
For corrected layers, record actual reviewer counts and models in the acceptance
manifest; the packager preserves those values rather than reusing historical
authoring metadata. Regression: two full rereads by one independent reviewer
count as two audits by one reviewer, not two self-audits or two reviewers.
Photo-submission wording must preserve who sends and who evaluates the pictures;
character lists must distinguish the named people rather than their possessions.
Evidence snapshots may be read-only. The packaging copier reuses identical bytes
and replaces changed destinations through a verified temporary file, preserving
the source snapshot's permissions. Opening an existing read-only snapshot for
overwrite fails after earlier package writes; the actual failure and corrected
filesystem regression are recorded in `package-copy-verification.json`.
Immutable audit tables can use valid CRLF endings from the CSV writer. Preserve
their byte hashes; run Git's whitespace check with
`core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol`. This retains
the normal whitespace checks while recognizing carriage returns as line endings.
If staging succeeds before such a check fails, reconcile the complete owned
index and unchanged checkout before continuing; do not reset the shared index.
