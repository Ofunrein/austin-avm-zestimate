from fastapi import APIRouter, Query
import pandas as pd
import traceback
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "ml/src"))
from avm.comps import find_comps
from api.schemas import CompProperty
from api.db import db

router = APIRouter()
_sold_df = None
_CACHE_TTL_DAYS = 7


def get_sold_df() -> pd.DataFrame:
    global _sold_df
    if _sold_df is None:
        p = Path(__file__).parents[2] / "ml/data/processed/train_features.parquet"
        _sold_df = pd.read_parquet(p) if p.exists() else pd.DataFrame()
    return _sold_df


def _make_cache_key(lat: float, lng: float, sqft: float) -> str:
    return f"{lat:.3f}_{lng:.3f}_{sqft:.0f}"


def _serialize_comps(records: list[dict]) -> list[dict]:
    return [{k: (v.item() if hasattr(v, "item") else v) for k, v in r.items()} for r in records]


@router.get("/comps", response_model=list[CompProperty])
def get_comps(
    lat: float = Query(...), lng: float = Query(...), sqft: float = Query(...),
    beds: int = Query(default=3), bath_total: float = Query(default=2.0),
    year_built: int = Query(default=2000), n: int = Query(default=5, le=10),
):
    cache_key = _make_cache_key(lat, lng, sqft)

    if db is not None:
        try:
            result = db.table("comps_cache").select("*").eq("cache_key", cache_key).execute()
            rows = result.data
            if rows:
                row = rows[0]
                created_at = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                if datetime.now(timezone.utc) - created_at < timedelta(days=_CACHE_TTL_DAYS):
                    return [CompProperty(**c) for c in row["comps_json"]]
        except Exception:
            traceback.print_exc()

    sold = get_sold_df()
    if sold.empty:
        return []

    subject = {"lat": lat, "lng": lng, "sqft_living": sqft, "beds": beds,
               "bath_total": bath_total, "age": 2024 - year_built}
    result_df = find_comps(subject, sold, n=n)
    if result_df.empty:
        return []

    records = result_df.to_dict(orient="records")
    comps_out = [CompProperty(
        address=r.get("address"), sale_price=r["sale_price"],
        sale_date=str(r["sale_date"]) if r.get("sale_date") else None,
        sqft_living=r["sqft_living"], beds=r.get("beds"), bath_total=r.get("bath_total"),
        distance_miles=r.get("distance_miles"), similarity_score=r["similarity_score"],
    ) for r in records]

    if db is not None:
        try:
            db.table("comps_cache").upsert({
                "cache_key": cache_key,
                "comps_json": _serialize_comps([c.model_dump() for c in comps_out]),
            }).execute()
        except Exception:
            traceback.print_exc()

    return comps_out
