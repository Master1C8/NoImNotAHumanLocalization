# Czech integration status

The earlier shared-state glossary fingerprint mismatch is resolved. The current `cs` row in `Documentation/localization-state.json` and the approved Czech glossary layer both pin SHA-256 `15387d7d390dd7fde7556b067854fbb08139b46e2831cca0357f5f6b32521d24`. The accepted text source remains `Documentation/text-source-acceptance-v1.json`, SHA-256 `a70750766d64d031aa5ff67ac5c0eb6212014768764bbd66f667d1d9e1b971ce`.

The Czech authored draft covers all 16,538 accepted visible IDs: 259 UI, 16,100 Dialogs, one selected ChecksDialogs entry and 178 supplemental static fields. The 410 table batches pass the project validator. `Translations/cs/static-text-draft.json` contains the static fields and its Czech-specific validation sidecar checks accepted IDs, source order, markup, placeholders, line breaks and the credits structure. Exact hashes, input pins and remaining work are in `Documentation/cs-text-checkpoint.json`.

Full semantic review, independent source-to-target diff review, assembled preserve-exactly checks and renderer/runtime testing remain pending. The shared row's translated count is a separate integration snapshot and should be reconciled from the accepted Czech corpus when the coordinator owns the shared write. Do not promote draft coverage to editorial acceptance.

Proposed terminology delta for coordinator review: Dialogs ID `110504457773588487` contrasts `Гостевой` (`Hostovec`, already in the approved glossary) with `Духовой`. The Czech draft uses `Duchovec` for the latter and retains the next sentence's explanation that it is the spirit of a dead person. Add `Духовой` → `Duchovec` to the shared Czech glossary only if the glossary coordinator accepts this additional term; no shared glossary file was changed here.

The Czech author has not changed shared state, the Git index, build helpers or the isolated game fixture. The integration coordinator should stage the complete Czech change only after final editorial and technical acceptance, inspect the full staged diff against other locale work, then commit and verify the resulting canonical tree and HEAD.
