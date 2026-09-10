import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from app.core.errors import APIError
from app.schemas.secure_india import SecureIndiaSummary


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "secure_india" / "snapshot.json"
ALLOWED_CRIME_TYPES = {"all", "financial", "commerce", "identity", "harassment", "other"}
ALLOWED_PERIODS = {"7d", "30d", "1y"}
ALLOWED_VIEWS = {"count", "per_lakh"}
LEGEND_BUCKETS = 5


@lru_cache(maxsize=1)
def _snapshot() -> dict[str, Any]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _nice_step(raw: float) -> float:
    """Round a raw bucket width up to a human-readable step (1/2/2.5/5 x 10^n)."""
    if raw <= 0:
        return 1.0
    magnitude = 10 ** math.floor(math.log10(raw))
    for multiple in (1, 2, 2.5, 5, 10):
        if raw <= magnitude * multiple:
            return magnitude * multiple
    return magnitude * 10


class SecureIndiaService:
    @staticmethod
    def metadata() -> dict[str, Any]:
        data = _snapshot()
        return {key: data[key] for key in ("dataset_id", "version", "source_type", "source_label", "published_at", "period_end", "methodology")}

    @staticmethod
    def _project(lon: float, lat: float, projection: dict[str, float]) -> tuple[float, float]:
        """Equirectangular projection into the 0-100 map viewBox used by the UI."""
        x = (lon - projection["lon_min"]) / (projection["lon_max"] - projection["lon_min"]) * 100
        y = (projection["lat_max"] - lat) / (projection["lat_max"] - projection["lat_min"]) * 100
        return round(x, 2), round(y, 2)

    @staticmethod
    def summary(
        *,
        crime_type: str = "all",
        state: str = "all",
        city: str = "all",
        period: Literal["7d", "30d", "1y"] = "30d",
        view: Literal["count", "per_lakh"] = "count",
    ) -> SecureIndiaSummary:
        crime_type = crime_type.casefold()
        if crime_type not in ALLOWED_CRIME_TYPES or period not in ALLOWED_PERIODS or view not in ALLOWED_VIEWS:
            raise APIError(status_code=422, code="INVALID_FILTER", message="One or more Secure India filters are invalid.")

        data = _snapshot()
        projection = data["projection"]
        all_cities = data["cities"]
        available_states = sorted({item["state"] for item in all_cities})
        available_cities = sorted(item["city"] for item in all_cities if state == "all" or item["state"] == state)
        if state != "all" and state not in available_states:
            raise APIError(status_code=422, code="INVALID_FILTER", message="The selected state is not in this dataset.")
        if city != "all" and city not in available_cities:
            raise APIError(status_code=422, code="INVALID_FILTER", message="The selected city is not in the selected state.")

        selected = [item for item in all_cities if (state == "all" or item["state"] == state) and (city == "all" or item["city"] == city)]
        factor = float(data["period_factors"][period])

        def category_count(item: dict[str, Any], category: str = crime_type) -> int:
            base = sum(item["counts"].values()) if category == "all" else item["counts"][category]
            return max(0, round(base * factor))

        def region(item: dict[str, Any]) -> dict[str, Any]:
            count = category_count(item)
            value = count if view == "count" else round(count / item["synthetic_population_lakh"], 1)
            x, y = SecureIndiaService._project(item["lon"], item["lat"], projection)
            return {
                "id": item["id"],
                "city": item["city"],
                "state": item["state"],
                "zone": item["zone"],
                "x": x,
                "y": y,
                "count": count,
                "value": value,
                "trend_percent": item["trend_percent"],
                "bucket": 0,
            }

        regions = [region(item) for item in selected]
        # Deterministic ordering: value first, then city name so ties never reshuffle.
        regions.sort(key=lambda item: (-item["value"], item["city"]))

        # Legend bins and per-region buckets are derived here so the map, the
        # legend and the ranked table can never disagree about a threshold.
        max_value = max((item["value"] for item in regions), default=0.0)
        step = _nice_step(max_value / LEGEND_BUCKETS) if max_value > 0 else 1.0
        legend = [
            {
                "index": index,
                "min": round(step * index, 1),
                "max": round(step * (index + 1), 1) if index < LEGEND_BUCKETS - 1 else None,
            }
            for index in range(LEGEND_BUCKETS)
        ]
        for item in regions:
            item["bucket"] = min(LEGEND_BUCKETS - 1, int(item["value"] // step)) if step > 0 else 0

        total = sum(item["count"] for item in regions)
        crime_totals = []
        for category in data["categories"]:
            count = sum(category_count(item, category["id"]) for item in selected)
            crime_totals.append({"id": category["id"], "count": count, "share_percent": round((count / total * 100) if total else 0, 1), "resource_slug": category["resource_slug"]})
        crime_totals.sort(key=lambda item: (-item["count"], item["id"]))

        rising = sum(1 for item in regions if item["trend_percent"] > 0)
        return SecureIndiaSummary.model_validate({
            "source": SecureIndiaService.metadata(),
            "filters": {"crime_type": crime_type, "state": state, "city": city, "period": period, "view": view},
            "available_states": available_states,
            "available_cities": available_cities,
            "metrics": [
                {"id": "reports", "value": total},
                {"id": "regions", "value": len(regions)},
                {"id": "rising", "value": rising},
                {"id": "categories", "value": len(data["categories"])},
            ],
            "legend": legend,
            "map_regions": regions,
            "rankings": regions,
            "hot_zones": regions[:5],
            "hot_crimes": crime_totals,
        })
