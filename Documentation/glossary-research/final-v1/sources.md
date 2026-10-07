# Russian canonical source glossary

Game: No, I'm not a Human, build 1.3.19. Source language: Russian (`ru`).
Owner-selected intended use: standard localization. Final glossary: 201 entries.
The exact final text passed two consecutive full-entry editorial readings with no
new findings. Their explicit coverage, artifact hashes and limitations are recorded
in `editorial-audits.json`; counts and JSON validation are not editorial evidence.

## Canonical inputs and delivery

Game checkout: `/Users/antonkrutov/Desktop/no I'm not a human`.
Master source: `/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary.json`.
All terms and meanings are explicitly authored Russian text in `characters.tsv`,
`voices.tsv`, `additional-voices.tsv` and `concepts.tsv`. The assembler only copies
those fields, approved agreement sentences and exact source excerpts. It does not
translate or generate descriptions. `supporting-keys.json` adds source context.
Reproduce the reviewed result from the game root with:

```sh
.venv/bin/python Scripts/build_source_glossary.py --output Documentation/glossary-research/final-v1 --review Documentation/glossary-research/editorial-audits.json
```

The review option accepts only a manual record matching the exact glossary, authored
inputs, source corpus, extractor, decisions and supporting keys. An unchanged script
run alone cannot approve a glossary. Changed text or inputs invalidate that record.
Earlier draft-v1, draft-v2 and review-candidate snapshots remain historical evidence;
their pending review states do not describe the final result.

## Selected source and roster

Pinned original build: Unity 6000.3.10f1, build GUID
`c003ddc7de634775a85305fef3b9a0d3`. The six original extraction inputs were rechecked
before finalization and matched. Russian extraction contains 52,788 serialized rows
across nine collections. Current Dialogs: 16,100 rows, including 15,693 compiled line
IDs and 407 supplemental current-table IDs. No compiled ID lacks Russian text. UI:
259 rows. These counts prove extraction properties, not runtime reachability.

Runtime level1 binds the current Dialogs GUID
`444ff14f1967f5a4c8eb9e4cf4c913f1` through YarnRunner/provider and the sharedassets0
Yarn project. The alternative resources Yarn project has an empty compiled program.
Legacy/demo/test-only material is retained for research but does not define current
canon. Full roster reconciliation is in `roster-review.json`: every explicit current
speaker code is mapped, phone/radio/TV roles are separated by scene, and bare-line
node families and the 57 rows lacking node metadata were adjudicated. Window and
Super narration are not extra NPCs. Death, Prophet, Mushroom Eater and the child
vision contexts were checked rather than treating every unprefixed line as narration.

The glossary contains 73 character/group/entity cards, 50 voice/participant/reference
cards and 78 concept cards. These are glossary counts, not a claim of 123 distinct
individual people. Group cards remain useful references beside individual roles.
Old stable IDs and their relative order are preserved; the player remains first.

## Owner decisions and uncertainty

The owner requested Russian communication and permitted fan wikis. Additional
research preceded approval of a safe strategy for the exact anonymous-role list.
On 2026-10-08 the owner answered «Да, закрепить это правило для перечисленных ролей»
for 28 anonymous roles and four reference groups. Two later roles,
`radio-ending-address` and `tv-fema-promotion`, were separately approved with
«Да, применить то же правило». `uncertainty-decision.json` records all 34 exact IDs.
The decision is not automatically extended to future entries.

For these roles, sex remains unknown. Preserve source pronouns, number of participants,
actions and speaker boundaries; do not add sex absent from the original. Neutral
wording must preserve agency. This resolves the translation strategy without inventing
identity, biological sex or human-versus-machine nature. The French recruitment
line's masculine wording does not override Russian plural wording. Cat and Death
retain their separate source-context agreement rules, without a biological claim.

## Supporting external sources

Facts below were checked in indexed page content returned by web search. Some Fandom
direct opens were blocked; they are not represented as successful direct reads.
Pinned Russian primary evidence takes precedence over speculation or version mismatch.

- [News Reporter](https://no-i-am-not-a-human.fandom.com/wiki/News_Reporter) and
  [Weather Reporter](https://no-i-am-not-a-human.fandom.com/wiki/Weather_Reporter):
  male roles stated by their infoboxes; news and forecast remain separate.
- [CR Channel](https://no-i-am-not-a-human.fandom.com/wiki/CR_Channel): female
  references support Female TV Presenter in the unusual interrupted eighth-day
  broadcast. This does not identify the advertising or FEMA promotion voices.
- [FEMA Agent](https://no-i-am-not-a-human.fandom.com/wiki/FEMA_Agent): male role;
  uncertainty about whether every visit is the same individual is retained.
- [Phone](https://no-i-am-not-a-human.fandom.com/wiki/Phone), its separate call
  transcripts, and [Radio](https://no-i-am-not-a-human.fandom.com/wiki/Radio):
  additional scene/participant comparison did not establish the unknown voices' sex.
- [Tattooed Woman](https://no-i-am-not-a-human.fandom.com/wiki/Tattooed_Woman):
  suggested radio association is not adopted; the current Russian host says «я знал».
- [Seductive Woman](https://no-i-am-not-a-human.fandom.com/wiki/Seductive_Woman):
  supports the final woman/child context; conditional pregnancy and child claims
  remain conditional. [Endings](https://no-i-am-not-a-human.fandom.com/wiki/Endings)
  supports identification of existing Prophet and Mushroom Eater ending speakers.
- [IT](https://no-i-am-not-a-human.fandom.com/wiki/IT): auxiliary fan label only.
  The Blind man's source account distinguishes the creature from the pale man.
- [Minor Characters](https://no-i-am-not-a-human.fandom.com/wiki/Minor_Characters):
  checked as supporting context, without adopting unofficial personal names.

No developer-provided terminology guide was established. A purported media kit with
mismatched developer/release information was rejected as an official authority.

## Material corrections made before clean audits

Primary-key excerpts are retained per entry in `glossary-evidence.json`.
The pale suspect is explicitly male in tv_2_extra2; the story about stolen skin is
explicitly unconfirmed. The angry husband assaults his wife after her announcement,
not an invented chronology. Couple speech, wife actions and husband shooting are
separated. Wheelchair variants are not one immutable disability biography. Jacket's
brother was forcibly recruited by КЧС, explicitly not taken to a quarantine zone.
FormerFema's contradictory entrance explanations are not accepted as stable biography.
Vigilante's outskirts-house killings are not merged with an unidentified TV shooter.
The Smile Guide's three poetic pages are present in UI Game_MushroomList.
Photo/ear/self-inspection actions and late signs were added, with doubt and explanations
preserved. «Отпустить» in the inspection menu does not mean evicting a resident.

## Image evidence and practical limits

`texture-review.json` records texture-name inventories, source/image hashes and
15 actual visual inspections. AURACAM, Маргоро and CR CHANNEL are supported by
readable logos. The ear-insect image supports an insect, not an inferred species or
resident identity. Tiny illegible newspaper/calendar marks are not guessed. Russian
Characters_ru contains three asset references, not embedded Texture2D images; that
reference inspection is not a runtime rendering check.

Readiness applies to this canonical source glossary for the selected 1.3.19 corpus.
It is not an exhaustive gameplay playthrough, per-image localized text inventory,
or completed font/rendering QA. The separate game-renderer gate remains incomplete.
No locale glossary translation, CMS publication or production deployment was performed.
Per-request model token telemetry is unavailable; no estimates are recorded.
