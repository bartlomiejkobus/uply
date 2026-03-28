from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.check import Check, CheckType, CheckStatus
from app.models.monitor import Monitor
from app.schemas.stats import (
    MonitorStatsResponse,
    UptimeBucket,
    UptimeChartResponse,
)

router = APIRouter(prefix="/api/monitors", tags=["stats"])

ALLOWED_PERIODS: dict[str, int] = {"24h": 24, "7d": 168, "30d": 720}
ALLOWED_BUCKETS: dict[str, int] = {"1h": 1, "6h": 6, "1d": 24}


@router.get(
    "/{monitor_id}/stats",
    response_model=MonitorStatsResponse,
    summary="Monitor statistics",
    description="Return uptime percentage, average response times (HTTP and ping), "
    "and current status for a monitor over the given period.",
)
async def get_monitor_stats(
    monitor_id: int,
    period: Literal["24h", "7d", "30d"] = Query(
        default="24h", description="Time window for statistics"
    ),
    db: AsyncSession = Depends(get_db),
):

    monitor = await db.get(Monitor, monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=ALLOWED_PERIODS[period])

    row = (
        await db.execute(
            select(
                func.count()
                .filter(Check.check_type == CheckType.HTTP)
                .label("total"),
                func.count()
                .filter(
                    Check.check_type == CheckType.HTTP,
                    Check.status == CheckStatus.UP,
                )
                .label("total_up"),
                func.avg(Check.response_time_ms)
                .filter(
                    Check.check_type == CheckType.HTTP,
                    Check.status == CheckStatus.UP,
                )
                .label("http_avg"),
                func.avg(Check.response_time_ms)
                .filter(
                    Check.check_type == CheckType.PING,
                    Check.status == CheckStatus.UP,
                )
                .label("ping_avg"),
            ).where(
                Check.monitor_id == monitor_id,
                Check.checked_at >= since,
            )
        )
    ).one()

    total_checks = row.total
    total_up = row.total_up
    total_down = total_checks - total_up

    uptime_percentage = (
        round((total_up / total_checks) * 100, 2) if total_checks > 0 else None
    )
    http_avg = round(row.http_avg, 1) if row.http_avg is not None else None
    ping_avg = round(row.ping_avg, 1) if row.ping_avg is not None else None

    last_check = (
        await db.execute(
            select(Check.status, Check.checked_at)
            .where(Check.monitor_id == monitor_id, Check.check_type == CheckType.HTTP)
            .order_by(Check.checked_at.desc())
            .limit(1)
        )
    ).one_or_none()

    return MonitorStatsResponse(
        monitor_id=monitor_id,
        period=period,
        uptime_percentage=uptime_percentage,
        http_avg_response_time_ms=http_avg,
        ping_avg_response_time_ms=ping_avg,
        total_checks=total_checks,
        total_up=total_up,
        total_down=total_down,
        current_status=last_check.status if last_check else None,
        last_checked_at=last_check.checked_at if last_check else None,
    )


@router.get(
    "/{monitor_id}/stats/uptime-chart",
    response_model=UptimeChartResponse,
    summary="Uptime chart data",
    description="Return uptime percentages grouped into fixed-size time buckets, "
    "suitable for rendering a bar/line chart on the frontend.",
)
async def get_uptime_chart(
    monitor_id: int,
    period: Literal["24h", "7d", "30d"] = Query(
        default="24h", description="Time window for the chart"
    ),
    bucket: Literal["1h", "6h", "1d"] = Query(
        default="1h", description="Size of each time bucket"
    ),
    db: AsyncSession = Depends(get_db),
):

    monitor = await db.get(Monitor, monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    since = now - timedelta(hours=ALLOWED_PERIODS[period])
    bucket_hours = ALLOWED_BUCKETS[bucket]
    bucket_start = since.replace(minute=0, second=0, microsecond=0)
    bucket_delta = timedelta(hours=bucket_hours)

    checks = (
        await db.execute(
            select(Check.checked_at, Check.status).where(
                Check.monitor_id == monitor_id,
                Check.check_type == CheckType.HTTP,
                Check.checked_at >= bucket_start,
                Check.checked_at < now,
            )
        )
    ).all()

    buckets_map: dict[datetime, list[CheckStatus]] = {}
    ts = bucket_start
    while ts < now:
        buckets_map[ts] = []
        ts += bucket_delta

    for checked_at, status in checks:
        slot = bucket_start + bucket_delta * (
            (checked_at - bucket_start) // bucket_delta
        )
        if slot in buckets_map:
            buckets_map[slot].append(status)

    result_buckets = []
    for ts, statuses in buckets_map.items():
        total = len(statuses)
        up = sum(1 for s in statuses if s == CheckStatus.UP)
        result_buckets.append(
            UptimeBucket(
                time_start=ts.replace(tzinfo=timezone.utc),
                time_end=(ts + bucket_delta).replace(tzinfo=timezone.utc),
                uptime_percentage=round((up / total) * 100, 2) if total > 0 else 100.0,
                total_checks=total,
                total_up=up,
                total_down=total - up,
            )
        )

    return UptimeChartResponse(
        monitor_id=monitor_id,
        period=period,
        bucket=bucket,
        buckets=result_buckets,
    )
