# Multilingual release verification — 18 September 2026

## Resumed checkpoint

- Production base: `ae37d648abe7ef538503d9205c8d8ef1016306ef` (GPT-4o-mini optimisation, PR #17).
- Multilingual implementation: `19df305470efc9b742e23b049029b348e2845877`.
- Review: PR #18, `feature/add-16-languages-frequency-sources`.
- Candidate versions: desktop 1.5.0; Android 0.5.0.

## Blocker found and repaired

The pushed desktop and Android gzip assets both had SHA-256
`2c035c0524e8466d2debd2018f4ad9758a935cec623a70ce8aa27b57870e0f6a`.
They contained malformed JSON at row 29,660 and failed complete gzip decompression.
The earlier local verification did not establish integrity of the pushed bytes.

Rebuilt the corpus using the checked-in builder, wordfreq 3.1.1, the pinned
FrequencyWords and frekwencja revisions, and the unchanged eight-option production
base from `ae37d64`. The result exactly matches the original manifest checksum:
`8d03860c37448f778a6ac523e1fece6affe8bd0b89112495c60f099e77743c7a`.
Both packaged assets now use those bytes. The manifest records all 32 source-file
hashes and the original base corpus hash. Gzip files are explicitly binary in Git.

Added regression coverage for full gzip/JSON decoding, manifest checksum, identical
desktop/mobile assets, and Flutter asset loading with 5,000 unique contiguous ranks
for every supported language/script option.

## Local verification

- Python: 78 passed, 1 platform-specific skip, 4 subtests passed; 87.45% coverage.
- Ruff lint/format and strict mypy: passed.
- Rebuilt corpus: 120,000 records, 5,000 per language/script option.

## Remaining release checks

- GitHub Windows tests and quality checks on the repaired commit.
- Flutter analysis/tests and release APK build, including the new asset-loading test.
- Windows installer and both macOS package builds; iOS compatibility check.
- Review and merge, followed by server deployment for the new language allowlist.
- Publish desktop 1.5.0 and Android 0.5.0 only after required release checks pass.
- Physical-device acceptance for generation, offline study, and installed TTS voices.

The 90-day inactivity purge remains disabled. Existing desktop files remain outside
the mobile cleanup lifecycle. The model optimisation framework is unchanged.
