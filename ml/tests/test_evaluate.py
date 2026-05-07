import numpy as np
import pandas as pd
import pytest
from avm.evaluate import metrics, metrics_by_zip, residual_summary


def test_metrics_perfect_prediction():
    y = np.array([400000.0, 500000.0, 300000.0])
    m = metrics(y, y)
    assert m["medape"] == pytest.approx(0.0)
    assert m["within_5pct"] == pytest.approx(1.0)
    assert m["within_10pct"] == pytest.approx(1.0)


def test_metrics_known_ape():
    y = np.array([100000.0])
    p = np.array([110000.0])  # 10% error
    m = metrics(y, p)
    assert m["medape"] == pytest.approx(10.0)


def test_metrics_by_zip_returns_all_zips():
    df = pd.DataFrame({
        "sale_price": [400000, 500000, 300000, 450000],
        "zip_code": ["78701", "78701", "78702", "78702"],
    })
    pred = np.array([410000, 490000, 310000, 440000])
    result = metrics_by_zip(df, pred)
    assert set(result["zip_code"]) == {"78701", "78702"}


def test_residual_summary_has_all_keys():
    df = pd.DataFrame({
        "sale_price": [300000, 450000, 600000, 800000, 200000],
        "zip_code": ["78701"] * 5,
        "year_built": [1980, 1995, 2005, 2015, 1960],
    })
    pred = np.array([310000, 440000, 590000, 820000, 210000])
    summary = residual_summary(df, pred)
    assert "overall" in summary
    assert "by_zip" in summary
    assert "by_price_tier" in summary
    assert "by_year_built" in summary
