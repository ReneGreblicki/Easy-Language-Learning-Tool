# Deck Generation Speed, Quality, and Price Optimisation Framework

## 1. Objective

Minimise complete deck-generation time and effective cost while preserving the accepted output
quality of the existing mobile generator. Quality is a release gate, not a tradeable average.

Decision weights after every hard quality gate passes:

- Quality: 50%
- Speed: 35%
- Price: 15%

## 2. Production configuration

| Component | Current setting |
|---|---|
| Primary model | `gpt-4o-mini` |
| Selective fallback | `gpt-5.6-terra` with reasoning effort `none` |
| Batch size | 24 rows |
| Concurrent batches | 6 |
| Primary attempts | 2 |
| Fallback condition | Primary request or deterministic validation fails twice |
| Published deck condition | Every batch completed and every expected row accepted |

The Further Learning recommendation model remains separately configured through
`OPENAI_MODEL`. Deck generation uses `OPENAI_GENERATION_MODEL` and
`OPENAI_GENERATION_FALLBACK_MODEL`, so optimisation cannot accidentally change recommendation
behaviour.

## 3. Quality gates

Every provider response must satisfy the strict JSON schema and all deterministic gates before it
can be stored:

1. Exact expected row count and row numbers.
2. No duplicate row numbers.
3. All four learning and translation fields are non-empty.
4. The generated learning-language word appears in its sentence.
5. No duplicate learning-language sentence within the batch.
6. Requested questions end with question punctuation.
7. Non-Thai sentences do not exceed the configured CEFR word limit.
8. Thai-script output contains Thai characters.
9. Paiboon-romanized Thai output contains no Thai characters.

A primary response that fails any gate is retried once. A second failure routes the entire batch
to the quality fallback. A fallback failure fails the job rather than publishing a partial or
unvalidated deck.

Semantic translation, naturalness, grammatical-person, part-of-speech, and CEFR-vocabulary
quality must also be assessed through a repeatable benchmark and stratified human review before
removing or weakening the fallback.

## 4. Evaluation dataset

Use the same fixed tasks for every model and configuration. The benchmark should cover:

- every supported learning language and script;
- A1 through C2;
- questions and statements;
- every grammatical-person assignment;
- regular, irregular, and invariant forms;
- common and lower-frequency ranks;
- ambiguous words;
- Thai script and Paiboon romanization.

Run every candidate at least three times. Do not compare models on different task sets.

## 5. Metrics

### Quality

Track schema validity, accepted-row rate, target-word inclusion, translation accuracy,
naturalness, grammar, CEFR suitability, script compliance, and duplicate rate.

Minimum production gates:

- 100% valid stored JSON and expected rows;
- at least 99.5% target-word inclusion;
- at least 98% acceptable translations;
- at least 97% natural sentences;
- at least 99% script compliance;
- no more than 1% duplicate or near-duplicate sentences;
- no statistically meaningful quality decline from the approved baseline.

### Speed

Primary metric:

```
accepted rows per minute =
accepted rows / (provider latency + retries + fallback latency)
```

Also report deck completion time, batch P50/P95 latency, retry rate, fallback rate, queue delay,
and rate-limit errors.

### Price

Primary metric:

```
cost per 1,000 accepted rows =
(input + output + retries + fallbacks) / accepted rows * 1,000
```

Pricing is configuration data and must be updated from the provider's current price sheet rather
than hard-coded into validation logic.

## 6. Telemetry

Each batch records:

- primary and accepted provider model;
- fallback model and whether it was used;
- attempt count;
- accepted rows;
- input and output tokens;
- cumulative provider latency;
- start and completion timestamps;
- validation errors that triggered fallback.

Each completed job records total input/output tokens, cumulative provider latency, fallback batch
count, model configuration, and completed rows.

## 7. Composite decision score

Only candidates that pass every hard quality gate are scored.

```
final score = 0.50 * quality + 0.35 * speed + 0.15 * price
```

Speed and price are normalized against the current approved baseline and capped at 150 to prevent
an extremely fast or cheap model from hiding a quality regression.

## 8. Operational thresholds

Investigate or roll back when any of the following occurs:

- accepted quality falls below 97%;
- fallback rate exceeds 5%;
- retry rate exceeds 3%;
- P95 batch latency rises more than 25% above baseline;
- cost per 1,000 accepted rows rises more than 20%;
- duplicate rate exceeds 1%;
- script compliance falls below 99%.

Rollback requires changing the server-side generation model secret or reverting the deployment;
no APK update is required.

## 9. Controlled optimisation sequence

1. Establish the `gpt-5-mini` historical baseline.
2. Run the fixed benchmark with `gpt-4o-mini`.
3. Review automated results and a blind stratified human sample.
4. Monitor the limited production rollout.
5. Compare 24x6 against alternative batch/concurrency configurations without changing models.
6. Promote only configurations on the quality-speed-price Pareto frontier.
7. Pin an approved model snapshot after benchmark stability is established.
