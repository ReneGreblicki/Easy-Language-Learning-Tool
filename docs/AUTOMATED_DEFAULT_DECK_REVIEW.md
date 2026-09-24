# Automated default-deck accuracy and cost-control workflow

## Decision

Generated content is never trusted because one model produced it or because another model repeated
it. Every row must accumulate independent evidence and pass a final network-free release gate.
Unresolved rows are quarantined; the pipeline never substitutes a plausible guess or publishes a
partial curriculum.

## Workflow

1. **Pinned source validation** — verify the exact SHA-256 of the 120,000-row corpus, 24 language
   options, contiguous ranks, normalized uniqueness, and expected scripts.
2. **Single-pass generation** — use `gpt-4o-mini` once. The previous all-row editorial pass is
   disabled because it approximately doubled model work without independent evidence.
3. **Free deterministic triage** — inspect every row for structure, IDs, CEFR allocation, source
   sense, script, placeholders, English leakage, duplicate sentences, numbers, frequency-list
   membership, source rank, and headword use.
4. **Selective model repair** — send only flagged rows to `gpt-4.1`. The repair model must differ
   from the generator. It receives the source, draft, and detected error codes and makes the
   smallest correction.
5. **Independent translation evidence** — back-translate every non-English word and sentence with
   the official Google Cloud Translation API. Evidence is content-bound by a row SHA-256. A saved
   export from another translation provider can be supplied instead.
6. **Conflict-only second repair** — send only word/sense or sentence conflicts revealed by
   back-translation to the repair model. Refresh translation evidence only for changed rows.
7. **Network-free final verification** — run `default_deck_quality.py`, which contains no HTTP or
   provider integration. It rechecks every row, the corpus checksum, independent-evidence coverage,
   and all release rules. It creates `review.json` only when there are zero hard errors and 100%
   independent-review coverage.
8. **Publication binding** — publication still requires a manifest whose SHA-256 matches the exact
   reviewed curriculum. Any later edit invalidates approval.

## Cost controls

- Generate once rather than generate plus full-model rewrite.
- Run deterministic checks before paid review.
- Batch repairs in groups of 24 and Google translations in groups of 50 rows.
- Review only flagged rows; never ask a model to rescore clean rows.
- Cache generation checkpoints and content-bound translation evidence.
- Refresh independent evidence only for changed rows after repair.
- Use the 5,000-word lists as a zero-cost confidence signal, while treating absence as a review
  warning because valid inflections and constructions may not be exact lemmas.
- Fail closed after two repair stages. Repeated model calls are more likely to add cost than truth.

## Evidence and outputs

| File | Purpose |
|---|---|
| `reviewed_curriculum.json` | Corrected candidate; still unpublished |
| `independent_backtranslations.json` | Provider, row hash, word and sentence back-translations |
| `offline_verification.json` | Complete findings and per-row accepted/quarantined status |
| `offline_verification.md` | Compact review summary |
| `review_trace.json` | Generator, repair models, calls, tokens, characters, and repair counts |
| `review.json` | Release manifest; exists only after every hard gate passes |

## Agent optimisation

Agents help only after deterministic triage. The economical pattern is:

- partition flagged rows by language/script;
- run independent language-specialist repair agents in parallel;
- use a separate adjudicator only when the generator, translation provider, and specialist disagree;
- keep deterministic final verification outside every agent.

Running several agents over all 24,000 generated rows would multiply cost without guaranteeing
independence. Agents share model weaknesses and should not vote on formatting or source-list facts
that code can establish exactly.

## Required configuration

Repository secrets:

- `OPENAI_API_KEY` — generation and selective repair.
- `GOOGLE_TRANSLATE_API_KEY` — official Google Cloud Translation v2 back-translation. Restrict the
  key to the Translation API and the CI environment.

If Google Cloud is not used, provide a JSON export from another independent translator with one row
per language/concept containing `language`, `id`, `backtranslated_word`,
`backtranslated_sentence`, and the content-bound `source_sha256`. Missing independent evidence
prevents approval.

## Commands

```bash
python tools/build_default_decks.py --pilot --model gpt-4o-mini \
  --editorial-mode selective --output default-deck-pilot

python tools/review_default_deck_curriculum.py \
  default-deck-pilot/curriculum.json --repair-model gpt-4.1 \
  --output default-deck-reviewed

python tools/default_deck_quality.py \
  default-deck-reviewed/reviewed_curriculum.json \
  --backtranslations default-deck-reviewed/independent_backtranslations.json \
  --output default-deck-final
```

Run the 30-row-per-language pilot first. A full 1,000-row-per-language build may proceed only after
the pilot creates `review.json` and the residual-warning distribution has been inspected.
