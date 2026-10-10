# UnityFS equal-size final block repair

The Hungarian screenshot run `outputs/six-scenes-all-locales-v1/hu` displayed
`No translation found` in place of UI strings. Its archive and installed file
SHA-256 values matched, but Unity rejected the locale table bundle. The original
failure log records provided CRC `6e45ed0a` and calculated CRC `0adc3049`.
The failure is at bundle decoding, before translation lookup; missing-font or
translation-content changes do not repair that boundary.

UnityPy 1.25.4's `CompressionHelper.chunk_based_compress` uses `>=` when deciding
whether a complete chunk should be stored raw, but `>` for its final chunk.
The Hungarian carrier has 70 blocks. Its last 96 payload bytes also produce
96 LZ4 bytes, so the helper emits codec 2 despite equal stored/raw lengths.
Unity's observed loader treats this size-equal block as raw. Decoding that one
block as raw reproduces the exact runtime CRC `0adc3049`; decoding its LZ4 flags
with UnityPy reproduces `6e45ed0a`. A UnityPy-only round trip therefore misses
the defect.

`Scripts/unity_bundle_writer.py` owns the compressed envelope, preserving the
complete uncompressed payload and directory. It stores every size-equal block
as the original raw bytes with codec 0. Genuinely smaller LZ4 blocks retain
compression. `build_locale_probe.save_verified` uses this shared writer, so
native-locale and translated overlay rebuilds retain the fix. Original objects
and allowed changes are still compared by the existing serializer verifier.
CRC validation stays enabled. Unity calculates CRC from uncompressed content;
see the [Unity integrity documentation](https://docs.unity.com/en-us/engine/6000.3/manual/assets-and-media/assets-managing-runtime/assetbundles-section/asset-bundles-integrity).

The repaired Hungarian table keeps the same CRC `6e45ed0a`, all 19 serialized
objects and the exact uncompressed payload SHA-256
`832353df14e632e06d7cff07e4d27971835088915fe640dced94d479d75ae971`.
Only its compressed envelope and the catalog's bundle-size field change.
The original archive remains immutable. `Scripts/repack_locale_bundle.py`
creates a new verified artifact from that archive without reauthoring strings.

An exhaustive offline scan of all 294 UnityFS artifacts in the 14 currently
selected archives found this ambiguous block only in Hungarian. That scan
checks compression boundaries; it does not claim runtime or linguistic review
of all locales. The screenshot planner now rejects ambiguous compressed
blocks before installing a locale and chooses the latest numbered verified
runtime-preview archive.

## Regression boundary

`Tests/test_unity_bundle_writer.py` checks the exact failing Hungarian artifact
and observed CRC pair, a deterministic 96-byte equal-size final-chunk
reproducer, compressible/incompressible positive controls, and an unchanged
Czech package. The corrected envelope must retain directory and decompressed
payload exactly, keep CRC enabled, and match both flag-driven decoding and the
observed Unity size-equal boundary. Existing catalog tests additionally check
that integrity edits stay within the intended field span and reject bad
original integrity values.

The size-equal CRC checker emulates the observed decoder boundary. It is not
proof of Unity runtime behavior. The unsqueezed diagnostic and the final fixed
LZ4 archive are separately loaded in the actual isolated game; source, build,
archive, installed payload, native captures and restoration evidence retain
separate hashes. Never accept the broken run's menu/Settings as valid localized
screenshots merely because visual state recognition succeeded.
