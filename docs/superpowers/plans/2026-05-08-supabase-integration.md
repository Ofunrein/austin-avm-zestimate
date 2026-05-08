# Supabase Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Supabase into the Austin AVM stack across three surfaces: (A) FastAPI prediction logging, (B) comps caching, (C) Next.js prediction history widget.

**Branch:** `dev/implementation`

**Schema already applied** at `supabase/schema.sql` — tables `predictions`, `benchmark_runs`, `comps_cache` exist in the target Supabase project.

---

## Sub-plan A: FastAPI → Supabase logging

### A-1: Add `supabase-py` to `api/requirements.txt`

**File:** `api/requirements.txt`

Append one line:

```
supabase>=2.10,<3
```

Full file after edit:

```
fastapi>=0.111
uvicorn[standard]>=0.29
pydantic>=2.7
xgboost>=2.0
lightgbm>=4.3
shap>=0.44
pandas>=2.0
numpy>=1.26
scikit-learn>=1.4
joblib>=1.4
huggingface-hub>=0.23
protobuf==3.20.3
supabase>=2.10,<3
```

Test command:

```bash
cd /path/to/avm-zestimate/api && pip install -r requirements.txt --quiet && python -c "import supabase; print(supabase.__version__)"
```

---

### A-2: Create `api/db.py` — Supabase client singleton

**File:** `api/db.py` (new)

```python
"""Supabase client — initialized once at import time from env vars.

Required env vars:
  SUPABASE_URL  — project URL, e.g. https://xxxx.supabase.co
  SUPABASE_KEY  — service-role secret key (never the anon key on the server)

Both vars must be present for the client to be non-None. If either is missing
(e.g. local dev without a .env file) the module returns None and all callers
must guard with `if db:`.
"""
from __future__ import annotations
import os
from supabase import create_client, Client

_url = os.environ.get("SUPABASE_URL", "")
_key = os.environ.get("SUPABASE_KEY", "")

db: Client | None = create_client(_url, _key) if (_url and _key) else None
```

**Verification:**

```bash
# With vars unset — must not raise, must return None
python -c "import api.db; assert api.db.db is None, 'expected None when env missing'"
echo "PASS: db is None when env missing"

# With vars set — must return a Client
SUPABASE_URL=https://placeholder.supabase.co SUPABASE_KEY=anon-placeholder \
  python -c "import importlib, os; import api.db as m; importlib.reload(m); from supabase import Client; assert isinstance(m.db, Client)"
echo "PASS: db is Client when env present"
```

---

### A-3: Modify `api/routers/predict.py` — fire-and-forget logging

The prediction response is fully computed before touching Supabase. The insert is wrapped in `try/except` so any DB failure is logged to stderr but never propagates to the caller.

**File:** `api/routers/predict.py`

Replace the existing file with:

```python
from fastapi import APIRouter
import numpy as np
import pandas as pd
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "ml/src"))
from avm.features import add_structural, add_location, add_market_features, build_feature_matrix
from avm.intervals import predict_intervals, confidence_score
from avm.shap_gen import make_explainer, top_shap_features
from api.schemas import PropertyInput, PredictionResponse, ShapFeature
from api.model_loader import load_all_models
from api.db import db

router = APIRouter()
_models = None


def get_models():
    global _models
    if _models is None:
        _models = load_all_models()
    return _models


def _property_to_df(p: PropertyInput) -> pd.DataFrame:
    return pd.DataFrame([p.model_dump()])


@router.post("/predict", response_model=PredictionResponse)
def predict(prop: PropertyInput):
    xgb_model, lgb_model, q_low, q_high, meta = get_models()
    df = _property_to_df(prop)
    df = add_structural(df)
    df, _ = add_location(df)
    df = add_market_features(df)
    X = build_feature_matrix(df)

    xgb_pred = float(np.expm1(xgb_model.predict(X)[0]))
    lgb_pred = float(np.expm1(lgb_model.predict(X)[0]))
    w = meta.get("xgb_weight", 0.5)
    predicted = w * xgb_pred + (1 - w) * lgb_pred

    low_arr, high_arr = predict_intervals(q_low, q_high, X)
    conf = confidence_score(
        np.array([predicted]), np.array([low_arr[0]]), np.array([high_arr[0]])
    )[0]

    explainer = make_explainer(xgb_model)
    shap_feats = top_shap_features(explainer, df, n=5)

    response = PredictionResponse(
        predicted_price=int(predicted),
        lower_bound=int(low_arr[0]),
        upper_bound=int(high_arr[0]),
        confidence_score=int(conf),
        shap_top5=[ShapFeature(**f) for f in shap_feats],
        model_version=meta.get("version", "1.0.0"),
    )

    # Fire-and-forget: log prediction to Supabase.
    # A DB failure must never break the prediction response.
    if db is not None:
        try:
            db.table("predictions").insert({
                "address": None,
                "lat": prop.lat,
                "lng": prop.lng,
                "sqft_living": prop.sqft_living,
                "beds": prop.beds,
                "baths_full": prop.baths_full,
                "year_built": prop.year_built,
                "zip_code": prop.zip_code,
                "predicted_price": response.predicted_price,
                "lower_bound": response.lower_bound,
                "upper_bound": response.upper_bound,
                "confidence_score": response.confidence_score,
                "shap_json": [f.model_dump() for f in response.shap_top5],
            }).execute()
        except Exception:
            traceback.print_exc()

    return response
```

**Test — happy path (no DB):**

```bash
cd /path/to/avm-zestimate
python -m pytest api/tests/test_predict_db.py -v
```

**Test file** `api/tests/test_predict_db.py` (new):

```python
"""Tests for Supabase logging in predict router.

These tests run without real Supabase credentials.
They verify: (1) DB failure never breaks the response,
             (2) insert is called with the right table when db is present.
"""
import importlib
import types
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient


VALID_PAYLOAD = {
    "sqft_living": 1800,
    "beds": 3,
    "baths_full": 2,
    "baths_half": 0,
    "year_built": 2005,
    "zip_code": "78701",
    "lat": 30.27,
    "lng": -97.74,
    "lot_sqft": 5000,
    "garage_spaces": 1,
    "has_pool": 0,
    "assessed_value": 0,
}


def _make_mock_models():
    """Return a tuple that mimics load_all_models() output."""
    import numpy as np

    xgb = MagicMock()
    xgb.predict.return_value = np.array([13.0])  # log-space; expm1 ≈ 442413

    lgb = MagicMock()
    lgb.predict.return_value = np.array([13.0])

    q_low = MagicMock()
    q_low.predict.return_value = np.array([12.8])

    q_high = MagicMock()
    q_high.predict.return_value = np.array([13.2])

    meta = {"version": "test", "xgb_weight": 0.5}
    return xgb, lgb, q_low, q_high, meta


@pytest.fixture()
def client_no_db():
    """TestClient with db=None (no env vars)."""
    with patch("api.db.db", None):
        with patch("api.routers.predict.get_models", return_value=_make_mock_models()):
            with patch("avm.features.add_structural", side_effect=lambda df: df), \
                 patch("avm.features.add_location", side_effect=lambda df: (df, None)), \
                 patch("avm.features.add_market_features", side_effect=lambda df: df), \
                 patch("avm.features.build_feature_matrix", side_effect=lambda df: df):
                from api.main import app
                yield TestClient(app)


@pytest.fixture()
def mock_db():
    table_mock = MagicMock()
    table_mock.insert.return_value.execute.return_value = MagicMock()
    db_mock = MagicMock()
    db_mock.table.return_value = table_mock
    return db_mock


def test_predict_returns_200_without_db(client_no_db):
    resp = client_no_db.post("/predict", json=VALID_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()
    assert "predicted_price" in data
    assert "confidence_score" in data


def test_predict_db_failure_does_not_propagate(mock_db):
    mock_db.table.side_effect = Exception("DB down")
    with patch("api.db.db", mock_db):
        with patch("api.routers.predict.get_models", return_value=_make_mock_models()):
            with patch("avm.features.add_structural", side_effect=lambda df: df), \
                 patch("avm.features.add_location", side_effect=lambda df: (df, None)), \
                 patch("avm.features.add_market_features", side_effect=lambda df: df), \
                 patch("avm.features.build_feature_matrix", side_effect=lambda df: df):
                from api.main import app
                client = TestClient(app)
                resp = client.post("/predict", json=VALID_PAYLOAD)
    assert resp.status_code == 200


def test_predict_calls_insert_with_correct_table(mock_db):
    with patch("api.db.db", mock_db):
        with patch("api.routers.predict.get_models", return_value=_make_mock_models()):
            with patch("avm.features.add_structural", side_effect=lambda df: df), \
                 patch("avm.features.add_location", side_effect=lambda df: (df, None)), \
                 patch("avm.features.add_market_features", side_effect=lambda df: df), \
                 patch("avm.features.build_feature_matrix", side_effect=lambda df: df):
                from api.main import app
                client = TestClient(app)
                client.post("/predict", json=VALID_PAYLOAD)
    mock_db.table.assert_called_with("predictions")
```

---

### A-4: Modify `api/routers/benchmark.py` — 24h cache via `benchmark_runs`

**Logic:**
1. On GET `/benchmark`, query `benchmark_runs` ordered by `created_at desc` limit 1.
2. If a row exists and `created_at` is within 24 hours, return it without recomputing.
3. Otherwise read from local model files (existing logic), INSERT the new row, return it.

**File:** `api/routers/benchmark.py`

Replace with:

```python
from fastapi import APIRouter
import json
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from api.schemas import BenchmarkResponse
from api.db import db

router = APIRouter()

_CACHE_TTL_HOURS = 24


def _read_from_files() -> BenchmarkResponse:
    meta_path = Path(__file__).parents[3] / "ml/models/meta.json"
    residuals_path = Path(__file__).parents[3] / "ml/models/residuals.json"

    if not meta_path.exists():
        return BenchmarkResponse(
            model_version="not-trained",
            test_medape=0, test_mae=0, test_rmse=0,
            test_within_5pct=0, test_within_10pct=0, n_test=0,
            baseline_zip_median_medape=0, baseline_ppsf_medape=0,
            by_zip=[],
        )

    meta = json.loads(meta_path.read_text())
    residuals = json.loads(residuals_path.read_text()) if residuals_path.exists() else {}
    overall = residuals.get("overall", {})

    return BenchmarkResponse(
        model_version=meta.get("version", "1.0.0"),
        test_medape=meta.get("test_medape", 0),
        test_mae=overall.get("mae", 0),
        test_rmse=overall.get("rmse", 0),
        test_within_5pct=overall.get("within_5pct", 0),
        test_within_10pct=overall.get("within_10pct", 0),
        n_test=overall.get("n", 0),
        baseline_zip_median_medape=0,
        baseline_ppsf_medape=0,
        by_zip=residuals.get("by_zip", []),
    )


def _row_to_response(row: dict) -> BenchmarkResponse:
    return BenchmarkResponse(
        model_version=row["model_version"],
        test_medape=row.get("medape", 0),
        test_mae=row.get("mae", 0),
        test_rmse=row.get("rmse", 0),
        test_within_5pct=row.get("within_5pct", 0),
        test_within_10pct=row.get("within_10pct", 0),
        n_test=row.get("n_test", 0),
        baseline_zip_median_medape=0,
        baseline_ppsf_medape=0,
        by_zip=row.get("residuals_json", {}).get("by_zip", []) if row.get("residuals_json") else [],
    )


@router.get("/benchmark", response_model=BenchmarkResponse)
def get_benchmark():
    # Attempt cache lookup
    if db is not None:
        try:
            result = (
                db.table("benchmark_runs")
                .select("*")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = result.data
            if rows:
                row = rows[0]
                created_at = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                age = datetime.now(timezone.utc) - created_at
                if age < timedelta(hours=_CACHE_TTL_HOURS):
                    return _row_to_response(row)
        except Exception:
            traceback.print_exc()

    # Cache miss — compute from local files
    fresh = _read_from_files()

    # Persist to Supabase (fire-and-forget)
    if db is not None:
        try:
            meta_path = Path(__file__).parents[3] / "ml/models/meta.json"
            residuals_path = Path(__file__).parents[3] / "ml/models/residuals.json"
            residuals_raw = json.loads(residuals_path.read_text()) if residuals_path.exists() else {}

            db.table("benchmark_runs").insert({
                "model_version": fresh.model_version,
                "medape": fresh.test_medape,
                "mae": fresh.test_mae,
                "rmse": fresh.test_rmse,
                "within_5pct": fresh.test_within_5pct,
                "within_10pct": fresh.test_within_10pct,
                "n_test": fresh.n_test,
                "test_period": None,
                "residuals_json": residuals_raw,
            }).execute()
        except Exception:
            traceback.print_exc()

    return fresh
```

**Test file** `api/tests/test_benchmark_cache.py` (new):

```python
"""Tests for benchmark 24h cache logic.

Runs without real Supabase credentials.
"""
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient


def _make_db_with_fresh_row(age_hours: float = 1.0) -> MagicMock:
    created = (datetime.now(timezone.utc) - timedelta(hours=age_hours)).isoformat()
    row = {
        "model_version": "cached-1.0",
        "medape": 5.5,
        "mae": 18000,
        "rmse": 25000,
        "within_5pct": 0.62,
        "within_10pct": 0.85,
        "n_test": 400,
        "residuals_json": {"by_zip": []},
        "created_at": created,
    }
    execute_mock = MagicMock()
    execute_mock.data = [row]
    chain = MagicMock()
    chain.execute.return_value = execute_mock
    chain.limit.return_value = chain
    chain.order.return_value = chain
    chain.select.return_value = chain
    db_mock = MagicMock()
    db_mock.table.return_value = chain
    return db_mock


def _make_db_empty() -> MagicMock:
    execute_mock = MagicMock()
    execute_mock.data = []
    chain = MagicMock()
    chain.execute.return_value = execute_mock
    chain.limit.return_value = chain
    chain.order.return_value = chain
    chain.select.return_value = chain
    insert_chain = MagicMock()
    insert_chain.execute.return_value = MagicMock()
    chain.insert = MagicMock(return_value=insert_chain)
    db_mock = MagicMock()
    db_mock.table.return_value = chain
    return db_mock


def test_benchmark_returns_cached_row_when_fresh():
    mock_db = _make_db_with_fresh_row(age_hours=1.0)
    with patch("api.db.db", mock_db):
        from api.main import app
        client = TestClient(app)
        resp = client.get("/benchmark")
    assert resp.status_code == 200
    assert resp.json()["model_version"] == "cached-1.0"


def test_benchmark_recomputes_when_cache_stale():
    mock_db = _make_db_with_fresh_row(age_hours=25.0)
    # Stale row — should fall through to file read
    # mock the insert chain on table so insert doesn't error
    insert_chain = MagicMock()
    insert_chain.execute.return_value = MagicMock()
    mock_db.table.return_value.insert = MagicMock(return_value=insert_chain)
    with patch("api.db.db", mock_db):
        with patch("api.routers.benchmark._read_from_files") as mock_read:
            mock_read.return_value = __import__("api.schemas", fromlist=["BenchmarkResponse"]).BenchmarkResponse(
                model_version="fresh-2.0",
                test_medape=4.1, test_mae=15000, test_rmse=22000,
                test_within_5pct=0.71, test_within_10pct=0.91, n_test=500,
                baseline_zip_median_medape=0, baseline_ppsf_medape=0, by_zip=[],
            )
            from api.main import app
            client = TestClient(app)
            resp = client.get("/benchmark")
    assert resp.status_code == 200
    assert resp.json()["model_version"] == "fresh-2.0"


def test_benchmark_returns_200_without_db():
    with patch("api.db.db", None):
        with patch("api.routers.benchmark._read_from_files") as mock_read:
            mock_read.return_value = __import__("api.schemas", fromlist=["BenchmarkResponse"]).BenchmarkResponse(
                model_version="no-db",
                test_medape=0, test_mae=0, test_rmse=0,
                test_within_5pct=0, test_within_10pct=0, n_test=0,
                baseline_zip_median_medape=0, baseline_ppsf_medape=0, by_zip=[],
            )
            from api.main import app
            client = TestClient(app)
            resp = client.get("/benchmark")
    assert resp.status_code == 200
```

**Run both A-3 and A-4 tests together:**

```bash
cd /path/to/avm-zestimate
python -m pytest api/tests/test_predict_db.py api/tests/test_benchmark_cache.py -v
```

---

### A-5: Add `SUPABASE_URL` and `SUPABASE_KEY` to HuggingFace Space secrets

This step requires manual action in the HF Spaces dashboard. No code change is needed.

**Steps:**
1. Go to `https://huggingface.co/spaces/<your-org>/avm-zestimate/settings`.
2. Under **Repository secrets**, add:
   - `SUPABASE_URL` — value: your Supabase project URL (e.g. `https://xxxx.supabase.co`)
   - `SUPABASE_KEY` — value: your Supabase **service-role** secret key (from Project Settings → API → service_role)
3. Redeploy the Space (push any commit or click "Restart space").
4. Verify in Space logs: the first `/predict` call should not print any traceback.

> The service-role key is used server-side only inside the HF Space Docker container. It is never exposed to the browser.

---

## Sub-plan B: Comps caching in FastAPI

### B-1: Modify `api/routers/comps.py` — 7-day `comps_cache` lookup

**Cache key format:** `"{lat:.3f}_{lng:.3f}_{sqft:.0f}"` — rounds coordinates to ~100m precision, sqft to nearest integer. Sufficient granularity to share results across requests for the same property.

TTL is 7 days (`created_at` older than 7 days → recompute and upsert).

**File:** `api/routers/comps.py`

Replace with:

```python
from fastapi import APIRouter, Query
import pandas as pd
import json
import traceback
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "ml/src"))
from avm.comps import find_comps
from api.schemas import CompProperty
from api.db import db

router = APIRouter()
_sold_df = None

_CACHE_TTL_DAYS = 7


def get_sold_df() -> pd.DataFrame:
    global _sold_df
    if _sold_df is None:
        p = Path(__file__).parents[3] / "ml/data/processed/train_features.parquet"
        if p.exists():
            _sold_df = pd.read_parquet(p)
        else:
            _sold_df = pd.DataFrame()
    return _sold_df


def _make_cache_key(lat: float, lng: float, sqft: float) -> str:
    return f"{lat:.3f}_{lng:.3f}_{sqft:.0f}"


def _serialize_comps(records: list[dict]) -> list[dict]:
    """Convert any non-JSON-serializable values (e.g. numpy types) to plain Python."""
    out = []
    for r in records:
        out.append({k: (v.item() if hasattr(v, "item") else v) for k, v in r.items()})
    return out


@router.get("/comps", response_model=list[CompProperty])
def get_comps(
    lat: float = Query(...),
    lng: float = Query(...),
    sqft: float = Query(...),
    beds: int = Query(default=3),
    bath_total: float = Query(default=2.0),
    year_built: int = Query(default=2000),
    n: int = Query(default=5, le=10),
):
    cache_key = _make_cache_key(lat, lng, sqft)

    # Cache lookup
    if db is not None:
        try:
            result = db.table("comps_cache").select("*").eq("cache_key", cache_key).execute()
            rows = result.data
            if rows:
                row = rows[0]
                created_at = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                age = datetime.now(timezone.utc) - created_at
                if age < timedelta(days=_CACHE_TTL_DAYS):
                    cached = row["comps_json"]
                    return [CompProperty(**c) for c in cached]
        except Exception:
            traceback.print_exc()

    # Cache miss — compute
    sold = get_sold_df()
    if sold.empty:
        return []

    subject = {
        "lat": lat, "lng": lng, "sqft_living": sqft,
        "beds": beds, "bath_total": bath_total, "age": 2024 - year_built,
    }
    result_df = find_comps(subject, sold, n=n)
    if result_df.empty:
        return []

    records = result_df.to_dict(orient="records")
    comps_out = [CompProperty(
        address=r.get("address"),
        sale_price=r["sale_price"],
        sale_date=str(r["sale_date"]) if r.get("sale_date") else None,
        sqft_living=r["sqft_living"],
        beds=r.get("beds"),
        bath_total=r.get("bath_total"),
        distance_miles=r.get("distance_miles"),
        similarity_score=r["similarity_score"],
    ) for r in records]

    # Persist to cache (upsert — same cache_key overwrites stale row)
    if db is not None:
        try:
            db.table("comps_cache").upsert({
                "cache_key": cache_key,
                "comps_json": _serialize_comps([c.model_dump() for c in comps_out]),
            }).execute()
        except Exception:
            traceback.print_exc()

    return comps_out
```

**Test file** `api/tests/test_comps_cache.py` (new):

```python
"""Tests for comps cache logic."""
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

_FRESH_COMPS = [
    {
        "address": "123 Main St",
        "sale_price": 420000.0,
        "sale_date": "2024-01-15",
        "sqft_living": 1750.0,
        "beds": 3.0,
        "bath_total": 2.0,
        "distance_miles": 0.3,
        "similarity_score": 0.91,
    }
]


def _db_with_cache_hit(age_days: float = 1.0) -> MagicMock:
    created = (datetime.now(timezone.utc) - timedelta(days=age_days)).isoformat()
    row = {"cache_key": "30.270_-97.740_1800", "comps_json": _FRESH_COMPS, "created_at": created}
    execute_mock = MagicMock()
    execute_mock.data = [row]
    chain = MagicMock()
    chain.execute.return_value = execute_mock
    chain.eq.return_value = chain
    chain.select.return_value = chain
    db_mock = MagicMock()
    db_mock.table.return_value = chain
    return db_mock


def _db_with_cache_miss() -> MagicMock:
    execute_mock = MagicMock()
    execute_mock.data = []
    chain = MagicMock()
    chain.execute.return_value = execute_mock
    chain.eq.return_value = chain
    chain.select.return_value = chain
    upsert_chain = MagicMock()
    upsert_chain.execute.return_value = MagicMock()
    chain.upsert = MagicMock(return_value=upsert_chain)
    db_mock = MagicMock()
    db_mock.table.return_value = chain
    return db_mock


def test_comps_returns_cache_hit():
    mock_db = _db_with_cache_hit(age_days=1.0)
    with patch("api.db.db", mock_db):
        from api.main import app
        client = TestClient(app)
        resp = client.get("/comps?lat=30.27&lng=-97.74&sqft=1800")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["address"] == "123 Main St"


def test_comps_recomputes_on_stale_cache():
    mock_db = _db_with_cache_miss()
    with patch("api.db.db", mock_db):
        with patch("api.routers.comps.get_sold_df") as mock_sold:
            mock_sold.return_value = __import__("pandas").DataFrame()  # returns []
            from api.main import app
            client = TestClient(app)
            resp = client.get("/comps?lat=30.27&lng=-97.74&sqft=1800")
    assert resp.status_code == 200
    assert resp.json() == []


def test_comps_cache_key_format():
    from api.routers.comps import _make_cache_key
    key = _make_cache_key(30.2711, -97.7437, 1823.6)
    assert key == "30.271_-97.744_1824"


def test_comps_returns_200_without_db():
    with patch("api.db.db", None):
        with patch("api.routers.comps.get_sold_df") as mock_sold:
            mock_sold.return_value = __import__("pandas").DataFrame()
            from api.main import app
            client = TestClient(app)
            resp = client.get("/comps?lat=30.27&lng=-97.74&sqft=1800")
    assert resp.status_code == 200
```

**Run:**

```bash
cd /path/to/avm-zestimate
python -m pytest api/tests/test_comps_cache.py -v
```

---

## Sub-plan C: Next.js prediction history

### C-1: Create `web/lib/supabase.ts` — typed client

This uses `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` — the anon (public) key is safe for client-side use because row-level security on the `predictions` table should allow anon reads.

**File:** `web/lib/supabase.ts` (new)

```typescript
import { createClient, SupabaseClient } from "@supabase/supabase-js";

export interface PredictionRow {
  id: string;
  address: string | null;
  lat: number;
  lng: number;
  sqft_living: number;
  beds: number;
  baths_full: number;
  year_built: number;
  zip_code: string;
  predicted_price: number;
  lower_bound: number;
  upper_bound: number;
  confidence_score: number;
  shap_json: Array<{
    feature: string;
    feature_value: number;
    shap_value: number;
    direction: "increases" | "decreases";
  }> | null;
  created_at: string;
}

const url = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

// Export a singleton. If env vars are missing (local dev without .env.local),
// the client is still created but all queries will fail gracefully.
export const supabase: SupabaseClient = createClient(url, key);

export async function fetchRecentPredictions(limit = 5): Promise<PredictionRow[]> {
  if (!url || !key) return [];
  const { data, error } = await supabase
    .from("predictions")
    .select("id, address, zip_code, sqft_living, beds, baths_full, year_built, predicted_price, lower_bound, upper_bound, confidence_score, created_at")
    .order("created_at", { ascending: false })
    .limit(limit);
  if (error) {
    console.error("[supabase] fetchRecentPredictions:", error.message);
    return [];
  }
  return (data ?? []) as PredictionRow[];
}
```

---

### C-2: Create `web/components/RecentValuations.tsx`

Fetches the last 5 prediction rows from Supabase on mount and renders a compact history list. Handles loading, empty, and error states. Follows the existing component style conventions (CSS vars, `framer-motion`, `text-xs` labels, `tabular-nums`).

**File:** `web/components/RecentValuations.tsx` (new)

```tsx
"use client";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { fetchRecentPredictions, PredictionRow } from "@/lib/supabase";

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);

const fmtDate = (iso: string) => {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
};

export function RecentValuations() {
  const [rows, setRows] = useState<PredictionRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRecentPredictions(5)
      .then(setRows)
      .finally(() => setLoading(false));
  }, []);

  if (!loading && rows.length === 0) return null;

  return (
    <div
      className="rounded-xl border mt-6"
      style={{ background: "var(--surface)", borderColor: "var(--border)" }}
    >
      <div className="px-5 py-3 border-b" style={{ borderColor: "var(--border)" }}>
        <p
          className="text-xs uppercase tracking-widest"
          style={{ color: "var(--text-subtle)" }}
        >
          Recent Valuations
        </p>
      </div>

      {loading ? (
        <div className="px-5 py-4 space-y-2">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="h-4 rounded animate-pulse"
              style={{ background: "var(--surface-raised)", width: `${60 + i * 10}%` }}
            />
          ))}
        </div>
      ) : (
        <AnimatePresence>
          <ul className="divide-y" style={{ borderColor: "var(--border)" }}>
            {rows.map((row, i) => (
              <motion.li
                key={row.id}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2, delay: i * 0.05 }}
                className="px-5 py-3 flex items-center justify-between gap-4"
              >
                <div className="min-w-0">
                  <p
                    className="text-sm font-medium truncate tabular-nums"
                    style={{ color: "var(--accent)" }}
                  >
                    {fmt(row.predicted_price)}
                  </p>
                  <p
                    className="text-xs mt-0.5 truncate"
                    style={{ color: "var(--text-muted)" }}
                  >
                    {row.sqft_living.toLocaleString()} sqft &middot; {row.beds}bd &middot; ZIP {row.zip_code}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <p
                    className="text-xs tabular-nums"
                    style={{ color: "var(--text-subtle)" }}
                  >
                    {fmtDate(row.created_at)}
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--text-subtle)" }}>
                    conf{" "}
                    <span
                      style={{
                        color:
                          row.confidence_score >= 70
                            ? "var(--accent)"
                            : row.confidence_score >= 40
                            ? "#f59e0b"
                            : "var(--red)",
                      }}
                    >
                      {row.confidence_score}
                    </span>
                    /100
                  </p>
                </div>
              </motion.li>
            ))}
          </ul>
        </AnimatePresence>
      )}
    </div>
  );
}
```

---

### C-3: Wire `<RecentValuations />` into `web/app/page.tsx`

Add the import and insert the component below the results section (after the closing `</div>` of the results column, before the closing outer `</div>`).

**File:** `web/app/page.tsx`

**Change 1 — add import** (after the existing imports block):

```typescript
import { RecentValuations } from "@/components/RecentValuations";
```

**Change 2 — add component** in the JSX return, after the closing `</div>` of the `grid` and before the outermost closing `</div>`:

The relevant section in the current file ends at line 145 (`</div>` closing the grid) and line 146 (`</div>` closing the outer `max-w-6xl` container). Insert `<RecentValuations />` between them:

```tsx
      </div>  {/* closes grid */}

      <RecentValuations />

    </div>  {/* closes max-w-6xl */}
```

Full tail of the updated JSX return (lines ~143–149):

```tsx
        </div>
      </div>

      <RecentValuations />

    </div>
  );
}
```

**Build check:**

```bash
cd /path/to/avm-zestimate/web
npm run build 2>&1 | tail -20
# expect: "Route (app) / ... compiled successfully"
```

**Dev smoke test:**

```bash
cd /path/to/avm-zestimate/web
# Create .env.local if it does not exist — leave vars empty for offline dev
touch .env.local
npm run dev
# Visit http://localhost:3000
# The Recent Valuations section should not appear when vars are empty (rows.length === 0)
# After wiring real Supabase vars it renders the last 5 rows
```

---

## Environment variable summary

| Context | Variable | Value source |
|---|---|---|
| HF Space (server) | `SUPABASE_URL` | HF Space secrets |
| HF Space (server) | `SUPABASE_KEY` | HF Space secrets — service-role key |
| Vercel (client) | `NEXT_PUBLIC_SUPABASE_URL` | Vercel project env vars (already set) |
| Vercel (client) | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Vercel project env vars (already set) |
| Local dev (API) | `SUPABASE_URL` | `api/.env` or shell export |
| Local dev (API) | `SUPABASE_KEY` | `api/.env` or shell export |
| Local dev (web) | `NEXT_PUBLIC_SUPABASE_URL` | `web/.env.local` |
| Local dev (web) | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `web/.env.local` |

---

## Full test suite command

```bash
cd /path/to/avm-zestimate
python -m pytest api/tests/test_predict_db.py api/tests/test_benchmark_cache.py api/tests/test_comps_cache.py -v
```

Expected output: all tests green, no real network calls, no real Supabase credentials required.

---

## Implementation order

- [ ] A-1: Add `supabase>=2.10,<3` to `api/requirements.txt`
- [ ] A-2: Create `api/db.py`
- [ ] A-3: Update `api/routers/predict.py` + create `api/tests/test_predict_db.py`
- [ ] A-4: Update `api/routers/benchmark.py` + create `api/tests/test_benchmark_cache.py`
- [ ] A-5: Add `SUPABASE_URL` + `SUPABASE_KEY` to HF Space secrets (manual)
- [ ] B-1: Update `api/routers/comps.py` + create `api/tests/test_comps_cache.py`
- [ ] C-1: Create `web/lib/supabase.ts`
- [ ] C-2: Create `web/components/RecentValuations.tsx`
- [ ] C-3: Update `web/app/page.tsx` to wire in `<RecentValuations />`
- [ ] Run full test suite — all green
- [ ] `npm run build` in `web/` — no TypeScript errors
- [ ] Deploy: push to `dev/implementation`; verify HF Space logs show no Supabase tracebacks on first `/predict` hit
