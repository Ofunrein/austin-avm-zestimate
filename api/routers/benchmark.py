from fastapi import APIRouter
import json
import os
import tempfile
from pathlib import Path
from api.schemas import BenchmarkResponse

router = APIRouter()

_meta_cache: dict | None = None
_residuals_cache: dict | None = None


def _load_json_artifact(filename: str) -> dict | None:
    """Load JSON from local models dir or HF Hub."""
    local = Path(__file__).parents[2] / "ml/models" / filename
    if local.exists():
        return json.loads(local.read_text())
    hf_repo = os.getenv("HF_REPO_ID", "")
    if hf_repo:
        try:
            from huggingface_hub import hf_hub_download
            path = hf_hub_download(repo_id=hf_repo, filename=filename)
            return json.loads(Path(path).read_text())
        except Exception:
            pass
    return None


@router.get("/benchmark", response_model=BenchmarkResponse)
def get_benchmark():
    global _meta_cache, _residuals_cache
    if _meta_cache is None:
        _meta_cache = _load_json_artifact("meta.json")
    if _residuals_cache is None:
        _residuals_cache = _load_json_artifact("residuals.json")

    if not _meta_cache:
        return BenchmarkResponse(model_version="not-trained")

    meta = _meta_cache
    residuals = _residuals_cache or {}
    overall = residuals.get("overall", {})

    return BenchmarkResponse(
        model_version=meta.get("version", "1.0.0"),
        test_medape=meta.get("test_medape") or None,
        test_mae=overall.get("mae") or None,
        test_rmse=overall.get("rmse") or None,
        test_within_5pct=overall.get("within_5pct") or None,
        test_within_10pct=overall.get("within_10pct") or None,
        n_test=overall.get("n") or None,
        baseline_zip_median_medape=meta.get("test_medape_zip_median") or None,
        baseline_ppsf_medape=meta.get("test_medape_ppsf") or None,
        by_zip=residuals.get("by_zip", []),
    )
