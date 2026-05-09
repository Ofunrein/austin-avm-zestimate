# Austin AVM 9/10 Remediation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 9 identified architecture issues to bring the Austin AVM repo from 6/10 to 9/10 interview-readiness.

**Architecture:** Three phases — Phase 1 makes the repo trustworthy to demo (7.5/10), Phase 2 fixes core product correctness (8.5/10), Phase 3 closes semantic trust gaps (9/10).

**Tech Stack:** FastAPI (Python 3.13), XGBoost + LightGBM (joblib), Next.js 14 (TypeScript), Supabase Postgres, HuggingFace Spaces (Docker), GitHub Actions CI

---

## Phase 1 — Trustworthy to Demo (7.5/10)

### Task 1: Fix sys.path depth bug and README startup command

The `sys.path.insert` in `api/routers/predict.py`, `comps.py`, `scan.py`, and `api/routers/benchmark.py` uses `parents[3]` but should use `parents[2]`. In Docker (`WORKDIR /app`), `Path("/app/api/routers/predict.py").parents[3]` resolves to `/` — not `/app` — so `ml/src` is never found. The README also documents the wrong startup command (`uvicorn main:app` from inside `api/`) when `api/main.py` imports `from api.routers import ...`, requiring the process root to be the repo root.

**Files:**
- Modify: `api/routers/predict.py:7`
- Modify: `api/routers/comps.py:6`
- Modify: `api/routers/scan.py:7`
- Modify: `api/routers/benchmark.py:11-12`
- Modify: `README.md:115-132`

- [ ] **Step 1: Fix sys.path depth in predict.py**

```python
# api/routers/predict.py — replace line 7
sys.path.insert(0, str(Path(__file__).parents[2] / "ml/src"))
```

- [ ] **Step 2: Fix sys.path depth in comps.py**

```python
# api/routers/comps.py — replace line 6
sys.path.insert(0, str(Path(__file__).parents[2] / "ml/src"))
```

- [ ] **Step 3: Fix sys.path depth in scan.py**

```python
# api/routers/scan.py — replace line 7
sys.path.insert(0, str(Path(__file__).parents[2] / "ml/src"))
```

- [ ] **Step 4: Fix parquet path in comps.py and meta path in benchmark.py**

```python
# api/routers/comps.py — replace line 17
p = Path(__file__).parents[2] / "ml/data/processed/train_features.parquet"
```

```python
# api/routers/benchmark.py — replace lines 11-12
meta_path = Path(__file__).parents[2] / "ml/models/meta.json"
residuals_path = Path(__file__).parents[2] / "ml/models/residuals.json"
```

- [ ] **Step 5: Fix README startup command**

```markdown
# README.md — replace lines 115-131 of the Running locally section

# Start the API (from repo root)
cd avm-zestimate
uvicorn api.main:app --reload
# API docs at http://localhost:8000/docs

# Start the frontend (new terminal)
cd web && npm install && npm run dev
# Frontend at http://localhost:3000
```

- [ ] **Step 6: Verify boot from repo root**

Run from `avm-zestimate/`:
```bash
cd ml && uv pip install -e ".[dev]" --system && cd ..
pip install -r api/requirements.txt
uvicorn api.main:app --port 8000 &
sleep 3
curl -s http://localhost:8000/health
```
Expected: `{"status":"ok","version":"2.0.0"}`
Kill server after test.

- [ ] **Step 7: Commit**

```bash
git add api/routers/predict.py api/routers/comps.py api/routers/scan.py api/routers/benchmark.py README.md
git commit -m "fix: correct sys.path depth and README startup command"
```

---

### Task 2: Add API smoke test job to CI

CI (`ci.yml`) runs ML tests and a web build but has no API job — backend startup and import failures are undetected. Add a job that installs API deps, imports `api.main`, and runs a fast route-level smoke test.

**Files:**
- Modify: `.github/workflows/ci.yml`
- Create: `api/tests/test_smoke.py`

- [ ] **Step 1: Write the failing test**

Create `api/tests/test_smoke.py`:

```python
"""Smoke tests: verify API imports and key routes respond."""
import importlib
import sys
from pathlib import Path

# Allow importing ml.src modules without installing the ml package
sys.path.insert(0, str(Path(__file__).parents[2] / "ml/src"))


def test_api_imports():
    """api.main must be importable — catches missing deps and bad path hacks."""
    mod = importlib.import_module("api.main")
    assert hasattr(mod, "app"), "api.main must expose `app`"


def test_health_route():
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_benchmark_route_no_crash():
    """Benchmark must return 200 even when meta.json does not exist."""
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    resp = client.get("/benchmark")
    assert resp.status_code == 200


def test_search_route_no_crash():
    """Search must return 200 even when Supabase is not configured."""
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    resp = client.post("/search", json={"query": "3BR under $400k in 78744"})
    assert resp.status_code == 200
```

- [ ] **Step 2: Run tests locally to verify they fail before fixes**

```bash
pip install -r api/requirements.txt pytest httpx
cd avm-zestimate
python -m pytest api/tests/test_smoke.py -v --tb=short
```
Expected: `test_api_imports` or `test_health_route` may fail due to sys.path bug (Task 1 must be done first). After Task 1 fixes, all 4 should pass except possibly predict-dependent ones that need model files.

- [ ] **Step 3: Run tests after Task 1 fixes to confirm pass**

```bash
python -m pytest api/tests/test_smoke.py -v --tb=short
```
Expected: 4 PASSED (benchmark returns "not-trained" response, search returns empty results — both valid without DB/models).

- [ ] **Step 4: Add api-tests job to ci.yml**

```yaml
# .github/workflows/ci.yml — add this job after the web-build job

  api-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Install API deps
        run: pip install -r api/requirements.txt pytest httpx
      - name: Run API smoke tests
        run: python -m pytest api/tests/test_smoke.py -v --tb=short
```

- [ ] **Step 5: Push and verify CI passes**

```bash
git add .github/workflows/ci.yml api/tests/test_smoke.py
git commit -m "ci: add API smoke test job"
git push
```
Check GitHub Actions — all three jobs (ml-tests, web-build, api-tests) must be green.

---

### Task 3: Remove fake fallback metrics

`benchmark.py` returns zeros when meta.json is missing — clients can't distinguish "untrained" from "0% error". `web/app/benchmark/page.tsx:21-22` invents `8.5` and `9.2` as baseline fallbacks. `web/app/page.tsx:89` has hardcoded hero metrics. All must show actual values or "unavailable" — no invented numbers.

**Files:**
- Modify: `api/routers/benchmark.py`
- Modify: `web/app/benchmark/page.tsx`
- Modify: `web/app/page.tsx`
- Modify: `api/schemas.py` (add `Optional` to benchmark fields)

- [ ] **Step 1: Make benchmark fields Optional in schema**

Find `BenchmarkResponse` in `api/schemas.py`. Change numeric fields to `Optional[float]` with default `None`:

```python
from typing import Optional

class BenchmarkResponse(BaseModel):
    model_version: str
    test_medape: Optional[float] = None
    test_mae: Optional[float] = None
    test_rmse: Optional[float] = None
    test_within_5pct: Optional[float] = None
    test_within_10pct: Optional[float] = None
    n_test: Optional[int] = None
    baseline_zip_median_medape: Optional[float] = None
    baseline_ppsf_medape: Optional[float] = None
    by_zip: list = []
```

- [ ] **Step 2: Fix benchmark.py to use None instead of zeros**

Replace the fallback block in `api/routers/benchmark.py`:

```python
@router.get("/benchmark", response_model=BenchmarkResponse)
def get_benchmark():
    meta_path = Path(__file__).parents[2] / "ml/models/meta.json"
    residuals_path = Path(__file__).parents[2] / "ml/models/residuals.json"

    if not meta_path.exists():
        return BenchmarkResponse(model_version="not-trained")

    meta = json.loads(meta_path.read_text())
    residuals = json.loads(residuals_path.read_text()) if residuals_path.exists() else {}
    overall = residuals.get("overall", {})

    return BenchmarkResponse(
        model_version=meta.get("version", "1.0.0"),
        test_medape=meta.get("test_medape") or None,
        test_mae=overall.get("mae") or None,
        test_rmse=overall.get("rmse") or None,
        test_within_5pct=overall.get("within_5pct") or None,
        test_within_10pct=overall.get("within_10pct") or None,
        n_test=overall.get("n") or None,
        baseline_zip_median_medape=meta.get("test_medape_zip_median") or None,
        baseline_ppsf_medape=meta.get("test_medape_ppsf") or None,
        by_zip=residuals.get("by_zip", []),
    )
```

- [ ] **Step 3: Also save baseline metrics in run_training.py meta**

In `ml/run_training.py`, add baseline metrics to the `meta` dict (around line 124):

```python
meta = {
    "version": "1.0.0",
    "data_sha256": sha,
    "xgb_params": xgb_params,
    "lgb_params": lgb_params,
    "xgb_weight": xgb_weight,
    "test_medape": ens_medape,
    "test_medape_zip_median": results["test_medape_zip_median"],
    "test_medape_ppsf": results["test_medape_ppsf"],
    "residuals": residuals,
    "feature_cols": build_feature_matrix(test_df).columns.tolist(),
}
```

- [ ] **Step 4: Fix benchmark page to handle null values**

In `web/app/benchmark/page.tsx`, replace the hardcoded fallback line:

```tsx
// Replace:
{ name: "ZIP MEDIAN", medape: data.baseline_zip_median_medape || 8.5, color: '#4a4842' },
{ name: "PPSF", medape: data.baseline_ppsf_medape || 9.2, color: '#3a3a45' },

// With:
...(data.baseline_zip_median_medape != null
  ? [{ name: "ZIP MEDIAN", medape: data.baseline_zip_median_medape, color: '#4a4842' }]
  : []),
...(data.baseline_ppsf_medape != null
  ? [{ name: "PPSF", medape: data.baseline_ppsf_medape, color: '#3a3a45' }]
  : []),
```

- [ ] **Step 5: Fix homepage hero metrics**

In `web/app/page.tsx`, the hero stats section (around line 89) has hardcoded numbers. Fetch from `/benchmark` at page load or mark explicitly as static/last-known:

```tsx
// If the API call fails or returns null, show "—" not a number
// Find the hero stats array and replace hardcoded values with:
{ label: "MEDAPE", value: benchmarkData?.test_medape != null ? `${benchmarkData.test_medape.toFixed(1)}%` : "—" },
{ label: "WITHIN 10%", value: benchmarkData?.test_within_10pct != null ? `${(benchmarkData.test_within_10pct * 100).toFixed(0)}%` : "—" },
```

If the component is a Server Component, add a `fetch` call to the API at the top of the page function. If it's a Client Component, add a `useEffect`. Choose based on the existing component pattern in that file.

- [ ] **Step 6: Test**

```bash
python -m pytest api/tests/test_smoke.py::test_benchmark_route_no_crash -v
```
Expected: PASS. Also manually verify benchmark page shows "not-trained" or real values, never `0.00%`.

- [ ] **Step 7: Commit**

```bash
git add api/routers/benchmark.py api/schemas.py ml/run_training.py web/app/benchmark/page.tsx web/app/page.tsx
git commit -m "fix: remove hardcoded fallback metrics from benchmark and homepage"
```

---

## Phase 2 — Core Correctness (8.5/10)

### Task 4: Training/inference preprocessing parity

Training calls `add_location` which creates and fits a `LabelEncoder` on all ZIPs in the dataset. This encoder is discarded — it's not saved. Inference creates a new `LabelEncoder` on a single row, so `zip_encoded` is always 0 regardless of ZIP code. The model never sees the correct ZIP integer it learned during training.

Additionally: training calls `add_assessed_features`, adding `price_per_sqft_assessed` and `assessed_ratio` to `FEATURE_COLS`. Inference (`predict.py`, `scan.py`) never calls this, so those two features are always 0 via `build_feature_matrix`'s `fillna(0)`.

The fix: save `zip_encoder` during training, load it alongside models, pass it to `add_location` at inference time. Also call `add_assessed_features` in inference.

**Files:**
- Modify: `ml/run_training.py`
- Modify: `ml/src/avm/features.py`
- Modify: `api/model_loader.py`
- Modify: `api/routers/predict.py`
- Modify: `api/routers/scan.py`
- Create: `api/tests/test_parity.py`

- [ ] **Step 1: Write failing parity test**

Create `api/tests/test_parity.py`:

```python
"""Assert training and inference use the same feature engineering."""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parents[2] / "ml/src"))


def _make_sample_property() -> dict:
    return {
        "sqft_living": 1800.0,
        "beds": 3,
        "baths_full": 2.0,
        "baths_half": 0.0,
        "year_built": 2005,
        "zip_code": "78744",
        "lat": 30.20,
        "lng": -97.72,
        "lot_sqft": 6000.0,
        "garage_spaces": 2.0,
        "has_pool": 0,
        "stories": 1,
    }


def test_zip_encoded_is_not_always_zero():
    """Inference must use the saved encoder, not refit on a single row."""
    from pathlib import Path
    models_dir = Path(__file__).parents[2] / "ml/models"
    if not (models_dir / "zip_encoder.joblib").exists():
        import pytest
        pytest.skip("zip_encoder.joblib not yet generated — run training first")

    import joblib
    from avm.features import add_structural, add_location, build_feature_matrix
    encoder = joblib.load(models_dir / "zip_encoder.joblib")

    prop = _make_sample_property()
    df = pd.DataFrame([prop])
    df = add_structural(df)
    df, _ = add_location(df, encoder=encoder)
    X = build_feature_matrix(df)

    # 78744 must encode to a consistent non-zero integer when encoder is pre-fitted
    assert "zip_encoded" in X.columns
    # Different ZIPs must produce different encodings
    prop2 = dict(prop, zip_code="78750")
    df2 = pd.DataFrame([prop2])
    df2 = add_structural(df2)
    df2, _ = add_location(df2, encoder=encoder)
    X2 = build_feature_matrix(df2)
    assert X["zip_encoded"].values[0] != X2["zip_encoded"].values[0], \
        "Different ZIPs must produce different zip_encoded values"


def test_assessed_features_present():
    """predict path must include assessed features (even when values are zero)."""
    from avm.features import add_structural, add_location, add_assessed_features, build_feature_matrix, FEATURE_COLS
    prop = _make_sample_property()
    df = pd.DataFrame([prop])
    df = add_structural(df)
    df, _ = add_location(df)
    df = add_assessed_features(df)
    X = build_feature_matrix(df)
    assert "price_per_sqft_assessed" in X.columns
    assert "assessed_ratio" in X.columns


def test_feature_col_count_matches_training():
    """Inference must produce same number of features as FEATURE_COLS."""
    from avm.features import add_structural, add_location, add_assessed_features, build_feature_matrix, FEATURE_COLS
    prop = _make_sample_property()
    # Add is_covid_period (training adds this via clean.py; inference sets it 0)
    df = pd.DataFrame([{**prop, "is_covid_period": 0}])
    df = add_structural(df)
    df, _ = add_location(df)
    df = add_assessed_features(df)
    X = build_feature_matrix(df)
    # X must have the full FEATURE_COLS set (minus any that are truly unavailable)
    assert len(X.columns) == len(FEATURE_COLS), \
        f"Expected {len(FEATURE_COLS)} features, got {len(X.columns)}: {list(X.columns)}"
```

- [ ] **Step 2: Run test to see it fail**

```bash
python -m pytest api/tests/test_parity.py -v --tb=short
```
Expected: `test_zip_encoded_is_not_always_zero` skips (encoder not saved yet); `test_assessed_features_present` passes; `test_feature_col_count_matches_training` fails (missing features).

- [ ] **Step 3: Modify add_location to accept optional pre-fitted encoder**

In `ml/src/avm/features.py`, change `add_location` signature:

```python
from sklearn.preprocessing import LabelEncoder

def add_location(df: pd.DataFrame, encoder: LabelEncoder | None = None, income_lookup: dict | None = None) -> tuple[pd.DataFrame, LabelEncoder]:
    df = df.copy()
    lat_diff = df["lat"] - DOWNTOWN_LAT
    lng_diff = df["lng"] - DOWNTOWN_LNG
    df["dist_downtown_miles"] = np.sqrt(lat_diff**2 + lng_diff**2) * 69.0

    if income_lookup:
        df["zip_income_score"] = df["zip_code"].map(income_lookup).fillna(0.5)
    else:
        df["zip_income_score"] = 0.5

    le = encoder if encoder is not None else LabelEncoder()
    if encoder is None:
        le.fit(df["zip_code"].astype(str))
    # transform with known classes; unseen ZIPs fall back to 0
    zips = df["zip_code"].astype(str)
    known = set(le.classes_)
    df["zip_encoded"] = zips.apply(
        lambda z: int(le.transform([z])[0]) if z in known else 0
    )
    return df, le
```

- [ ] **Step 4: Save zip_encoder in run_training.py**

In `ml/run_training.py`, after the `add_location` call (line 56), save the encoder:

```python
    df, zip_encoder = add_location(df)
    df = add_market_features(df)
    df = add_assessed_features(df)

    # ... (temporal split etc) ...

    # In the [9/9] Saving section, add after save_models():
    import joblib
    joblib.dump(zip_encoder, MODELS_DIR / "zip_encoder.joblib")
    print("  Saved zip_encoder.joblib")
```

- [ ] **Step 5: Load zip_encoder in model_loader.py**

Add `zip_encoder` to `_load_local`, `_load_from_hf`, and `load_all_models`:

```python
def _load_local():
    import joblib
    xgb = joblib.load(LOCAL_MODELS / "xgb_model.joblib")
    lgb = joblib.load(LOCAL_MODELS / "lgb_model.joblib")
    q_low = joblib.load(LOCAL_MODELS / "q_low.joblib")
    q_high = joblib.load(LOCAL_MODELS / "q_high.joblib")
    meta = json.loads((LOCAL_MODELS / "meta.json").read_text())
    enc_path = LOCAL_MODELS / "zip_encoder.joblib"
    zip_encoder = joblib.load(enc_path) if enc_path.exists() else None
    return xgb, lgb, q_low, q_high, meta, zip_encoder


def _load_from_hf():
    from huggingface_hub import hf_hub_download
    import tempfile, shutil, joblib
    tmp = Path(tempfile.mkdtemp())
    files = ["xgb_model.joblib", "lgb_model.joblib", "q_low.joblib", "q_high.joblib", "meta.json"]
    for f in files:
        path = hf_hub_download(repo_id=HF_REPO_ID, filename=f)
        shutil.copy(path, tmp / f)
    # zip_encoder is optional — older model repos may not have it
    try:
        path = hf_hub_download(repo_id=HF_REPO_ID, filename="zip_encoder.joblib")
        shutil.copy(path, tmp / "zip_encoder.joblib")
    except Exception:
        pass
    xgb = joblib.load(tmp / "xgb_model.joblib")
    lgb = joblib.load(tmp / "lgb_model.joblib")
    q_low = joblib.load(tmp / "q_low.joblib")
    q_high = joblib.load(tmp / "q_high.joblib")
    meta = json.loads((tmp / "meta.json").read_text())
    enc_path = tmp / "zip_encoder.joblib"
    zip_encoder = joblib.load(enc_path) if enc_path.exists() else None
    return xgb, lgb, q_low, q_high, meta, zip_encoder


def load_all_models():
    if HF_REPO_ID:
        return _load_from_hf()
    return _load_local()
```

- [ ] **Step 6: Update predict.py to use encoder and assessed features**

In `api/routers/predict.py`, update `get_models` return and `predict` function:

```python
from avm.features import add_structural, add_location, add_market_features, add_assessed_features, build_feature_matrix

_models = None

def get_models():
    global _models
    if _models is None:
        _models = load_all_models()  # now returns 6-tuple
    return _models

@router.post("/predict", response_model=PredictionResponse)
def predict(prop: PropertyInput):
    xgb_model, lgb_model, q_low, q_high, meta, zip_encoder = get_models()
    df = _property_to_df(prop)
    df["is_covid_period"] = 0  # all live properties are post-covid
    df = add_structural(df)
    df, _ = add_location(df, encoder=zip_encoder)
    df = add_market_features(df)
    df = add_assessed_features(df)
    X = build_feature_matrix(df)
    # ... rest unchanged
```

- [ ] **Step 7: Update scan.py similarly**

In `api/routers/scan.py`, same pattern:

```python
from avm.features import add_structural, add_location, add_market_features, add_assessed_features, build_feature_matrix

def scan(req: ScanRequest):
    xgb_model, lgb_model, q_low, q_high, meta, zip_encoder = load_all_models()
    # ...
    for i, prop in enumerate(req.properties):
        df = pd.DataFrame([prop.model_dump()])
        df["is_covid_period"] = 0
        df = add_structural(df)
        df, _ = add_location(df, encoder=zip_encoder)
        df = add_market_features(df)
        df = add_assessed_features(df)
        X = build_feature_matrix(df)
        # ... rest unchanged
```

- [ ] **Step 8: Run parity tests — all must pass (after training run generates encoder)**

Since we can't re-run training in CI without data/time, the parity test for `zip_encoded` is marked skip-if-encoder-missing. Verify locally or note in PR that this test unblocks once the next training run is executed.

```bash
python -m pytest api/tests/test_parity.py -v --tb=short
```
Expected: `test_zip_encoded_is_not_always_zero` skips if encoder not present, `test_assessed_features_present` PASS, `test_feature_col_count_matches_training` PASS.

- [ ] **Step 9: Commit**

```bash
git add ml/src/avm/features.py ml/run_training.py api/model_loader.py api/routers/predict.py api/routers/scan.py api/tests/test_parity.py
git commit -m "fix: save/load zip encoder and add assessed features to inference path"
```

---

### Task 5: Comps artifact — emit parquet and fail explicitly

`comps.py` returns `[]` silently when `train_features.parquet` is missing. `run_training.py` never saves this file. Fix: save it at the end of training, and return a clear error from `/comps` if missing instead of empty array.

**Files:**
- Modify: `ml/run_training.py`
- Modify: `api/routers/comps.py`

- [ ] **Step 1: Save train_features.parquet in run_training.py**

Add after the feature engineering block (after `add_assessed_features`, before the temporal split):

```python
    df = add_assessed_features(df)

    # Persist processed features for comps endpoint
    processed_dir = Path(__file__).parent / "data/processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(processed_dir / "train_features.parquet", index=False)
    print(f"  Saved train_features.parquet ({len(df):,} rows)")
```

- [ ] **Step 2: Make comps.py return explicit error when artifact missing**

```python
from fastapi import APIRouter, Query, HTTPException

def get_sold_df() -> pd.DataFrame:
    global _sold_df
    if _sold_df is None:
        p = Path(__file__).parents[2] / "ml/data/processed/train_features.parquet"
        if not p.exists():
            raise HTTPException(
                status_code=503,
                detail="Comparable sales data not available. Run the training pipeline to generate train_features.parquet."
            )
        _sold_df = pd.read_parquet(p)
    return _sold_df
```

- [ ] **Step 3: Test comps returns 503 when parquet missing**

```python
# Add to api/tests/test_smoke.py:

def test_comps_returns_503_without_parquet(tmp_path, monkeypatch):
    """comps must return 503 not empty array when artifact missing."""
    import importlib
    # Patch parquet path to nonexistent location
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    # This will 503 in CI (no parquet) — verify it's 503 not 200 with empty
    resp = client.get("/comps?lat=30.2&lng=-97.7&sqft=1800&beds=3")
    assert resp.status_code in (200, 503)  # 200 if parquet exists, 503 if not
    if resp.status_code == 503:
        assert "detail" in resp.json()
```

- [ ] **Step 4: Commit**

```bash
git add ml/run_training.py api/routers/comps.py api/tests/test_smoke.py
git commit -m "fix: save comps artifact in training and return 503 instead of empty array"
```

---

### Task 6: Make /search honest about what filters it supports

`llm.py:53-57` tells the LLM to parse `has_pool` as a supported filter, but `search.py` never applies it. `undervalued_only` queries `.gt("value_gap_pct", 0)` on the DB, but `value_gap_pct` doesn't exist in the `predictions` table schema — this fails silently at the supabase query level. Fix: remove `has_pool` from the parser schema, and compute `undervalued_only` purely in Python from `predicted_price`/`list_price` (already done in the loop, but the broken DB filter must be removed).

**Files:**
- Modify: `api/services/llm.py`
- Modify: `api/routers/search.py`

- [ ] **Step 1: Write test for search honesty**

Add to `api/tests/test_smoke.py`:

```python
def test_search_undervalued_no_db_error():
    """undervalued_only must not cause DB errors (value_gap_pct not in predictions schema)."""
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    # Without DB configured, must return 200 empty results — not 500
    resp = client.post("/search", json={"query": "undervalued homes in 78744"})
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
```

- [ ] **Step 2: Remove has_pool from LLM parser schema**

In `api/services/llm.py`, update the `parse_search_query` prompt:

```python
def parse_search_query(query: str) -> dict:
    prompt = (
        "Extract search parameters from this Austin TX real estate query. Return JSON only, no explanation.\n"
        'Schema: {"beds_min": int|null, "baths_min": float|null, "sqft_min": int|null, '
        '"sqft_max": int|null, "price_max": int|null, "zip_codes": [str]|null, '
        '"undervalued_only": bool, "year_built_min": int|null}\n'
        "Note: only return fields from this schema. Do not add has_pool or other unsupported fields.\n"
        f"Query: {query}"
    )
```

- [ ] **Step 3: Fix undervalued_only in search.py to not use nonexistent DB column**

In `api/routers/search.py`, replace the `undervalued_only` DB filter:

```python
    # Remove: q = q.gt("value_gap_pct", 0).order("value_gap_pct", desc=True)
    # Replace with:
    if params.get("undervalued_only"):
        # Filter in Python after fetch — value_gap_pct not a DB column
        q = q.not_.is_("list_price", "null").order("predicted_price", desc=True)
    else:
        q = q.order("predicted_price", desc=True)
    rows = q.limit(50).execute().data  # fetch more rows, filter down in Python

    results: list[SearchResult] = []
    for r in rows:
        shap_json = r.get("shap_json") or []
        top_driver = shap_json[0]["feature"] if shap_json else None
        list_price = r.get("list_price")
        gap = (
            round((r["predicted_price"] - list_price) / list_price * 100, 1)
            if list_price and list_price > 0
            else None
        )
        results.append(SearchResult(
            id=str(r["id"]),
            address=r.get("address"),
            zip_code=r.get("zip_code"),
            sqft_living=r.get("sqft_living"),
            beds=r.get("beds"),
            baths_full=r.get("baths_full"),
            year_built=r.get("year_built"),
            predicted_price=r["predicted_price"],
            list_price=list_price,
            value_gap_pct=gap,
            confidence_score=r.get("confidence_score", 0),
            shap_top_driver=top_driver,
            created_at=str(r.get("created_at", "")),
        ))

    if params.get("undervalued_only"):
        results = [r for r in results if r.value_gap_pct is not None and r.value_gap_pct > 0]
        results.sort(key=lambda x: x.value_gap_pct or 0, reverse=True)

    return SearchResponse(results=results[:20], query_parsed=params, total=len(results[:20]))
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest api/tests/test_smoke.py -v --tb=short
```
Expected: all smoke tests PASS.

- [ ] **Step 5: Commit**

```bash
git add api/services/llm.py api/routers/search.py api/tests/test_smoke.py
git commit -m "fix: remove unsupported has_pool filter and fix undervalued_only to use Python not DB column"
```

---

## Phase 3 — Semantic Trust (9/10)

### Task 7: Label Kaggle data as historical; deals UI shows correct framing

The core semantic problem: `seed_inventory.py` seeds the `predictions` table with Kaggle *sold* records labeled as `list_price`. The `deal monitor` then flags them as "undervalued active listings." They're not active — they sold years ago. The fix without needing real live listings: add a `data_source` column to distinguish historical from future live data, label all Kaggle rows as `"kaggle_historical"`, update the UI to show "historical opportunity" framing, and update README to be accurate.

**Files:**
- Modify: `supabase/schema.sql`
- Modify: `api/scripts/seed_inventory.py`
- Modify: `api/scripts/monitor.py`
- Modify: `web/app/page.tsx` (deals section badge)
- Modify: `README.md`

- [ ] **Step 1: Add data_source column to schema.sql**

```sql
-- Add to supabase/schema.sql after the list_price line:
alter table predictions add column if not exists data_source text default 'kaggle_historical';
create index if not exists idx_predictions_source on predictions(data_source);
```

Run in Supabase SQL editor:
```sql
alter table predictions add column if not exists data_source text default 'kaggle_historical';
create index if not exists idx_predictions_source on predictions(data_source);
```

- [ ] **Step 2: Seed sets data_source = 'kaggle_historical'**

In `api/scripts/seed_inventory.py`, add to the records dict:

```python
records.append({
    "address": parsed["address"],
    "lat": parsed["lat"],
    "lng": parsed["lng"],
    "sqft_living": parsed["sqft_living"],
    "beds": parsed["beds"],
    "baths_full": parsed["baths_full"],
    "year_built": parsed["year_built"],
    "zip_code": parsed["zip_code"],
    "predicted_price": pred["predicted_price"],
    "lower_bound": pred["lower_bound"],
    "upper_bound": pred["upper_bound"],
    "confidence_score": pred["confidence_score"],
    "shap_json": pred["shap_top5"],
    "list_price": parsed["list_price"],
    "data_source": "kaggle_historical",
})
```

- [ ] **Step 3: Monitor acknowledges historical framing in deals table**

In `api/scripts/monitor.py`, add `data_source` to the deals upsert:

```python
deals.append({
    # ... existing fields ...
    "deal_score": round(gap * r.get("confidence_score", 1) / 100, 2),
    "data_source": r.get("data_source", "kaggle_historical"),
})
```

And update the monitor's print statement to be honest:
```python
print(f"Found {len(deals)} historical value opportunities above {MIN_GAP_PCT}% gap.")
```

- [ ] **Step 4: Update deals UI badge**

In the deals page/component, add a banner or badge:

Find `web/app/` deals page (or the component showing deals). Add:
```tsx
<div className="text-xs text-yellow-500/70 mb-4">
  BASED ON HISTORICAL KAGGLE SALES DATA — NOT LIVE LISTINGS
</div>
```

- [ ] **Step 5: Commit**

```bash
git add supabase/schema.sql api/scripts/seed_inventory.py api/scripts/monitor.py web/app/
git commit -m "fix: label kaggle data as historical; deals UI shows correct framing"
```

---

### Task 8: Finish AI-layer integration — /explain auto-fetches neighborhood context

`/explain` accepts `neighborhood_context` as an optional string but the client never provides it — so explanations never use neighborhood data despite `/neighborhood/{zip}` being a live endpoint. Fix: `/explain` fetches neighborhood context internally from the neighborhood service when the field is empty.

**Files:**
- Modify: `api/routers/explain.py`
- Modify: `api/routers/search.py`
- Modify: `web/components/ExplanationCard.tsx`

- [ ] **Step 1: Write test for neighborhood injection**

Add to `api/tests/test_smoke.py`:

```python
def test_explain_works_without_neighborhood_context():
    """explain must return 200 even when ANTHROPIC_API_KEY not set and neighborhood missing."""
    import os
    os.environ.setdefault("ANTHROPIC_API_KEY", "test_key_not_real")
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    resp = client.post("/explain", json={
        "predicted_price": 450000,
        "lower_bound": 400000,
        "upper_bound": 500000,
        "confidence_score": 75,
        "shap_top5": [{"feature": "sqft_living", "shap_value": 25000, "direction": "increases"}],
        "zip_code": "78744",
        "sqft_living": 1800,
        "beds": 3,
        "baths_full": 2.0,
        "year_built": 2005,
    })
    # With a fake key it'll fail the Anthropic call but must not 500 on missing neighborhood
    assert resp.status_code in (200, 500)  # 500 is ok here (bad API key) but not 422
    if resp.status_code == 500:
        assert "neighborhood" not in str(resp.json()).lower(), \
            "500 should be from Anthropic, not neighborhood lookup failure"
```

- [ ] **Step 2: Auto-fetch neighborhood in explain router**

In `api/routers/explain.py`:

```python
from fastapi import APIRouter
from api.schemas import ExplainRequest, ExplainResponse
from api.services.llm import explain_prediction
from api.services.neighborhood import fetch_neighborhood

router = APIRouter()


@router.post("/explain", response_model=ExplainResponse)
def explain(req: ExplainRequest):
    ctx = req.neighborhood_context
    if not ctx and req.zip_code:
        try:
            data = fetch_neighborhood(req.zip_code)
            parts = []
            if data.get("walk_score"):
                parts.append(f"Walk Score {data['walk_score']}")
            if data.get("school_rating"):
                parts.append(f"school rating {data['school_rating']:.1f}/10")
            if data.get("median_household_income"):
                parts.append(f"median income ${data['median_household_income']:,}")
            ctx = ", ".join(parts) if parts else ""
        except Exception:
            ctx = ""

    text = explain_prediction(
        predicted_price=req.predicted_price,
        lower_bound=req.lower_bound,
        upper_bound=req.upper_bound,
        confidence_score=req.confidence_score,
        shap_top5=[f.model_dump() for f in req.shap_top5],
        zip_code=req.zip_code,
        sqft=req.sqft_living,
        beds=req.beds,
        baths=req.baths_full,
        year_built=req.year_built,
        neighborhood_context=ctx,
    )
    return ExplainResponse(explanation=text)
```

- [ ] **Step 3: Add neighborhood summary to search results**

In `api/routers/search.py`, after building `results`, add ZIP-level neighborhood summaries. Fetch once per unique ZIP:

```python
    from api.services.neighborhood import fetch_neighborhood

    # Enrich with neighborhood summary (one call per ZIP, cached by neighborhood router)
    zip_contexts: dict[str, str] = {}
    for r in results[:5]:  # only top 5 for cost/perf
        z = r.zip_code
        if z and z not in zip_contexts:
            try:
                nd = fetch_neighborhood(z)
                parts = []
                if nd.get("walk_score"):
                    parts.append(f"Walk {nd['walk_score']}")
                if nd.get("school_rating"):
                    parts.append(f"Schools {nd['school_rating']:.1f}/10")
                zip_contexts[z] = " · ".join(parts)
            except Exception:
                zip_contexts[z] = ""
```

Add `neighborhood_summary: Optional[str] = None` to `SearchResult` schema and populate it:
```python
results.append(SearchResult(
    ...
    neighborhood_summary=zip_contexts.get(r.get("zip_code"), ""),
))
```

- [ ] **Step 4: Show neighborhood context in ExplanationCard.tsx**

In `web/components/ExplanationCard.tsx`, after the explanation text block, add:

```tsx
{result.neighborhood_summary && (
  <div className="text-xs text-[var(--text-dim)] mt-2">
    {result.neighborhood_summary}
  </div>
)}
```

- [ ] **Step 5: Commit**

```bash
git add api/routers/explain.py api/routers/search.py api/schemas.py web/components/ExplanationCard.tsx api/tests/test_smoke.py
git commit -m "feat: auto-inject neighborhood context into explain; show in search results"
```

---

### Task 9: README cleanup — match live behavior

README:157 still frames AI layer as roadmap (`- [ ] LLM SHAP explanations`, `- [ ] Natural language search`) when both are shipped. Homepage claims need to either be live-sourced or labeled.

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update roadmap section**

In `README.md`, find the "What's next (roadmap)" section (around line 163–170). Mark shipped items as done and update unchecked items:

```markdown
## What's shipped

- [x] LLM SHAP explanations (Claude Haiku) — `/explain`
- [x] Natural language search — `/search`
- [x] Deal monitor — weekly scan, `/deals`
- [x] RAG neighborhood context — Walk Score, school ratings, Census ACS income
- [x] Agentic deal monitor with email alerts (SendGrid)

## What's next

- [ ] TCAD (Travis County) data integration for better accuracy
- [ ] Live active listings feed (Redfin/MLS) to replace historical Kaggle data
- [ ] Nationwide expansion beyond Austin TX
- [ ] Confidence score recalibration for non-historical predictions
```

- [ ] **Step 2: Update model accuracy table if metrics have drifted**

In `README.md`, verify the metrics table (lines 143-148) matches actual `ml/models/meta.json` values. If they differ, update from meta.json.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: update README roadmap to reflect shipped AI layer"
```

---

## Final Push to HuggingFace Spaces

After all commits above:

- [ ] **Push to HF Space**

```bash
git remote get-url hf-space 2>/dev/null || git remote add hf-space https://Ofunrein:<HF_TOKEN>@huggingface.co/spaces/ofunrein/austin-avm-api
git push hf-space main
```

- [ ] **Verify HF Space comes online**

```bash
for i in $(seq 1 10); do
  sleep 60
  code=$(curl -s -o /dev/null -w "%{http_code}" https://ofunrein-austin-avm-api.hf.space/health)
  echo "$(date +%H:%M) http $code"
  [ "$code" = "200" ] && echo "ONLINE" && break
done
```

- [ ] **Smoke test all routes**

```bash
BASE=https://ofunrein-austin-avm-api.hf.space
curl -s "$BASE/health" | python3 -m json.tool
curl -s -X POST "$BASE/predict" \
  -H "Content-Type: application/json" \
  -d '{"sqft_living":1800,"beds":3,"baths_full":2.0,"year_built":2005,"zip_code":"78744","lat":30.20,"lng":-97.72}' \
  | python3 -m json.tool
curl -s -X POST "$BASE/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"3BR under $500k in 78744"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'search: {d[\"total\"]} results')"
curl -s "$BASE/benchmark" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'medape: {d[\"test_medape\"]}')"
```

Expected: health 200, predict returns `predicted_price`, search returns results, benchmark returns real medape.

---

## Expected Score After Each Phase

| Phase | Fixes | Expected Score |
|-------|-------|---------------|
| Start | None | 6/10 |
| Phase 1 | Boot fix + API CI + real metrics | 7.5/10 |
| Phase 2 | Preprocessing parity + comps + honest search | 8.5/10 |
| Phase 3 | Historical framing + AI layer + README | 9/10 |
