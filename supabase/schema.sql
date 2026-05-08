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
  alerted_at timestamptz,
  created_at timestamptz default now()
);

create index if not exists idx_neighborhood_created on neighborhood_cache(created_at desc);
create index if not exists idx_deals_created on deals(created_at desc);
create index if not exists idx_deals_gap on deals(value_gap_pct desc);
