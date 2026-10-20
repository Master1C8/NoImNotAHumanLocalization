# Romanian batch validation finding

`Scripts/validate_game_text_batch.py` accepted `Translations/ro/ui-batch-002.json`
when the target for UI ID `66450728108675072` was `Română`. The Russian source is
`Русский`, the label for the Russian option in the language selector.
`Source/preserve-exactly-v4.json` marks this ID `wholeTextExact: true`. A direct
call to `preserve_exact.check_value` rejected the batch with
`Whole-text exact value mismatch`. The Romanian batch now retains `Русский` and
passes the exact contract.

## Proposed shared delta for the integration coordinator

Have `validate_game_text_batch.py` load the pinned preserve-exact manifest and
call its shared `check_value` for every authored stable ID before writing a
successful validation sidecar. Check the manifest's source inventory and scope
hashes first. Keep the existing collection, ID, order and glossary checks. This
would apply the same grammar, whole-value and designated-substring contract
during each batch, rather than waiting for complete locale coverage.

Add a focused regression with otherwise valid UI batch metadata and two cases
that differ only in this target value:

- `Русский` passes.
- `Română` fails specifically at the `wholeTextExact` boundary.

The shared validator and tests are outside the Romanian chat's write ownership.
