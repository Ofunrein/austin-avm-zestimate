"""Train XGBoost and LightGBM with temporal CV + Optuna tuning."""
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import optuna
import pandas as pd
import xgboost as xgb
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error

from avm.baseline import medape, within_pct
from avm.features import build_feature_matrix, FEATURE_COLS
from avm.split import temporal_cv_folds

LOG = logging.getLogger(__name__)
optuna.logging.set_verbosity(optuna.logging.WARNING)

MODELS_DIR = Path(__file__).parents[3] / "models"


def _cv_medape(model_cls, params: dict, folds, log_target: bool = True) -> float:
    scores = []
    for fold in folds:
        X_tr = build_feature_matrix(fold.train)
        X_val = build_feature_matrix(fold.val)
        y_tr = np.log1p(fold.train["sale_price"]) if log_target else fold.train["sale_price"]
        y_val = fold.val["sale_price"].values

        m = model_cls(**params)
        m.fit(X_tr, y_tr)
        pred = m.predict(X_val)
        if log_target:
            pred = np.expm1(pred)
        scores.append(medape(y_val, pred))
    return float(np.mean(scores))


def tune_xgboost(folds, n_trials: int = 50) -> dict:
    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 300, 1500),
            "max_depth": trial.suggest_int("max_depth", 3, 8),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-4, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-4, 10.0, log=True),
            "random_state": 42,
            "n_jobs": -1,
        }
        return _cv_medape(xgb.XGBRegressor, params, folds)

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
    return study.best_params


def tune_lightgbm(folds, n_trials: int = 50) -> dict:
    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 300, 1500),
            "max_depth": trial.suggest_int("max_depth", 3, 8),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 50),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-4, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-4, 10.0, log=True),
            "random_state": 42,
            "n_jobs": -1,
            "verbose": -1,
        }
        return _cv_medape(lgb.LGBMRegressor, params, folds)

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
    return study.best_params


def train_final(
    train_df: pd.DataFrame,
    xgb_params: dict,
    lgb_params: dict,
) -> tuple[Any, Any]:
    """Train final XGB + LGB on full train set."""
    X = build_feature_matrix(train_df)
    y = np.log1p(train_df["sale_price"])

    xgb_model = xgb.XGBRegressor(**{**xgb_params, "random_state": 42, "n_jobs": -1})
    xgb_model.fit(X, y)

    lgb_model = lgb.LGBMRegressor(**{**lgb_params, "random_state": 42, "n_jobs": -1, "verbose": -1})
    lgb_model.fit(X, y)

    return xgb_model, lgb_model


def ensemble_predict(
    xgb_model, lgb_model, X: pd.DataFrame, xgb_weight: float = 0.5
) -> np.ndarray:
    xgb_pred = np.expm1(xgb_model.predict(X))
    lgb_pred = np.expm1(lgb_model.predict(X))
    return xgb_weight * xgb_pred + (1 - xgb_weight) * lgb_pred


def save_models(xgb_model, lgb_model, meta: dict) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(xgb_model, MODELS_DIR / "xgb_model.joblib")
    joblib.dump(lgb_model, MODELS_DIR / "lgb_model.joblib")
    import json
    (MODELS_DIR / "meta.json").write_text(json.dumps(meta, indent=2))
    LOG.info("Models saved to %s", MODELS_DIR)


def load_models():
    xgb_model = joblib.load(MODELS_DIR / "xgb_model.joblib")
    lgb_model = joblib.load(MODELS_DIR / "lgb_model.joblib")
    return xgb_model, lgb_model
