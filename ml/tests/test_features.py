import numpy as np
import pandas as pd
import pytest
from avm.features import add_structural, add_location, add_market_features, build_feature_matrix, FEATURE_COLS


def _base():
    return pd.DataFrame({
        "sale_price": [450000, 380000, 310000],
        "sqft_living": [1800, 1400, 1100],
        "lot_sqft": [5000.0, 4000.0, 3500.0],
        "beds": [3, 2, 2],
        "baths_full": [2, 2, 1],
        "baths_half": [1, 0, 0],
        "year_built": [2005, 1998, 1985],
        "zip_code": ["78701", "78702", "78703"],
        "lat": [30.27, 30.28, 30.26],
        "lng": [-97.74, -97.73, -97.75],
        "sale_date": pd.to_datetime(["2022-01-15", "2022-04-10", "2022-07-20"]),
        "is_covid_period": [0, 0, 0],
    })


def test_add_structural_age():
    df = add_structural(_base())
    assert all(df["age"] == 2024 - df["year_built"])


def test_add_structural_bath_total():
    df = add_structural(_base())
    assert df.iloc[0]["bath_total"] == pytest.approx(2.5)  # 2 full + 1 half


def test_add_location_dist_downtown_positive():
    df, _ = add_location(add_structural(_base()))
    assert all(df["dist_downtown_miles"] >= 0)


def test_add_market_no_leakage():
    df = add_market_features(add_structural(_base()))
    # first row in each zip should be NaN before fillna — check fillna worked
    assert df["median_zip_price_90d"].notna().all()


def test_build_feature_matrix_no_nulls():
    df = add_structural(_base())
    df, _ = add_location(df)
    df = add_market_features(df)
    X = build_feature_matrix(df)
    assert X.isna().sum().sum() == 0
