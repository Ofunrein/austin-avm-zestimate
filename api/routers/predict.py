from fastapi import APIRouter
import numpy as np
import pandas as pd
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "ml/src"))
from avm.features import add_structural, add_location, add_market_features, add_assessed_features, build_feature_matrix
from avm.intervals import predict_intervals, confidence_score
from avm.shap_gen import make_explainer, top_shap_features
from api.schemas import PropertyInput, PredictionResponse, ShapFeature
from api.model_loader import load_all_models
from api.db import db

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
    xgb_model, lgb_model, q_low, q_high, meta = get_models()
    df = _property_to_df(prop)
    df = add_structural(df)
    df, _ = add_location(df)
    df = add_market_features(df)
    df = add_assessed_features(df)
    df["is_covid_period"] = 0
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

    response = PredictionResponse(
        predicted_price=int(predicted),
        lower_bound=int(low_arr[0]),
        upper_bound=int(high_arr[0]),
        confidence_score=int(conf),
        shap_top5=[ShapFeature(**f) for f in shap_feats],
        model_version=meta.get("version", "1.0.0"),
    )

    if db is not None:
        try:
            db.table("predictions").insert({
                "address": None,
                "lat": prop.lat,
                "lng": prop.lng,
                "sqft_living": prop.sqft_living,
                "beds": prop.beds,
                "baths_full": prop.baths_full,
                "year_built": prop.year_built,
                "zip_code": prop.zip_code,
                "predicted_price": response.predicted_price,
                "lower_bound": response.lower_bound,
                "upper_bound": response.upper_bound,
                "confidence_score": response.confidence_score,
                "shap_json": [f.model_dump() for f in response.shap_top5],
            }).execute()
        except Exception:
            traceback.print_exc()

    return response
