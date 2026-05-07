"""SHAP explanations for individual predictions."""
from __future__ import annotations
import numpy as np
import pandas as pd
import shap
from avm.features import build_feature_matrix, FEATURE_COLS


def make_explainer(xgb_model) -> shap.TreeExplainer:
    return shap.TreeExplainer(xgb_model)


def top_shap_features(
    explainer: shap.TreeExplainer,
    row: pd.DataFrame,
    n: int = 5,
) -> list[dict]:
    """
    Return top N SHAP drivers for a single prediction row.
    Each dict: {feature, feature_value, shap_value, direction}
    """
    X = build_feature_matrix(row)
    shap_values = explainer.shap_values(X)

    if shap_values.ndim == 2:
        sv = shap_values[0]
    else:
        sv = shap_values

    cols = [c for c in FEATURE_COLS if c in row.columns]
    pairs = sorted(zip(cols, sv, X.iloc[0].values), key=lambda x: abs(x[1]), reverse=True)[:n]

    return [
        {
            "feature": feat,
            "feature_value": float(val),
            "shap_value": float(sv_),
            "direction": "increases" if sv_ > 0 else "decreases",
        }
        for feat, sv_, val in pairs
    ]
