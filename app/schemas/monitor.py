from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class MonitorCreate(BaseModel):
    url: HttpUrl = Field(description="URL to monitor (HTTP or HTTPS)")


class MonitorResponse(BaseModel):
    id: int = Field(description="Unique monitor ID")
    url: str = Field(description="Monitored URL")
    is_active: bool = Field(description="Whether monitoring is active")
    created_at: datetime = Field(description="Creation timestamp (UTC)")
    updated_at: datetime = Field(description="Last update timestamp (UTC)")

    model_config = {"from_attributes": True}
