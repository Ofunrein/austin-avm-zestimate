---
title: Austin AVM API
sdk: docker
pinned: false
---

# Austin AVM — AI-Powered Home Valuation

An automated valuation model (AVM) for Austin, TX real estate. Like Zillow's Zestimate, but open-source, explainable, and built on a free stack.

**Live:** [austin-avm.vercel.app](https://austin-avm.vercel.app) · **API:** [ofunrein-austin-avm-api.hf.space](https://ofunrein-austin-avm-api.hf.space/docs)

---

## What does it do?

Give it a property — square footage, bedrooms, bathrooms, year built, ZIP code — and it tells you:

- **Estimated value** (e.g. $453,000)
- **Confidence range** (e.g. $398k–$512k, 90% probability)
- **Why** — which features drove the price up or down (powered by SHAP)
- **Comparable sales** — similar homes that sold nearby
- **AI explanation** — plain English narrative from Claude interpreting the valuation

---

## What is an AVM?

An Automated Valuation Model predicts real estate prices using machine learning instead of a human appraiser. Zillow calls theirs the "Zestimate." Banks use AVMs for mortgage decisions. This one is trained on Austin TX sales data.

**How it works:**
1. Trained on ~10,000 historical Austin home sales
2. Learns patterns: bigger homes cost more, older homes cost less, some ZIP codes command premiums
3. Given a new property, applies those patterns to estimate value
4. Uses two models (XGBoost + LightGBM) and averages them for better accuracy

---

## What makes it different from a simple price lookup?

- **Explainability** — SHAP values show exactly which features added or subtracted value. Zillow doesn't show this.
- **Confidence intervals** — instead of one number, gives a probable range using quantile regression
- **AI narrative** — Claude (the AI) reads the SHAP values and writes a 2-sentence explanation in plain English
- **Natural language search** — type "3BR under $400k in 78704 with pool" and get ranked results
- **Deal monitor** — weekly scan of Austin listings to flag undervalued properties

---

## Tech stack

| Layer | Technology | Why |
|-------|-----------|-----|
| ML model | XGBoost + LightGBM | Best accuracy on tabular data |
| Hyperparameter tuning | Optuna | Automated search for best model settings |
| Explainability | SHAP | Shows feature contributions per prediction |
| API | FastAPI (Python) | Fast, auto-generates docs at /docs |
| AI layer | Claude Haiku (Anthropic) | LLM explanations + NL search parsing |
| Frontend | Next.js + Tailwind | React framework, deployed to Vercel |
| Database | Supabase (Postgres) | Stores predictions, benchmark runs, comps cache |
| API hosting | HuggingFace Spaces | Free Docker hosting for ML APIs |
| Frontend hosting | Vercel | Free Next.js hosting |
| Experiment tracking | MLflow | Logs each training run's metrics |
| CI/CD | GitHub Actions | Runs tests on every push |

Total cost: **$0/month** on free tiers.

---

## Project structure

```
avm-zestimate/
├── ml/                      # Machine learning pipeline
│   ├── src/avm/             # Core ML modules
│   │   ├── ingest.py        # Download + parse raw data
│   │   ├── clean.py         # Filter bad records, normalize columns
│   │   ├── features.py      # Engineer features (age, market metrics, etc.)
│   │   ├── train.py         # Train XGBoost + LightGBM, tune with Optuna
│   │   ├── intervals.py     # Quantile regression for confidence intervals
│   │   ├── shap_gen.py      # SHAP explainability
│   │   ├── comps.py         # Find comparable sales
│   │   └── evaluate.py      # Metrics: MedAPE, MAE, RMSE
│   ├── models/              # Saved model artifacts
│   └── run_training.py      # Full training pipeline (9 steps)
│
├── api/                     # FastAPI backend
│   ├── routers/
│   │   ├── predict.py       # POST /predict — single property valuation
│   │   ├── benchmark.py     # GET /benchmark — model accuracy stats
│   │   ├── comps.py         # POST /comps — find comparable sales
│   │   └── scan.py          # POST /scan — batch CSV valuation
│   ├── schemas.py           # Request/response data shapes
│   └── main.py              # App entry point
│
├── web/                     # Next.js frontend
│   ├── app/
│   │   ├── page.tsx         # Homepage (prediction form + results)
│   │   ├── benchmark/       # Model accuracy dashboard
│   │   ├── scanner/         # Batch CSV upload
│   │   └── model-card/      # Model documentation
│   └── components/          # Reusable UI components
│
├── supabase/
│   └── schema.sql           # Database table definitions
│
└── Dockerfile               # Container for HuggingFace Spaces
```

---

## Running locally

**Requirements:** Python 3.11+, Node 20+, uv (Python package manager)

```bash
# Clone
git clone https://github.com/Ofunrein/avm-zestimate
cd avm-zestimate

# Install Python deps
cd ml && uv sync && cd ..

# Train the model (requires Kaggle API key for data download)
python ml/run_training.py 10   # 10 Optuna trials for quick test

# Start the API (from repo root)
uvicorn api.main:app --reload
# API docs at http://localhost:8000/docs

# Start the frontend (new terminal)
cd web && npm install && npm run dev
# Frontend at http://localhost:3000
```

---

## Model accuracy

Trained and evaluated on Austin TX sales data with a temporal split (train on older sales, test on recent ones — no data leakage).

| Metric | Value | What it means |
|--------|-------|---------------|
| MedAPE | ~12-13% | Median absolute % error — half of predictions are within 12-13% of actual price |
| Within 10% | ~45% | 45% of predictions land within 10% of sale price |
| Within 20% | ~72% | 72% of predictions land within 20% of sale price |

For context: Zillow's published national MedAPE is ~4.5%, but they have 20+ years of MLS data across all markets. On a single city with free public data, 12-13% is competitive.

---

## How the ML model works (simplified)

1. **Data:** ~10k Austin home sales from Kaggle (2018–2021)
2. **Features used:** sqft, bedrooms, bathrooms, year built, ZIP code, lot size, garage spaces, pool, stories, price per sqft ratio, market median by ZIP, home age
3. **Two models trained:** XGBoost and LightGBM (gradient boosted decision trees)
4. **Tuning:** Optuna tries 50 different hyperparameter combinations, picks the best
5. **Ensemble:** Final prediction averages XGBoost and LightGBM outputs
6. **Intervals:** Two additional quantile regression models predict the 5th and 95th percentile, forming the confidence range
7. **SHAP:** After predicting, SHAP calculates how much each feature contributed to that specific prediction

---

## What's shipped

- [x] LLM SHAP explanations (Claude Haiku) — `/explain`
- [x] Natural language search — `/search` (beds, price, ZIP, year built, undervalued filter)
- [x] RAG neighborhood context — Walk Score, TEA school ratings, Census ACS income, Austin crime data
- [x] Deal monitor — weekly GitHub Actions scan, `/deals`, email alerts via SendGrid
- [x] Comparable sales — `/comps` (requires training artifact)

## What's next

- [ ] Live active listings feed (Redfin/MLS) to replace historical Kaggle data for deals
- [ ] TCAD (Travis County) assessed-value data integration for accuracy improvement
- [ ] Nationwide expansion beyond Austin TX
- [ ] Confidence score recalibration (current scores are low for historical backtest data)

---

## License

MIT
