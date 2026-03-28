from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.check import Check, CheckType, CheckStatus
from app.models.monitor import Monitor
from app.schemas.stats import DashboardMonitor, DashboardSummaryResponse

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Dashboard summary",
    description="Return a summary of all monitors with their current status, "
    "24-hour uptime percentage, and average response times.",
)
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Monitor))
    monitors = result.scalars().all()

    since_24h = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
    dashboard_monitors = []
    monitors_up = 0
    monitors_down = 0

    for monitor in monitors:
        last_check = (
            await db.execute(
                select(Check.status, Check.checked_at)
                .where(
                    Check.monitor_id == monitor.id,
                    Check.check_type == CheckType.HTTP,
                )
                .order_by(Check.checked_at.desc())
                .limit(1)
            )
        ).one_or_none()

        current_status = last_check.status if last_check else None
        last_checked_at = last_check.checked_at if last_check else None

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
                    Check.monitor_id == monitor.id,
                    Check.checked_at >= since_24h,
                )
            )
        ).one()

        uptime_24h = (
            round((row.total_up / row.total) * 100, 2)
            if row.total > 0
            else None
        )
        http_avg = round(row.http_avg, 1) if row.http_avg is not None else None
        ping_avg = round(row.ping_avg, 1) if row.ping_avg is not None else None

        if current_status == CheckStatus.UP:
            monitors_up += 1
        elif current_status == CheckStatus.DOWN:
            monitors_down += 1

        dashboard_monitors.append(
            DashboardMonitor(
                id=monitor.id,
                url=monitor.url,
                is_active=monitor.is_active,
                current_status=current_status,
                uptime_24h=uptime_24h,
                http_avg_response_time_ms=http_avg,
                ping_avg_response_time_ms=ping_avg,
                last_checked_at=last_checked_at,
            )
        )

    return DashboardSummaryResponse(
        total_monitors=len(monitors),
        monitors_up=monitors_up,
        monitors_down=monitors_down,
        monitors=dashboard_monitors,
    )
