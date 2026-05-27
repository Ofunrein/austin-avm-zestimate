-- Supabase security hardening for public schema tables.
-- Run this in Supabase SQL Editor for project lisforfokxoibdlmtkag / austin-avm.
--
-- The application accesses these tables from trusted server code with the
-- SUPABASE_SERVICE_ROLE_KEY. Browser clients should not read/write these tables
-- directly. Enabling RLS with no anon/authenticated policies blocks public REST
-- access while the service_role can still perform backend jobs.

-- Vercel cron touches this table to keep the free Supabase project active.
create table if not exists public.keepalive (
  id integer primary key default 1,
  touched_at timestamptz default now(),
  source text,
  constraint keepalive_single_row check (id = 1)
);
insert into public.keepalive (id, touched_at, source)
values (1, now(), 'schema')
on conflict (id) do nothing;

-- Enable RLS and remove direct browser/API table access from anon/authenticated.
-- This block skips any table that does not exist yet so it is safe to run alone.
do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'predictions',
    'benchmark_runs',
    'comps_cache',
    'neighborhood_cache',
    'deals',
    'keepalive'
  ]
  loop
    if to_regclass(format('public.%I', table_name)) is not null then
      execute format('alter table public.%I enable row level security', table_name);
      execute format('alter table public.%I force row level security', table_name);
      execute format('revoke all on table public.%I from anon, authenticated', table_name);
      execute format('grant all on table public.%I to service_role', table_name);
    end if;
  end loop;
end $$;

grant usage on schema public to service_role;

-- Verification query: should return rls_enabled=true for every existing table.
select
  n.nspname as schemaname,
  c.relname as tablename,
  c.relrowsecurity as rls_enabled,
  c.relforcerowsecurity as rls_forced
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relkind = 'r'
  and c.relname in (
    'predictions',
    'benchmark_runs',
    'comps_cache',
    'neighborhood_cache',
    'deals',
    'keepalive'
  )
order by c.relname;
