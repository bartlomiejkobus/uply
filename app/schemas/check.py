from datetime import datetime

from pydantic import BaseModel


class CheckPairResponse(BaseModel):
    """One row in the check history = an HTTP + ping pair from the same cycle."""

    checked_at: datetime
    ping_ms: float | None
    http_response: str | None
    combined_status: str


class PaginatedCheckPairs(BaseModel):
    items: list[CheckPairResponse]
    total: int
    limit: int
    offset: int
