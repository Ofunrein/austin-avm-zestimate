"""Load model artifacts from HuggingFace Hub or local path."""
import json
import os
from pathlib import Path
import joblib

HF_REPO_ID = os.getenv("HF_REPO_ID", "")
LOCAL_MODELS = Path(__file__).parent.parent / "ml/models"


def _load_local():
    xgb = joblib.load(LOCAL_MODELS / "xgb_model.joblib")
    lgb = joblib.load(LOCAL_MODELS / "lgb_model.joblib")
    q_low = joblib.load(LOCAL_MODELS / "q_low.joblib")
    q_high = joblib.load(LOCAL_MODELS / "q_high.joblib")
    meta = json.loads((LOCAL_MODELS / "meta.json").read_text())
    return xgb, lgb, q_low, q_high, meta


def _load_from_hf():
    from huggingface_hub import hf_hub_download
    import tempfile, shutil
    tmp = Path(tempfile.mkdtemp())
    files = ["xgb_model.joblib", "lgb_model.joblib", "q_low.joblib", "q_high.joblib", "meta.json"]
    for f in files:
        path = hf_hub_download(repo_id=HF_REPO_ID, filename=f)
        shutil.copy(path, tmp / f)
    xgb = joblib.load(tmp / "xgb_model.joblib")
    lgb = joblib.load(tmp / "lgb_model.joblib")
    q_low = joblib.load(tmp / "q_low.joblib")
    q_high = joblib.load(tmp / "q_high.joblib")
    meta = json.loads((tmp / "meta.json").read_text())
    return xgb, lgb, q_low, q_high, meta


def load_all_models():
    if HF_REPO_ID:
        return _load_from_hf()
    return _load_local()
