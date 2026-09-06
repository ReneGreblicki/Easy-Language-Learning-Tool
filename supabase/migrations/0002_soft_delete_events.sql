begin;

create or replace function public.track_deck_soft_delete()
returns trigger
language plpgsql
security definer set search_path = ''
as $$
begin
    if old.deleted_at is null and new.deleted_at is not null then
        insert into public.deletion_tombstones(
            user_id, entity_type, entity_id, deleted_at, expires_at
        ) values (
            new.user_id, 'deck', new.id, new.deleted_at, new.deleted_at + interval '90 days'
        )
        on conflict (user_id, entity_type, entity_id) do update set
            deleted_at = excluded.deleted_at,
            expires_at = excluded.expires_at;

        insert into public.sync_events(user_id, entity_type, entity_id, operation, revision)
        values (new.user_id, 'deck', new.id, 'soft_delete', new.revision + 1)
        on conflict do nothing;
    elsif old.deleted_at is not null and new.deleted_at is null then
        delete from public.deletion_tombstones
        where user_id = new.user_id and entity_type = 'deck' and entity_id = new.id;

        insert into public.sync_events(user_id, entity_type, entity_id, operation, revision)
        values (new.user_id, 'deck', new.id, 'restore', new.revision + 1)
        on conflict do nothing;
    end if;
    new.revision := new.revision + 1;
    new.updated_at := now();
    return new;
end;
$$;

create trigger on_deck_soft_delete
    before update of deleted_at on public.decks
    for each row
    when (old.deleted_at is distinct from new.deleted_at)
    execute procedure public.track_deck_soft_delete();

commit;
