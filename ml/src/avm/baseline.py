"""Naive baselines to beat: tax appraisal, ZIP median, price-per-sqft."""
import numpy as np
import pandas as pd


def predict_tax_appraisal(df: pd.DataFrame) -> np.ndarray:
    """Use assessed_value as prediction (tax appraisal baseline)."""
    if "assessed_value" in df.columns:
        return df["assessed_value"].fillna(df["sale_price"].median()).values
    return predict_zip_median(df)


def predict_zip_median(df: pd.DataFrame) -> np.ndarray:
    """Use rolling ZIP 90-day median as prediction."""
    return df["median_zip_price_90d"].fillna(df["sale_price"].median()).values


def predict_ppsf(df: pd.DataFrame, zip_ppsf: dict | None = None) -> np.ndarray:
    """Price per sqft × sqft. Uses ZIP-level PPSF from training data."""
    ppsf = df["median_zip_ppsf_90d"].fillna(250.0)
    return (ppsf * df["sqft_living"]).values


def medape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Median Absolute Percentage Error (%)."""
    ape = np.abs(y_true - y_pred) / np.abs(y_true) * 100
    return float(np.median(ape))


def within_pct(y_true: np.ndarray, y_pred: np.ndarray, pct: float) -> float:
    """Fraction of predictions within pct% of true value."""
    ape = np.abs(y_true - y_pred) / np.abs(y_true) * 100
    return float(np.mean(ape <= pct))
