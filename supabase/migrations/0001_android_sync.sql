begin;

create extension if not exists pgcrypto;

create type public.study_rating as enum ('new', 'learning', 'known', 'difficult');

create table public.profiles (
    user_id uuid primary key references auth.users(id) on delete cascade,
    username text not null unique check (username ~ '^[A-Za-z0-9_]{3,30}$'),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = ''
as $$
begin
    insert into public.profiles(user_id, username)
    values (
        new.id,
        coalesce(
            nullif(new.raw_user_meta_data ->> 'username', ''),
            'user_' || left(replace(new.id::text, '-', ''), 12)
        )
    );
    return new;
end;
$$;

create trigger on_auth_user_created
    after insert on auth.users
    for each row execute procedure public.handle_new_user();

create table public.devices (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    installation_id uuid not null,
    platform text not null check (platform in ('windows', 'macos', 'android')),
    display_name text not null,
    last_seen_at timestamptz not null default now(),
    unique (user_id, installation_id)
);

create table public.decks (
    id uuid primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    title text not null check (char_length(title) between 1 and 200),
    source_language text not null,
    translation_language text not null,
    cefr_level text,
    settings jsonb not null default '{}'::jsonb,
    source_device_id uuid references public.devices(id) on delete set null,
    revision bigint not null default 1 check (revision > 0),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    deleted_at timestamptz,
    purge_after timestamptz,
    check (
        (deleted_at is null and purge_after is null)
        or (deleted_at is not null and purge_after >= deleted_at + interval '30 days')
    )
);

create table public.cards (
    id uuid primary key,
    deck_id uuid not null references public.decks(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    rank integer not null check (rank between 1 and 5000),
    foreign_word text not null,
    word_translation text not null,
    foreign_sentence text not null,
    sentence_translation text not null,
    revision bigint not null default 1 check (revision > 0),
    updated_at timestamptz not null default now(),
    unique (deck_id, rank)
);

create table public.card_audio (
    id uuid primary key,
    card_id uuid not null references public.cards(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    side text not null check (side in ('foreign_word', 'foreign_sentence')),
    storage_path text not null,
    sha256 text not null check (sha256 ~ '^[a-f0-9]{64}$'),
    byte_size bigint not null check (byte_size > 0),
    updated_at timestamptz not null default now(),
    unique (card_id, side)
);

create table public.study_progress (
    user_id uuid not null references auth.users(id) on delete cascade,
    card_id uuid not null references public.cards(id) on delete cascade,
    rating public.study_rating not null default 'new',
    review_count integer not null default 0 check (review_count >= 0),
    last_reviewed_at timestamptz,
    revision bigint not null default 1 check (revision > 0),
    updated_at timestamptz not null default now(),
    primary key (user_id, card_id)
);

create table public.sync_events (
    sequence bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    entity_type text not null check (entity_type in ('deck', 'card', 'audio', 'progress')),
    entity_id uuid not null,
    operation text not null check (operation in ('upsert', 'soft_delete', 'restore')),
    revision bigint not null,
    created_at timestamptz not null default now(),
    unique (user_id, entity_type, entity_id, revision)
);

create table public.deletion_tombstones (
    user_id uuid not null references auth.users(id) on delete cascade,
    entity_type text not null check (entity_type = 'deck'),
    entity_id uuid not null,
    deleted_at timestamptz not null,
    expires_at timestamptz not null,
    primary key (user_id, entity_type, entity_id),
    check (expires_at >= deleted_at + interval '90 days')
);

create index decks_user_updated_idx on public.decks(user_id, updated_at);
create index cards_deck_rank_idx on public.cards(deck_id, rank);
create index sync_events_user_sequence_idx on public.sync_events(user_id, sequence);
create index tombstones_expiry_idx on public.deletion_tombstones(expires_at);

alter table public.profiles enable row level security;
alter table public.devices enable row level security;
alter table public.decks enable row level security;
alter table public.cards enable row level security;
alter table public.card_audio enable row level security;
alter table public.study_progress enable row level security;
alter table public.sync_events enable row level security;
alter table public.deletion_tombstones enable row level security;

create policy profiles_owner on public.profiles
    using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy devices_owner on public.devices
    using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy decks_owner on public.decks
    using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy cards_owner on public.cards
    using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy audio_owner on public.card_audio
    using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy progress_owner on public.study_progress
    using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy events_owner on public.sync_events
    using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy tombstones_owner on public.deletion_tombstones
    using (user_id = auth.uid()) with check (user_id = auth.uid());

insert into storage.buckets (id, name, public)
values ('flashcard-audio', 'flashcard-audio', false)
on conflict (id) do nothing;

create policy audio_objects_read on storage.objects for select
    using (
        bucket_id = 'flashcard-audio'
        and (storage.foldername(name))[1] = auth.uid()::text
    );
create policy audio_objects_insert on storage.objects for insert
    with check (
        bucket_id = 'flashcard-audio'
        and (storage.foldername(name))[1] = auth.uid()::text
    );
create policy audio_objects_update on storage.objects for update
    using (
        bucket_id = 'flashcard-audio'
        and (storage.foldername(name))[1] = auth.uid()::text
    )
    with check (
        bucket_id = 'flashcard-audio'
        and (storage.foldername(name))[1] = auth.uid()::text
    );
create policy audio_objects_delete on storage.objects for delete
    using (
        bucket_id = 'flashcard-audio'
        and (storage.foldername(name))[1] = auth.uid()::text
    );

commit;
