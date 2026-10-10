# Bulgarian independent review 02

Status: **complete with findings; CLEAN rejected**. Root owns acceptance, author correction, integration and release.

## Read coverage

- Read all **2,110** exact delta source/current Bulgarian full-unit pairs against the approved glossary and compiled consumer context. The delta is 147 corrected ∪ 1,180 new ∪ 894 invalidated; overlaps counted once, retired 0.
- Checked all **908 mandatory regression IDs**: 401 fresh pairs, 507 exact unchanged prior independent decisions. Read all 735 normal voice-risk candidates across 112 literal speaker/choice-prefix categories, including 84 without an explicit source speaker prefix. Four additional selector-risk pairs outside the delta were read.
- Both normal cycle-002 closure/delta verification commands passed at final sealing. All 411 authored files, 411 sidecars and 851 total pinned inputs stayed unchanged. Independently reparsed all 3,255 compiled nodes.

## Findings

**43 consolidated complete replacements** are in `findings.json`; no correction was applied. They include 33 voice-register findings plus idiom, kinship, number-reference, wordplay, scatological register, agency, added detail and grammar findings. Concrete defects include mother/grandmother changed to mother/father, literal translation of “Ёбаный свет”, singular reference replacing plural inspection signs, an added red hue, a changed rock imperative, and malformed “пълна шибания”. Corrected nun, photo/gun referents and static brand/credits wording were read in full.

**One selector finding** is in `selector-findings.json`: six actual source IDs escape v4, four outside the assigned delta. Suggested bounded recipe additions cover посра-, срал-, теребоньк-, смехуеч-, ахуит-, and exact хз/хули, with positive/negative controls. These are review candidates, not six automatic translation defects. Repair the canonical selector recipe and regenerate the exact next dependency delta.

## Evidence and limits

`review.json` is the structured report. `per-id-read-verdicts.json`, `read.ids` and the two mandatory ID lists record exact reads and applicability. `verify_evidence_v2.py` is a read-only reproducibility check. `final-verification.json` records final normal verification and the diagnostic list-order correction; the original failed verifier remains immutable.

The 66 delta dialogue IDs absent from the compiled program were still read as full accepted table units; active runtime reachability is unverified. No game launch, rendering, font/layout, texture, packaging or runtime result is claimed. Of 147 correction-before values, 36 had independently stored prior closure text; the other 111 rely on the author's preserved full-before plan and baseline hashes. This is an exact delta review, not a new full-corpus pass.

Model: Codex GPT-6 family; exact backend/reasoning not exposed. Input, cached input, output, reasoning and total token telemetry are **unknown**; no estimate or zero is substituted. The reporting tail is unmeasured. Coordinator usage is root-owned and separate.
