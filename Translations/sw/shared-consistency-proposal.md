# Proposed shared exact-source consistency check

## Finding

During Swahili dialogue drafting, the identical Russian line `TV: Минутку…` appeared in separate batches with two Swahili targets (`TV: Subiri kidogo…` and `TV: Dakika moja…`). The Swahili drafts now use `TV: Subiri kidogo…` consistently. Structural batch validation passed both variants because it checks each batch independently.

## Proposed recipe change for the integration coordinator

Before accepting a locale's full batch set, build a mapping from the canonical `Dialogs` source string to every target in that locale. Flag any exact source with more than one target, along with its source IDs and batch paths. Allow an explicit, reviewed context exception only when the source is genuinely ambiguous in different scenes. Apply the same check to all table collections where exact repetition is reused. Keep the check in the shared validation recipe, so regenerated reports preserve it.

## Regression scenario

Create two otherwise valid batches that translate one identical source line to different targets. Each per-batch structural check should pass, while the aggregate consistency check must fail and identify both IDs and files. Change one target to match; the aggregate check should then pass. A matching positive control with two different Russian sources must not be flagged.

This is a proposal only. No shared script or state file was changed during parallel locale work.

## Semantic review guardrail

Swahili draft review also caught two polarity/condition errors that structural checks could not detect: Russian `не позволяешь` was initially rendered as permission, and `Если надо` was initially rendered as the speaker needing something. A later line, `не иждивенец`, initially lost its negation. The editorial recipe should explicitly compare the actor, negation, condition and object of each source-target pair, especially in short follow-up lines whose meaning depends on the previous line.

Regression scenario: pair a Russian negative statement with a Swahili affirmative statement that keeps the same nouns and speaker prefix. Structural validation should pass, while the semantic audit must reject the polarity change and point to the exact source and target. Use a matching corrected Swahili negative statement as the positive control.

Character codes are not story facts. In the `FormerFema` scene, the speaker explicitly says he did not work for KHD and took the uniform from a corpse. An editorial review and its progress report should derive identity from the source scene and approved glossary, not from the code name. Regression scenario: show the reviewer a misleading speaker code and a source line denying the implied affiliation; the accepted target and review note must preserve the denial.

An unprefixed player choice must remain unprefixed even when neighboring dialogue uses a character code. The Russian choice `Ошибаешься. Я бы с удовольствием не пускал таких сопляков, как ты` was initially drafted with an added `Tourist:` prefix; the per-batch structural validator accepted it. The Swahili draft was corrected before acceptance. Add a shared structural rule that rejects a new speaker/service prefix when the canonical source has none. Regression scenario: use a source player choice without a prefix and an otherwise valid target that starts with `Tourist:`; assert rejection for the added prefix specifically. The matching positive control keeps the same target words without the prefix and passes.
