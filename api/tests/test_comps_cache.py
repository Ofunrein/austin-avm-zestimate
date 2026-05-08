"""Tests for comps 7-day cache."""
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

_COMPS = [{"address": "123 Main St", "sale_price": 420000.0, "sale_date": "2024-01-15",
           "sqft_living": 1750.0, "beds": 3.0, "bath_total": 2.0,
           "distance_miles": 0.3, "similarity_score": 0.91}]


def _db_hit(age_days=1.0):
    created = (datetime.now(timezone.utc) - timedelta(days=age_days)).isoformat()
    row = {"cache_key": "30.270_-97.740_1800", "comps_json": _COMPS, "created_at": created}
    ex = MagicMock(); ex.data = [row]
    chain = MagicMock()
    for m in ("select", "eq"): setattr(chain, m, MagicMock(return_value=chain))
    chain.execute.return_value = ex
    db_mock = MagicMock(); db_mock.table.return_value = chain
    return db_mock


def _db_miss():
    ex = MagicMock(); ex.data = []
    chain = MagicMock()
    for m in ("select", "eq"): setattr(chain, m, MagicMock(return_value=chain))
    chain.execute.return_value = ex
    upsert_chain = MagicMock(); upsert_chain.execute.return_value = MagicMock()
    chain.upsert = MagicMock(return_value=upsert_chain)
    db_mock = MagicMock(); db_mock.table.return_value = chain
    return db_mock


def test_cache_key_format():
    from api.routers.comps import _make_cache_key
    assert _make_cache_key(30.2711, -97.7437, 1823.6) == "30.271_-97.744_1824"


def test_returns_cache_hit():
    with patch("api.routers.comps.db", _db_hit()):
        from api.main import app
        resp = TestClient(app).get("/comps?lat=30.27&lng=-97.74&sqft=1800")
    assert resp.status_code == 200
    assert resp.json()[0]["address"] == "123 Main St"


def test_miss_returns_empty_when_no_sold_data():
    with patch("api.routers.comps.db", _db_miss()), \
         patch("api.routers.comps.get_sold_df", return_value=__import__("pandas").DataFrame()):
        from api.main import app
        resp = TestClient(app).get("/comps?lat=30.27&lng=-97.74&sqft=1800")
    assert resp.status_code == 200
    assert resp.json() == []


def test_returns_200_without_db():
    with patch("api.routers.comps.db", None), \
         patch("api.routers.comps.get_sold_df", return_value=__import__("pandas").DataFrame()):
        from api.main import app
        resp = TestClient(app).get("/comps?lat=30.27&lng=-97.74&sqft=1800")
    assert resp.status_code == 200
