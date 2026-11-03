begin;
-- Shared content never enters public.decks, so existing personal-deck quotas exclude it.
create table public.default_decks (
  id uuid primary key,
  title text not null,
  source_language text not null,
  default_level text not null check (default_level in ('A1','A2','B1')),
  card_count int not null check (card_count in (300,400)),
  content_version int,
  unique(source_language,default_level)
);
create table public.default_concepts (
  id int primary key check (id between 1 and 1000),
  default_level text not null check (default_level in ('A1','A2','B1')),
  english_word text not null,
  english_sentence text not null,
  sense text not null
);
create table public.default_card_identity (
  id uuid primary key,
  deck_id uuid not null references public.default_decks(id),
  concept_id int not null references public.default_concepts(id),
  unique(deck_id,concept_id)
);
create table public.default_translations (
  card_id uuid not null references public.default_card_identity(id),
  content_version int not null check (content_version > 0),
  word text not null check (length(word)>0),
  sentence text not null check (length(sentence)>0),
  rank int not null check (rank between 1 and 1000),
  source_rank int check (source_rank between 1 and 5000),
  primary key(card_id,content_version)
);
create table public.default_study_progress (
  user_id uuid not null references auth.users(id) on delete cascade,
  card_id uuid not null references public.default_card_identity(id),
  rating public.study_rating not null default 'new',
  review_count int not null default 0 check(review_count>=0),
  last_reviewed_at timestamptz,
  updated_at timestamptz not null default now(),
  primary key(user_id,card_id)
);
alter table public.default_decks enable row level security;
alter table public.default_concepts enable row level security;
alter table public.default_card_identity enable row level security;
alter table public.default_translations enable row level security;
alter table public.default_study_progress enable row level security;
create policy catalog_read on public.default_decks for select to authenticated using (true);
create policy identity_read on public.default_card_identity for select to authenticated using (true);
create policy progress_own on public.default_study_progress for all to authenticated using (user_id=auth.uid()) with check(user_id=auth.uid());
grant select on public.default_decks, public.default_card_identity to authenticated;
grant select,insert,update,delete on public.default_study_progress to authenticated;
-- Draft sentences/translations are accessible only to the publisher and the guarded RPC.
revoke all on public.default_concepts, public.default_translations from anon, authenticated;

insert into public.default_decks(id,title,source_language,default_level,card_count)
select md5('default:'||lang||':'||level)::uuid,
       level||' · '||title,lang,level,n
from unnest(array['US English','European Spanish','German','European Portuguese','French','Italian',
'Thai (Thai script)','Thai (Paiboon romanization)','Polish','Dutch','Danish','Croatian','Vietnamese',
'Chinese (Simplified)','Malayalam','Slovak','Russian','Norwegian','Korean','Hungarian','Swedish',
'Indonesian','Japanese','Turkish']) lang
cross join (values ('A1','Everyday foundations',400),('A2','Everyday conversations',300),('B1','Express yourself',300)) levels(level,title,n);

create function public.read_default_deck(p_deck_id uuid,p_translation_language text default 'US English')
returns jsonb language plpgsql security definer set search_path='' as $$
declare d public.default_decks; result jsonb;
begin
  if auth.uid() is null then raise exception 'Sign in required'; end if;
  select * into d from public.default_decks where id=p_deck_id;
  if d.id is null or d.content_version is null then raise exception 'Default deck content is awaiting publication'; end if;
  select jsonb_agg(jsonb_build_object('id',i.id,'rank',t.rank,'foreign_word',t.word,
    'foreign_sentence',t.sentence,'word_translation',tr.word,'sentence_translation',tr.sentence,
    'rating',coalesce(p.rating::text,'new')) order by t.rank)
  into result
  from public.default_card_identity i
  join public.default_translations t on t.card_id=i.id and t.content_version=d.content_version
  join public.default_decks td on td.source_language=p_translation_language and td.default_level=d.default_level
  join public.default_card_identity ti on ti.deck_id=td.id and ti.concept_id=i.concept_id
  join public.default_translations tr on tr.card_id=ti.id and tr.content_version=td.content_version
  left join public.default_study_progress p on p.card_id=i.id and p.user_id=auth.uid()
  where i.deck_id=d.id;
  if coalesce(jsonb_array_length(result),0)<>d.card_count then raise exception 'Complete translation is not published yet'; end if;
  return to_jsonb(d)||jsonb_build_object('translation_language',p_translation_language,'cards',result);
end;
$$;
revoke all on function public.read_default_deck(uuid,text) from public,anon;
grant execute on function public.read_default_deck(uuid,text) to authenticated;
commit;
