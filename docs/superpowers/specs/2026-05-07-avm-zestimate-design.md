# AVM Zestimate — Design Spec
**Date:** 2026-05-07  
**Market:** Austin TX  
**Goal:** Beat Zillow's published Austin MedAPE (~4.5%) on a held-out test set. Deploy publicly with benchmark dashboard.  
**Cost target:** $0 (Vercel Hobby + HuggingFace Spaces free + Supabase free tier)

---

## 1. Repository Structure

```
avm-zestimate/
├── ml/                        # data pipeline + training
│   ├── data/                  # raw + processed CSVs (gitignored)
│   ├── notebooks/             # EDA, residual analysis
│   ├── src/
│   │   ├── ingest.py          # download Travis CAD, Kaggle, parse .numbers
│   │   ├── clean.py           # merge, dedup, outlier removal
│   │   ├── features.py        # feature engineering
│   │   ├── train.py           # XGBoost + LightGBM + ensemble, temporal CV
│   │   ├── evaluate.py        # MedAPE, MAE, RMSE, within-5/10%, residual plots
│   │   ├── shap_gen.py        # SHAP values per prediction
│   │   └── comps.py           # comparable sales engine
│   ├── mlflow/                # experiment tracking (local)
│   ├── models/                # serialized model artifacts (pushed to HF)
│   └── model_card.md
├── api/                       # FastAPI on HuggingFace Spaces
│   ├── main.py
│   ├── routers/
│   │   ├── predict.py         # POST /predict
│   │   ├── comps.py           # GET /comps
│   │   ├── benchmark.py       # GET /benchmark
│   │   └── scan.py            # POST /scan (undervalued detector)
│   ├── models/                # Pydantic schemas
│   ├── Dockerfile
│   └── requirements.txt
├── web/                       # Next.js 14 App Router on Vercel
│   ├── app/
│   │   ├── page.tsx           # address lookup + prediction UI
│   │   ├── benchmark/         # accuracy dashboard
│   │   ├── scanner/           # undervalued property detector
│   │   └── upload/            # CSV batch scorer
│   ├── components/
│   │   ├── ShapWaterfall.tsx
│   │   ├── CompsTable.tsx
│   │   ├── BenchmarkChart.tsx
│   │   └── ZipAccuracyTable.tsx
│   └── lib/
│       └── api.ts             # typed API client
└── .github/
    └── workflows/
        ├── ci.yml             # lint + test on PR
        └── retrain.yml        # triggered on data push
```

---

## 2. Data Sources

| Source | What | Format | How to get |
|--------|------|--------|-----------|
| Travis County CAD | 400k+ Austin property records — sqft, beds, baths, year_built, assessed value, lot size, grade, condition | CSV export | traviscad.org public download |
| Kaggle Austin Housing | ~47k Austin sale transactions with price, date, address | CSV | Kaggle API (`kaggle datasets download`) |
| compass_austin_listings.numbers | Local Compass Austin MLS listings | Apple Numbers (parsed via zip+protobuf) | Already in ~/Downloads |
| Census Geocoder | lat/lng from address | API (free, no key) | batch geocode up to 10k/request |
| OpenStreetMap / Nominatim | Distance to downtown, amenity counts | API (free) | via `osmnx` or direct Overpass |

**Merge key:** normalized address string → geocoded lat/lng → spatial join  
**Target variable:** `sale_price` (log-transformed for training, inverse-transformed for output)  
**Date filter:** Sales 2018–2024. COVID period (2020-Q2 to 2021-Q2) retained but flagged with `is_covid_period` boolean feature — let model learn the signal rather than discard data.

---

## 3. Feature Engineering

**Structural:**
- sqft_living, lot_sqft, beds, baths_full, baths_half, stories
- year_built, effective_year, remodel_year
- has_pool, has_garage, garage_spaces
- grade (CAD quality grade 1–10), condition_score

**Location:**
- zip_code (one-hot or target-encoded)
- lat, lng
- distance_to_downtown_miles (Euclidean to 30.2672°N 97.7431°W)
- school_district_score (ZIP-level proxy: median household income from Census ACS 5-year, normalized 0–1; no paid API dependency)

**Market:**
- median_zip_sale_price_90d (rolling, computed from training data — no leakage past cutoff)
- median_sqft_price_zip_90d
- days_on_market (from Kaggle/Compass data where available)

**Derived:**
- price_per_sqft_assessed (assessed_value / sqft — signal, not target)
- age = 2024 - year_built
- effective_age = 2024 - effective_year

---

## 4. ML Model

**Primary:** XGBoost regressor  
**Challenger:** LightGBM regressor  
**Final:** Weighted blend if ensemble MedAPE < min(XGB, LGB) by >0.5%

**Validation strategy:** Temporal cross-validation  
- Sort all transactions by sale_date  
- 5 folds: each fold trains on all data before cutoff, validates on next 6-month window  
- Prevents future data leakage — required for any honest AVM benchmark

**Hyperparameter tuning:** Optuna (50 trials per model, minimizes MedAPE on CV)

**Prediction output:**
- `predicted_price` — point estimate (inverse log-transform)
- `lower_bound`, `upper_bound` — 90% prediction interval via quantile regression (XGBoost `quantile` objective at α=0.05 and α=0.95)
- `confidence_score` — 0–100, derived from interval width relative to price
- `shap_values` — top 5 features with direction and magnitude

**Win condition:** MedAPE < 4.0% on held-out 2024 test set (Zillow Austin baseline: ~4.5%)

**Experiment tracking:** MLflow (local), log: params, CV MedAPE, test MedAPE, model artifact path, training data SHA256

---

## 5. Comparable Sales Engine

For each prediction request:
1. Filter sold properties within 1-mile radius and ±20% sqft and ±5 years age
2. Normalize features: sqft, beds, baths, age, lot_sqft
3. Compute cosine similarity on normalized feature vector
4. Return top 5 most similar with: address, sale_price, sale_date, sqft, beds, baths, similarity_score
5. Cache results in Supabase `comps_cache` keyed by (lat, lng, sqft bucket)

---

## 6. Undervalued Property Scanner

Input: batch of listings (CSV upload or Supabase `listings` table)  
Process:
1. Run AVM on each listing
2. Compute `value_gap = predicted_price - list_price`
3. Flag as undervalued if `value_gap / list_price > 0.08` (>8% below model estimate)
4. Rank by value_gap descending

Output: sorted table of undervalued properties with predicted price, list price, gap %, SHAP top driver

---

## 7. API — FastAPI on HuggingFace Spaces

**Deployment:** HuggingFace Spaces, Docker runtime, CPU free tier  
**Model loading:** Load from HF model repo on startup (`huggingface_hub.hf_hub_download`)  
**Cold start:** ~30s (acceptable for portfolio/demo)

Endpoints:
```
POST /predict
  body: { address, sqft, beds, baths, year_built, ... }
  returns: { predicted_price, lower_bound, upper_bound, confidence_score, shap_top5 }

GET /comps?lat=&lng=&sqft=&beds=&baths=&year_built=
  returns: [{ address, sale_price, sale_date, sqft, similarity_score }]

GET /benchmark
  returns: { medape, mae, rmse, within_5pct, within_10pct, zillow_baseline, by_zip: [...] }

POST /scan
  body: [{ address, list_price, sqft, ... }]
  returns: [{ address, predicted_price, list_price, value_gap_pct, shap_top_driver }]
```

**Auth:** None for demo (public API). Add API key header if traffic becomes abusive.

---

## 8. Frontend — Next.js 14 on Vercel

**Pages:**

`/` — Address lookup  
- Input: address autocomplete (free Census geocoder)  
- Output: predicted price card, confidence interval bar, SHAP waterfall chart, comps table  
- Below fold: "Is this over or underpriced?" badge based on value_gap vs current Zillow estimate

`/benchmark` — Accuracy dashboard  
- Model MedAPE vs Zillow baseline (bar chart)  
- Table: accuracy by ZIP code (MedAPE, MAE, n_sales)  
- Training data summary: n records, date range, data sources

`/scanner` — Undervalued detector  
- CSV upload (address, list_price, sqft, beds, baths, year_built)  
- Runs POST /scan, returns sortable table  
- Download results as CSV

`/model-card` — Static page from model_card.md  
- Training data, metrics, limitations, bias analysis, version

---

## 9. Database — Supabase Postgres (free tier)

Tables:
```sql
predictions (id, address, lat, lng, sqft, beds, baths, year_built,
             predicted_price, lower_bound, upper_bound, confidence_score,
             shap_json, created_at)

properties (parcel_id, address, lat, lng, sqft, beds, baths, year_built,
            lot_sqft, grade, condition, zip_code, sale_price, sale_date)

comps_cache (cache_key, comps_json, created_at)

benchmark_runs (id, model_version, medape, mae, rmse, within_5pct,
                within_10pct, n_test, test_period, created_at)
```

Row limit on free tier: 500MB storage, ~50k rows predictions before cleanup needed.

---

## 10. CI/CD

`.github/workflows/ci.yml` — on every PR:
- `pytest ml/tests/` — data pipeline + feature engineering tests
- `pytest api/tests/` — API endpoint tests
- `npm run typecheck && npm run build` — web build check

`.github/workflows/retrain.yml` — triggered manually or on `data/` push:
- Run `ml/src/train.py`
- Log to MLflow
- If new MedAPE < current best: push model to HF, update `benchmark_runs`

---

## 11. Model Card (summary)

- **Training data:** Travis CAD + Kaggle Austin sales 2018–2024, ~47k transactions after cleaning
- **Target market:** Austin TX (Travis County)
- **Known limitations:** Luxury homes (>$2M) underrepresented, new construction (<2 years) may undervalue, does not account for interior renovation quality
- **Bias check:** Report MedAPE by ZIP median income quartile (flag if >2x error in lowest quartile)
- **Version:** semver, logged with training data SHA256 in MLflow

---

## 12. Success Criteria

| Metric | Target |
|--------|--------|
| MedAPE on 2024 test set | < 4.0% (beats Zillow ~4.5%) |
| Within 5% | > 60% of predictions |
| Within 10% | > 85% of predictions |
| API p95 latency | < 2s (excluding cold start) |
| Frontend Lighthouse score | > 90 |
| Public URL live | Yes |
| Benchmark dashboard public | Yes |
| Model card published | Yes |
