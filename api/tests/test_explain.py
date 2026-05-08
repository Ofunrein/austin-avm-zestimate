import os
import sys
import types
from unittest.mock import patch, MagicMock

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

# Stub avm package so routers that import it at module level don't fail
_avm_mods = [
    "avm", "avm.features", "avm.intervals", "avm.shap_gen", "avm.comps",
]
for _mod in _avm_mods:
    if _mod not in sys.modules:
        sys.modules[_mod] = types.ModuleType(_mod)

_avm_f = sys.modules["avm.features"]
for _fn in ("add_structural", "add_location", "add_market_features", "build_feature_matrix"):
    setattr(_avm_f, _fn, lambda *a, **k: None)

_avm_i = sys.modules["avm.intervals"]
for _fn in ("predict_intervals", "confidence_score"):
    setattr(_avm_i, _fn, lambda *a, **k: None)

_avm_s = sys.modules["avm.shap_gen"]
for _fn in ("make_explainer", "top_shap_features"):
    setattr(_avm_s, _fn, lambda *a, **k: None)

sys.modules["avm.comps"].find_comps = lambda *a, **k: None


def _app():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


def _mock_explain(text: str = "This home is valued at $453k. Strong buy signal."):
    return patch("api.routers.explain.explain_prediction", return_value=text)


def test_explain_endpoint_returns_explanation():
    with _mock_explain():
        resp = _app().post("/explain", json={
            "predicted_price": 453235,
            "lower_bound": 398000,
            "upper_bound": 512000,
            "confidence_score": 82,
            "shap_top5": [
                {"feature": "sqft_living", "feature_value": 1850.0,
                 "shap_value": 45000.0, "direction": "increases"},
            ],
            "zip_code": "78704",
            "sqft_living": 1850.0,
            "beds": 3,
            "baths_full": 2.0,
            "year_built": 1978,
        })
    assert resp.status_code == 200
    assert resp.json()["explanation"] == "This home is valued at $453k. Strong buy signal."


def test_explain_endpoint_missing_required_field_returns_422():
    with _mock_explain():
        resp = _app().post("/explain", json={"predicted_price": 450000})
    assert resp.status_code == 422


def test_explain_endpoint_passes_neighborhood_context():
    captured = {}

    def fake_explain(**kwargs):
        captured.update(kwargs)
        return "Explanation."

    with patch("api.routers.explain.explain_prediction", side_effect=fake_explain):
        _app().post("/explain", json={
            "predicted_price": 450000,
            "lower_bound": 400000,
            "upper_bound": 500000,
            "confidence_score": 75,
            "shap_top5": [],
            "zip_code": "78704",
            "sqft_living": 1500.0,
            "beds": 3,
            "baths_full": 2.0,
            "year_built": 2000,
            "neighborhood_context": "Walk Score 89",
        })
    assert captured.get("neighborhood_context") == "Walk Score 89"
