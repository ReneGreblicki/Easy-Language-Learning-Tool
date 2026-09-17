begin;

alter table public.mobile_generation_jobs
    add column if not exists primary_model text,
    add column if not exists fallback_model text,
    add column if not exists fallback_batches integer not null default 0
        check (fallback_batches >= 0),
    add column if not exists input_tokens bigint not null default 0
        check (input_tokens >= 0),
    add column if not exists output_tokens bigint not null default 0
        check (output_tokens >= 0),
    add column if not exists generation_latency_ms bigint not null default 0
        check (generation_latency_ms >= 0);

alter table public.mobile_generation_batches
    add column if not exists provider_model text,
    add column if not exists fallback_model text,
    add column if not exists used_fallback boolean not null default false,
    add column if not exists attempt_count integer not null default 0
        check (attempt_count >= 0),
    add column if not exists accepted_rows integer not null default 0
        check (accepted_rows >= 0),
    add column if not exists input_tokens bigint not null default 0
        check (input_tokens >= 0),
    add column if not exists output_tokens bigint not null default 0
        check (output_tokens >= 0),
    add column if not exists latency_ms bigint not null default 0
        check (latency_ms >= 0),
    add column if not exists started_at timestamptz,
    add column if not exists completed_at timestamptz,
    add column if not exists validation_errors jsonb not null default '[]'::jsonb;

create index if not exists mobile_generation_batches_metrics_idx
    on public.mobile_generation_batches(job_id, used_fallback, completed_at);

commit;
