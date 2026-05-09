from fastapi import APIRouter
import numpy as np
import pandas as pd
from pathlib import Path

from avm.features import add_structural, add_location, add_market_features, add_assessed_features, build_feature_matrix
from avm.intervals import predict_intervals, confidence_score
from avm.shap_gen import make_explainer, top_shap_features
from api.schemas import PropertyInput, PredictionResponse, ShapFeature
from api.model_loader import load_all_models

router = APIRouter()
_models = None


def get_models():
    global _models
    if _models is None:
        _models = load_all_models()
    return _models


def _property_to_df(p: PropertyInput) -> pd.DataFrame:
    return pd.DataFrame([p.model_dump()])


@router.post("/predict", response_model=PredictionResponse)
def predict(prop: PropertyInput):
    xgb_model, lgb_model, q_low, q_high, meta, zip_encoder = get_models()
    df = _property_to_df(prop)
    df["is_covid_period"] = 0
    df = add_structural(df)
    df, _ = add_location(df, encoder=zip_encoder)
    df = add_market_features(df)
    df = add_assessed_features(df)
    X = build_feature_matrix(df)

    xgb_pred = float(np.expm1(xgb_model.predict(X)[0]))
    lgb_pred = float(np.expm1(lgb_model.predict(X)[0]))
    w = meta.get("xgb_weight", 0.5)
    predicted = w * xgb_pred + (1 - w) * lgb_pred

    low_arr, high_arr = predict_intervals(q_low, q_high, X)
    conf = confidence_score(
        np.array([predicted]), np.array([low_arr[0]]), np.array([high_arr[0]])
    )[0]

    explainer = make_explainer(xgb_model)
    shap_feats = top_shap_features(explainer, df, n=5)

    return PredictionResponse(
        predicted_price=int(predicted),
        lower_bound=int(low_arr[0]),
        upper_bound=int(high_arr[0]),
        confidence_score=int(conf),
        shap_top5=[ShapFeature(**f) for f in shap_feats],
        model_version=meta.get("version", "1.0.0"),
    )
