# Indonesian final offline text gate

No, I'm not a Human v1.3.19, source `ru`, target `id`. The first full semantic pass covers 16,538 accepted text units. Independent review 03 is clean on the exact 21-ID final delta and 845 applicable mandatory regression IDs. The text draft covers all 16,538 units; runtime, visual, build, installation and release checks remain separate.

`gate-receipt.json` is the immutable full offline gate result. `run-final.py --verify` reproduces source/glossary, first-pass, correction-chain, accepted-ID, static/credits, preserve-exact, closure and mandatory-decision checks against the frozen sidecars. `run.py --verify` additionally reruns all 331 string batch validators and the static validator; it is deliberately slower. The task-owned full validator sweep already ran every input and left all 332 sidecars byte-identical to the reviewed artifact manifest. Neither recipe launches the game or changes shared scripts/state.

`root-handoff.json` is the standard coordinator input. `integration-set.json` lists exact hashes for the proposed locale-owned path set, excluding those two self-referential manifest files; their hashes are reported separately. `administrative-update.json` pins the exact preimages and after hashes of the only operational checkpoint changes after independent review.
