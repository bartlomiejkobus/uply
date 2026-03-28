import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.check import Check, CheckType, CheckStatus
from app.schemas.stats import (
    MonitorStatsResponse,
    UptimeBucket,
    UptimeChartResponse,
    DashboardMonitor,
    DashboardSummaryResponse,
)
from app.services import monitor_service

ALLOWED_PERIODS: dict[str, int] = {"24h": 24, "7d": 168, "30d": 720}
ALLOWED_BUCKETS: dict[str, int] = {"1h": 1, "6h": 6, "1d": 24}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _since(period: str) -> datetime:
    return _utcnow() - timedelta(hours=ALLOWED_PERIODS[period])


def _round_or_none(value: float | None, digits: int = 1) -> float | None:
    return round(value, digits) if value is not None else None


def _uptime_pct(up: int, total: int, default: float | None = None) -> float | None:
    return round((up / total) * 100, 2) if total > 0 else default


async def _get_uptime_row(db: AsyncSession, monitor_id: int, since: datetime):
    return (
        await db.execute(
            select(
                func.count().filter(Check.check_type == CheckType.HTTP).label("total"),
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


async def _get_last_http_check(db: AsyncSession, monitor_id: int):
    return (
        await db.execute(
            select(Check.status, Check.checked_at)
            .where(Check.monitor_id == monitor_id, Check.check_type == CheckType.HTTP)
            .order_by(Check.checked_at.desc())
            .limit(1)
        )
    ).one_or_none()


async def get_monitor_stats(
    db: AsyncSession, monitor_id: int, period: str
) -> MonitorStatsResponse:
    since = _since(period)

    row, last_check = await asyncio.gather(
        _get_uptime_row(db, monitor_id, since),
        _get_last_http_check(db, monitor_id),
    )

    return MonitorStatsResponse(
        monitor_id=monitor_id,
        period=period,
        uptime_percentage=_uptime_pct(row.total_up, row.total),
        http_avg_response_time_ms=_round_or_none(row.http_avg),
        ping_avg_response_time_ms=_round_or_none(row.ping_avg),
        total_checks=row.total,
        total_up=row.total_up,
        total_down=row.total - row.total_up,
        current_status=last_check.status if last_check else None,
        last_checked_at=last_check.checked_at if last_check else None,
    )


async def get_uptime_chart(
    db: AsyncSession, monitor_id: int, period: str, bucket: str
) -> UptimeChartResponse:
    now = _utcnow()
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
                uptime_percentage=_uptime_pct(up, total, default=100.0),
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


async def get_dashboard_summary(db: AsyncSession) -> DashboardSummaryResponse:
    monitors = await monitor_service.list_monitors(db)

    since_24h = _utcnow() - timedelta(hours=24)
    dashboard_monitors = []
    monitors_up = 0
    monitors_down = 0

    for monitor in monitors:
        last_check = await _get_last_http_check(db, monitor.id)
        current_status = last_check.status if last_check else None
        last_checked_at = last_check.checked_at if last_check else None

        row = await _get_uptime_row(db, monitor.id, since_24h)

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
                uptime_24h=_uptime_pct(row.total_up, row.total),
                http_avg_response_time_ms=_round_or_none(row.http_avg),
                ping_avg_response_time_ms=_round_or_none(row.ping_avg),
                last_checked_at=last_checked_at,
            )
        )

    return DashboardSummaryResponse(
        total_monitors=len(monitors),
        monitors_up=monitors_up,
        monitors_down=monitors_down,
        monitors=dashboard_monitors,
    )
