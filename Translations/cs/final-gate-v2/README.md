# Czech final gate v2

The batch192 current structural sidecar has been refreshed by the normal owning
CLI. Its exact previous bytes are retained in
`dialogue-batch-192.validation.preimage.json` with SHA-256
`0552c4ce248d8a7c263f1faf758f9b6994db7a2053888ba6f29ba28984dfd5e0`.
`sidecar-repair.json` binds the original, archived and current receipts and the
owning CLI stdout. All 411 authored file hashes and the other 410 current
sidecars remain unchanged. The complete original `../final-gate/` directory
and all reviewed receipts remain unchanged.

Run from the canonical checkout:

```sh
.venv/bin/python -B Translations/cs/final-gate-v2/verify.py
```

The verifier checks the complete first semantic pass, correction chain,
source/glossary/context, current text and sidecars, clean review04,
1,131 closure decisions (one fresh and 1,130 prior), 178 unique mandatory
unchanged independent decisions, static/credits/repetition derivations and
the unchanged canonical preserve-exact and locale-only corpus receipts.

It executes `accept_locale_text.accept` through every real guard before the
first persistent write. That write is intercepted and no acceptance receipt
is created. It then exercises the actual `accepted_inputs` checks using only
the prospective receipt in memory. This substitutes the receipt storage/read
boundary; it does not issue root editorial acceptance or establish runtime
behavior.

`root-handoff.json` is the current author handoff; `integration-plan.json`
contains the exact proposed authored/evidence path and hash sets, and
`integration-hashes.json` pins the final gate and handoff. The canonical
preserve-exact receipt remains at `../final-gate/preserve-exact.json` because
the authored set is byte-identical. The former sidecar blocker in v1 remains
historical evidence and is resolved for this handoff.

Root owns acceptance, build and Git integration. Existing progress documents
were not rewritten; their exact hashes are retained in `pre-repair-pins.json`.
Source ambiguities, historical batch020 serializer reconstruction versus
unavailable separately persisted old bytes, and unrun runtime/font/layout
checks retain their previous limits. Images and textures remain outside scope.
