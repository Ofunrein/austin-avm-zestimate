from fastapi import APIRouter
import numpy as np
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "ml/src"))
from avm.features import add_structural, add_location, add_market_features, build_feature_matrix
from avm.shap_gen import make_explainer, top_shap_features
from api.model_loader import load_all_models
from api.schemas import ScanRequest, ScanItem

router = APIRouter()


@router.post("/scan", response_model=list[ScanItem])
def scan(req: ScanRequest):
    xgb_model, lgb_model, q_low, q_high, meta = load_all_models()
    w = meta.get("xgb_weight", 0.5)
    explainer = make_explainer(xgb_model)
    results = []

    for i, prop in enumerate(req.properties):
        df = pd.DataFrame([prop.model_dump()])
        df = add_structural(df)
        df, _ = add_location(df)
        df = add_market_features(df)
        X = build_feature_matrix(df)

        xgb_pred = float(np.expm1(xgb_model.predict(X)[0]))
        lgb_pred = float(np.expm1(lgb_model.predict(X)[0]))
        predicted = w * xgb_pred + (1 - w) * lgb_pred
        list_price = prop.list_price
        gap_pct = (predicted - list_price) / list_price * 100

        shap_feats = top_shap_features(explainer, df, n=1)
        top_driver = shap_feats[0]["feature"] if shap_feats else None

        results.append(ScanItem(
            index=i,
            predicted_price=int(predicted),
            list_price=list_price,
            value_gap_pct=round(gap_pct, 2),
            is_undervalued=gap_pct > 8.0,
            shap_top_driver=top_driver,
        ))

    return sorted(results, key=lambda x: x.value_gap_pct, reverse=True)
