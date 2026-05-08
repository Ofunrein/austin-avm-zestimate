from datetime import datetime, timedelta, timezone
from fastapi import APIRouter
from api.schemas import NeighborhoodResponse
from api.services.neighborhood import fetch_neighborhood
from api.db import db

router = APIRouter()
_TTL_DAYS = 30


@router.get("/neighborhood/{zip_code}", response_model=NeighborhoodResponse)
def get_neighborhood(zip_code: str):
    if db:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=_TTL_DAYS)).isoformat()
        cached = (
            db.table("neighborhood_cache")
            .select("data_json,created_at")
            .eq("cache_key", zip_code)
            .gte("created_at", cutoff)
            .execute()
        )
        if cached.data:
            return NeighborhoodResponse(**cached.data[0]["data_json"])

    data = fetch_neighborhood(zip_code)

    if db:
        try:
            db.table("neighborhood_cache").upsert(
                {"cache_key": zip_code, "data_json": data}
            ).execute()
        except Exception:
            pass

    return NeighborhoodResponse(**data)
