from datetime import datetime

from pydantic import BaseModel, HttpUrl


class MonitorCreate(BaseModel):
    url: HttpUrl


class MonitorResponse(BaseModel):
    id: int
    url: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
