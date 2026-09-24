# Automated default-deck accuracy and cost-control workflow

## Decision

Generated content is never trusted because one model produced it. Every row must accumulate a
content-bound Google-draft/GPT-edit provenance chain and pass a final network-free release gate.
Unresolved rows are quarantined; the pipeline never substitutes a plausible guess or publishes a
partial curriculum.

## Workflow

1. **Pinned source validation** — verify the exact SHA-256 of the 120,000-row corpus, 24 language
   options, contiguous ranks, normalized uniqueness, and expected scripts.
2. **Canonical English generation** — use `gpt-5.6-luna` once to create the 1,000 English examples
   and senses.
3. **Google sentence draft** — translate each English sentence with Cloud Translation Basic v2.
   Thai Paiboon is produced from the reviewed Thai-script row by the dedicated tone-marked prompt.
4. **Luna post-edit** — retain accurate Google wording, but correct grammar, CEFR complexity and
   meaning while selecting a dictionary headword that matches the embedded target-language top-5,000
   corpus. A frequent but semantically unrelated candidate is never accepted.
5. **Free deterministic triage** — inspect every row for structure, IDs, CEFR allocation, source
   sense, script, placeholders, English leakage, duplicate sentences, numbers, frequency-list
   membership, source rank, and headword use.
6. **Selective adjudication** — send only flagged rows to `gpt-4.1-mini`. It receives the source,
   Google draft, Luna result and detected error codes and makes the smallest correction.
7. **Network-free final verification** — run `default_deck_quality.py`, which contains no HTTP or
   provider integration. It rechecks every row, both content hashes, the corpus checksum, complete
   hybrid-evidence coverage, and all release rules. It creates `review.json` only when there are zero
   hard errors and 100% evidence coverage.
8. **Publication binding** — publication still requires a manifest whose SHA-256 matches the exact
   reviewed curriculum. Any later edit invalidates approval.

## Cost controls

- Paid workflows are manual-only and share one GitHub Actions concurrency group. A second run
  waits instead of overlapping the first.
- The pilot has a hard `$0.50` build-model budget and `$0.50` adjudication budget. Every model
  request reserves a conservative maximum output allowance before it is sent; a request that could
  exceed the remaining budget is blocked locally.
- A full build is capped at `$4` for English generation and Luna post-editing, 950,000 Google source
  characters (`$19` without any free credit), and `$1` for selective adjudication. The aggregate
  worst-case cap is `$24`, leaving `$1` below the requested `$25` ceiling.
- The comparison workflow uses five representative language/script options, `gpt-6-luna` as its
  judge, and a combined maximum of `$0.50`. `gpt-6-astra` is not part of the automated workflow.
- Generate English once, translate once, and post-edit once.
- Run deterministic checks before paid review.
- Batch repairs in groups of 24 and Google translations in groups of 50 rows.
- Review only flagged rows; never ask a model to rescore clean rows.
- Cache generation checkpoints and content-bound translation evidence.
- Rebind hybrid evidence to the corrected row hash after adjudication.
- Use the 5,000-word lists as a zero-cost confidence signal, while treating absence as a review
  warning because valid inflections and constructions may not be exact lemmas.
- Fail closed after two repair stages. Repeated model calls are more likely to add cost than truth.

## Google Cloud Translation use and safeguards

Cloud Translation Basic v2 is used only during the maintainer-run content build. It receives only
the generated English sentences and creates target-language drafts. It never receives an app
account, email address, device identifier, analytics event, API credential, or other end-user data.
The result is not published directly: Luna must post-edit it against the pinned English sense,
CEFR level and target-language frequency corpus.

The complete Google plan is calculated before the first request. The pilot is blocked when it would
exceed 100,000 source characters or 48 requests; a full build is blocked above 950,000 characters or
1,100 requests. Each request contains at most 20 sentences so its GPT post-edit checkpoint has the
same content boundary. Automatic retries are disabled
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
| `hybrid_evidence.json` | Google draft, editor/adjudicator models and content-bound source/target hashes |
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
- `GOOGLE_TRANSLATE_API_KEY` — official Google Cloud Translation v2 sentence drafts. Restrict the
  key to the Cloud Translation API. GitHub-hosted runner addresses are dynamic, so the provider
  character quota—not an IP allow-list—is the reliable provider-side hard limit.

## Commands

```bash
python tools/build_default_decks.py --pilot --pipeline hybrid --model gpt-5.6-luna \
  --max-cost-usd 0.50 --max-google-characters 100000 \
  --max-google-requests 48 --output default-deck-pilot

python tools/review_default_deck_curriculum.py \
  default-deck-pilot/curriculum.json \
  --hybrid-evidence default-deck-pilot/hybrid_evidence.json \
  --repair-model gpt-4.1-mini --escalation-model gpt-4.1-mini \
  --max-openai-cost-usd 0.50 --skip-google \
  --output default-deck-reviewed

python tools/default_deck_quality.py \
  default-deck-reviewed/reviewed_curriculum.json \
  --hybrid-evidence default-deck-reviewed/hybrid_evidence.json \
  --output default-deck-final
```

Run the 30-row-per-language pilot first. A full 1,000-row-per-language build may proceed only after
the automated pilot creates `review.json`. With the 100,000-character provider quota, the resumable
full build is expected to require approximately ten daily runs; completed batches are not repurchased.
