from typing import Annotated

from fastapi import APIRouter, Query

from app.schemas.route import RouteComputeResponse
from app.services.google_routes import compute_google_route

router = APIRouter(prefix="/api/routes", tags=["routes"])


@router.get("/compute", response_model=RouteComputeResponse)
async def compute_route_endpoint(
    from_placeid: Annotated[str, Query(..., description="Origin place ID")],
    to_placeid: Annotated[str, Query(..., description="Destination place ID")],
    travel_mode: Annotated[str, Query(description="DRIVE, WALK, BICYCLE, TRANSIT, TWO_WHEELER")] = "DRIVE",
    routing_preference: Annotated[
        str,
        Query(description="TRAFFIC_AWARE_OPTIMAL, TRAFFIC_AWARE, TRAFFIC_UNAWARE"),
    ] = "TRAFFIC_AWARE_OPTIMAL",
    language_code: Annotated[str | None, Query(description="Language code (e.g. tr, en)")] = None,
    units: Annotated[str | None, Query(description="METRIC or IMPERIAL")] = None,
) -> RouteComputeResponse:
    payload = await compute_google_route(
        from_placeid=from_placeid,
        to_placeid=to_placeid,
        travel_mode=travel_mode,
        routing_preference=routing_preference,
        language_code=language_code,
        units=units,
    )
    return RouteComputeResponse(**payload)
