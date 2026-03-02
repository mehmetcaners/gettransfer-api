from pydantic import BaseModel


class RouteComputeResponse(BaseModel):
    from_placeid: str
    to_placeid: str
    travel_mode: str
    routing_preference: str
    distance_meters: int | None = None
    duration_seconds: int | None = None
    polyline: str | None = None
    route_url: str
