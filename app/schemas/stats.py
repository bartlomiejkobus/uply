from datetime import datetime

from pydantic import BaseModel, Field


class MonitorStatsResponse(BaseModel):
    monitor_id: int
    period: str = Field(description="Time window: '24h', '7d', or '30d'")
    uptime_percentage: float | None = Field(description="Uptime as percentage (0-100), null if no checks")
    http_avg_response_time_ms: float | None = Field(description="Average HTTP response time in ms (UP checks only)")
    ping_avg_response_time_ms: float | None = Field(description="Average ping time in ms (UP checks only)")
    total_checks: int = Field(description="Total HTTP checks in period")
    total_up: int = Field(description="Number of successful checks")
    total_down: int = Field(description="Number of failed checks")
    current_status: str | None = Field(description="Latest HTTP check status: 'up' or 'down'")
    last_checked_at: datetime | None = Field(description="Timestamp of last HTTP check (UTC)")


class UptimeBucket(BaseModel):
    time_start: datetime = Field(description="Bucket start time (UTC)")
    time_end: datetime = Field(description="Bucket end time (UTC)")
    uptime_percentage: float = Field(description="Uptime percentage for this bucket (defaults to 100 if no checks)")
    total_checks: int = Field(description="Number of checks in this bucket")
    total_up: int
    total_down: int


class UptimeChartResponse(BaseModel):
    monitor_id: int
    period: str = Field(description="Time window: '24h', '7d', or '30d'")
    bucket: str = Field(description="Bucket size: '1h', '6h', or '1d'")
    buckets: list[UptimeBucket] = Field(description="Time-series uptime data")


class DashboardMonitor(BaseModel):
    id: int
    url: str
    is_active: bool
    current_status: str | None = Field(description="Latest status: 'up', 'down', or null")
    uptime_24h: float | None = Field(description="24-hour uptime percentage")
    http_avg_response_time_ms: float | None = Field(description="Avg HTTP response time (24h, ms)")
    ping_avg_response_time_ms: float | None = Field(description="Avg ping time (24h, ms)")
    last_checked_at: datetime | None

class DashboardSummaryResponse(BaseModel):
    total_monitors: int = Field(description="Total registered monitors")
    monitors_up: int = Field(description="Monitors with last check UP")
    monitors_down: int = Field(description="Monitors with last check DOWN")
    monitors: list[DashboardMonitor]
