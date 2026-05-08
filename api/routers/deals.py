from fastapi import APIRouter, Query
from api.schemas import DealResponse
from api.db import db

router = APIRouter()


@router.get("/deals", response_model=list[DealResponse])
def get_deals(
    zip_code: str | None = Query(default=None),
    min_gap: float = Query(default=10.0),
    min_confidence: int = Query(default=70),
    limit: int = Query(default=20, le=50),
):
    if not db:
        return []

    q = (
        db.table("deals")
        .select("*")
        .gte("value_gap_pct", min_gap)
        .gte("confidence_score", min_confidence)
    )
    if zip_code:
        q = q.eq("zip_code", zip_code)

    rows = q.order("deal_score", desc=True).limit(limit).execute().data

    return [
        DealResponse(
            id=str(r["id"]),
            address=r.get("address"),
            zip_code=r.get("zip_code"),
            list_price=r.get("list_price"),
            predicted_price=r["predicted_price"],
            value_gap_pct=float(r["value_gap_pct"]),
            confidence_score=r["confidence_score"],
            beds=r.get("beds"),
            baths_full=r.get("baths_full"),
            sqft_living=r.get("sqft_living"),
            year_built=r.get("year_built"),
            photo_url=r.get("photo_url"),
            condition_note=r.get("condition_note"),
            shap_top_driver=r.get("shap_top_driver"),
            deal_score=r.get("deal_score"),
            created_at=str(r.get("created_at", "")),
        )
        for r in rows
    ]
