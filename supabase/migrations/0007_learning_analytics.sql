begin;
create table public.learning_privacy_preferences (
  user_id uuid primary key references auth.users(id) on delete cascade,
  enabled boolean not null default false,
  revision int not null default 0,
  first_opened boolean not null default false
);
create table public.learning_unique_cards (
  user_id uuid not null references auth.users(id) on delete cascade,
  language text not null,
  card_id uuid not null,
  primary key(user_id,language,card_id)
);
create table public.learning_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  kind text not null check(kind in ('first_deck_opened','card_milestone','deck_generated')),
  language text not null,
  milestone int check(milestone in (10,100,500,1000)),
  occurred_at timestamptz not null default now()
);
create index learning_events_retention on public.learning_events(occurred_at);
create table public.learning_receipts (
  user_id uuid not null references auth.users(id) on delete cascade,
  event_id uuid not null,
  received_at timestamptz not null default now(),
  primary key(user_id,event_id)
);
alter table public.learning_privacy_preferences enable row level security;
alter table public.learning_unique_cards enable row level security;
alter table public.learning_events enable row level security;
alter table public.learning_receipts enable row level security;
revoke all on public.learning_privacy_preferences,public.learning_unique_cards,public.learning_events,public.learning_receipts from anon,authenticated;

create function public.learning_privacy() returns jsonb
language plpgsql security definer set search_path='' as $$
declare p public.learning_privacy_preferences;
begin
  if auth.uid() is null then raise exception 'Sign in required'; end if;
  select * into p from public.learning_privacy_preferences where user_id=auth.uid();
  return jsonb_build_object('enabled',coalesce(p.enabled,false),'revision',coalesce(p.revision,0));
end; $$;

create function public.set_learning_analytics(p_enabled boolean) returns jsonb
language plpgsql security definer set search_path='' as $$
declare p public.learning_privacy_preferences;
begin
  if auth.uid() is null or p_enabled is null then raise exception 'Sign in and a preference are required'; end if;
  insert into public.learning_privacy_preferences(user_id) values(auth.uid()) on conflict do nothing;
  select * into p from public.learning_privacy_preferences where user_id=auth.uid() for update;
  if p.enabled<>p_enabled then
    update public.learning_privacy_preferences set enabled=p_enabled,revision=revision+1,first_opened=false where user_id=auth.uid();
  end if;
  if not p_enabled then
    delete from public.learning_unique_cards where user_id=auth.uid();
    delete from public.learning_events where user_id=auth.uid();
    delete from public.learning_receipts where user_id=auth.uid();
  end if;
  return public.learning_privacy();
end; $$;

create function public.record_learning_activity(p_event_id uuid,p_kind text,p_language text,
 p_occurred_at timestamptz,p_revision int,p_card_id uuid default null) returns text
language plpgsql security definer set search_path='' as $$
declare p public.learning_privacy_preferences; n int; added int;
begin
  if auth.uid() is null then raise exception 'Sign in required'; end if;
  select * into p from public.learning_privacy_preferences where user_id=auth.uid() for update;
  if p.user_id is null or not p.enabled then return 'disabled'; end if;
  if p_revision is distinct from p.revision then return 'stale'; end if;
  if p_event_id is null or p_kind is null or p_kind not in ('deck_opened','card_opened') or
    p_language is null or not exists(select 1 from public.default_decks where source_language=p_language)
    then return 'invalid'; end if;
  if p_occurred_at is null or p_occurred_at>now()+interval '5 minutes' then return 'invalid'; end if;
  if p_occurred_at<now()-interval '90 days' then return 'expired'; end if;
  if p_kind='card_opened' and (p_card_id is null or not (
    exists(select 1 from public.cards c join public.decks d on d.id=c.deck_id
      where c.id=p_card_id and c.user_id=auth.uid() and d.source_language=p_language)
    or exists(select 1 from public.default_card_identity c join public.default_decks d on d.id=c.deck_id
      where c.id=p_card_id and d.source_language=p_language and d.content_version is not null)))
    then return 'invalid'; end if;
  insert into public.learning_receipts(user_id,event_id) values(auth.uid(),p_event_id) on conflict do nothing;
  get diagnostics added=row_count;
  if added=0 then return 'ok'; end if;
  if p_kind='deck_opened' then
    if not p.first_opened then
      insert into public.learning_events(user_id,kind,language,occurred_at) values(auth.uid(),'first_deck_opened',p_language,p_occurred_at);
      update public.learning_privacy_preferences set first_opened=true where user_id=auth.uid();
    end if;
  else
    select count(*) into n from public.learning_unique_cards where user_id=auth.uid() and language=p_language;
    if n<1000 then
      insert into public.learning_unique_cards(user_id,language,card_id) values(auth.uid(),p_language,p_card_id) on conflict do nothing;
      get diagnostics added=row_count;
      if added=1 and n+1 in (10,100,500,1000) then
        insert into public.learning_events(user_id,kind,language,milestone,occurred_at)
        values(auth.uid(),'card_milestone',p_language,n+1,p_occurred_at);
      end if;
    end if;
  end if;
  return 'ok';
end; $$;

create function public.record_completed_generation() returns trigger
language plpgsql security definer set search_path='' as $$
declare permitted boolean;
begin
  if new.status='completed' and old.status is distinct from 'completed' then
    select enabled into permitted from public.learning_privacy_preferences where user_id=new.user_id for update;
    if permitted then
      insert into public.learning_events(id,user_id,kind,language)
      values(new.id,new.user_id,'deck_generated',new.source_language) on conflict do nothing;
    end if;
  end if;
  return new;
end; $$;
create trigger learning_generation_completed after update of status on public.mobile_generation_jobs
for each row execute function public.record_completed_generation();

create function public.purge_learning_analytics() returns void
language sql security definer set search_path='' as $$
  delete from public.learning_events where occurred_at<now()-interval '90 days';
  delete from public.learning_receipts where received_at<now()-interval '90 days';
$$;
revoke all on function public.learning_privacy(),public.set_learning_analytics(boolean),
 public.record_learning_activity(uuid,text,text,timestamptz,int,uuid),
 public.record_completed_generation(),public.purge_learning_analytics() from public,anon;
grant execute on function public.learning_privacy(),public.set_learning_analytics(boolean),
 public.record_learning_activity(uuid,text,text,timestamptz,int,uuid) to authenticated;
commit;
