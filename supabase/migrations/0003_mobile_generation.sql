begin;

create table public.mobile_generation_usage (
    id uuid primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    requested_rows integer not null check (requested_rows between 1 and 20),
    status text not null check (status in ('started', 'completed', 'failed')),
    created_at timestamptz not null default now(),
    completed_at timestamptz
);

create index mobile_generation_usage_user_created_idx
    on public.mobile_generation_usage(user_id, created_at desc);

alter table public.mobile_generation_usage enable row level security;

-- Generation usage is security-sensitive quota data. Mobile clients receive no direct
-- table policy; the authenticated Edge Function writes it with the service role.
revoke all on table public.mobile_generation_usage from anon, authenticated;

commit;
