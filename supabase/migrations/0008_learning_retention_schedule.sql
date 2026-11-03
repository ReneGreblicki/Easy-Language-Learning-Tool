-- Analytics-only retention. No deck inactivity deletion.
create extension if not exists pg_cron;
select cron.schedule('purge-learning-analytics', '17 3 * * *', 'select public.purge_learning_analytics()');
