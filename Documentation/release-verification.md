# Published release verification

Windows and universal macOS 0.2.1 were published on October 20, 2026.
Download the platform installer, evidence ZIP and `PUBLICATION-SHA256SUMS` from
[the published release](https://github.com/Master1C8/NoImNotAHumanLocalization/releases/tag/release-0.2.1-4b1fdd732a3e).

On macOS run `shasum -a 256 -c PUBLICATION-SHA256SUMS` after downloading all three
ZIPs; when downloading only one platform, compare that file and the evidence ZIP
with their corresponding checksum lines. On Windows use `Get-FileHash <file> -Algorithm SHA256`.

| Platform | Installer | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| windows | `NoHuman-Launcher-Windows-0.2.1.zip` | 86417735 | `869b50f6bf287acd28f2a4ebcc303b70f5838482002f0bd2c8b8292eef830392` |
| macos | `NoHuman-Launcher-macOS-0.2.1.zip` | 87414256 | `783e88e332faa76bdfcab290c0e3f5ed5328fdf31e41b03d0bc630ecd962419c` |

The evidence archive is `NoHuman-0.2.1-4b1fdd732a3e-evidence.zip`, SHA-256
`9e9c06022b854a83dbebc47b3b2e010b4adce9de01b4b90aceecaa9c8240e22a`.
The actual build commit is
[`4b1fdd732a3e47fc4680d13679114e83ca74a2ee`](https://github.com/Master1C8/NoImNotAHumanLocalization/commit/4b1fdd732a3e47fc4680d13679114e83ca74a2ee).
Match it against the release tag, `provenance.json` and the installer ZIP's root
`vnrevival-release.json`, rather than substituting the latest repository HEAD.

The evidence contains the full source-tree listing, build log, retained payload
origin and inventory. Ten native engine checks cover 410 files, ownership,
corrupt input, rollback and continued recovery after interruption. Fault injection
uses a separate test executable; the production engine has its own verification
receipt. These checks do not establish a new real-game playthrough.

This is an unsigned local build record, not a GitHub attestation or independent
security audit. macOS uses ad hoc signing without notarization. The retained payload
is outside the public source repository. Historical records retain their original
creation dates and statuses. Exact source provenance of earlier installer archives
remains unknown; reusing their verified payload does not identify their old binaries.

To build a future release locally, use `Launcher/build-provenance.py --help` from
clean, pushed main with the retained payload and a new output directory.
