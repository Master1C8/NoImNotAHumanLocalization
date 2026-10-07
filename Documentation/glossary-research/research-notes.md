# Russian canonical source glossary research

Game: No, I'm not a Human, build 1.3.19, source locale `ru`.
Intended use: owner-selected standard localization. This is an initial source
draft, not an approved translation input. No prior canonical glossary exists.

## Inputs and scope

The game's canonical checkout is `/Users/antonkrutov/Desktop/no I'm not a human`.
The master glossary destination is
`/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary.json`.
The source extractor and authored-input assembler are `Scripts/extract_glossary_corpus.py`
and `Scripts/build_source_glossary.py` in the game checkout. TSV inputs are explicitly
authored text; the assembler only copies fields and the explicitly authored agreement
sentences. It does not translate or infer descriptions.

The six extraction input pins still match the installed original files. The extracted
Russian bundle contains 52,788 serialized rows across nine collections. The bound
current `Dialogs` collection contains 16,100 rows; 15,693 line IDs occur in the compiled
Yarn program and 407 supplemental current-table IDs do not. This proves ID presence,
not scene reachability. `UI` has 259 serialized rows. Legacy/demo/test collections
are retained for research but do not establish the current roster or mechanics.
Counts are not a visible translation workload or exhaustive semantic coverage.

`glossary-evidence.json` binds each draft entry to an exact Russian key, numerical ID,
collection, excerpt and node metadata. The game's raw corpus, report and runtime
bindings are in `Source/glossary-corpus-v2`. SHA-256 identities are in that evidence
file. One excerpt supports one observation, not necessarily every biographical claim
in an entry. Detailed source-fidelity review remains pending.

## Owner decisions

On 2026-10-08 the owner resumed standalone Russian source-glossary work and requested
Russian chat communication. This does not authorize game runtime work, publication
or deployment. Standard localization was already selected in the game checkpoint.

The owner chose additional research rather than approving a proposed neutrality
strategy for unknown phone/radio/TV roles. These entries remain `needs-review`;
no neutrality approval is recorded. The owner then explicitly permitted fan wikis.
That permits research, not replacing unsupported facts with guesses.

## Supporting fan sources checked

The following facts were available in indexed web-search page content. Direct opens
of some Fandom pages failed; that limitation must not be represented as a successful
direct-page read. The notes below use only the facts actually returned by search.

- [News Reporter](https://no-i-am-not-a-human.fandom.com/wiki/News_Reporter): the
  infobox explicitly labels the reporter male. Source `tv_3_necessary` matches the
  news role. Do not add the name, age or private relationships found in unrelated
  fan roleplay pages.
- [Weather Reporter](https://no-i-am-not-a-human.fandom.com/wiki/Weather_Reporter):
  the infobox explicitly labels the weather presenter male. Source
  `line:tv_1_extra1_03a4237` introduces a forecast. Forecasts are distinct from news.
- [CR Channel](https://no-i-am-not-a-human.fandom.com/wiki/CR_Channel): the page
  distinguishes the news reporter, weather reporter and Female TV Presenter, and
  describes the latter as taking over an interrupted eighth-day broadcast. This is
  supporting role identification for `female-tv-presenter`; a directly verified
  infobox/official textual gender statement is still desirable.
- [FEMA Agent](https://no-i-am-not-a-human.fandom.com/wiki/FEMA_Agent): the infobox
  labels the gas-mask agent male. It also notes uncertainty about whether every visit
  is the same person. The draft must not silently resolve that identity uncertainty.
- [Phone](https://no-i-am-not-a-human.fandom.com/wiki/Phone) and the separate
  [FEMA call](https://no-i-am-not-a-human.fandom.com/wiki/Phone/Script_Call%3A_FEMA),
  [ForRest call](https://no-i-am-not-a-human.fandom.com/wiki/Phone/Script_Call%3A_ForRest),
  [Foreign Embassy call](https://no-i-am-not-a-human.fandom.com/wiki/Phone/Script_Call%3A_Foreign_Embassy)
  and [Phone Roulette call](https://no-i-am-not-a-human.fandom.com/wiki/Phone/Script_Call%3A_Phone_Roulette)
  transcripts support distinct roles but do not establish the unknown voices' gender.
- [Tattooed Woman](https://no-i-am-not-a-human.fandom.com/wiki/Tattooed_Woman): the
  article suggests an association with the fourth-day radio voice. The Russian radio
  line `line:radio_4_010d417` uses masculine self-reference. Do not merge `Alt` and
  the radio host from that suggestion; investigate attribution and version differences.
- [Minor Characters](https://no-i-am-not-a-human.fandom.com/wiki/Minor_Characters):
  its summary says the angry man's wife was hit for wanting to join the cult. This
  agrees with the Russian announcement-before-assault sequence. Mentioned relatives
  are not automatically speaking characters.

A purported media-kit site with mismatched developer/release information was rejected
as an official authority. Search did not establish a developer-provided terminology
guide. Official Steam announcements were used only to locate possible developer
materials, not to override the pinned source build.

## Corrections and additional evidence

- `pale-visitor`: Russian `line:tv_2_extra2_03d0e5d` directly calls the suspect a
  pale man of middle age. The accompanying `line:tv_2_extra2_0ad57ac` says some people
  report another person's skin; `line:tv_2_extra2_0e3a51a` explicitly says that claim
  is unconfirmed. Gender description is established; the skin story is not.
- `angry-wounded-man`: `line:Anger_Asking_4_02e0c6c` records the wife's announcement
  that she is leaving for the cult; `line:Anger_Asking_4_00d32bd` records his assault.
  The previous draft's "after she left" chronology was corrected to "after her
  announcement". Preserve responsibility for the violence.
- `wheelchair-man`: `line:WheelChair_Asking_SpecialEvent_1_022eec4` and
  `line:WheelChair_Asking_SpecialEvent_2_09d1e17` establish the legs/liking-the-chair
  variant. Do not force every branch into one immutable disability biography.
- `husband-and-wife`: `line:Couple_Asking_5_3_3_2_03967da` explicitly separates the
  wife's movement and husband's shooting. `line:Couple_Asking_5_3_070700a` refers to
  his pistol, while player choices refer to a shotgun. Extra entries identify both
  participants without inventing direct speech for the wife.
- `fema-recruitment-voice`: the earlier extracted comparison records masculine
  French wording at `line:phone_wifefema_2_1_065231a`; Russian uses plural "они".
  A localized gender marker is not a verified Russian canonical decision. Research
  remains open; do not silently upgrade the draft to confirmed male.
- `cat` and `death`: preserve source reference forms. Biological sex is not invented.
  Death's feminine noun/pronoun and poetic "brother" are explicitly separate
  contextual forms, not evidence of one biological category.

## Remaining work

1. Research every unresolved ID listed in `glossary-evidence.json`; retain the owner's
   additional-research decision. Also investigate `female-tv-presenter`'s primary
   evidence and the radio-host/Alt attribution conflict.
2. Reconcile every current speaking role, grouped broadcast, alternate Yarn project
   and text-bearing texture. The current extraction is useful but does not prove
   an exhaustive runtime-visible roster. Reconcile supplemental current-table rows
   and do not pull legacy/demo/test-only identities into current canon.
3. Check all character biographies, recurring concepts, UI distinctions and item
   effects against enough source context. Add missing concepts by meaning, not quota.
4. Resolve material questions, then perform two consecutive clean full-entry audits
   of unchanged content. Current accepted clean full audits: **0**. A source-key
   match, script row count or JSON validation is not an editorial audit.

No glossary locale translation, CMS publication or production deployment was run.
