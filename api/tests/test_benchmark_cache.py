"""Tests for benchmark 24h cache."""
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from api.schemas import BenchmarkResponse


def _fresh_row(age_hours=1.0):
    created = (datetime.now(timezone.utc) - timedelta(hours=age_hours)).isoformat()
    return {"model_version": "cached-1.0", "medape": 5.5, "mae": 18000, "rmse": 25000,
            "within_5pct": 0.62, "within_10pct": 0.85, "n_test": 400,
            "residuals_json": {"by_zip": []}, "created_at": created}


def _db_returning(rows):
    ex = MagicMock(); ex.data = rows
    chain = MagicMock()
    for m in ("select", "order", "limit"): setattr(chain, m, MagicMock(return_value=chain))
    chain.execute.return_value = ex
    insert_chain = MagicMock(); insert_chain.execute.return_value = MagicMock()
    chain.insert = MagicMock(return_value=insert_chain)
    db_mock = MagicMock(); db_mock.table.return_value = chain
    return db_mock


def _mock_fresh_response():
    return BenchmarkResponse(model_version="fresh-2.0", test_medape=4.1, test_mae=15000,
        test_rmse=22000, test_within_5pct=0.71, test_within_10pct=0.91, n_test=500,
        baseline_zip_median_medape=0, baseline_ppsf_medape=0, by_zip=[])


def test_returns_cached_when_fresh():
    with patch("api.routers.benchmark.db", _db_returning([_fresh_row(1.0)])):
        from api.main import app
        resp = TestClient(app).get("/benchmark")
    assert resp.status_code == 200
    assert resp.json()["model_version"] == "cached-1.0"


def test_recomputes_when_stale():
    with patch("api.routers.benchmark.db", _db_returning([_fresh_row(25.0)])), \
         patch("api.routers.benchmark._read_from_files", return_value=_mock_fresh_response()):
        from api.main import app
        resp = TestClient(app).get("/benchmark")
    assert resp.json()["model_version"] == "fresh-2.0"


def test_returns_200_without_db():
    with patch("api.routers.benchmark.db", None), \
         patch("api.routers.benchmark._read_from_files", return_value=_mock_fresh_response()):
        from api.main import app
        resp = TestClient(app).get("/benchmark")
    assert resp.status_code == 200
