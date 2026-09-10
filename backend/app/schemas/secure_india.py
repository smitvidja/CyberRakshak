from typing import Literal

from pydantic import BaseModel


class SecureIndiaSource(BaseModel):
    dataset_id: str
    version: str
    source_type: Literal["SYNTHETIC"]
    source_label: str
    published_at: str
    period_end: str
    methodology: str


class SecureIndiaFilters(BaseModel):
    crime_type: str
    state: str
    city: str
    period: Literal["7d", "30d", "1y"]
    view: Literal["count", "per_lakh"]


class SecureIndiaMetric(BaseModel):
    id: str
    value: float


class SecureIndiaRegion(BaseModel):
    id: str
    city: str
    state: str
    zone: str
    x: float
    y: float
    count: int
    value: float
    trend_percent: int
    bucket: int


class SecureIndiaCrime(BaseModel):
    id: str
    count: int
    share_percent: float
    resource_slug: str


class SecureIndiaLegendBin(BaseModel):
    index: int
    min: float
    max: float | None


class SecureIndiaSummary(BaseModel):
    source: SecureIndiaSource
    filters: SecureIndiaFilters
    available_states: list[str]
    available_cities: list[str]
    metrics: list[SecureIndiaMetric]
    legend: list[SecureIndiaLegendBin]
    map_regions: list[SecureIndiaRegion]
    rankings: list[SecureIndiaRegion]
    hot_zones: list[SecureIndiaRegion]
    hot_crimes: list[SecureIndiaCrime]

