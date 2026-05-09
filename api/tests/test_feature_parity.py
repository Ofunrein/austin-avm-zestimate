"""
Preprocessing parity contract: proves inference produces exactly the same
feature columns (name + order) that training recorded in meta["feature_cols"].
"""
import sys
from pathlib import Path
import json
import pandas as pd

_ml_src = Path(__file__).parents[2] / "ml/src"
if _ml_src.exists() and str(_ml_src) not in sys.path:
    sys.path.insert(0, str(_ml_src))

from avm.features import (
    add_structural, add_location, add_market_features,
    add_assessed_features, build_feature_matrix, FEATURE_COLS,
)

_SAMPLE = {
    "sqft_living": 1800.0, "beds": 3, "baths_full": 2.0, "baths_half": 0.0,
    "year_built": 2005, "zip_code": "78744", "lat": 30.20, "lng": -97.72,
    "lot_sqft": 6000.0, "garage_spaces": 2, "has_pool": 0,
    "stories": 1, "assessed_value": 0.0, "is_covid_period": 0,
}


def _build_inference_X(encoder=None) -> pd.DataFrame:
    df = pd.DataFrame([_SAMPLE])
    df = add_structural(df)
    df, _ = add_location(df, encoder=encoder)
    df = add_market_features(df)
    df = add_assessed_features(df)
    return build_feature_matrix(df)


def test_inference_columns_match_feature_cols():
    """Inference matrix columns must exactly match FEATURE_COLS (same set)."""
    X = _build_inference_X()
    inferred = set(X.columns)
    expected = set(FEATURE_COLS)
    missing = expected - inferred
    extra = inferred - expected
    assert not missing, f"Missing from inference: {missing}"
    assert not extra, f"Extra in inference (not in FEATURE_COLS): {extra}"


def test_inference_column_count():
    X = _build_inference_X()
    assert len(X.columns) == len(FEATURE_COLS), (
        f"Expected {len(FEATURE_COLS)} features, got {len(X.columns)}"
    )


def test_assessed_features_present():
    X = _build_inference_X()
    assert "price_per_sqft_assessed" in X.columns
    assert "assessed_ratio" in X.columns


def test_assessed_ratio_no_keyerror():
    """assessed_ratio must not raise KeyError when sale_price absent."""
    X = _build_inference_X()
    assert X["assessed_ratio"].iloc[0] == 0.0  # sale_price absent → 0.0


def test_zip_encoded_present():
    X = _build_inference_X()
    assert "zip_encoded" in X.columns


def test_covid_period_present():
    X = _build_inference_X()
    assert "is_covid_period" in X.columns
    assert X["is_covid_period"].iloc[0] == 0


def test_inference_matches_meta_feature_cols_if_available():
    """When meta.json exists, inferred columns must exactly match meta['feature_cols']."""
    meta_path = Path(__file__).parents[2] / "ml/models/meta.json"
    if not meta_path.exists():
        import pytest
        pytest.skip("meta.json not found — run training first")
    meta = json.loads(meta_path.read_text())
    recorded = meta.get("feature_cols", [])
    if not recorded:
        import pytest
        pytest.skip("meta.json has no feature_cols key")

    X = _build_inference_X()
    actual = list(X.columns)
    assert actual == recorded, (
        f"Column mismatch.\n"
        f"In meta but not inference: {set(recorded) - set(actual)}\n"
        f"In inference but not meta: {set(actual) - set(recorded)}\n"
        f"Order diff: meta={recorded}, inference={actual}"
    )


def test_no_nan_in_inference_output():
    X = _build_inference_X()
    nan_cols = X.columns[X.isna().any()].tolist()
    assert not nan_cols, f"NaN values in inference features: {nan_cols}"
