from datetime import datetime

from pydantic import BaseModel


class MonitorStatsResponse(BaseModel):
    monitor_id: int
    period: str
    uptime_percentage: float | None
    http_avg_response_time_ms: float | None
    ping_avg_response_time_ms: float | None
    total_checks: int
    total_up: int
    total_down: int
    current_status: str | None
    last_checked_at: datetime | None


class UptimeBucket(BaseModel):
    time_start: datetime
    time_end: datetime
    uptime_percentage: float
    total_checks: int
    total_up: int
    total_down: int


class UptimeChartResponse(BaseModel):
    monitor_id: int
    period: str
    bucket: str
    buckets: list[UptimeBucket]
