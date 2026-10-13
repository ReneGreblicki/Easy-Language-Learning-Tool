"""Verify the configured Supabase database and publish hash-approved defaults.

Uses the existing server-only management token. Logs only schema/count metadata.
Content writes occur in one transaction; personal deck/progress tables are untouched.
"""

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import build_default_decks as builder

PROJECT = "jmnsrikmqopdhmnkjmah"
APPROVED_SHA = "7c181ef149bd6bc3b89a38e5552bbf34ef13f2e738b7832b47624482560f612b"
TABLES = (
    "default_decks",
    "default_concepts",
    "default_card_identity",
    "default_translations",
    "default_study_progress",
    "learning_privacy_preferences",
    "learning_events",
)


def query(sql, read_only=True):
    assert os.environ["PROJECT_REF"] == PROJECT, "Unexpected deployment target"
    token = os.environ["SUPABASE_ACCESS_TOKEN"]
    request = urllib.request.Request(
        f"https://api.supabase.com/v1/projects/{PROJECT}/database/query",
        data=json.dumps({"query": sql, "read_only": read_only}).encode(),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        # Provider response bodies and credentials are deliberately not logged.
        raise RuntimeError(f"Supabase database query failed: HTTP {error.code}") from None


def inspect_database():
    tables = query(
        "select relname as name, relrowsecurity as rls from pg_class c "
        "join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' "
        "and c.relkind='r' order by relname"
    )
    present = {row["name"] for row in tables}
    report = {
        "project_ref": PROJECT,
        "missing_tables": sorted(set(TABLES) - present),
        "default_table_rls": {r["name"]: r["rls"] for r in tables if r["name"] in TABLES},
    }
    migration_table = query(
        "select to_regclass('supabase_migrations.schema_migrations') is not null as present"
    )
    if migration_table[0]["present"]:
        report["migrations"] = query(
            "select version from supabase_migrations.schema_migrations order by version"
        )
    if "default_decks" in present:
        report["catalog"] = query(
            "select count(*)::int as decks, count(distinct source_language)::int as languages, "
            "count(content_version)::int as published_decks, max(content_version) as latest_version "
            "from public.default_decks"
        )
    if "default_translations" in present:
        report["versions"] = query(
            "select content_version, count(*)::int as rows from public.default_translations "
            "group by content_version order by content_version"
        )
    cron = query("select exists(select 1 from pg_extension where extname='pg_cron') as enabled")
    report["pg_cron"] = cron[0]["enabled"]
    if report["pg_cron"]:
        report["cron_jobs"] = query(
            "select jobname, schedule, active from cron.job "
            "where jobname like '%learning%' or jobname like '%retention%'"
        )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deploy", type=Path, help="Directory with approved curriculum and review")
    parser.add_argument("--report", type=Path, default=Path("database-verification.json"))
    args = parser.parse_args()
    before = inspect_database()
    args.report.write_text(json.dumps({"before": before}, indent=2))
    print(json.dumps(before, indent=2))
    if args.deploy:
        assert not before["missing_tables"], "Apply required migrations before publishing"
        assert all(before["default_table_rls"].values()), "RLS is missing"
        catalog = before["catalog"][0]
        assert catalog["decks"] == 72 and catalog["languages"] == 24, "Unexpected catalog"
        assert not before["versions"] and catalog["published_decks"] == 0, (
            "Existing content: choose a new version explicitly"
        )
        path = args.deploy / "curriculum.json"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == APPROVED_SHA, (
            "Unapproved curriculum hash"
        )
        sql = builder.publication_sql(path, args.deploy / "review.json", 1)
        # Serialize against any other publisher; assertions run again inside the
        # transaction so a changed version cannot be overwritten after preflight.
        guard = """begin;
        select pg_advisory_xact_lock(hashtext('default-content-publication'));
        lock table public.default_decks, public.default_translations in exclusive mode;
        do $$ begin
          if exists(select 1 from public.default_translations) or
             exists(select 1 from public.default_decks where content_version is not null)
          then raise exception 'Default content was published after preflight'; end if;
        end $$;
        """
        checks = """do $$ begin
          if (select count(*) from public.default_concepts) <> 1000 or
             (select count(*) from public.default_translations where content_version=1) <> 24000 or
             (select count(*) from public.default_decks where content_version=1) <> 72 or
             exists(select 1 from public.default_decks d left join public.default_card_identity i
               on i.deck_id=d.id left join public.default_translations t on t.card_id=i.id
               and t.content_version=1 group by d.id,d.card_count having count(t.card_id)<>d.card_count)
          then raise exception 'Incomplete published curriculum'; end if;
        end $$;
        commit;
        """
        guarded = sql.replace("begin;", guard, 1).removesuffix("commit;\n") + checks
        query(guarded, read_only=False)
        after = inspect_database()
        counts = query("select count(*)::int as concepts from public.default_concepts")
        assert after["catalog"][0]["published_decks"] == 72
        assert after["versions"] == [{"content_version": 1, "rows": 24000}]
        assert counts[0]["concepts"] == 1000
        assert after["pg_cron"], "Analytics retention extension is missing"
        assert any(
            job["jobname"] == "purge-learning-analytics" and job["active"]
            for job in after["cron_jobs"]
        ), "Analytics retention job is missing"
        # An unpersisted test subject verifies the authenticated RPC; it creates
        # neither an auth user nor personal study data and returns only counts.
        rpc = query("""with identity as materialized (
          select set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111119',true) as uid
          )
          select count(*)::int as checked_decks,
            bool_and(jsonb_array_length(public.read_default_deck(id,'US English')->'cards')=card_count) as complete,
            has_function_privilege('authenticated','public.read_default_deck(uuid,text)','execute') as permitted
          from identity cross join public.default_decks where identity.uid is not null;""")
        rpc_counts = [r for r in rpc if "checked_decks" in r]
        assert rpc_counts and rpc_counts[0]["checked_decks"] == 72 and rpc_counts[0]["complete"]
        assert rpc_counts[0]["permitted"]
        args.report.write_text(
            json.dumps(
                {
                    "before": before,
                    "after": after,
                    "approved_sha256": APPROVED_SHA,
                    "deployed_version": 1,
                    "authenticated_rpc": rpc_counts[0],
                },
                indent=2,
            )
        )
        print(
            "Verified published content: 72 decks, 1,000 concepts, 24,000 translations, version 1"
        )


if __name__ == "__main__":
    main()
