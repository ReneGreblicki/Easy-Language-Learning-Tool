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
4. **Selective model repair** — send only flagged rows to `gpt-5.6-luna`. It receives the source,
   draft, and detected error codes and makes the smallest correction. Only residual hard errors
   are escalated to `gpt-4.1`.
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

- Paid workflows are manual-only and share one GitHub Actions concurrency group. A second run
  waits instead of overlapping the first.
- The content pilot has a hard `$0.10` generation budget and `$0.40` review budget. Every model
  request reserves a conservative maximum output allowance before it is sent; a request that could
  exceed the remaining budget is blocked locally.
- The comparison workflow uses five representative language/script options, `gpt-6-luna` as its
  judge, and a combined maximum of `$0.50`. `gpt-6-astra` is not part of the automated workflow.
- Generate once rather than generate plus full-model rewrite.
- Run deterministic checks before paid review.
- Batch repairs in groups of 24 and Google translations in groups of 50 rows.
- Review only flagged rows; never ask a model to rescore clean rows.
- Cache generation checkpoints and content-bound translation evidence.
- Refresh independent evidence only for changed rows after repair.
- Use the 5,000-word lists as a zero-cost confidence signal, while treating absence as a review
  warning because valid inflections and constructions may not be exact lemmas.
- Fail closed after two repair stages. Repeated model calls are more likely to add cost than truth.

## Google Cloud Translation use and safeguards

Cloud Translation Basic v2 is used only during the maintainer-run content build. It receives the
generated target word and sentence and translates them back to English. It never receives an app
account, email address, device identifier, analytics event, API credential, or other end-user data.
The result is independent evidence, not the published answer: deterministic rules compare it with
the pinned English sense and quarantine conflicts.

The pilot is blocked before its first Google request when it would exceed either 100,000 source
characters or 48 requests. Each request contains at most 50 rows. Automatic retries are disabled
for Google calls because repeating a request could be billable. Every successful batch is saved in
a content-addressed checkpoint and restored by GitHub Actions on a later run. Changed rows consume
the remaining cap; they do not receive a fresh second allowance.

The API key is read only from the `GOOGLE_TRANSLATE_API_KEY` GitHub Actions secret. It is sent in the
`X-goog-api-key` header rather than the URL, is never written to an artifact, and is scoped only to
the review step. In Google Cloud, the key must be restricted to the Cloud Translation API. Set the
project's **Characters sent to general model per project per day** quota to 100,000 for the pilot.
That provider-side character quota is the final hard stop if local controls fail. Billing budgets
and alerts should also be enabled, but alerts alone are not spending caps.

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
  key to the Cloud Translation API. GitHub-hosted runner addresses are dynamic, so the provider
  character quota—not an IP allow-list—is the reliable provider-side hard limit.

If Google Cloud is not used, provide a JSON export from another independent translator with one row
per language/concept containing `language`, `id`, `backtranslated_word`,
`backtranslated_sentence`, and the content-bound `source_sha256`. Missing independent evidence
prevents approval.

## Commands

```bash
python tools/build_default_decks.py --pilot --model gpt-4o-mini \
  --editorial-mode selective --max-cost-usd 0.10 --output default-deck-pilot

python tools/review_default_deck_curriculum.py \
  default-deck-pilot/curriculum.json --repair-model gpt-5.6-luna \
  --escalation-model gpt-4.1 --max-openai-cost-usd 0.40 \
  --max-google-characters 100000 --max-google-requests 48 \
  --output default-deck-reviewed

python tools/default_deck_quality.py \
  default-deck-reviewed/reviewed_curriculum.json \
  --backtranslations default-deck-reviewed/independent_backtranslations.json \
  --output default-deck-final
```

Run the 30-row-per-language pilot first. A full 1,000-row-per-language build may proceed only after
the pilot creates `review.json` and the residual-warning distribution has been inspected.
