# Bulgarian text integration proposal

Scope: `bg` only, No, I'm not a Human v1.3.19. Apply after the locale coordinator verifies [bg-text-checkpoint.json](bg-text-checkpoint.json) against the final authored files. This file does not own the shared state or Git index.

The current shared `Documentation/localization-state.json` row already shows `bg` at `translate-edit`, with 320/16,538 authored visible units. Preserve that concurrent edit. The remaining concrete row update is:

| JSON pointer | Current | Proposed |
| --- | --- | --- |
| `/localeRows[locale=bg]/sourceInventoryFingerprint` | `null` | `a70750766d64d031aa5ff67ac5c0eb6212014768764bbd66f667d1d9e1b971ce` |

This fingerprint is the raw SHA-256 of `Documentation/text-source-acceptance-v1.json`, the same scope used by the Thai locale row. Keep `editorial` pending and preserve the earlier menu and Settings probe evidence in `runtime` and `visual`; the newly authored Bulgarian text has not been built or tested in game.

Commit coordination: inspect the complete staged diff and own the exclusive stage, commit, and HEAD verification transaction. The Bulgarian authored files are under `Translations/bg/`; the Bulgarian checkpoint is `Documentation/bg-text-checkpoint.json`. Do not include another locale's unverified files in a Bulgarian completion claim.
