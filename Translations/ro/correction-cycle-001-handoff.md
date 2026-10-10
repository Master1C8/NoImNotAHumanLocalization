# Romanian correction cycle 001: independent-review handoff

Game: No, I'm not a Human 1.3.19. Locale: `ro` from Russian `ru`. Scope: text only; translated images and textures are excluded. Author status only. Root assigns an identifiable independent reviewer. No editorial, runtime, visual, package, or release acceptance is claimed.

## Pinned inputs and first pass

- Accepted source: 16,538 IDs (16,360 table, 178 supplemental static TMP). `Source/localization-inventory-v3/strings.jsonl` SHA-256 `ecd96645c2ca6f23f8bf3ab2fcf65709e961478ae15a38e83d94cc335a408bf0`; `static-text.jsonl` SHA-256 `3791c851b1c2282b2908ba288830df07110a9d9fcc75d7e86e710e8485024efc`.
- Exact manifest: `Source/preserve-exactly-v4.json` SHA-256 `d431b758ca205925e637e2020ac60f47a290d9680299b1774387d951079fe226`.
- Approved Romanian glossary: `Documentation/glossary-translations/ro/layer.json` SHA-256 `c67cc629aa173a6710090c12cb5ccfea5adb0bbeb0136fc5df06039196b499c9`; the SiteForMods reviewed layer has the same raw SHA-256.
- `Translations/ro/semantic-review-progress.json` pins all 16,538 first-pass reviewed units, 415 pre-correction authored file hashes, 121 immutable review segments, and 46 finding files containing 71 findings. The first 260-row finding file is only one part. The first-pass progress SHA-256 remains pinned in the plan and closure manifest; the first-pass rows and finding files were not rewritten.

## Correction and closure

- `correction-cycle-001-plan.json`: all 71 findings adjudicated, 71 accepted, four proposals reworded after context review, zero rejected. The plan contains exact source, before, after, reason, ID, authored path and entry index for every correction. It passed a projected full 16,538-row preserve-exact check before application. Plan SHA-256: `df9f621aeff88bbbc4b43d25b0ae53ddceb24cbb91fb0517248ceefbd480bfe0`.
- The 71 values were applied in 55 authored files (54 table batches and `static-text-draft.json`). No repeat-expansion map or credits role map was affected; their recipes remain unchanged. All 55 affected structural validators passed and refreshed their locale-owned sidecars.
- Reviewer set: `correction-cycle-001-closure-v3/manifest.json`, SHA-256 `7254db26ef4cd24b881a7afb4519bf31f17fb8c6c1c1d799c85c21d43c3faf88`. It pins 71 changed IDs and 3,090 closure IDs in canonical order, plus 396 scene/branch-context IDs, 71 exact-repetition IDs, 2,306 glossary/referent occurrence IDs, 35 runtime-binding IDs, and 2,643 mandatory-regression IDs. Components overlap. The manifest hashes every component list, review row, dynamic context file, before/after authored file and affected validator sidecar. All ID files use UTF-8 LF with a final LF; the review rows are JSONL with the same newline convention.
- Earlier `correction-cycle-001-closure/` and `correction-cycle-001-closure-v2/` are immutable superseded selector drafts, not reviewer sets. The first pulled unrelated character dialogue through a key-alternative predicate; the second missed eye and family-role occurrences. The v3 recipe is `correction-cycle-001-recipe-v3.py`, pinned by the v3 manifest.
- `correction-cycle-001-full-exact.validation.json` records the post-correction 16,538/16,538 exact check, SHA-256 `22da2efe204ddebe406e0dd6cf94d5aea145f97d26766d6c0d543b74119dd655`. The project read-only command `.venv/bin/python Scripts/report_locale_readiness.py --exact --compact` also returned `ro 16538/16538 validated=16538 observed=16538 problems=0` after sidecar regeneration. No shared state was updated.

## Static TMP source role and source finding

`tmp:level0:2016:m_text` is `Super speed` in `InGameDevMenu > Panel (initialActive=false) > PlayerTab > SuperSpeed > Label`, with no localized-string binding. The bounded asset evidence in `Documentation/static-text-scope-v2.json` (SHA-256 `1236570c4ff15bb00eed3b5d4b7cbf8a2b2291772e4c028c69c0836cbb11edaa`) classifies it as a developer-menu control. Its Romanian correction is `Superviteză`. Release reachability is still unverified. `source-findings-cycle-001.json` records the shared source metadata proposal separately; no protected source or glossary was edited.

## Reviewer procedure and limits

1. Verify pinned inputs, plan, closure manifest and current authored hashes. Run `.venv/bin/python Translations/ro/correction-cycle-001-recipe-v3.py verify-closure`. This verifies hashes and corrected values. For an independent selector regeneration, use the pinned recipe with a fresh locale-owned output directory and compare component ID-file contents; do not overwrite any immutable closure.
2. Read `correction-cycle-001-closure-v3/review-rows.jsonl` source/before/after with the approved glossary, full relevant scene/branch keys, exact repetitions, referent roles and mandatory regression component lists. Check every changed replacement as a complete unit, not merely its edited phrase. Use `changed-ids.txt` and `closure-ids.txt` as the exact cycle lists.
3. Check `dynamic-consumer-context.json` for the occupied-room `{0}` branch and the corrected BigLebowski rhyme. It assembles two sample occupant substitutions and retains the related branch rows. The flattened string table does not prove executable Yarn order, trimming or every live occupant value; those remain runtime questions, not passed checks.
4. Record objective findings and an exact delta. If edits follow, use corrected IDs plus newly added closure IDs plus explicitly invalidated prior evidence, preserving every prior closure. Check the mandatory regression catalog in that diff cycle. A clean independent result must name the reviewer and the exact unchanged artifact and closure hashes.

The correction recipe normalized JSON formatting in four touched batches (`dialogue-batch-003`, `dialogue-batch-006`, `ui-batch-003`, `ui-batch-005`). Their original byte layouts cannot be reconstructed by the recipe, while all 16,538 original stable IDs/targets and every unchanged target field were checked against immutable first-pass rows. The closure manifest pins each before and after file hash. The independent reviewer should inspect these four complete batch diffs for any non-text field change.

Next action: root assigns independent dependency-aware review of the v3 closure and regression catalog. Runtime and visual testing remain out of this author task.
