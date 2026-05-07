import pandas as pd
import numpy as np
import pytest
from avm.comps import find_comps, haversine_miles


def _sold():
    return pd.DataFrame({
        "address": [f"{i} Main St" for i in range(20)],
        "sale_price": np.linspace(300000, 600000, 20),
        "sale_date": pd.date_range("2022-01-01", periods=20, freq="ME"),
        "sqft_living": np.linspace(1400, 2200, 20),
        "beds": [3] * 20,
        "bath_total": [2.0] * 20,
        "age": [20] * 20,
        "lat": np.linspace(30.25, 30.35, 20),
        "lng": np.linspace(-97.80, -97.70, 20),
        "zip_code": ["78701"] * 20,
    })


def test_haversine_zero_distance():
    d = haversine_miles(30.27, -97.74, np.array([30.27]), np.array([-97.74]))
    assert d[0] == pytest.approx(0.0, abs=0.01)


def test_find_comps_returns_n():
    subject = {"lat": 30.30, "lng": -97.75, "sqft_living": 1800, "beds": 3, "bath_total": 2.0, "age": 20}
    comps = find_comps(subject, _sold(), n=5)
    assert len(comps) <= 5


def test_find_comps_similarity_bounded():
    subject = {"lat": 30.30, "lng": -97.75, "sqft_living": 1800, "beds": 3, "bath_total": 2.0, "age": 20}
    comps = find_comps(subject, _sold(), n=5)
    if not comps.empty:
        assert all(comps["similarity_score"].between(0, 1))
