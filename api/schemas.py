"""Pydantic v2 schemas for all API endpoints."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


class PropertyInput(BaseModel):
    sqft_living: float = Field(..., gt=0, le=20000)
    beds: int = Field(..., ge=0, le=20)
    baths_full: float = Field(..., ge=0, le=20)
    baths_half: float = Field(default=0, ge=0, le=10)
    year_built: int = Field(..., ge=1850, le=2025)
    zip_code: str = Field(..., pattern=r"^\d{5}$")
    lat: float = Field(..., ge=29.0, le=31.5)
    lng: float = Field(..., ge=-99.0, le=-96.5)
    lot_sqft: float = Field(default=0, ge=0)
    garage_spaces: int = Field(default=0, ge=0, le=10)
    has_pool: int = Field(default=0, ge=0, le=1)
    stories: float = Field(default=1, ge=0, le=10)
    assessed_value: float = Field(default=0, ge=0)


class ShapFeature(BaseModel):
    feature: str
    feature_value: float
    shap_value: float
    direction: Literal["increases", "decreases"]


class PredictionResponse(BaseModel):
    predicted_price: int
    lower_bound: int
    upper_bound: int
    confidence_score: int
    shap_top5: list[ShapFeature]
    model_version: str


class CompProperty(BaseModel):
    address: str | None = None
    sale_price: float
    sale_date: str | None = None
    sqft_living: float
    beds: float | None = None
    bath_total: float | None = None
    distance_miles: float | None = None
    similarity_score: float


class ScanInputItem(BaseModel):
    sqft_living: float = Field(..., gt=0, le=20000)
    beds: int = Field(..., ge=0, le=20)
    baths_full: float = Field(..., ge=0, le=20)
    baths_half: float = Field(default=0, ge=0, le=10)
    year_built: int = Field(..., ge=1850, le=2025)
    zip_code: str = Field(..., pattern=r"^\d{5}$")
    lat: float = Field(..., ge=29.0, le=31.5)
    lng: float = Field(..., ge=-99.0, le=-96.5)
    lot_sqft: float = Field(default=0, ge=0)
    garage_spaces: int = Field(default=0, ge=0, le=10)
    has_pool: int = Field(default=0, ge=0, le=1)
    stories: float = Field(default=1, ge=0, le=10)
    assessed_value: float = Field(default=0, ge=0)
    list_price: float = Field(..., gt=0)


class ScanRequest(BaseModel):
    properties: list[ScanInputItem]


class ScanItem(BaseModel):
    index: int
    predicted_price: int
    list_price: float
    value_gap_pct: float
    is_undervalued: bool
    shap_top_driver: str | None = None


class BenchmarkResponse(BaseModel):
    model_version: str
    test_medape: float
    test_mae: float
    test_rmse: float
    test_within_5pct: float
    test_within_10pct: float
    n_test: int
    baseline_zip_median_medape: float
    baseline_ppsf_medape: float
    zillow_published_medape_reference: float = 4.5
    by_zip: list[dict]
