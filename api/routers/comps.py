from fastapi import APIRouter, Query
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "ml/src"))
from avm.comps import find_comps
from api.schemas import CompProperty

router = APIRouter()
_sold_df = None


def get_sold_df() -> pd.DataFrame:
    global _sold_df
    if _sold_df is None:
        p = Path(__file__).parents[3] / "ml/data/processed/train_features.parquet"
        if p.exists():
            _sold_df = pd.read_parquet(p)
        else:
            _sold_df = pd.DataFrame()
    return _sold_df


@router.get("/comps", response_model=list[CompProperty])
def get_comps(
    lat: float = Query(...),
    lng: float = Query(...),
    sqft: float = Query(...),
    beds: int = Query(default=3),
    bath_total: float = Query(default=2.0),
    year_built: int = Query(default=2000),
    n: int = Query(default=5, le=10),
):
    sold = get_sold_df()
    if sold.empty:
        return []
    subject = {"lat": lat, "lng": lng, "sqft_living": sqft,
               "beds": beds, "bath_total": bath_total, "age": 2024 - year_built}
    result = find_comps(subject, sold, n=n)
    if result.empty:
        return []
    records = result.to_dict(orient="records")
    return [CompProperty(
        address=r.get("address"),
        sale_price=r["sale_price"],
        sale_date=str(r["sale_date"]) if r.get("sale_date") else None,
        sqft_living=r["sqft_living"],
        beds=r.get("beds"),
        bath_total=r.get("bath_total"),
        distance_miles=r.get("distance_miles"),
        similarity_score=r["similarity_score"],
    ) for r in records]
