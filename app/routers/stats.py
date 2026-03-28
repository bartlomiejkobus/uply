from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.monitor import Monitor
from app.schemas.stats import MonitorStatsResponse, UptimeChartResponse
from app.services import stats_service
from app.services.monitor_service import get_monitor_or_404

router = APIRouter(prefix="/api/monitors", tags=["stats"])


@router.get(
    "/{monitor_id}/stats",
    response_model=MonitorStatsResponse,
    summary="Monitor statistics",
    description="Return uptime percentage, average response times (HTTP and ping), "
    "and current status for a monitor over the given period.",
)
async def get_monitor_stats(
    monitor: Monitor = Depends(get_monitor_or_404),
    period: Literal["24h", "7d", "30d"] = Query(
        default="24h", description="Time window for statistics"
    ),
    db: AsyncSession = Depends(get_db),
):
    return await stats_service.get_monitor_stats(db, monitor.id, period)


@router.get(
    "/{monitor_id}/stats/uptime-chart",
    response_model=UptimeChartResponse,
    summary="Uptime chart data",
    description="Return uptime percentages grouped into fixed-size time buckets, "
    "suitable for rendering a bar/line chart on the frontend.",
)
async def get_uptime_chart(
    monitor: Monitor = Depends(get_monitor_or_404),
    period: Literal["24h", "7d", "30d"] = Query(
        default="24h", description="Time window for the chart"
    ),
    bucket: Literal["1h", "6h", "1d"] = Query(
        default="1h", description="Size of each time bucket"
    ),
    db: AsyncSession = Depends(get_db),
):
    return await stats_service.get_uptime_chart(db, monitor.id, period, bucket)
