import pandas as pd
import pytest
from avm.clean import clean, normalise_kaggle, data_sha256


def _sample():
    return pd.DataFrame({
        "sale_price": [450000, 99, 11_000_000, 380000],
        "sqft_living": [1800, 1200, 1500, 0],
        "beds": [3, 2, 4, 3],
        "baths_full": [2, 1, 3, 2],
        "year_built": [2005, 2010, 2000, 1920],
        "zip_code": ["78701", "78702", "99999", "78703"],
        "lat": [30.27, 30.28, 30.29, 30.26],
        "lng": [-97.74, -97.73, -97.72, -97.75],
        "sale_date": ["2022-01-01", "2022-02-01", "2022-03-01", "2022-04-01"],
    })


def test_clean_removes_price_outliers():
    df = clean(_sample())
    assert all(df["sale_price"].between(50_000, 10_000_000))


def test_clean_removes_sqft_zero():
    df = clean(_sample())
    assert all(df["sqft_living"] >= 200)


def test_clean_filters_non_austin_zips():
    df = clean(_sample())
    assert all(df["zip_code"].str.match(r"^78[67]\d{2}$"))


def test_clean_adds_covid_flag():
    df = _sample()
    df.loc[0, "sale_date"] = "2020-06-15"
    result = clean(df)
    covid_rows = result[result["is_covid_period"] == 1]
    assert len(covid_rows) >= 1


def test_data_sha256_deterministic():
    df = _sample()
    assert data_sha256(df) == data_sha256(df)
    assert len(data_sha256(df)) == 16
