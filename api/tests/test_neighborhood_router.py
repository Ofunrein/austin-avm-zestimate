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

_FAKE_NEIGHBORHOOD = {
    "zip_code": "78704",
    "school_rating": "C",
    "walk_score": 89,
    "transit_score": 52,
    "bike_score": 71,
    "median_income": 72400,
    "population_density": 4200.0,
    "crime_incidents_per_1k": 18.3,
    "summary": "Walk Score 89, school rating C (TEA), median income $72k",
}


def _app():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


def test_neighborhood_returns_data():
    with patch("api.routers.neighborhood.fetch_neighborhood", return_value=_FAKE_NEIGHBORHOOD):
        with patch("api.routers.neighborhood.db", None):
            resp = _app().get("/neighborhood/78704")
    assert resp.status_code == 200
    data = resp.json()
    assert data["zip_code"] == "78704"
    assert data["walk_score"] == 89
    assert "summary" in data


def test_neighborhood_uses_cache_when_available():
    from datetime import datetime, timezone
    fake_cache_row = {"data_json": _FAKE_NEIGHBORHOOD, "created_at": datetime.now(timezone.utc).isoformat()}
    mock_db = type("DB", (), {
        "table": lambda self, name: type("T", (), {
            "select": lambda self, *a: type("S", (), {
                "eq": lambda self, *a: type("E", (), {
                    "gte": lambda self, *a: type("G", (), {
                        "execute": lambda self: type("R", (), {"data": [fake_cache_row]})()
                    })()
                })()
            })()
        })()
    })()
    with patch("api.routers.neighborhood.db", mock_db):
        with patch("api.routers.neighborhood.fetch_neighborhood") as mock_fetch:
            resp = _app().get("/neighborhood/78704")
    mock_fetch.assert_not_called()
    assert resp.status_code == 200
