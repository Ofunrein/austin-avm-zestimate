from fastapi import APIRouter, Query
from api.schemas import DealResponse
from api.db import db

router = APIRouter()


def _rows_from_predictions(limit: int, min_gap: float) -> list[dict]:
    rows = (
        db.table("predictions")
        .select(
            "id,address,zip_code,list_price,predicted_price,confidence_score,"
            "beds,baths_full,sqft_living,year_built,photo_url,shap_json,created_at"
        )
        .not_.is_("predicted_price", "null")
        .not_.is_("list_price", "null")
        .gt("list_price", 0)
        .limit(limit * 4)  # fetch extra to filter after gap calc
        .execute()
        .data
    )
    out = []
    for r in rows:
        lp = r.get("list_price") or 0
        pp = r.get("predicted_price") or 0
        if not lp or not pp:
            continue
        gap = (pp - lp) / lp * 100
        if gap < min_gap:
            continue
        conf = r.get("confidence_score") or 50
        shap = r.get("shap_json")
        shap_driver = None
        if shap and isinstance(shap, list) and len(shap) > 0:
            shap_driver = shap[0].get("feature") if isinstance(shap[0], dict) else None
        out.append({
            "id": str(r["id"]),
            "address": r.get("address"),
            "zip_code": r.get("zip_code"),
            "list_price": lp,
            "predicted_price": pp,
            "value_gap_pct": round(gap, 2),
            "confidence_score": conf,
            "beds": r.get("beds"),
            "baths_full": r.get("baths_full"),
            "sqft_living": r.get("sqft_living"),
            "year_built": r.get("year_built"),
            "photo_url": r.get("photo_url"),
            "shap_top_driver": shap_driver,
            "deal_score": round(gap * conf / 100, 2),
            "created_at": r.get("created_at"),
        })
    out.sort(key=lambda x: x["deal_score"], reverse=True)
    return out[:limit]


@router.get("/opportunities", response_model=list[DealResponse])
@router.get("/deals", response_model=list[DealResponse], include_in_schema=False)
def get_opportunities(
    limit: int = Query(default=20, le=100),
    min_gap: float = Query(default=0.0),
):
    if not db:
        return []
    # Try predictions table first (seeded Kaggle data with photo_url)
    try:
        rows = _rows_from_predictions(limit, min_gap)
        if rows:
            return [DealResponse(**r) for r in rows]
    except Exception:
        pass
    # Fallback to legacy deals table
    q = (
        db.table("deals")
        .select("*")
        .gte("value_gap_pct", min_gap)
        .order("deal_score", desc=True)
        .limit(limit)
    )
    rows = q.execute().data
    return [DealResponse(**r) for r in rows]
