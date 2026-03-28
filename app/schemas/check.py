from datetime import datetime

from pydantic import BaseModel, Field


class CheckPairResponse(BaseModel):
    """One row in the check history = an HTTP + ping pair from the same cycle."""

    checked_at: datetime = Field(description="Timestamp of the check cycle (UTC)")
    ping_ms: float | None = Field(description="Ping round-trip time in ms, null if ping failed")
    http_response: str | None = Field(description="HTTP status like '200 OK', null if request failed")
    combined_status: str = Field(description="Overall status: 'up', 'partial', or 'down'")


class PaginatedCheckPairs(BaseModel):
    items: list[CheckPairResponse] = Field(description="Check pairs for the current page")
    total: int = Field(description="Total number of check pairs")
    limit: int = Field(description="Page size")
    offset: int = Field(description="Number of items skipped")
