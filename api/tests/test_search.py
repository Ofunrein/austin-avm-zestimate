import os
import sys
import types
from unittest.mock import patch

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

# Stub avm modules (predict/comps/scan routers import them at module level)
_avm_mods = ["avm", "avm.features", "avm.intervals", "avm.shap_gen", "avm.comps"]
for _mod in _avm_mods:
    if _mod not in sys.modules:
        sys.modules[_mod] = types.ModuleType(_mod)
_avm_f = sys.modules["avm.features"]
for _fn in ("add_structural", "add_location", "add_market_features", "build_feature_matrix"):
    setattr(_avm_f, _fn, lambda *a, **k: None)
_avm_i = sys.modules["avm.intervals"]
setattr(_avm_i, "predict_intervals", lambda *a, **k: ([0], [0]))
setattr(_avm_i, "confidence_score", lambda *a, **k: [75])
_avm_s = sys.modules["avm.shap_gen"]
setattr(_avm_s, "make_explainer", lambda *a, **k: None)
setattr(_avm_s, "top_shap_features", lambda *a, **k: [])
_avm_c = sys.modules["avm.comps"]
setattr(_avm_c, "find_comps", lambda *a, **k: None)

_FAKE_PARAMS = {"beds_min": 3, "price_max": 400000, "zip_codes": ["78704"], "undervalued_only": False}
_FAKE_ROWS = [
    {
        "id": "uuid-1",
        "address": "123 Main St",
        "zip_code": "78704",
        "sqft_living": 1800.0,
        "beds": 3,
        "baths_full": 2.0,
        "year_built": 2005,
        "predicted_price": 380000,
        "list_price": None,
        "confidence_score": 80,
        "shap_json": [{"feature": "sqft_living", "shap_value": 30000}],
        "created_at": "2026-05-01T00:00:00",
    }
]


def _mock_db(rows):
    class FakeQuery:
        def select(self, *a): return self
        def gte(self, *a): return self
        def lte(self, *a): return self
        def eq(self, *a): return self
        def in_(self, *a): return self
        def order(self, *a, **kw): return self
        def limit(self, *a): return self
        def execute(self): return type("R", (), {"data": rows})()
    return type("DB", (), {"table": lambda self, n: FakeQuery()})()


def _app():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


def test_search_returns_results():
    with patch("api.routers.search.parse_search_query", return_value=_FAKE_PARAMS):
        with patch("api.routers.search.db", _mock_db(_FAKE_ROWS)):
            resp = _app().post("/search", json={"query": "3BR under $400k in 78704"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["results"][0]["predicted_price"] == 380000


def test_search_no_db_returns_empty():
    with patch("api.routers.search.parse_search_query", return_value=_FAKE_PARAMS):
        with patch("api.routers.search.db", None):
            resp = _app().post("/search", json={"query": "3BR in 78704"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_search_undervalued_only_filters():
    rows = [
        {**_FAKE_ROWS[0], "predicted_price": 400000, "list_price": 350000},  # gap +14%
        {**_FAKE_ROWS[0], "id": "uuid-2", "predicted_price": 300000, "list_price": 320000},  # gap -6%
    ]
    params = {**_FAKE_PARAMS, "undervalued_only": True}
    with patch("api.routers.search.parse_search_query", return_value=params):
        with patch("api.routers.search.db", _mock_db(rows)):
            resp = _app().post("/search", json={"query": "undervalued 3BR"})
    body = resp.json()
    assert all(r["value_gap_pct"] > 0 for r in body["results"])


def test_deals_endpoint_returns_list():
    fake_deal = {
        "id": "uuid-deal-1",
        "address": "456 Oak Ave",
        "zip_code": "78704",
        "list_price": 350000,
        "predicted_price": 410000,
        "value_gap_pct": 17.1,
        "confidence_score": 82,
        "beds": 3,
        "baths_full": 2.0,
        "sqft_living": 1800.0,
        "year_built": 2005,
        "photo_url": None,
        "condition_note": None,
        "shap_top_driver": "sqft_living",
        "deal_score": 14.0,
        "created_at": "2026-05-05T00:00:00",
    }
    with patch("api.routers.deals.db", _mock_db([fake_deal])):
        resp = _app().get("/deals")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["value_gap_pct"] == 17.1


def test_deals_no_db_returns_empty():
    with patch("api.routers.deals.db", None):
        resp = _app().get("/deals")
    assert resp.status_code == 200
    assert resp.json() == []
