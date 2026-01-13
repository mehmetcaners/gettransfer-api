from pydantic import BaseModel


class PlaceSuggestion(BaseModel):
    place_id: str
    description: str
    main_text: str | None = None
    secondary_text: str | None = None
