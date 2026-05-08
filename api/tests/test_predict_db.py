"""Tests for Supabase logging in predict router."""
from contextlib import ExitStack
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

VALID_PAYLOAD = {
    "sqft_living": 1800, "beds": 3, "baths_full": 2, "baths_half": 0,
    "year_built": 2005, "zip_code": "78701", "lat": 30.27, "lng": -97.74,
    "lot_sqft": 5000, "garage_spaces": 1, "has_pool": 0, "assessed_value": 0,
}


def _mock_models():
    import numpy as np
    xgb = MagicMock(); xgb.predict.return_value = np.array([13.0])
    lgb = MagicMock(); lgb.predict.return_value = np.array([13.0])
    q_low = MagicMock(); q_low.predict.return_value = np.array([12.8])
    q_high = MagicMock(); q_high.predict.return_value = np.array([13.2])
    meta = {"version": "test", "xgb_weight": 0.5}
    return xgb, lgb, q_low, q_high, meta


def _patch_features():
    return [
        patch("avm.features.add_structural", side_effect=lambda df: df),
        patch("avm.features.add_location", side_effect=lambda df: (df, None)),
        patch("avm.features.add_market_features", side_effect=lambda df: df),
        patch("avm.features.build_feature_matrix", side_effect=lambda df: df),
        patch("api.routers.predict.make_explainer", return_value=MagicMock()),
        patch("api.routers.predict.top_shap_features", return_value=[
            {"feature": "sqft_living", "feature_value": 1800.0, "shap_value": 0.5, "direction": "increases"},
            {"feature": "beds", "feature_value": 3.0, "shap_value": 0.2, "direction": "increases"},
            {"feature": "year_built", "feature_value": 2005.0, "shap_value": 0.1, "direction": "increases"},
            {"feature": "lat", "feature_value": 30.27, "shap_value": -0.1, "direction": "decreases"},
            {"feature": "lng", "feature_value": -97.74, "shap_value": -0.05, "direction": "decreases"},
        ]),
    ]


def test_predict_returns_200_without_db():
    with ExitStack() as stack:
        stack.enter_context(patch("api.routers.predict.db", None))
        stack.enter_context(patch("api.routers.predict.get_models", return_value=_mock_models()))
        for p in _patch_features():
            stack.enter_context(p)
        from api.main import app
        client = TestClient(app)
        resp = client.post("/predict", json=VALID_PAYLOAD)
    assert resp.status_code == 200
    assert "predicted_price" in resp.json()


def test_predict_db_failure_does_not_propagate():
    mock_db = MagicMock()
    mock_db.table.side_effect = Exception("DB down")
    with ExitStack() as stack:
        stack.enter_context(patch("api.routers.predict.db", mock_db))
        stack.enter_context(patch("api.routers.predict.get_models", return_value=_mock_models()))
        for p in _patch_features():
            stack.enter_context(p)
        from api.main import app
        client = TestClient(app)
        resp = client.post("/predict", json=VALID_PAYLOAD)
    assert resp.status_code == 200


def test_predict_calls_insert_with_predictions_table():
    insert_chain = MagicMock(); insert_chain.execute.return_value = MagicMock()
    table_mock = MagicMock(); table_mock.insert.return_value = insert_chain
    mock_db = MagicMock(); mock_db.table.return_value = table_mock
    with ExitStack() as stack:
        stack.enter_context(patch("api.routers.predict.db", mock_db))
        stack.enter_context(patch("api.routers.predict.get_models", return_value=_mock_models()))
        for p in _patch_features():
            stack.enter_context(p)
        from api.main import app
        client = TestClient(app)
        client.post("/predict", json=VALID_PAYLOAD)
    mock_db.table.assert_called_with("predictions")
