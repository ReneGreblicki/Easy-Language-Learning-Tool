begin;

alter table public.decks
    add column if not exists mobile_removed_at timestamptz,
    add column if not exists mobile_purge_after timestamptz,
    add column if not exists last_used_at timestamptz not null default now();

alter table public.decks
    drop constraint if exists decks_mobile_cleanup_window;
alter table public.decks
    add constraint decks_mobile_cleanup_window check (
        (mobile_removed_at is null and mobile_purge_after is null)
        or (
            mobile_removed_at is not null
            and mobile_purge_after >= mobile_removed_at + interval '14 days'
        )
    );

create index if not exists decks_mobile_purge_idx
    on public.decks(user_id, mobile_purge_after)
    where mobile_purge_after is not null;
create index if not exists decks_last_used_idx
    on public.decks(user_id, last_used_at);

alter table public.mobile_generation_usage
    drop constraint if exists mobile_generation_usage_requested_rows_check;
alter table public.mobile_generation_usage
    add constraint mobile_generation_usage_requested_rows_check
    check (requested_rows between 1 and 5000);

create table public.mobile_generation_jobs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    deck_id uuid not null unique,
    title text not null check (char_length(title) between 1 and 200),
    source_language text not null,
    source_language_code text not null,
    translation_language text not null,
    translation_language_code text not null,
    settings jsonb not null,
    tasks jsonb not null,
    total_rows integer not null check (total_rows between 1 and 5000),
    completed_rows integer not null default 0 check (completed_rows between 0 and 5000),
    status text not null default 'queued'
        check (status in ('queued', 'running', 'completed', 'failed')),
    error_message text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    started_at timestamptz,
    completed_at timestamptz
);

create table public.mobile_generation_batches (
    job_id uuid not null references public.mobile_generation_jobs(id) on delete cascade,
    batch_index integer not null check (batch_index >= 0),
    tasks jsonb not null,
    rows jsonb,
    status text not null default 'queued'
        check (status in ('queued', 'running', 'completed', 'failed')),
    error_message text,
    updated_at timestamptz not null default now(),
    primary key (job_id, batch_index)
);

create index mobile_generation_jobs_user_created_idx
    on public.mobile_generation_jobs(user_id, created_at desc);
create index mobile_generation_batches_pending_idx
    on public.mobile_generation_batches(job_id, status, batch_index);

alter table public.mobile_generation_jobs enable row level security;
alter table public.mobile_generation_batches enable row level security;

create policy mobile_generation_jobs_owner_select on public.mobile_generation_jobs
    for select using (user_id = auth.uid());

revoke insert, update, delete on table public.mobile_generation_jobs from anon, authenticated;
revoke all on table public.mobile_generation_batches from anon, authenticated;

commit;
