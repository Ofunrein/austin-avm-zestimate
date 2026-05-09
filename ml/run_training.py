#!/usr/bin/env python3
"""
Full training pipeline:
  1. Load + clean data
  2. Feature engineering
  3. Temporal CV split
  4. Tune XGBoost + LightGBM
  5. Train final models
  6. Train quantile models
  7. Evaluate vs baselines
  8. Log to MLflow
  9. Save model artifacts
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / "src"))

from avm.clean import clean, data_sha256
from avm.evaluate import metrics, residual_summary
from avm.experiment import log_run
from avm.features import (
    add_structural, add_location, add_market_features,
    add_assessed_features, build_feature_matrix,
)
from avm.ingest import load_kaggle_austin
from avm.intervals import train_quantile_models, save_quantile_models
from avm.enrich_census import fetch_zip_income_scores
from avm.enrich_tcad import build_tcad_lookup
from avm.split import temporal_cv_folds, train_test_split_temporal
from avm.train import tune_xgboost, tune_lightgbm, train_final, ensemble_predict, save_models
from avm.baseline import predict_zip_median, predict_ppsf, medape as bmedape
from avm.shap_gen import make_explainer

MODELS_DIR = Path(__file__).parent.parent / "models"  # avm-zestimate/models/ (matches train.py)
N_OPTUNA_TRIALS = int(sys.argv[1]) if len(sys.argv) > 1 else 50


def main():
    print("=== Austin AVM Training Pipeline ===")

    # 1. Load + clean
    print("[1/9] Loading data...")
    raw = load_kaggle_austin()
    df = clean(raw)
    print(f"  Clean records: {len(df):,}")

    sha = data_sha256(df)
    print(f"  Data SHA256: {sha}")

    # Load enrichment data (fail-soft: training still works without them)
    print("[1b/9] Loading enrichment data...")
    try:
        income_lookup = fetch_zip_income_scores()
        print(f"  Census ACS: {len(income_lookup):,} ZIP income scores")
    except Exception as e:
        income_lookup = {}
        print(f"  Census ACS: skipped ({e})")

    tcad_path = Path(__file__).parent / "data/raw/tcad_parcels.csv"
    try:
        tcad_lookup = build_tcad_lookup(tcad_path)
        print(f"  TCAD: {len(tcad_lookup):,} parcel values")
    except Exception as e:
        tcad_lookup = {}
        print(f"  TCAD: skipped ({e})")

    # 2. Feature engineering
    print("[2/9] Feature engineering...")
    df = add_structural(df)
    df, zip_encoder = add_location(df, income_lookup=income_lookup)
    df = add_market_features(df)
    df = add_assessed_features(df, tcad_lookup=tcad_lookup)

    # Persist processed features for comps endpoint
    processed_dir = Path(__file__).parent / "data/processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(processed_dir / "train_features.parquet", index=False)
    print(f"  Saved train_features.parquet ({len(df):,} rows)")

    # 3. Split — use last 20% of date range as test (adapts to any dataset)
    print("[3/9] Temporal split...")
    if "sale_date" in df.columns and df["sale_date"].notna().any():
        max_date = df["sale_date"].max()
        min_date = df["sale_date"].min()
        span = max_date - min_date
        test_cutoff = min_date + span * 0.80
        test_start = test_cutoff.strftime("%Y-%m-%d")
    else:
        test_start = "2021-01-01"
    train_df, test_df = train_test_split_temporal(df, test_start=test_start)
    folds = temporal_cv_folds(train_df, n_folds=5)
    print(f"  Train: {len(train_df):,} | Test: {len(test_df):,} | CV folds: {len(folds)}")

    # 4. Tune
    print(f"[4/9] Tuning XGBoost ({N_OPTUNA_TRIALS} trials)...")
    xgb_params = tune_xgboost(folds, n_trials=N_OPTUNA_TRIALS)
    print(f"  XGB best params: {xgb_params}")

    print(f"[5/9] Tuning LightGBM ({N_OPTUNA_TRIALS} trials)...")
    lgb_params = tune_lightgbm(folds, n_trials=N_OPTUNA_TRIALS)
    print(f"  LGB best params: {lgb_params}")

    # 5. Train final
    print("[6/9] Training final models...")
    xgb_model, lgb_model = train_final(train_df, xgb_params, lgb_params)

    # 6. Quantile models
    print("[7/9] Training quantile models...")
    X_train = build_feature_matrix(train_df)
    q_low, q_high = train_quantile_models(train_df, X_train, xgb_params)
    save_quantile_models(q_low, q_high)

    # 7. Evaluate
    print("[8/9] Evaluating...")
    X_test = build_feature_matrix(test_df)
    y_test = test_df["sale_price"].values

    ensemble_preds = ensemble_predict(xgb_model, lgb_model, X_test)
    xgb_preds = np.expm1(xgb_model.predict(X_test))
    lgb_preds = np.expm1(lgb_model.predict(X_test))

    zip_med_preds = predict_zip_median(test_df)
    ppsf_preds = predict_ppsf(test_df)

    ens_metrics = metrics(y_test, ensemble_preds)
    results = {
        "test_medape_ensemble": float(ens_metrics["medape"]),
        "test_medape_xgb": float(metrics(y_test, xgb_preds)["medape"]),
        "test_medape_lgb": float(metrics(y_test, lgb_preds)["medape"]),
        "test_medape_zip_median": float(bmedape(y_test, zip_med_preds)),
        "test_medape_ppsf": float(bmedape(y_test, ppsf_preds)),
        # cast all ensemble metrics to float (metrics() returns int for "n")
        **{f"test_{k}": float(v) for k, v in ens_metrics.items()},
    }

    print("\n  === Results ===")
    for k, v in results.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.3f}")

    residuals = residual_summary(test_df, ensemble_preds)

    xgb_medape = results["test_medape_xgb"]
    lgb_medape = results["test_medape_lgb"]
    ens_medape = results["test_medape_ensemble"]
    best_single = min(xgb_medape, lgb_medape)
    xgb_weight = 0.5 if ens_medape < best_single - 0.5 else (1.0 if xgb_medape <= lgb_medape else 0.0)
    print(f"\n  Ensemble weight XGB={xgb_weight:.2f}, LGB={1-xgb_weight:.2f}")

    # 8. Save
    print("[9/9] Saving models + logging MLflow...")
    meta = {
        "version": "1.0.0",
        "data_sha256": sha,
        "xgb_params": xgb_params,
        "lgb_params": lgb_params,
        "xgb_weight": xgb_weight,
        "test_medape": ens_medape,
        "test_medape_zip_median": results.get("test_medape_zip_median"),
        "test_medape_ppsf": results.get("test_medape_ppsf"),
        "residuals": residuals,
        "feature_cols": build_feature_matrix(test_df).columns.tolist(),
    }
    save_models(xgb_model, lgb_model, meta)

    import joblib
    joblib.dump(zip_encoder, MODELS_DIR / "zip_encoder.joblib")
    print("  Saved zip_encoder.joblib")

    run_id = log_run(
        run_name="full-pipeline",
        params={**xgb_params, "xgb_weight": xgb_weight, "n_test": len(test_df)},
        metrics=results,
        artifacts_dir=MODELS_DIR,
        data_sha=sha,
    )
    print(f"\nMLflow run_id: {run_id}")
    print(f"Test MedAPE (ensemble): {ens_medape:.2f}%")

    (MODELS_DIR / "residuals.json").write_text(json.dumps(residuals, indent=2))
    print("Done.")


if __name__ == "__main__":
    main()
