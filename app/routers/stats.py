from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.check import Check, CheckType, CheckStatus
from app.models.monitor import Monitor
from app.schemas.stats import MonitorStatsResponse

router = APIRouter(prefix="/api/monitors", tags=["stats"])

ALLOWED_PERIODS: dict[str, int] = {"24h": 24, "7d": 168, "30d": 720}


@router.get("/{monitor_id}/stats", response_model=MonitorStatsResponse)
async def get_monitor_stats(
    monitor_id: int,
    period: str = Query(default="24h"),
    db: AsyncSession = Depends(get_db),
):
    """Return uptime and response-time statistics for a monitor."""
    if period not in ALLOWED_PERIODS:
        raise HTTPException(status_code=400, detail="Period must be '24h', '7d', or '30d'")

    monitor = await db.get(Monitor, monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    since = datetime.now(timezone.utc) - timedelta(hours=ALLOWED_PERIODS[period])

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
