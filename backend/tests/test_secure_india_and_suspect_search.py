import json
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.public_rate_limit import PublicSearchRateLimiter, suspect_search_rate_limiter
from app.models import ReportedSuspect, SuspectCorrectionRequest, User
from app.models.enums import ReportedSuspectIdentifierType, ReportedSuspectStatus, UserRole
from app.services.reported_suspect_service import normalize_identifier
from app.services.secure_india_service import SecureIndiaService


def _citizen(session: Session) -> User:
    user = User(email=f"search-{uuid4().hex}@example.com", password_hash="not-used", role=UserRole.CITIZEN)
    session.add(user)
    session.commit()
    return user


def test_secure_india_returns_filtered_synthetic_aggregates(api_client: tuple[TestClient, Session]) -> None:
    client, _ = api_client
    response = client.get("/api/v1/secure-india/summary?crime_type=financial&state=Maharashtra&period=7d&view=per_lakh")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["source"]["source_type"] == "SYNTHETIC"
    assert data["source"]["dataset_id"] == "secure-india-synthetic-v1"
    assert {item["state"] for item in data["map_regions"]} == {"Maharashtra"}
    assert data["filters"] == {"crime_type": "financial", "state": "Maharashtra", "city": "all", "period": "7d", "view": "per_lakh"}
    assert response.headers["cache-control"] == "public, max-age=300"


def test_suspect_search_is_exact_normalized_and_verified_only(api_client: tuple[TestClient, Session]) -> None:
    client, session = api_client
    suspect_search_rate_limiter.reset()
    user = _citizen(session)
    normalized = normalize_identifier(ReportedSuspectIdentifierType.PHONE, "98765 43210")
    session.add_all([
        ReportedSuspect(user_id=user.id, identifier_type=ReportedSuspectIdentifierType.PHONE, identifier_value="98765 43210", normalized_identifier=normalized, status=ReportedSuspectStatus.VERIFIED),
        ReportedSuspect(user_id=user.id, identifier_type=ReportedSuspectIdentifierType.PHONE, identifier_value="+91 98765 43210", normalized_identifier=normalized, status=ReportedSuspectStatus.SUBMITTED),
    ])
    session.commit()

    matched = client.post("/api/v1/suspects/search", json={"identifier_type": "PHONE", "identifier_value": "+91-98765-43210"})
    assert matched.status_code == 200
    result = matched.json()["data"]
    assert result["match_state"] == "REPORTED_SIGNAL_FOUND"
    assert result["eligible_report_count"] == 1
    assert result["masked_identifier"].endswith("3210")
    assert "98765" not in str(result)

    no_match = client.post("/api/v1/suspects/search", json={"identifier_type": "PHONE", "identifier_value": "9123456780"})
    assert no_match.status_code == 200
    assert no_match.json()["data"]["match_state"] == "NO_ELIGIBLE_SIGNAL_FOUND"


def test_correction_stores_no_raw_identifier(api_client: tuple[TestClient, Session]) -> None:
    client, session = api_client
    raw = "correction-check@upi"
    response = client.post("/api/v1/suspects/corrections", json={"identifier_type": "UPI", "identifier_value": raw, "reason": "This identifier belongs to me and the signal appears incorrect."})
    assert response.status_code == 201
    correction = session.scalar(select(SuspectCorrectionRequest).where(SuspectCorrectionRequest.id == response.json()["data"]["id"]))
    assert correction is not None
    assert raw not in correction.masked_identifier
    assert raw not in correction.identifier_fingerprint
    assert len(correction.identifier_fingerprint) == 64


def test_public_search_rate_limiter_has_a_controlled_limit() -> None:
    limiter = PublicSearchRateLimiter(limit=2, window_seconds=60)
    limiter.check("192.0.2.10")
    limiter.check("192.0.2.10")
    try:
        limiter.check("192.0.2.10")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 429
        assert getattr(exc, "code", None) == "RATE_LIMITED"
    else:
        raise AssertionError("expected public rate limit")


def test_session_10_1_contracts_are_registered(api_client: tuple[TestClient, Session]) -> None:
    client, _ = api_client
    paths = client.get("/openapi.json").json()["paths"]
    for path in (
        "/api/v1/secure-india/metadata",
        "/api/v1/secure-india/summary",
        "/api/v1/suspects/search",
        "/api/v1/suspects/corrections",
        "/api/v1/admin/suspect-corrections",
        "/api/v1/admin/suspect-corrections/{correction_id}/status",
    ):
        assert path in paths


# --- Secure India aggregate contract (Session 10.1) -------------------------


def test_secure_india_rejects_invalid_filters(api_client: tuple[TestClient, Session]) -> None:
    client, _ = api_client
    for query in (
        "crime_type=not-a-category",
        "state=Atlantis",
        "state=Karnataka&city=Mumbai",  # city must belong to the selected state
        "period=99y",
        "view=per_person",
    ):
        response = client.get("/api/v1/secure-india/summary?" + query)
        assert response.status_code == 422, query
        assert "data" not in response.json() or response.json().get("data") is None


def test_secure_india_legend_bins_agree_with_region_buckets(api_client: tuple[TestClient, Session]) -> None:
    client, _ = api_client
    for query in ("", "?view=per_lakh", "?crime_type=harassment&period=1y"):
        data = client.get("/api/v1/secure-india/summary" + query).json()["data"]
        legend = data["legend"]
        assert [item["index"] for item in legend] == list(range(len(legend)))
        assert legend[-1]["max"] is None, "the top bin must be open ended"
        for region in data["map_regions"]:
            selected_bin = legend[region["bucket"]]
            assert region["value"] >= selected_bin["min"], (query, region)
            if selected_bin["max"] is not None:
                assert region["value"] < selected_bin["max"], (query, region)


def test_secure_india_sections_are_internally_consistent(api_client: tuple[TestClient, Session]) -> None:
    client, _ = api_client
    data = client.get("/api/v1/secure-india/summary?period=1y").json()["data"]
    regions = data["map_regions"]
    metrics = {item["id"]: item["value"] for item in data["metrics"]}

    assert metrics["reports"] == sum(item["count"] for item in regions)
    assert metrics["regions"] == len(regions)
    assert data["rankings"] == regions, "one ordered snapshot drives both surfaces"
    assert data["hot_zones"] == regions[:5]
    assert [item["value"] for item in regions] == sorted((item["value"] for item in regions), reverse=True)
    assert sum(item["count"] for item in data["hot_crimes"]) == metrics["reports"]
    assert abs(sum(item["share_percent"] for item in data["hot_crimes"]) - 100) <= 0.5


def test_secure_india_ranking_order_is_deterministic(api_client: tuple[TestClient, Session]) -> None:
    client, _ = api_client
    first = client.get("/api/v1/secure-india/summary?crime_type=other").json()["data"]["rankings"]
    second = client.get("/api/v1/secure-india/summary?crime_type=other").json()["data"]["rankings"]
    assert [item["id"] for item in first] == [item["id"] for item in second]


def test_secure_india_never_exposes_row_level_or_personal_fields(api_client: tuple[TestClient, Session]) -> None:
    client, _ = api_client
    body = client.get("/api/v1/secure-india/summary").text.casefold()
    for leaked in ("complaint_id", "complaint_number", "user_id", "reporter", "email", "phone", "evidence", "storage_key", "latitude", "longitude"):
        assert leaked not in body, leaked
    allowed = {"id", "city", "state", "zone", "x", "y", "count", "value", "trend_percent", "bucket"}
    assert set(client.get("/api/v1/secure-india/summary").json()["data"]["map_regions"][0]) == allowed


def test_secure_india_projection_and_snapshot_are_valid() -> None:
    from app.services.secure_india_service import _snapshot

    snapshot = _snapshot()
    identifiers = [city["id"] for city in snapshot["cities"]]
    categories = {category["id"] for category in snapshot["categories"]}
    assert len(identifiers) == len(set(identifiers)), "city ids must be unique"

    for city in snapshot["cities"]:
        assert set(city["counts"]) == categories, city["id"]
        assert all(value >= 0 for value in city["counts"].values()), city["id"]
        # per-lakh is only offered because every row carries a real denominator
        assert city["synthetic_population_lakh"] > 0, city["id"]
        assert snapshot["projection"]["lon_min"] <= city["lon"] <= snapshot["projection"]["lon_max"]
        assert snapshot["projection"]["lat_min"] <= city["lat"] <= snapshot["projection"]["lat_max"]

    projection = snapshot["projection"]
    summary = SecureIndiaService.summary()
    assert all(0 <= region.x <= projection["view_box_width"] for region in summary.map_regions)
    assert all(0 <= region.y <= projection["view_box_height"] for region in summary.map_regions)
    kolkata = next(region for region in summary.map_regions if region.id == "kolkata")
    kochi = next(region for region in summary.map_regions if region.id == "kochi")
    mumbai = next(region for region in summary.map_regions if region.id == "mumbai")
    assert kolkata.x > mumbai.x, "eastern city must project to the right of a western one"
    assert kochi.y > mumbai.y, "southern city must project below a northern one"


def _svg_path_to_rings(path: str) -> list[list[tuple[float, float]]]:
    """Parse the M x y L x y ... Z subpaths emitted by the geometry build step."""
    rings: list[list[tuple[float, float]]] = []
    for chunk in path.split("M"):
        chunk = chunk.strip()
        if not chunk:
            continue
        numbers = [float(value) for value in chunk.replace("Z", "").replace("L", " ").split()]
        points = list(zip(numbers[0::2], numbers[1::2]))
        if len(points) >= 3:
            rings.append(points)
    return rings


def _point_in_rings(x: float, y: float, rings: list[list[tuple[float, float]]]) -> bool:
    """Even-odd ray casting, so holes inside a state correctly read as outside."""
    inside = False
    for ring in rings:
        for index in range(len(ring)):
            x1, y1 = ring[index]
            x2, y2 = ring[(index + 1) % len(ring)]
            if (y1 > y) != (y2 > y):
                crossing = x1 + (y - y1) / (y2 - y1) * (x2 - x1)
                if crossing > x:
                    inside = not inside
    return inside


def test_every_city_projects_inside_its_declared_state() -> None:
    """The map must never place a city in the wrong state.

    Guards the exact defect that a national-outline containment check misses: an
    outline can be wrong in shape while still swallowing every marker.
    """
    from app.services.secure_india_service import DATA_PATH, SecureIndiaService

    asset_path = DATA_PATH.resolve().parents[4] / "frontend" / "public" / "data" / "india-states-v1.json"
    assert asset_path.exists(), f"published geometry asset missing at {asset_path}"
    geometry = json.loads(asset_path.read_text(encoding="utf-8"))

    snapshot = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    projection = snapshot["projection"]
    # The asset and the API must share one frame, or every marker is offset.
    assert geometry["view_box"]["width"] == projection["view_box_width"]
    assert geometry["view_box"]["height"] == projection["view_box_height"]

    rings_by_state = {state["name"]: _svg_path_to_rings(state["d"]) for state in geometry["states"]}
    misplaced = []
    for region in SecureIndiaService.summary().map_regions:
        rings = rings_by_state.get(region.state)
        assert rings, f"no published geometry for {region.state}"
        if not _point_in_rings(region.x, region.y, rings):
            elsewhere = [name for name, other in rings_by_state.items() if _point_in_rings(region.x, region.y, other)]
            misplaced.append(f"{region.city} declared {region.state} but plotted in {elsewhere or 'no state'}")
    assert not misplaced, "; ".join(misplaced)


def test_secure_india_per_lakh_uses_the_declared_denominator() -> None:
    from app.services.secure_india_service import _snapshot

    counts = {region.id: region for region in SecureIndiaService.summary(view="count").map_regions}
    rates = {region.id: region for region in SecureIndiaService.summary(view="per_lakh").map_regions}
    populations = {city["id"]: city["synthetic_population_lakh"] for city in _snapshot()["cities"]}

    for identifier, rate_region in rates.items():
        expected = round(counts[identifier].count / populations[identifier], 1)
        assert rate_region.value == expected, identifier
        assert rate_region.count == counts[identifier].count, "the underlying count must not change with the view"
