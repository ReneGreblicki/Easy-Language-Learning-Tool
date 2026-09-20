import { PGlite } from '@electric-sql/pglite';
import { readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
const db = new PGlite();
await db.exec(`
create role anon; create role authenticated;
create schema auth;
create table auth.users(id uuid primary key);
create function auth.uid() returns uuid language sql as $$ select nullif(current_setting('test.account_id',true),'')::uuid $$;
create type public.study_rating as enum ('new','learning','known','difficult');
create table public.decks(id uuid primary key,user_id uuid,source_language text);
create table public.cards(id uuid primary key,deck_id uuid,user_id uuid);
create table public.mobile_generation_jobs(id uuid primary key,user_id uuid,source_language text,status text);
`);
for (const name of ['0006_default_decks.sql','0007_learning_analytics.sql']) {
  await db.exec(await readFile(new URL('../migrations/'+name,import.meta.url),'utf8'));
}
const user='11111111-1111-4111-8111-111111111111', other='22222222-2222-4222-8222-222222222222';
await db.exec(`insert into auth.users values('${user}'),('${other}'); set test.account_id='${user}';`);
const scalar = async sql => Object.values((await db.query(sql)).rows[0])[0];
assert.equal((await scalar('select public.learning_privacy()')).enabled,false);
assert.equal(await scalar(`select public.record_learning_activity(gen_random_uuid(),'deck_opened','German',now(),0)`),'disabled');
assert.equal((await scalar('select public.set_learning_analytics(true)')).revision,1);
await db.exec(`insert into public.decks values('${user}','${user}','German');
insert into public.cards select md5(n::text)::uuid,'${user}','${user}' from generate_series(1,1001) n;
select public.record_learning_activity(gen_random_uuid(),'deck_opened','German',now(),1);
select public.record_learning_activity(gen_random_uuid(),'deck_opened','French',now(),1);
select public.record_learning_activity(gen_random_uuid(),'card_opened','German',now(),1,md5(n::text)::uuid) from generate_series(1,1001) n;
select public.record_learning_activity(gen_random_uuid(),'card_opened','German',now(),1,md5(n::text)::uuid) from generate_series(1,1001) n;`);
assert.equal(await scalar("select count(*)::int from public.learning_unique_cards"),1000);
assert.deepEqual((await db.query("select milestone from public.learning_events where kind='card_milestone' order by milestone")).rows.map(r=>r.milestone),[10,100,500,1000]);
assert.equal(await scalar("select count(*)::int from public.learning_events where kind='first_deck_opened'"),1);
await assert.rejects(db.exec(`select public.record_learning_activity(gen_random_uuid(),'card_opened','French',now(),1,md5('1')::uuid)`));
await db.exec(`insert into public.mobile_generation_jobs values('${user}','${user}','German','running');
update public.mobile_generation_jobs set status='completed'; update public.mobile_generation_jobs set status='completed';`);
assert.equal(await scalar("select count(*)::int from public.learning_events where kind='deck_generated'"),1);
await db.exec(`set test.account_id='${other}'; select public.set_learning_analytics(true);`);
await assert.rejects(db.exec(`select public.record_learning_activity(gen_random_uuid(),'card_opened','German',now(),1,md5('1')::uuid)`));
await db.exec(`set role authenticated;`);
await assert.rejects(db.exec('select * from public.learning_unique_cards'));
await assert.rejects(db.exec('update public.default_decks set content_version=1'));
await assert.rejects(db.exec("select public.read_default_deck((select id from public.default_decks limit 1))"));
await db.exec(`reset role; set test.account_id='${user}'; select public.set_learning_analytics(false);`);
assert.equal(await scalar("select count(*)::int from public.learning_unique_cards"),0);
assert.equal(await scalar("select count(*)::int from public.learning_events"),0);
await db.exec('select public.set_learning_analytics(true)');
assert.equal(await scalar(`select public.record_learning_activity(gen_random_uuid(),'deck_opened','German',now(),1)`),'stale');
await db.exec(`insert into public.learning_events(user_id,kind,language,occurred_at) values('${user}','first_deck_opened','German',now()-interval '91 days'); select public.purge_learning_analytics();`);
assert.equal(await scalar("select count(*)::int from public.learning_events"),0);
assert.equal(await scalar('select count(*)::int from public.default_decks'),72);
// A published default deck hydrates translations and private progress without personal slots.
await db.exec(`
insert into public.default_concepts select n,'A1','word '||n,'sentence '||n,'sense '||n from generate_series(1,400) n;
insert into public.default_card_identity
select md5(d.source_language||n)::uuid,d.id,n from public.default_decks d cross join generate_series(1,400) n
where d.default_level='A1' and d.source_language in ('German','US English');
insert into public.default_translations(card_id,content_version,word,sentence,rank)
select id,1,'word '||concept_id,'sentence '||concept_id,concept_id from public.default_card_identity;
update public.default_decks set content_version=1 where default_level='A1' and source_language in ('German','US English');
`);
const hydrated = await scalar("select public.read_default_deck((select id from public.default_decks where source_language='German' and default_level='A1'))");
assert.equal(hydrated.cards.length,400);
assert.equal(hydrated.default_level,'A1');
assert.equal(await scalar('select count(*)::int from public.decks'),1);
await db.exec(`grant usage on schema auth to authenticated;
set role authenticated;
insert into public.default_study_progress(user_id,card_id,rating) values('${user}','${hydrated.cards[0].id}','known');
set test.account_id='${other}';`);
assert.equal(await scalar('select count(*)::int from public.default_study_progress'),0);
await assert.rejects(db.exec(`insert into public.default_study_progress(user_id,card_id) values('${user}','${hydrated.cards[1].id}')`));
await db.exec('reset role');
console.log('PASS: unique cards, all four milestones, first use, completion, consent revisions, deletion, retention, RLS, unpublished catalog, complete translations and private default-deck progress.');
await db.close();
