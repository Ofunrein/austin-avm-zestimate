-- Run this in Supabase SQL editor at https://supabase.com/dashboard

create table if not exists predictions (
  id uuid primary key default gen_random_uuid(),
  address text,
  lat numeric,
  lng numeric,
  sqft_living numeric,
  beds integer,
  baths_full numeric,
  year_built integer,
  zip_code text,
  predicted_price integer,
  lower_bound integer,
  upper_bound integer,
  confidence_score integer,
  shap_json jsonb,
  created_at timestamptz default now()
);

create table if not exists benchmark_runs (
  id uuid primary key default gen_random_uuid(),
  model_version text not null,
  medape numeric,
  mae numeric,
  rmse numeric,
  within_5pct numeric,
  within_10pct numeric,
  n_test integer,
  test_period text,
  residuals_json jsonb,
  created_at timestamptz default now()
);

create table if not exists comps_cache (
  cache_key text primary key,
  comps_json jsonb not null,
  created_at timestamptz default now()
);

-- indexes for benchmark dashboard and lookup performance
create index if not exists idx_predictions_zip on predictions(zip_code);
create index if not exists idx_predictions_created on predictions(created_at desc);
create index if not exists idx_benchmark_created on benchmark_runs(created_at desc);

-- Add list_price to predictions for search/deal comparison
alter table predictions add column if not exists list_price integer;

-- Data source: distinguish historical Kaggle sales from future live listings
alter table predictions add column if not exists data_source text default 'kaggle_historical';
create index if not exists idx_predictions_source on predictions(data_source);

-- Neighborhood context cache (30-day TTL enforced in app layer)
create table if not exists neighborhood_cache (
  cache_key text primary key,
  data_json jsonb not null,
  created_at timestamptz default now()
);

-- Agentic deal monitor results
create table if not exists deals (
  id uuid primary key default gen_random_uuid(),
  address text,
  zip_code text,
  list_price integer,
  predicted_price integer,
  value_gap_pct numeric,
  confidence_score integer,
  beds integer,
  baths_full numeric,
  sqft_living numeric,
  year_built integer,
  photo_url text,
  condition_note text,
  shap_top_driver text,
  deal_score numeric,
  data_source text default 'kaggle_historical',
  alerted_at timestamptz,
  created_at timestamptz default now()
);

create index if not exists idx_neighborhood_created on neighborhood_cache(created_at desc);
create index if not exists idx_deals_created on deals(created_at desc);
create index if not exists idx_deals_gap on deals(value_gap_pct desc);

-- Backfill: add data_source to existing deals table (no-op if column already exists)
alter table deals add column if not exists data_source text default 'kaggle_historical';

-- UNIQUE constraints required for upsert on_conflict="address"
-- NOTE: Must also be run manually in the Supabase dashboard SQL editor
create unique index if not exists idx_predictions_address on predictions(address);
create unique index if not exists idx_deals_address on deals(address);

-- Property photo URL for opportunity display
alter table predictions add column if not exists photo_url text;

-- Security hardening: Supabase warns when public-schema tables have RLS off.
-- This app reads/writes Supabase only from trusted backend/server code with the
-- service role key, so anon/authenticated browser roles should not get direct
-- table access. Keep this block in sync with supabase/rls-security.sql.
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
-- This block skips any table that does not exist yet so it is safe to re-run.
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
